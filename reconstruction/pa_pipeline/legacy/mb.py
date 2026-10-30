"""Reference-free MB reconstruction from the same standard RF and geometry as BP.

The shared branch uses crop -> matched FIR -> optional support projection.
It deliberately records this separately from the legacy BP Butterworth branch.
Torch and the CUDA compiler are loaded only when reconstruction is requested.
"""
from dataclasses import asdict, dataclass
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.signal import fftconvolve, firwin
from .common import PreparedPA, Reconstruction, json_save, sample_config, save_result, reconstruct_prepared
from .core.config import axes, fingerprint, subset_frames
from .normal import prepare_normal


@dataclass(frozen=True)
class MBOptions:
    sensor_radius_mm: float
    radial_order: int = 3
    angular_order: int = 16
    fir_order: int = 128
    fir_beta: float = 8.0
    mask_first_samples: int = 0
    matched_channel_demean: bool = False
    iterations: int = 5
    power_iterations: int = 2
    l1_relative: float = 0.02
    tv_relative: float = 0.005
    l2_relative: float = 0.003
    sensor_batch_size: int = 1024

    def validate(self):
        for key in ('radial_order', 'angular_order', 'iterations', 'power_iterations', 'sensor_batch_size'):
            value = getattr(self, key)
            if type(value) is not int or value < 1:
                raise ValueError(key + ' must be a positive integer')
        if type(self.mask_first_samples) is not int or self.mask_first_samples < 0:
            raise ValueError('mask_first_samples must be a nonnegative integer')
        if type(self.fir_order) is not int or self.fir_order < 2 or self.fir_order % 2:
            raise ValueError('fir_order must be a positive even integer')
        for key in ('sensor_radius_mm', 'fir_beta', 'l1_relative', 'tv_relative', 'l2_relative'):
            value = getattr(self, key)
            if not np.isfinite(value) or value < 0:
                raise ValueError(key + ' must be finite and nonnegative')


@dataclass
class PreparedMB:
    shared: PreparedPA
    kernel: np.ndarray
    mask_ct: np.ndarray
    options: MBOptions
    source_parameters: dict


def array_sha256(value):
    a = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def matched_kernel(cfg, options):
    f = cfg['defaults']['signal']['filter']
    if not f['enabled']:
        return np.ones(1, dtype='f4')
    fs = float(cfg['defaults']['signal']['sampling_frequency_hz'])
    band = np.asarray(f['band_hz'], dtype=float)
    if band.shape != (2,) or not 0 < band[0] < band[1] < fs / 2:
        raise ValueError('Invalid source band for matched FIR')
    kernel = firwin(options.fir_order + 1, band, pass_zero=False, fs=fs,
                    window=('kaiser', options.fir_beta), scale=False)
    kernel /= np.max(np.abs(np.fft.fft(kernel, 4096)))
    return kernel.astype('f4')


def apply_shared_temporal(data_ct, kernel, mask_ct, demean=False):
    """Finite linear convolution with a centered origin, then support projection."""
    if np.iscomplexobj(data_ct):
        raise ValueError('MB requires real RF, not an analytic signal')
    zero = (len(kernel) - 1) // 2
    filtered = fftconvolve(data_ct, kernel[None, :], mode='full', axes=1)
    filtered = filtered[:, zero:zero + data_ct.shape[1]].astype('f4')
    filtered *= mask_ct
    if demean:
        counts = np.maximum(mask_ct.sum(axis=1, keepdims=True), 1)
        means = filtered.sum(axis=1, keepdims=True, dtype='f8') / counts
        filtered = ((filtered - means) * mask_ct).astype('f4')
    return np.ascontiguousarray(filtered)


