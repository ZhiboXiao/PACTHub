"""Leaf MIP with a rotating hemisphere above a 20-step matrix on the right."""
from pathlib import Path
import argparse, functools, hashlib, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SIZE=(1440,1080);FPS=30;DURATION=18
WHITE='#f7f8f8';SILVER='#d0d6e0';MUTED='#8a8f98'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ease(t):return (lambda x:x*x*(3-2*x))(np.clip(t,0,1))

def bowl(image, angle, centre=(1360,325), radius=157):
    """Shaded hemisphere plus meridians, without detector dots."""
    az=math.radians(-38);elev=math.radians(27)
    normal=np.array([math.cos(elev)*math.cos(az),math.cos(elev)*math.sin(az),math.sin(elev)])
    right=np.array([-math.sin(az),math.cos(az),0]);up=np.cross(normal,right)
    def pts(theta,phi):
        theta,phi=np.broadcast_arrays(theta,phi+angle)
        return np.stack([np.sin(theta)*np.cos(phi),np.sin(theta)*np.sin(phi),-np.cos(theta)],axis=-1)
    def project(p):
        return np.stack([centre[0]+radius*(p@right),centre[1]-radius*(p@up)],axis=-1)
    faces=[]
    for t0,t1 in zip(np.linspace(0,np.pi/2,11)[:-1],np.linspace(0,np.pi/2,11)[1:]):
        for p0,p1 in zip(np.linspace(0,2*np.pi,61)[:-1],np.linspace(0,2*np.pi,61)[1:]):
            p=pts(np.array([t0,t0,t1,t1]),np.array([p0,p1,p1,p0]));mean=p.mean(0)
            light=.4+.6*max(0,float(mean@np.array([-.3,-.4,.85])))
            value=int(15+33*light)
            faces.append((float(mean@normal),project(p),value))
    d=ImageDraw.Draw(image)
    for _,p,v in sorted(faces,key=lambda a:a[0]):d.polygon([tuple(q) for q in p],fill=(v,v+1,v+2))
    for theta in np.linspace(.28,np.pi/2,6):
        p=pts(theta,np.linspace(0,2*np.pi,181));xy=project(p)
        for i in range(180):
            brightness=95 if p[i]@normal>-.15 else 49
            d.line([tuple(xy[i]),tuple(xy[i+1])],fill=(brightness,brightness+3,brightness+6),width=1)
    for phi in np.linspace(0,2*np.pi,13)[:-1]:
        p=pts(np.linspace(.06,np.pi/2,75),phi);xy=project(p)
        for i in range(74):
            brightness=117 if p[i]@normal>-.15 else 52
            d.line([tuple(xy[i]),tuple(xy[i+1])],fill=(brightness,brightness+3,brightness+6),width=1)
    rim=project(pts(np.pi/2,np.linspace(0,2*np.pi,201)))
    d.line([tuple(q) for q in rim],fill=SILVER,width=2)
    # One broad longitudinal strip makes the slow physical rotation legible.
    phi=-.2
    strip=pts(np.r_[np.linspace(.15,np.pi/2,50),np.linspace(np.pi/2,.15,50)],
              np.r_[np.full(50,phi-.025),np.full(50,phi+.025)])
    d.polygon([tuple(q) for q in project(strip)],fill='#adb4bf')
    # A fine orbit arrow sits above the opening; it is explanatory, not a ruler.
    orbit=pts(np.pi/2,np.linspace(-.1,1.0,70))*1.13;orbit[:,2]=.18
    xy=project(orbit);d.line([tuple(q) for q in xy],fill=WHITE,width=2)
    tip=xy[-1];vec=(tip-xy[-3]);vec/=np.linalg.norm(vec);side=np.array([-vec[1],vec[0]])
    d.polygon([tuple(tip),tuple(tip-vec*11+side*4),tuple(tip-vec*11-side*4)],fill=WHITE)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path,required=True)
    parser.add_argument('--preview-only',action='store_true')
    args=parser.parse_args();work=args.work_dir;source=work/'leaf-results'
    @functools.lru_cache(None)
    def font(n):return ImageFont.truetype(str(work/'InterVariable.ttf'),n)
    pairs=[];records=[]
    for n in range(1,21):
        with np.load(source/f'leaf_{n:02d}.npz') as data:
            pairs.append((data['mip'].copy(),data['oblique'].copy()))
            assert all(np.isfinite(a).all() for a in pairs[-1])
            assert pairs[-1][1].max()<=pairs[-1][0].max()+1e-6
            dx=float(data['x'][1]-data['x'][0]);pitch=float(data['oblique_pitch_mm'])
        records.append(json.loads((source/f'leaf_{n:02d}.json').read_text()))
    cap=float(np.percentile(pairs[-1][0],99.6));low=cap*.055
    def screen(a):return Image.fromarray(np.uint8(np.rint(np.clip((a-low)/(cap-low),0,1)*255))).convert('RGB')
    images=[tuple(screen(a) for a in pair) for pair in pairs]
    boxes=[(24,80,800,1012)]
    resized=[];locations=[];scales=[]
    for j,(l,t,r,b) in enumerate(boxes):
        w,h=images[0][j].size;scale=min((r-l)/w,(b-t)/h)
        size=(round(w*scale),round(h*scale));locations.append((round((l+r-size[0])/2),round((t+b-size[1])/2)))
        scales.append(scale);resized.append([pair[j].resize(size,Image.Resampling.LANCZOS) for pair in images])
    step=abs(records[0]['geometry']['frame_angle_step_parameter_deg'])*np.pi/180
    def frame(t):
        elapsed=max(0.,(t-.8)/.7)
        n=min(19,int(elapsed));progress=min(elapsed,19.)
        blend=float(ease((elapsed-n)/.20)) if n else 1.
        im=Image.new('RGB',SIZE,'black');d=ImageDraw.Draw(im)
        d.text((44,26),'Intensity MIP',font=font(34),fill=WHITE)
        d.text((1396,32),'20241115_104329',font=font(27),fill=MUTED,anchor='ra')
        for j in range(1):
            image=resized[j][n]
            if n and blend<1:image=Image.blend(resized[j][n-1],image,blend)
            im.paste(image,locations[j])
            bar=5/dx*scales[j];x=boxes[j][2]-36;y=1042
            d.line((x-bar,y,x,y),fill=WHITE,width=4)
            d.text((x,y-21),'5 mm',font=font(26),fill=SILVER,anchor='rs')
        bowl(im,progress*step,centre=(1120,255),radius=211)
        d.text((1120,510),'Rotating array',font=font(34),fill=SILVER,anchor='mm')
        d.line((880,564,1360,564),fill='#202225',width=1)
        d.text((880,602),'Accumulated exposures',font=font(31),fill=SILVER)
        for i in range(20):
            col=i%5;row=i//5;x=880+col*100;y=671+row*79
            active=i<=n
            strength=blend if i==n else 1.
            fill=tuple(round(a+(b-a)*strength) for a,b in zip((17,18,20),(208,214,224))) if active else '#111214'
            d.rounded_rectangle((x,y,x+80,y+60),radius=5,fill=fill,outline='#3c3f44' if active else '#25272b',width=1)
            text_colour=('#08090a' if strength>=.5 else SILVER) if active else '#62666d'
            d.text((x+40,y+30),f'{i+1:02d}',font=font(29),fill=text_colour,anchor='mm')
        d.text((1360,1028),f'{n+1:02d} / 20',font=font(32),fill=WHITE,anchor='rm')
        return im
    if args.preview_only:
        frame(17).save(work/'leaf-layout-preview.png')
        return
    movie=ROOT/'assets/media/overview-leaf-compound.mp4';poster=ROOT/'assets/images/showcase/overview-leaf.webp'
    command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{SIZE[0]}x{SIZE[1]}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-threads','4','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for i in range(FPS*DURATION):
            im=frame(i/FPS);proc.stdin.write(np.asarray(im).tobytes())
            if i in [0,150,300,510]:im.save(work/f'leaf-film-{i:03d}.png')
        proc.stdin.close();assert proc.wait()==0
    finally:
        if proc.poll() is None:proc.kill()
    final_frame=frame(17)
    for i in range(20):
        assert final_frame.getpixel((880+(i%5)*100+8,671+(i//5)*79+8))==(208,214,224)
    final_frame.save(poster,lossless=True)
    record=dict(sample_id=records[0]['sample_id'],counts=list(range(1,21)),frames_1based=list(range(1,21)),
        reconstruction=records[-1],display_window=[low,cap],common_window=True,extra_gain=False,
        views=['axial MIP'],detail_inset=False,
        layout=dict(image='left',hemisphere='upper right',exposure_matrix='lower right',canvas_px=list(SIZE)),
        final_result_hold_seconds=round(DURATION-(.8+19*.7+.2*.7),2),
        array_animation=dict(shape='hemisphere',angle_step_deg=abs(records[0]['geometry']['frame_angle_step_parameter_deg']),
                             matrix=[4,5],mode='consecutive accumulation',schematic=True),
        numerical_outputs=[dict(count=i+1,sha256=sha(source/f'leaf_{i+1:02d}.npz')) for i in range(20)])
    (ROOT/'data/leaf-compounding.json').write_text(json.dumps(record,indent=2)+'\n')
    library=json.loads((ROOT/'data/overview-library.json').read_text(encoding='utf-8'))
    library['films']=[entry for entry in library['films'] if entry['id']!='temporal']
    entry=next(e for e in library['films'] if e['id']=='rotation')
    entry.update(movie=movie.relative_to(ROOT).as_posix(),poster=poster.relative_to(ROOT).as_posix(),
        title={'en':'Rotation compounding','zh':'旋转复合'},
        description={'en':'A leaf, reconstructed from 1 to 20 exposures.','zh':'从 1 到 20 次曝光，看叶脉结构逐步呈现。'},
        source='data/leaf-compounding.json',duration_seconds=DURATION,sha256=sha(movie),poster_sha256=sha(poster))
    (ROOT/'data/overview-library.json').write_text(json.dumps(library,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('LEAF FILM COMPLETE',flush=True)

if __name__=='__main__':main()
