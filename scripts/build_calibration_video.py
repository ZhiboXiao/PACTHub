"""Animate measured FOV geometry and sound-speed BP candidates.

Inputs are numerical BP results from one 20-exposure acquisition. The speed
scores are recomputed with the published pipeline's full-MIP scoring function.
"""
from pathlib import Path
import argparse, hashlib, json, math, subprocess, sys
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image, ImageDraw, ImageFont

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--aligned-sweep',type=Path,required=True)
parser.add_argument('--qa-dir',type=Path,required=True)
parser.add_argument('--font-dir',type=Path,default=Path('C:/Windows/Fonts'))
args=parser.parse_args();root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'reconstruction'))
from pa_pipeline.selection.speed_legacy import score_stack
from pa_pipeline.selection.fov_legacy import select_fov

source=args.source_root;qa=args.qa_dir;qa.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
loc=np.load(source/'localization20/mips.npz');scout=loc['xy'][0]
cfg=read(source/'localization20/parameters.json');grid=cfg['defaults']['grid']
fov,mask=select_fov(scout,grid['center_mm'],grid['space_mm'],vessel_prior=True,sigma_upper=4)
saved=read(source/'fov_selection.json')
assert abs(fov['initial_z_rotation_deg']-saved['initial_z_rotation_deg'])<1e-8
files=['localization20/mips.npz','localization20/parameters.json','fov_selection.json']
folder=args.aligned_sweep;a=np.load(folder/'mips.npz');speedcfg=read(folder/'parameters.json')
images=a['xy'];speeds=a['speeds'];xyz=[a['axis_'+v] for v in 'xyz']
assert speedcfg['defaults']['frames']['indices_1based']==cfg['defaults']['frames']['indices_1based']
np.testing.assert_allclose(speedcfg['defaults']['grid']['space_mm'],saved['target_space_xyz_mm'])
np.testing.assert_allclose(speedcfg['defaults']['grid']['center_mm'],saved['center_rotated_mm'])
assert speedcfg['defaults']['geometry']['additional_z_rotation_deg']==saved['initial_z_rotation_deg']
order=np.argsort(speeds);images=np.asarray(images)[order];speeds=np.asarray(speeds)[order]
scores,support=score_stack(images);curve=np.asarray(scores['global_normalized_gradient']);best=int(curve.argmax())
assert len(np.unique(speeds))==len(speeds) and 0<best<len(speeds)-1
W,H,FPS,DURATION=1280,720,24,32
BG='#081119';FG='#e0edf4';MUTED='#8fa8b9';TEAL='#80d5de';AMBER='#e6b778';LINE='#29414f'
fontcache={}
def font(size,bold=False):
    key=(size,bold)
    if key not in fontcache:fontcache[key]=ImageFont.truetype(str(args.font_dir/('arialbd.ttf' if bold else 'arial.ttf')),size)
    return fontcache[key]
def label(draw,xy,text,size=20,color=FG,bold=False):draw.text(xy,text,font=font(size,bold),fill=color)
def gray(a,cap,low=0):return Image.fromarray(np.uint8(np.clip((a-low)/(cap-low),0,1)*255)).convert('RGB')
cap=float(np.percentile(images,99.8));low=.025*cap
scap=float(np.percentile(scout,99.8));scoutimage=gray(scout,scap,.025*scap).resize((510,510),Image.Resampling.BICUBIC)
left=(62,142);extent=[float(loc['axis_x'][0]),float(loc['axis_x'][-1]),float(loc['axis_y'][0]),float(loc['axis_y'][-1])]
def physical(points):
    p=np.asarray(points);q=np.empty_like(p,dtype=float)
    q[...,0]=left[0]+(p[...,0]-extent[0])/(extent[1]-extent[0])*510
    q[...,1]=left[1]+(p[...,1]-extent[2])/(extent[3]-extent[2])*510
    return q
