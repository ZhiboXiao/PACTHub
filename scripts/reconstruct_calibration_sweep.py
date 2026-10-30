"""Recompute a measured BP speed sweep on the recorded, oriented final FOV.

The source parameter file fixes frames, filtering, detector geometry and FOV.
Only the speed and explicitly recorded preview sampling density vary.
"""
from pathlib import Path
import argparse, copy, hashlib, json, sys, time
import numpy as np

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--parameters', type=Path, required=True)
ap.add_argument('--pa-file', type=Path, required=True)
ap.add_argument('--detector-file', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--density', type=float, default=5.)
args = ap.parse_args()
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'reconstruction'))
from pa_pipeline.legacy.common import prepare_config, reconstruct_prepared
from pa_pipeline.legacy.core.config import axes

args.out.mkdir(parents=True, exist_ok=True)
cfg = json.loads(args.parameters.read_text(encoding='utf-8'))
cfg['inputs']['pa_files'] = [str(args.pa_file.resolve())]
cfg['inputs']['acquisition_groups'][0]['pa_file'] = str(args.pa_file.resolve())
cfg['inputs']['detector_file'] = str(args.detector_file.resolve())
d = cfg['defaults']
d['grid']['resolution_px_mm'] = args.density
for key in ['shape_xyz', 'actual_spacing_mm', 'extent_xyz_mm']:
    d['grid'].pop(key, None)
d['projection'].update(z_policy='full_grid')
speeds = np.arange(1488, 1499.01, .5)
d['reconstruction']['sweep_m_s'] = speeds.tolist()
cfg['provenance']['video_sweep'] = dict(source_parameters_sha256=hashlib.sha256(args.parameters.read_bytes()).hexdigest(),
    physical_FOV='Recorded standard reconstruction FOV, including its centre and Z rotation',
    sampling_density_px_mm=args.density)
text = json.dumps(cfg, indent=2)
param = args.out/'parameters.json'
if param.exists():
    assert param.read_text(encoding='utf-8') == text, 'Existing cache parameters differ'
else:
    param.write_text(text, encoding='utf-8')
start = time.perf_counter()
prepared = prepare_config(cfg)
print('PREPARED', prepared.data_ct.shape, 'SECONDS', time.perf_counter()-start, flush=True)
images = []
records = []
for speed in speeds:
    path = args.out/f'speed_{speed:.1f}.npz'
    if not path.exists():
        prepared.parameters['defaults']['reconstruction']['single_speed_m_s'] = float(speed)
        began = time.perf_counter()
        result = reconstruct_prepared(prepared, backend='cuda')
        seconds = time.perf_counter()-began
        np.savez_compressed(path, xy=result.mip_yx, seconds=seconds)
        print('SPEED', speed, 'SECONDS', seconds, flush=True)
    cache = np.load(path)
    images.append(cache['xy'])
    records.append(dict(speed_m_s=float(speed), seconds=float(cache['seconds'])))
xyz = axes(cfg)
np.savez_compressed(args.out/'mips.npz', xy=np.stack(images), speeds=speeds,
                    **{'axis_'+a:v for a,v in zip('xyz',xyz)})
(args.out/'result.json').write_text(json.dumps(dict(status='complete',device='Local NVIDIA RTX 4080',
    rows=records,seconds=time.perf_counter()-start),indent=2),encoding='utf-8')
print('COMPLETE', args.out, flush=True)