def prepare_mb(sample, *, options, frames=None):
    options.validate()
    source = sample_config(sample)
    if 'mb_preprocessing' in source:
        raise ValueError('Use profile/reconstruction_parameters.json to replay MB; effective parameters describe already processed RF')
    if frames is not None:
        source = subset_frames(source, frames)
    signal = source['defaults']['signal']
    if signal['analytic_signal']:
        raise ValueError('MB requires real RF; analytic_signal must be false')
    projection = source['defaults']['projection']
    if projection['plane'] != 'xy' or projection['method'] != 'maximum' or projection['z_policy'] != 'full_grid':
        raise ValueError('Initial MB adapter requires full-grid XY maximum projection')
    kernel = matched_kernel(source, options)
    base = copy.deepcopy(source)
    base['defaults']['signal']['filter']['enabled'] = False
    prepared = prepare_normal(base)
    if options.mask_first_samples >= prepared.data_ct.shape[1]:
        raise ValueError('Time mask removes the entire signal')
    started = time.perf_counter()
    mask = np.ones_like(prepared.data_ct, dtype='f4')
    mask[:, :options.mask_first_samples] = 0
    prepared.data_ct = apply_shared_temporal(prepared.data_ct, kernel, mask, options.matched_channel_demean)
    prepared.parameters['mb_preprocessing'] = dict(
        schema='pa.mb.shared/1.0', source_filter=copy.deepcopy(signal['filter']),
        order=['raw_energy_estimate', 'global_polarity_and_energy_scale', 'source_time_crop', 'matched_FIR', 'support_projection'],
        fir_boundary='zero_extension_linear_convolution', fir_zero_index_1based=(len(kernel)+1)//2,
        fir_coefficients=kernel.tolist(), fir_sha256=array_sha256(kernel),
        mask_first_samples=options.mask_first_samples, matched_channel_demean=options.matched_channel_demean,
        predelay_policy='use_recorded_cropped_signal_clock_without_implicit_shift',
        data_ct_sha256=array_sha256(prepared.data_ct), sensor_xyz_sha256=array_sha256(prepared.sensor_xyz_mm),
        raw_and_detector_stat_fingerprint=fingerprint(source),
        fingerprint_scope='configuration_and_file_stats_not_full_raw_content',
        source_replay_file='../profile/reconstruction_parameters.json')
    prepared.timing['shared_fir_mask_s'] = time.perf_counter() - started
    return PreparedMB(prepared, kernel, mask, options, source)


def disk_quadrature(sensors, radius, radial_order, angular_order, normals=None):
    """Area-normalized disk quadrature, normals pointing toward the origin."""
    sensors = np.asarray(sensors, dtype='f8')
    distances = np.linalg.norm(sensors, axis=1)
    if np.any(distances == 0) or not np.isfinite(sensors).all():
        raise ValueError('Disk orientation requires finite, nonzero sensor positions')
    normal = -sensors / distances[:, None] if normals is None else np.asarray(normals,dtype='f8')
    if normal.shape!=sensors.shape or not np.allclose(np.linalg.norm(normal,axis=1),1,atol=2e-5):
        raise ValueError('Invalid disk normals')
    reference = np.tile([0., 0., 1.], (len(sensors), 1))
    reference[np.abs(normal[:, 2]) > .9] = [0., 1., 0.]
    u = np.cross(normal, reference); u /= np.linalg.norm(u, axis=1)[:, None]
    v = np.cross(normal, u)
    nodes, weights = np.polynomial.legendre.leggauss(radial_order)
    r = radius * np.sqrt((nodes + 1) / 2)
    theta = np.arange(angular_order) * (2 * np.pi / angular_order)
    positions = (r[:, None, None, None] *
                 (np.cos(theta)[None, :, None, None] * u[None, None, :, :] +
                  np.sin(theta)[None, :, None, None] * v[None, None, :, :]))
    offsets = positions.reshape(-1, len(sensors), 3).transpose(2, 0, 1)
    weights = np.repeat(weights / (2 * angular_order), angular_order)
    return np.ascontiguousarray(offsets, dtype='f4'), weights.astype('f4')


