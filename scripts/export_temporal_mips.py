"""Export compact display-oriented linear MIPs for browser ROI measurements.

The common valid mask excludes registration borders consistently at every time.
Source NPZ files are produced by register_temporal.py; no intensity transform is
applied before one shared 8-bit quantization. Annotated images are rendered separately.
"""
from pathlib import Path
import argparse, gzip, hashlib, json, struct
import numpy as np
from PIL import Image
from display_utils import scale_bar
from temporal_codec import encode_preview

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def display_order(array, series):
    result = array[..., ::-1, :]
    if series.get('display_rotation_deg') == 180:
        result = result[..., ::-1, ::-1]
    if series.get('display_flip_y'):
        result = result[..., ::-1, :]
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--registered-dir', type=Path, required=True)
    ap.add_argument('--flip-abdominal', action='store_true')
    args = ap.parse_args()
    path = ROOT / 'data/temporal.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    out = ROOT / 'assets/data/temporal'
    out.mkdir(parents=True, exist_ok=True)
    for series in data['series']:
        source = args.registered_dir / (series['id'] + '_registered.npz')
        with np.load(source) as z:
            registered = z['registered'].astype('f4')
            common = z['common_valid'].astype(bool)
            x, y = z['x'], z['y']
        X, Y = np.meshgrid(x, y)
        assert np.isfinite(registered).all()
        # Check against all previously published means before changing presentation.
        for roi in series['regions']:
            x0, x1, y0, y1 = roi['bounds_xy_mm']
            mask = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & common
            means = registered[:, mask].mean(1, dtype='f8')
            assert np.allclose(means, roi['mean_linear'], rtol=1e-12, atol=1e-12)
        if args.flip_abdominal and series['id'] == 'abdominal':
            series['display_flip_y'] = True
        pixels = np.ascontiguousarray(display_order(registered, series), dtype='<f4')
        valid = np.ascontiguousarray(display_order(common, series), dtype='u1')
        dx, dy = display_order(X, series)[0], display_order(Y, series)[:, 0]
        n, h, w = pixels.shape
        packed, codec = encode_preview(pixels, valid)
        target = out / (series['id'] + '.q8.gz')
        target.write_bytes(packed)
        defaults = []
        for roi in series['regions'][:2]:
            a, b, c, d = roi['bounds_xy_mm']
            rows, cols = np.where((display_order(X, series) >= a) & (display_order(X, series) <= b) &
                                  (display_order(Y, series) >= c) & (display_order(Y, series) <= d))
            defaults.append([int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1])
        series['interactive_mips'] = dict(
            **codec, url=target.relative_to(ROOT).as_posix(), registered_source_sha256=digest(source),
            display_axis_edges_mm=dict(x=[float(dx[0] - (dx[1]-dx[0])/2), float(dx[-1] + (dx[1]-dx[0])/2)],
                                       y=[float(dy[0] - (dy[1]-dy[0])/2), float(dy[-1] + (dy[1]-dy[0])/2)]),
            default_rois_xyxy=defaults, frame_order=[f['acquisition_id'] for f in series['frames']],
            common_valid_pixels=int(valid.sum()), includes_scale_bar=False,
            definition='Registered linear BP MIPs in displayed XY order, globally quantized to 8 bits across all timepoints; fixed shared-valid mask; no display window, gamma, or annotations in numerical data.',
        )
        if series['id'] == 'abdominal' and args.flip_abdominal:
            for im, frame in zip(pixels, series['frames']):
                screen = np.uint8(np.rint(np.clip(im / series['display_window'][1], 0, 1) * 255))
                annotated, bar = scale_bar(Image.fromarray(screen), 1 / abs(float(np.median(np.diff(x)))), 5, font_fraction=.06)
                annotated.save(ROOT / frame['image'], lossless=True, method=6)
            series['scale_bar'] = bar
        print(series['id'], pixels.shape, target.stat().st_size, 'bytes; original means verified', flush=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