contour=Image.new('RGBA',(510,510));maskalpha=Image.fromarray(np.uint8(mask)*65).resize((510,510),Image.Resampling.NEAREST)
contour.paste((80,210,220,0),(0,0,510,510));contour.putalpha(maskalpha)
target=saved['target_space_xyz_mm'];center=np.asarray(saved['center_rotated_mm'][:2]);angle=float(saved['initial_z_rotation_deg'])
# This is a coordinate illustration of the candidate grid, not a new BP volume.
tx=np.linspace(-target[0]/2,target[0]/2,240)+center[0];ty=np.linspace(-target[1]/2,target[1]/2,480)+center[1]
xx,yy=np.meshgrid(tx,ty);r=math.radians(angle);xn=np.cos(r)*xx+np.sin(r)*yy;yn=-np.sin(r)*xx+np.cos(r)*yy
candidate=map_coordinates(scout,[(yn-extent[2])/(extent[3]-extent[2])*(scout.shape[0]-1),(xn-extent[0])/(extent[1]-extent[0])*(scout.shape[1]-1)],order=1,mode='constant',cval=0)
candidate_image=gray(candidate,scap,.025*scap)
candidate_frames={}
def candidate_preview(progress):
    key=round(progress*72)
    if key not in candidate_frames:
        theta=math.radians(angle*key/72)
        nx=np.cos(theta)*xx+np.sin(theta)*yy;ny=-np.sin(theta)*xx+np.cos(theta)*yy
        values=map_coordinates(scout,[(ny-extent[2])/(extent[3]-extent[2])*(scout.shape[0]-1),(nx-extent[0])/(extent[1]-extent[0])*(scout.shape[1]-1)],order=1,mode='constant',cval=0)
        candidate_frames[key]=gray(values,scap,.025*scap)
    return candidate_frames[key]
x,y,z=xyz;roi=[-7.,7.,-8.,8.]
ix=np.flatnonzero((x>=roi[0])&(x<=roi[1]));iy=np.flatnonzero((y>=roi[2])&(y<=roi[3]))
fulls=[gray(a,cap,low).resize((260,520),Image.Resampling.BICUBIC) for a in images]
crops=[gray(a[np.ix_(iy,ix)],cap,low).resize((225,258),Image.Resampling.BICUBIC) for a in images]
imageleft=(117,137)
def crop_box():
    return (imageleft[0]+ix[0]/(len(x)-1)*260,imageleft[1]+iy[0]/(len(y)-1)*520,imageleft[0]+ix[-1]/(len(x)-1)*260,imageleft[1]+iy[-1]/(len(y)-1)*520)

def stroke(draw,points,fraction,color=TEAL,width=3):
    p=np.vstack([points,points[0]]);length=np.linalg.norm(np.diff(p,axis=0),axis=1);remaining=float(fraction)*length.sum()
    for a,b,dist in zip(p[:-1],p[1:],length):
        if remaining<=0:break
        end=a+(b-a)*min(1,remaining/dist);draw.line([tuple(a),tuple(end)],fill=color,width=width);remaining-=dist

def curve_plot(draw,index,final=False):
    bx,by,bw,bh=572,438,620,168
    vmin=math.floor(curve.min()*1000)/1000-.002;vmax=math.ceil(curve.max()*1000)/1000+.003
    point=lambda i:(bx+(speeds[i]-speeds[0])/(speeds[-1]-speeds[0])*bw,by+bh-(curve[i]-vmin)/(vmax-vmin)*bh)
    for value in np.linspace(vmin+.001,vmax-.001,4):
        py=by+bh-(value-vmin)/(vmax-vmin)*bh
        draw.line((bx,py,bx+bw,py),fill=LINE,width=1);label(draw,(bx-53,py-10),f'{value:.3f}',15,MUTED)
    for speed in [1488,1490,1492,1494,1496,1499]:
        px=bx+(speed-speeds[0])/(speeds[-1]-speeds[0])*bw
        label(draw,(px-19,by+bh+13),str(speed),15,MUTED)
    pts=[point(i) for i in range(len(speeds) if final else index+1)]
    if len(pts)>1:draw.line(pts,fill=TEAL,width=3)
    for px,py in pts:draw.ellipse((px-3,py-3,px+3,py+3),fill=TEAL)
    px,py=point(best if final else index);draw.line((px,by,px,by+bh),fill='#4b6b72',width=1)
    draw.ellipse((px-6,py-6,px+6,py+6),fill=AMBER if final else FG)
    label(draw,(bx,by-37),'FULL-MIP NORMALIZED GRADIENT',17,MUTED)
    label(draw,(bx+bw-145,by+bh+43),'Sound speed / m/s',16,MUTED)

