"""Apply the established, temporally fixed display masks to the motion film."""
from pathlib import Path
import argparse, hashlib, json, subprocess
import cv2, numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--masks',type=Path,required=True)
    parser.add_argument('--qa-dir',type=Path,required=True);args=parser.parse_args()
    args.qa_dir.mkdir(parents=True,exist_ok=True)
    with np.load(args.masks) as z:masks=[z['movie_gray'].copy(),z['movie_depth'].copy()]
    source=ROOT/'assets/media/hero-pact.mp4';movie=ROOT/'assets/media/overview-motion-cutout.mp4'
    poster=ROOT/'assets/images/showcase/overview-motion-cutout.webp'
    capture=cv2.VideoCapture(str(source));fps=capture.get(cv2.CAP_PROP_FPS);count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    w=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    assert (w,h)==(856,870)
    assert masks[0].shape==(870,428) and masks[1].shape==(870,386)
    proc=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','856x870','-r',str(fps),'-i','-','-an','-c:v','libx264','-crf','17','-preset','fast','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE)
    max_exterior=0
    try:
        for i in range(count):
            ok,bgr=capture.read();assert ok
            raw=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB);out=np.zeros_like(raw)
            out[:,:428]=np.uint8(np.rint(raw[:,:428].astype('f4')*masks[0][...,None]))
            rgb=np.maximum(raw[:,470:].astype('f4')-[12,10,0],0)
            out[:,470:]=np.uint8(np.rint(rgb*masks[1][...,None]))
            max_exterior=max(max_exterior,int(out[:,470:][masks[1]==0].max()))
            proc.stdin.write(out.tobytes())
            if i==0:
                Image.fromarray(out).save(poster,lossless=True)
                Image.fromarray(np.hstack([raw,out])).save(args.qa_dir/'motion-cutout-comparison.png')
            if i in [0,count//2,count-1]:Image.fromarray(out).save(args.qa_dir/f'motion-cutout-{i:03d}.png')
        proc.stdin.close();assert proc.wait()==0
    finally:
        capture.release()
        if proc.poll() is None:proc.kill()
    record=dict(source=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
        mask_source_sha256=sha(args.masks),mask_policy='Established temporal-union support, fixed for every frame',
        original_source_modified=False,depth_rgb_pedestal=[12,10,0],depth_lut_recomputed=False,
        native_dimensions=[w,h],frame_count=count,fps=fps,duration_seconds=count/fps,
        exterior_depth_max_before_encoding=max_exterior,movie=movie.relative_to(ROOT).as_posix(),movie_sha256=sha(movie),
        poster=poster.relative_to(ROOT).as_posix(),poster_sha256=sha(poster))
    (ROOT/'data/motion-cutout.json').write_text(json.dumps(record,indent=2)+'\n')
    library=json.loads((ROOT/'data/overview-library.json').read_text(encoding='utf-8'))
    entry=next(e for e in library['films'] if e['id']=='motion')
    entry.update(movie=record['movie'],poster=record['poster'],source='data/motion-cutout.json',
                 duration_seconds=count/fps,sha256=record['movie_sha256'],poster_sha256=record['poster_sha256'])
    (ROOT/'data/overview-library.json').write_text(json.dumps(library,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('MOTION CUTOUT COMPLETE',count,count/fps,flush=True)

if __name__=='__main__':main()
