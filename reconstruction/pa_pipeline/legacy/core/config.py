"""Resolve the CURRENT dataset profile, never guess an original scan trajectory."""
import copy
import hashlib
import json
import re
from pathlib import Path

import numpy as np

def read_json(path):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError('Duplicate JSON key: ' + k)
            d[k] = v
        return d
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def config_path(path):
    path = Path(path)
    return path / 'reconstruction_parameters.json' if path.is_dir() else path


def load_config(path):
    cfg = read_json(config_path(path))
    if cfg.get('schema_version') != '1.0.0':
        raise ValueError('Unsupported sample schema')
    return cfg


def selected_pa(cfg):
    inp = cfg['inputs']
    groups = [g for g in inp['acquisition_groups'] if g['group_id'] == inp['selected_group_id']]
    if len(groups) != 1 or not groups[0].get('pa_file'):
        raise ValueError('A unique selected PA acquisition is required')
    path = Path(groups[0]['pa_file'])
    if str(path) not in inp['pa_files']:
        raise ValueError('Selected PA file is absent from pa_files')
    return path


def frame_offset(formula):
    # Deliberately no eval, and no silently replacing -138.5 with -135.
    match = re.fullmatch(r'-\(i_fr_stat-1\)\*delta_angle([+-]\d+(?:\.\d+)?)',
                         re.sub(r'\s+', '', formula or ''))
    if not match:
        raise ValueError('Unsupported frame angle formula: ' + str(formula))
    return float(match[1])


def require_ready(cfg, check_files=True):
    """Fail closed on missing parameters or requested, unimplemented operations."""
    d, inp = cfg['defaults'], cfg['inputs']
    if not d['reconstruction']['enabled'] or inp['entrypoint'] != 'split_pa_file':
        raise ValueError('No configured PA reconstruction (US-only/unresolved sample)')
    if cfg['validation']['execution_hold'] or cfg['validation']['conflicts']:
        raise ValueError('Sample has a hold or unresolved parameter conflicts')
    for section, keys in {
        'signal': ['sampling_frequency_hz', 'predelay_samples', 'polarity', 'time_samples_1based'],
        'frames': ['indices_1based'],
        'geometry': ['base_z_rotation_deg', 'additional_z_rotation_deg', 'frame_angle_step_parameter_deg'],
        'grid': ['center_mm', 'space_mm', 'resolution_px_mm'],
        'reconstruction': ['single_speed_m_s', 'receive_half_angle_deg', 'angle_compensation'],
    }.items():
        for key in keys:
            if d[section].get(key) is None:
                raise ValueError('Unresolved ' + section + '.' + key)
    for stage in ['fov_detection', 'boundary', 'speed_selection', 'us']:
        if d[stage]['enabled']:
            raise ValueError('Optional stage must run separately with an explicit reviewed profile: ' + stage)
    if d['reconstruction']['mode'] != 'single_speed':
        raise ValueError('This adapter supports current single-speed profiles, not arbitrary dual boundaries')
    if 'scan' in cfg:
        s = cfg['scan']
        if s['stitching'] or s['group_geometry_policy'] != 'selected_group_cached_geometry_only':
            raise ValueError('Unverified scan stitching/geometry is not executable')
        if s['selected_group_id'] != inp['selected_group_id']:
            raise ValueError('Changing scan acquisition requires its own geometry AND frame selection')
    g = d['geometry']
    if (g['coordinate_unit'] != 'mm' or g['detector_axes'] != ['x', 'y', 'z']
            or g['rotation_origin_mm'] != [0, 0, 0] or g['sensor_axis_model'] != 'toward_origin'
            or g['transform_order'] != ['base_Rz', 'frame_Rz', 'additional_Rz']):
        raise ValueError('Unsupported detector coordinate convention')
    frame_offset(g['frame_angle_formula'])
    frames = d['frames']['indices_1based']
    if (d['frames']['mode'] != 'explicit_indices' or len(frames) != d['frames']['count']
            or not frames or len(set(frames)) != len(frames)
            or any(type(f) is not int or f < 1 for f in frames)):
        raise ValueError('Explicit, unique, 1-based frame indices required; gating is not silently rerun')
    s = d['signal']
    if (s['additional_denoising'] or s['bad_channels_1based'] or s['channel_calibration_file']
            or s['channels_1based_range_inclusive'] != [1, 1024]
            or s['crop_stage'] != 'after_filter_and_energy_normalization'
            or s['nan_policy'] != 'replace_with_zero'):
        raise ValueError('Unsupported signal operation; refusing to silently omit it')
    if s['filter']['enabled'] and (s['filter']['kind'] != 'butterworth_bandpass' or not s['filter']['zero_phase']):
        raise ValueError('Only original Butterworth/filtfilt filtering is implemented')
    r = d['reconstruction']
    if r.get('algorithm') == 'xu_wang_2005_ubp':
        expected=dict(distance_weight='solid_angle',time_interpolation='linear',apodization='none',postprocess='signed')
        if any(r.get(key)!=value for key,value in expected.items()):
            raise ValueError('Inconsistent public UBP profile')
    elif r.get('algorithm') is not None:
        raise ValueError('Unknown BP algorithm')
    # Legacy reconstruction options are metadata only. The public adapter writes
    # its actual literature-based choices explicitly before reconstruction.
    required = [selected_pa(cfg)]
    if g.get('detector_xyz_mm') is None:
        if not inp.get('detector_file'):
            raise ValueError('Missing detector coordinates')
        required.append(Path(inp['detector_file']))
    for path in required:
        if check_files and not path.is_file():
            raise FileNotFoundError(path)
    axes(cfg)