def frame(t):
    stage=0 if t<6 else 1 if t<12 else 2 if t<27 else 3
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    label(d,(36,20),'PACTHub  /  RECONSTRUCTION PARAMETERS',15,TEAL)
    titles=['Locate the visible anatomy','Set the oriented field of view','Sweep sound speed on the final FOV','Select the focus-score maximum']
    label(d,(36,51),titles[stage],33,FG,True)
    label(d,(36,98),'20241213_151351   /   20 measured exposures   /   BP',18,MUTED)
    if stage<2:
        im.paste(scoutimage,left);d=ImageDraw.Draw(im)
        progress=min(1,t/3) if stage==0 else 1
        overlay=contour.copy();overlay.putalpha(maskalpha.point(lambda p:int(p*.65*progress)))
        im.paste(overlay,left,overlay);d=ImageDraw.Draw(im)
        pts=physical(saved['fitted_rectangle_xy_mm']);stroke(d,pts,min(1,max(0,(t-2)/3)))
        c=np.asarray(saved['center_native_mm'][:2]);u=np.asarray(saved['long_axis_xy']);axis=physical([c-u*32,c+u*32])
        if t>3:d.line([tuple(axis[0]),tuple(axis[1])],fill=AMBER,width=2)
        d.line((left[0]+370,left[1]+480,left[0]+370+10/80*510,left[1]+480),fill='white',width=3)
        label(d,(left[0]+365,left[1]+453),'10 mm',16)
        if stage==0:
            label(d,(658,158),'SCOUT FIELD',18,TEAL);label(d,(658,190),'80 × 80 × 20 mm',37,FG,True)
            label(d,(658,270),'01   Local-contrast support',23,FG)
            label(d,(658,320),'02   Principal long axis',23,FG)
            label(d,(658,370),'03   Oriented bounds',23,FG)
            label(d,(658,464),'Visible structure',17,MUTED)
            label(d,(658,493),f'{saved["fitted_width_mm"]:.1f} × {saved["fitted_length_mm"]:.1f} mm',33,TEAL,True)
            label(d,(658,559),'Outline follows the measured MIP.',18,MUTED)
        else:
            progress=min(1,(t-6)/3.5)
            im.paste(candidate_preview(progress),(825,147));d=ImageDraw.Draw(im)
            label(d,(624,158),'FINAL FOV',17,TEAL)
            label(d,(624,193),f'{angle*progress:.2f}°',35,FG,True)
            label(d,(624,242),'Z-axis rotation',16,MUTED)
            label(d,(624,330),'40 × 80',29,FG,True);label(d,(624,371),'mm in XY',18,MUTED)
            label(d,(624,437),'Z span',16,MUTED);label(d,(624,468),'20 mm',29,FG,True)
            label(d,(625,566),'Fixed for the sweep',17,AMBER)
            label(d,(825,638),'Coordinate preview',17,MUTED)
        footer='FOV geometry / scout coordinates' if stage==0 else 'Recorded XY orientation  /  fixed 20 mm Z span'
    else:
        index=min(len(speeds)-1,int((t-12)/15*len(speeds))) if stage==2 else best
        im.paste(fulls[index],imageleft);d=ImageDraw.Draw(im);d.rectangle(crop_box(),outline=TEAL,width=2)
        label(d,(779,176),'Same',16,TEAL);label(d,(779,199),'region',16,TEAL)
        im.paste(crops[0],(536,137));im.paste(crops[index],(898,137));d=ImageDraw.Draw(im)
        label(d,(536,365),'',16,MUTED)
        label(d,(779,229),'→',36,MUTED)
        label(d,(536,114),f'{speeds[0]:.1f} m/s',17,MUTED)
        label(d,(898,114),f'{speeds[index]:.1f} m/s',20,AMBER if stage==3 else TEAL,True)
        curve_plot(d,index,stage==3)
        d.line((imageleft[0]+204,638,imageleft[0]+204+5/40*260,638),fill='white',width=3)
        label(d,(imageleft[0]+194,612),'5 mm',16)
        label(d,(42,668),f'{"SELECTED" if stage==3 else "CANDIDATE"}   {speeds[index]:.1f} m/s',20,AMBER if stage==3 else TEAL,True)
        footer=f'Final FOV: 40 × 80 × 20 mm  /  {len(speeds)} BP candidates'
    if stage<2:label(d,(36,681),footer,16,MUTED)
    else:label(d,(468,681),footer,16,MUTED)
    return im

