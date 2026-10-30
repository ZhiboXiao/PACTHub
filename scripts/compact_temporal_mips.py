"""Quantize website previews and audit their ROI errors against float originals."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from temporal_codec import encode_preview, decode_payload

ROOT = Path(__file__).resolve().parents[1]


def metrics(original, decoded, mask, boxes):
    intensity_errors, trace_errors = [], []
    for x0,y0,x1,y1 in boxes:
        support = mask[y0:y1,x0:x1]
        if support.mean() < .5:
            continue
        before = original[:,y0:y1,x0:x1][:,support].mean(1, dtype='f8')
        after = decoded[:,y0:y1,x0:x1][:,support].mean(1, dtype='f8')
        if np.any(before <= 0):
            continue
        intensity_errors.extend(np.abs(after/before-1)*100)
        trace_errors.extend(np.abs((after/after[0])/(before/before[0])-1)*100)
    def stats(values):
        return dict(readings=len(values), median_pct=float(np.median(values)),
                    p99_pct=float(np.percentile(values,99)), max_pct=float(max(values)))
    return dict(mean_intensity=stats(intensity_errors), relative_trace=stats(trace_errors))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path,required=True);args=ap.parse_args()
    path=ROOT/'data/temporal.json';data=json.loads(path.read_text(encoding='utf-8'));report=[]
    for series in data['series']:
        meta=series['interactive_mips']
        source=ROOT/'assets/data/temporal'/f"{series['id']}.f32.gz"
        original_bytes=source.read_bytes();original,mask=decode_payload(original_bytes)
        packed, compact=encode_preview(original,mask)
        decoded,mask2=decode_payload(packed)
        assert np.array_equal(mask,mask2) and original.shape==decoded.shape
        assert np.max(np.abs(decoded-original)) <= compact['quantization']['maximum_pixel_absolute_error']+1e-12
        defaults=metrics(original,decoded,mask,meta['default_rois_xyxy'])
        rng=np.random.default_rng(20261027);n,h,w=original.shape;random={}
        for width in [4,8,16,32,64]:
            boxes=[]
            for _ in range(200):
                x=int(rng.integers(0,w-width));y=int(rng.integers(0,h-width));boxes.append([x,y,x+width,y+width])
            random[str(width)]=metrics(original,decoded,mask,boxes)
        target=source.with_name(series['id']+'.q8.gz');target.write_bytes(packed)
        meta.update(compact,url=target.relative_to(ROOT).as_posix(),
                    float_source_sha256=hashlib.sha256(original_bytes).hexdigest(),
                    preview_validation=defaults)
        meta['definition']='Registered linear BP MIPs, globally quantized to 8 bits across the complete series; shared-valid mask; decoded linear intensity for ROI means; display window, gamma and annotations excluded.'
        report.append(dict(series=series['id'],original_bytes=len(original_bytes),preview_bytes=len(packed),
                           reduction_pct=100*(1-len(packed)/len(original_bytes)),
                           maximum_pixel_absolute_error=float(np.max(np.abs(decoded-original))),
                           default_rois=defaults,random_square_rois=random,
                           seed=20261027,trials_per_size=200))
        print(series['id'],len(original_bytes),'->',len(packed),'bytes',flush=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
