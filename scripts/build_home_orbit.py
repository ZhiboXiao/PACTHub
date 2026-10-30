"""A full-width, seamless long-axis orbit from the released Figure 5b volume."""
from pathlib import Path
import argparse, hashlib, json, subprocess
import cv2, h5py, numpy as np
from PIL import Image
import build_hero_story as render

ROOT = Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--work-dir',type=Path,required=True)
    args=p.parse_args();args.work_dir.mkdir(parents=True,exist_ok=True)
    with h5py.File(args.source,'r') as f:
        volume=np.maximum(f['frontal_view_img'][:].transpose(0,2,1)[:,:,::-1],0).copy()
    support=render.envelope(volume.max(0),.022,close=43,dilate=8,feather=6)
    volume*=support[None]
    render.SIDE=1000;render.FPS=24
    renderer=render.Renderer(volume,-90);del volume
    layouts={'desktop':dict(size=(1920,1320),center=(1000,630),scale=2.00,screen_angle_deg=30),
             'mobile':dict(size=(1080,1080),center=(540,540),scale=1.24,screen_angle_deg=40)}
    outputs={};encoders={}
    for name,layout in layouts.items():
        path=ROOT/f'assets/media/hero-orbit-{name}.mp4';outputs[name]=path
        encoders[name]=subprocess.Popen(render.encode_cmd(path,layout['size']),stdin=subprocess.PIPE)
    try:
        for i in range(288):
            frame=renderer.frame(1+i/24)
            for name,layout in layouts.items():
                scale=layout['scale'];x,y=layout['center']
                mat=cv2.getRotationMatrix2D((500,500),-(180+layout['screen_angle_deg']),scale)
                mat[:,2]+=(x-500,y-500)
                canvas=cv2.warpAffine(frame,mat,layout['size'])
                encoders[name].stdin.write(canvas.tobytes())
                if i==0:
                    Image.fromarray(canvas).save(ROOT/f'assets/images/hero-orbit-{name}.webp',quality=95)
                    Image.fromarray(canvas).save(args.work_dir/f'hero-{name}.png')
                if i in [0,36,72,144,216,287] and name=='desktop':
                    Image.fromarray(canvas).save(args.work_dir/f'orbit-{i:03d}.png')
            if i%48==0:print('ORBIT',i,288,flush=True)
        for proc in encoders.values():
            proc.stdin.close()
            assert proc.wait()==0
    finally:
        renderer.win.Finalize()
        for proc in encoders.values():
            if proc.poll() is None:proc.kill()
    record=dict(source=dict(file=args.source.name,variable='frontal_view_img',sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                            release_doi='10.6084/m9.figshare.28443374.v3',figure='Figure 5b',license='CC BY 4.0'),
                presentation=dict(axis='specimen long axis Y',angle_deg=12,cycles=2,duration_seconds=12,fps=24,
                                  screen_angle_deg=layouts['desktop']['screen_angle_deg'],head_tail_reversed=True,display_window=[render.LOW,render.HIGH],layouts=layouts,
                                  loop='Complete 12-second orbit; no physiological-movie transition'),
                outputs={name:dict(file=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                   size_bytes=path.stat().st_size) for name,path in outputs.items()})
    (ROOT/'data/hero-story.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('COMPLETE',flush=True)


if __name__=='__main__':main()