movie=root/'assets/media/fov-sound-speed.mp4';poster=root/'assets/images/showcase/calibration-poster.webp'
cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for k in range(DURATION*FPS):
    im=frame(k/FPS);proc.stdin.write(im.tobytes())
    if k in [4*FPS,9*FPS,19*FPS,29*FPS]:im.save(qa/f'calibration_{k//FPS:02d}s.png')
    if k%(6*FPS)==0:print('FRAME',k,'/',DURATION*FPS,flush=True)
proc.stdin.close();assert proc.wait()==0
frame(29).save(poster,quality=94,method=6)
captions=[
 (0,6,'A measured 20-exposure BP scout defines the visible signal support and principal long axis.','使用实测 20 帧 BP 大视场图，提取可见信号区域并确定长轴。'),
 (6,12,'Use the recorded 40 × 80 × 20 mm FOV and −12.145° Z correction for the following BP reconstructions.','后续 BP 重建统一采用已经确定的 40 × 80 × 20 mm 视野与 −12.145° Z 轴校正。'),
 (12,20,'Reconstruct every speed on the same final FOV with the same 20 exposures. All candidates share one display window.','所有声速使用同一批 20 帧，在确定后的 FOV 内重建，并共用同一显示窗。'),
 (20,27,'Each point is recomputed from a complete floating-point BP MIP. The curve follows measured candidates without fitting.','每个评分来自完整浮点 BP MIP，曲线依次连接实际候选点。'),
 (27,32,f'The full-MIP normalized-gradient score peaks at {speeds[best]:.1f} m/s for this acquisition.',f'该采集的全 MIP 归一化梯度评分在 {speeds[best]:.1f} m/s 达到最高。')]
metadata=dict(movie=str(movie.relative_to(root)).replace('\\','/'),movie_sha256=sha(movie),poster=str(poster.relative_to(root)).replace('\\','/'),poster_sha256=sha(poster),duration_seconds=DURATION,fps=FPS,frame_count=FPS*DURATION,frame_size=[W,H],
 acquisition_id='20241213_151351',frames_1based=cfg['defaults']['frames']['indices_1based'],source_kind='BP recomputed locally from PA data on the recorded final FOV',
 source_sha256={**{name:sha(source/name) for name in files},**{'aligned_sweep/'+name:sha(folder/name) for name in ['mips.npz','parameters.json','result.json']}},
 fov=dict(scout_grid=grid,center_native_mm=saved['center_native_mm'],center_rotated_mm=saved['center_rotated_mm'],angle_deg=angle,fitted_rectangle_xy_mm=saved['fitted_rectangle_xy_mm'],target_space_xyz_mm=target,scout_flags=fov['segmentation_flags'],applied_to_speed_reconstruction=True,display='Scout orientation preview followed by true BP on the recorded final FOV'),
 speed=dict(grid=speedcfg['defaults']['grid'],speeds_m_s=speeds.tolist(),scores=curve.tolist(),method='full_global_normalized_gradient',selected_m_s=float(speeds[best]),score_source_sha256=sha(root/'reconstruction/pa_pipeline/selection/speed_legacy.py'),common_support_pixels=int(support.sum()),inset_xy_mm=roi),
 display=dict(scout_linear_window=[.025*scap,scap],speed_linear_window=[low,cap],window_shared_across_speeds=True,gamma=1,scout_shape_yx=list(scout.shape),speed_shape_syx=list(images.shape)),
 chapters=[dict(start=0,end=6,key='film.locate'),dict(start=6,end=12,key='film.orient'),dict(start=12,end=27,key='film.sweep'),dict(start=27,end=32,key='film.select')],
 captions=[dict(start=a,end=b,text=dict(en=en,zh=zh)) for a,b,en,zh in captions])
(root/'data/calibration-video.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,'item') else x.tolist())+'\n',encoding='utf-8')
print('COMPLETE',movie,'SELECTED',speeds[best],flush=True)
