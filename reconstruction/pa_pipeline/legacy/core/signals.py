"""Read unified PA without repeating board mapping, /16 or per-channel flips."""
import time

import h5py
import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, filtfilt, hilbert

from .config import frame_offset, require_ready, selected_pa


def rz(degrees):
    t = np.deg2rad(degrees)
    c, s = np.cos(t), np.sin(t)
    # Match MATLAB cosd/sind at quadrantal angles.
    if degrees % 90 == 0:
        c, s = round(c), round(s)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype='f8')


def pa_shape(path):
    if h5py.is_hdf5(path):
        with h5py.File(path) as h:
            shape = h['pa_data'].shape
            if len(shape) != 3 or shape[2] != 1024:
                raise ValueError('Expected MATLAB v7.3 [frame,time,channel] storage')
            return shape[2], shape[1], shape[0]
    a = loadmat(path, variable_names=['pa_data'])['pa_data']
    return (*a.shape, 1) if a.ndim == 2 else a.shape


def read_frames(path, ids):
    """Yield (original_PA_index, time x channel), with one open handle per worker."""
    if h5py.is_hdf5(path):
        with h5py.File(path) as h:
            ds = h['pa_data']
            if len(ds.shape) != 3 or ds.shape[2] != 1024 or max(ids) > ds.shape[0]:
                raise ValueError('PA shape/index mismatch')
            if len(ids) > 1 and ds.chunks and ds.chunks[0] > 1:
                # MATLAB files pack ALL frames into each tiny time/channel chunk.
                # Reading each frame separately repeatedly inflates the whole file.
                # Decode once in bounded time blocks, retaining only selected frames.
                selected = np.empty((len(ids), ds.shape[1], ds.shape[2]), dtype=ds.dtype)
                indices = np.asarray(ids)-1
                for t in range(0, ds.shape[1], 256):
                    selected[:,t:t+256,:] = ds[:,t:t+256,:][indices]
                for j,i in enumerate(ids):
                    yield i, np.asarray(selected[j], dtype='f8')
                return
            for i in ids:
                yield i, np.asarray(ds[i-1], dtype='f8')
    else:
        a = loadmat(path, variable_names=['pa_data'])['pa_data']
        if a.ndim == 2:
            a = a[:, :, None]
        if a.shape[0] != 1024 or max(ids) > a.shape[2]:
            raise ValueError('PA shape/index mismatch')
        for i in ids:
            yield i, np.asarray(a[:, :, i-1].T, dtype='f8')


def detector_positions(cfg, ids, apply_additional=True):
    g = cfg['defaults']['geometry']
    path = cfg['inputs']['detector_file']
    if g.get('detector_xyz_mm') is not None:
        detector = np.asarray(g['detector_xyz_mm'], dtype='f8')
    elif h5py.is_hdf5(path):
        with h5py.File(path) as h:
            detector = h['detector'][:].T.astype('f8')
    else:
        detector = np.asarray(loadmat(path)['detector'], dtype='f8')
    if detector.shape != (1024, 3) or not np.isfinite(detector).all():
        raise ValueError('Expected 1024 x 3 finite detector coordinates')
    offset = np.asarray(g.get('base_coordinate_offset_mm', [0, 0, 0]), dtype='f8')
    if offset.shape != (3,) or not np.isfinite(offset).all():
        raise ValueError('Invalid detector offset')
    detector = (detector + offset) * np.asarray(g['detector_axis_signs'])
    detector = detector @ rz(g['base_z_rotation_deg']).T
    base_precision = g.get('base_coordinate_dtype', 'float64')
    if base_precision not in ['float32', 'float64']:
        raise ValueError('Unsupported base-coordinate precision')
    detector = detector.astype(base_precision)
    out = []
    for i in ids:
        angle = -(i-1)*g['frame_angle_step_parameter_deg'] + frame_offset(g['frame_angle_formula'])
        additional = g['additional_z_rotation_deg'] if apply_additional else 0.
        if base_precision == 'float32':
            rotated = detector @ rz(angle).astype('f4').T
            if additional != 0:
                rotated = rotated @ rz(additional).astype('f4').T
            out.append(rotated)
        else:
            out.append((detector @ rz(angle).T) @ rz(additional).T)
    return np.stack(out)  # frame, channel, xyz; keep original indices.


def filter_coefficients(cfg):
    s = cfg['defaults']['signal']
    f = s['filter']
    if not f['enabled']:
        return np.array([1.]), np.array([1.])
    return butter(f['order_argument'], np.asarray(f['band_hz'])/(s['sampling_frequency_hz']/2), btype='bandpass')


def preprocess_frame(raw_tc, cfg, coefficients=None):
    s = cfg['defaults']['signal']
    e = s['energy_normalization']
    energy = 1.
    if e['enabled']:
        if e['method'] != 'max_over_time_of_channel_mean':
            raise ValueError('Unsupported energy method')
        lo, hi = e['window_samples_1based']
        if not 1 <= lo <= hi <= len(raw_tc):
            raise ValueError('Invalid energy window')
        energy = float(np.max(np.mean(raw_tc[lo-1:hi], axis=1)))
        if not np.isfinite(energy) or energy == 0:
            raise ValueError('Zero/nonfinite pulse energy: do not fabricate normalization')
    if s['filter']['enabled']:
        b, a = coefficients if coefficients is not None else filter_coefficients(cfg)
        # MATLAB filtfilt's classic odd extension: 3*(max(len(a),len(b))-1).
        filtered = filtfilt(b, a, raw_tc, axis=0, padtype='odd', padlen=3*(max(len(a), len(b))-1))
    else:
        filtered = raw_tc.copy()
    filtered *= s['polarity']
    filtered[np.isnan(filtered)] = 0
    filtered = e['signal_scale'] * filtered / energy  # scale remains when norm disabled.
    lo, hi = s['time_samples_1based']
    if not 1 <= lo <= hi <= len(filtered):
        raise ValueError('Invalid time crop')
    filtered = filtered[lo-1:hi]
    if s['analytic_signal']:
        filtered = hilbert(filtered, axis=0)
    if not np.isfinite(filtered).all():
        raise ValueError('Nonfinite preprocessed signal')
    return filtered, energy


def prepare(cfg):
    require_ready(cfg)
    started = time.perf_counter()
    ids = cfg['defaults']['frames']['indices_1based']
    lo, hi = cfg['defaults']['signal']['time_samples_1based']
    dtype = 'complex64' if cfg['defaults']['signal']['analytic_signal'] else 'float32'
    data = np.empty((len(ids)*1024, hi-lo+1), dtype=dtype)
    coeffs = filter_coefficients(cfg)
    energies, io_s, filter_s = [], 0., 0.
    iterator = iter(read_frames(selected_pa(cfg), ids))
    for j in range(len(ids)):
        tick = time.perf_counter(); _, raw = next(iterator); io_s += time.perf_counter()-tick
        tick = time.perf_counter(); processed, e = preprocess_frame(raw, cfg, coeffs)
        data[j*1024:(j+1)*1024] = processed.T
        energies.append(e); filter_s += time.perf_counter()-tick
    tick = time.perf_counter()
    sensors = detector_positions(cfg, ids).reshape(-1, 3).astype('f4')
    timing = dict(pa_read_s=io_s, filter_energy_crop_s=filter_s,
                  geometry_s=time.perf_counter()-tick, prepare_total_s=time.perf_counter()-started)
    return data, sensors, np.asarray(energies), timing
