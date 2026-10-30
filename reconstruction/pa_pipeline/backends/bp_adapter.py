"""PAdata/JSON adapter for the literature UBP; no reconstruction equations here."""
import copy
import numpy as np
from .literature_ubp import ubp_volume, implementation_record

PUBLIC_ALGORITHM = 'xu_wang_2005_ubp'
EFFECTIVE_OPTIONS = dict(algorithm=PUBLIC_ALGORITHM, time_interpolation='linear',
                        distance_weight='solid_angle', apodization='none',
                        receive_half_angle_deg=90.0, angle_compensation=True,
                        postprocess='signed', normalization='sum_geometric_solid_angles')


def public_profile(cfg):
    """Keep source JSON untouched; make the actual public baseline explicit."""
    result = copy.deepcopy(cfg)
    recon = result['defaults']['reconstruction']
    if recon.get('algorithm') not in (None, PUBLIC_ALGORITHM):
        raise ValueError('Unsupported reconstruction algorithm: '+str(recon['algorithm']))
    if recon.get('algorithm') != PUBLIC_ALGORITHM:
        result['public_bp_adapter'] = dict(
            source='10.1103/PhysRevE.71.016706, Eqs. (20)-(22)',
            source_options_replaced={k:recon.get(k) for k in EFFECTIVE_OPTIONS if k in recon},
            effective_options=EFFECTIVE_OPTIONS,
            time_axis_convention='processed_sample_k_time_s=(k+1+predelay_samples)/sampling_frequency_hz',
            signal_domain='band-limited measured PA signal; no detector impulse-response inversion',
            surface_quadrature='equal area cells; available solid-angle normalization')
    recon.update(EFFECTIVE_OPTIONS)
    return result


def physical_time_axis(cfg, samples):
    """Dataset clock convention. Cropping is already included in predelay."""
    signal = cfg['defaults']['signal']
    return (np.arange(samples, dtype=np.float64)+1+float(signal['predelay_samples']))/float(signal['sampling_frequency_hz'])


def reconstruct(data, sensors, cfg, backend='cuda', speed=None, volume_sink=None, normals=None):
    from ..legacy.core.config import axes
    cfg = public_profile(cfg)
    if cfg['defaults']['signal']['analytic_signal'] or np.iscomplexobj(data):
        raise ValueError('Literature UBP requires real signed PA data; set analytic_signal=false in the JSON')
    if normals is None:
        if cfg['defaults']['geometry']['sensor_axis_model'] != 'toward_origin':
            raise ValueError('Provide surface normals for this geometry')
        direction = -np.asarray(sensors, dtype=np.float64)
        length = np.linalg.norm(direction, axis=1, keepdims=True)
        if np.any(length == 0):raise ValueError('An origin detector has no radial surface normal')
        normals = direction/length
    ax = axes(cfg)
    chosen_speed = cfg['defaults']['reconstruction']['single_speed_m_s'] if speed is None else speed
    progress_bucket=[-1]
    def progress(done,total):
        bucket=10*done//total
        if total>=1_000_000 and bucket>progress_bucket[0]:
            print('UBP',round(100*done/total,1),'percent',flush=True);progress_bucket[0]=bucket
    volume = ubp_volume(data, physical_time_axis(cfg, data.shape[1]), sensors, normals, ax,
                        sound_speed_m_s=chosen_speed, backend=backend,progress=progress)
    if volume_sink is not None: volume_sink[:] = volume
    projection = cfg['defaults']['projection']
    if projection['plane'] != 'xy' or projection['method'] != 'maximum':
        raise ValueError('The dataset adapter exports XY maximum projections')
    policy = projection['z_policy']
    if policy == 'full_grid': keep = np.ones(len(ax[2]), dtype=bool)
    elif policy == 'index_range':
        lo, hi = projection['z_indices_1based_inclusive']
        if not 1 <= lo <= hi <= len(ax[2]):raise ValueError('Invalid projection Z range')
        keep = (np.arange(len(ax[2])) >= lo-1) & (np.arange(len(ax[2])) < hi)
    elif policy == 'physical_range':
        lo, hi = projection['z_range_mm']; keep = (ax[2] >= lo) & (ax[2] <= hi)
    else: raise ValueError('Unsupported projection Z policy')
    if not np.any(keep):raise ValueError('Projection Z support is empty')
    return volume[keep].max(axis=0), ax