def axes(cfg):
    g = cfg['defaults']['grid']
    center, space = np.asarray(g['center_mm'], float), np.asarray(g['space_mm'], float)
    res = float(g['resolution_px_mm'])
    if center.shape != (3,) or space.shape != (3,) or not np.isfinite(np.r_[center, space, res]).all():
        raise ValueError('Invalid grid')
    shape = np.floor(space * res + .5).astype(int)  # MATLAB round for positive lengths.
    sampling = g.get('sampling_rule', 'legacy_round_inclusive')
    if sampling == 'source_intervals_plus_one':
        if not np.allclose(space*res, shape, atol=1e-8, rtol=0):
            raise ValueError('Source grid requires integer FOV*resolution intervals')
        shape += 1
    elif sampling != 'legacy_round_inclusive':
        raise ValueError('Unsupported grid sampling rule: ' + str(sampling))
    if min(space) <= 0 or res <= 0 or min(shape) < 2:
        raise ValueError('Grid must have at least two points on each axis')
    if g.get('shape_xyz') is not None and list(shape) != g['shape_xyz']:
        raise ValueError('Stale grid shape: regenerate derived axes after editing FOV')
    extent = g.get('extent_xyz_mm')
    if extent is not None and not np.allclose(extent, np.c_[center-space/2, center+space/2], atol=2e-5, rtol=0):
        raise ValueError('Stale grid extent after center/FOV edit')
    # Match MATLAB wrapper's single(start) + index * single(spacing).
    return [np.float32(c-s/2) + np.arange(int(n), dtype='f4') * np.float32(s/(n-1))
            for c, s, n in zip(center, space, shape)]


def subset_frames(cfg, ids):
    out = copy.deepcopy(cfg)
    original = cfg['defaults']['frames']['indices_1based']
    if not ids or len(set(ids)) != len(ids) or not set(ids) <= set(original):
        raise ValueError('Input frames must be a nonempty subset of the recorded selected frames')
    out['defaults']['frames']['indices_1based'] = list(ids)
    out['defaults']['frames']['count'] = len(ids)
    return out


def fingerprint(cfg):
    """Physics/frames + PA/detector stat identity; explicitly NOT a full raw-byte checksum."""
    files = []
    paths=[selected_pa(cfg)]
    if cfg['defaults']['geometry'].get('detector_xyz_mm') is None:
        paths.append(Path(cfg['inputs']['detector_file']))
    for p in paths:
        stat = p.stat()
        files.append([str(p), stat.st_size, stat.st_mtime_ns])
    payload = {'defaults': {k: cfg['defaults'][k] for k in
                           ['signal', 'frames', 'geometry', 'grid', 'reconstruction', 'projection']},
               'group': cfg['inputs']['selected_group_id'], 'files': files}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