def build_inputs(prepared, device):
    import torch
    if not isinstance(prepared, PreparedMB):
        raise TypeError('Expected PreparedMB from prepare_mb')
    p = prepared.shared; cfg = p.parameters; options = prepared.options
    ax = axes(cfg)
    expected = (cfg['defaults']['frames']['count'] * 1024,
                cfg['defaults']['signal']['time_samples_1based'][1] - cfg['defaults']['signal']['time_samples_1based'][0] + 1)
    if p.data_ct.shape != expected or p.sensor_xyz_mm.shape != (expected[0], 3):
        raise ValueError('Prepared RF/geometry dimensions disagree with parameters')
    if (prepared.mask_ct.shape != expected or not np.isfinite(p.data_ct).all()
            or not np.all((prepared.mask_ct == 0) | (prepared.mask_ct == 1))):
        raise ValueError('Invalid prepared data or binary mask')
    offsets, weights = disk_quadrature(p.sensor_xyz_mm, options.sensor_radius_mm, options.radial_order, options.angular_order, p.sensor_axis_xyz)
    # Same float32 start and spacing construction as core.config.axes / BP.
    space = cfg['defaults']['grid']['space_mm']
    inputs = dict(sensors=p.sensor_xyz_mm.T.copy(), offsets=offsets, weights=weights,
        filtered_data=p.data_ct.T.copy(), data_mask=prepared.mask_ct.T.copy(), kernel=prepared.kernel,
        zero_index=(len(prepared.kernel)+1)//2, grid_size=np.array([len(a) for a in ax], dtype='i4'),
        grid_origin=np.array([a[0] for a in ax], dtype='f4'),
        grid_spacing=np.array([s/(len(a)-1) for s, a in zip(space, ax)], dtype='f4'),
        num_samples=expected[1], fs_mhz=cfg['defaults']['signal']['sampling_frequency_hz']/1e6,
        predelay_samples=cfg['defaults']['signal']['predelay_samples'],
        sound_speed_mps=cfg['defaults']['reconstruction']['single_speed_m_s'],
        sensor_radius_mm=options.sensor_radius_mm, matched_channel_demean=options.matched_channel_demean)
    for key in ('sensors', 'offsets', 'weights', 'filtered_data', 'data_mask', 'kernel'):
        inputs[key+'_gpu'] = torch.from_numpy(np.ascontiguousarray(inputs[key], dtype='f4')).to(device)
    return inputs


def reconstruct_mb_prepared(prepared, *, device=0, return_volume=True):
    import torch
    from .mb_backend.runtime import load_projector, solve
    from .mb_backend.operator import ExactV3Operator
    options = prepared.options; options.validate()
    device = torch.device(f'cuda:{device}' if isinstance(device, int) else device)
    if device.type != 'cuda' or not torch.cuda.is_available():
        raise RuntimeError('MB requires a working PyTorch CUDA runtime')
    started = time.perf_counter()
    with torch.cuda.device(device), torch.no_grad():
        inputs = build_inputs(prepared, device)
        projector = load_projector(device)
        op = ExactV3Operator(projector, inputs, sensor_batch_size=options.sensor_batch_size)
        volume, summary = solve(op, inputs['filtered_data_gpu'], options)
        torch.cuda.synchronize(device)
        array = volume.cpu().numpy()
    p = prepared.shared
    cfg = copy.deepcopy(p.parameters)
    cfg['actual_reconstruction'] = dict(method='MB', backend='torch_cuda_v3', options=asdict(options),
        propagation='homogeneous_single_speed', spatial_model='finite_disk_quadrature',
        objective='0.5*||Ax-b||_2^2 + lambda_L1*||x||_1 + lambda_TV*TV(x) + 0.5*lambda_L2*||x||_2^2; x>=0',
        tv_convention='forward_voxel_differences_without_spacing_division',
        amplitude='solver_input_L2_normalization_reversed; operator_units_not_calibrated_Pa',
        legacy_BP_weighting_fields_applied=False)
    timing = dict(p.timing, mb_with_compile_transfer_s=time.perf_counter()-started)
    result = Reconstruction(array.max(axis=0), axes(cfg), cfg, timing, array if return_volume else None)
    summary.update(torch_version=torch.__version__, cuda_version=torch.version.cuda,
                   gpu_name=torch.cuda.get_device_name(device), device=str(device))
    return result, summary
