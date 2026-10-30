"""Animate the manuscript's exact Q calculation using its vascular control.

All scores are recomputed in 3D; 2D MIPs only illustrate the intermediate fields.
Usage: --evidence-root dataset_unified_q_validation_20261020 --qa-dir PATH
"""
from pathlib import Path
import argparse,sys,json,hashlib,csv,subprocess,math
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont
ap=argparse.ArgumentParser();ap.add_argument('--evidence-root',type=Path,required=True);ap.add_argument('--qa-dir',type=Path,required=True)
args=ap.parse_args();sys.path.insert(0,str(args.evidence_root.resolve()))
from unified_metrics import prepare,evaluate
from reference_foreground import contrast
root=Path(__file__).resolve().parents[1];out=root/'assets/media';out.mkdir(exist_ok=True)
qa=args.qa_dir;qa.mkdir(exist_ok=True,parents=True)
# Identical seed, geometry and amplitudes to run_all.py::vascular(4099).
sp=np.array([.2,.2,.2]);z,y,x=np.meshgrid((np.arange(96)-48)*.2,(np.arange(128)-64)*.2,(np.arange(96)-48)*.2,indexing='ij')
taper=lambda a,b:np.clip((y-a)/.6,0,1)*np.clip((b-y)/.6,0,1)
tube=lambda xc,zc,w,amp,a,b:amp*np.exp(-((x-xc)**2+(z-zc)**2)/(2*w*w))*taper(a,b)
strong=tube(-2+.7*np.sin(y/4),1+.3*np.cos(y/5),.3,1.,-10,10)
branch=tube(-2+.4*(y+4),1+.2*(y+4),.22,.45,-4,6)
weak=tube(2+.4*np.sin(y/3),-1+.3*np.sin(y/4),.2,.3,-10,10)
noise=gaussian_filter(np.random.default_rng(4099).standard_normal(x.shape),2.5);noise/=noise.std()
bg=np.maximum(.20+.06*np.sin(y/3)+.04*np.cos(x/3)+.025*noise,0)
clean=strong+branch+weak;r=(clean+bg).astype('f4')
ref,m=prepare(r,sp)
cases=[('Background removed',(clean).astype('f4'),'background',0.),('Gaussian blur / 0.30 mm',(gaussian_filter(clean,.3/sp)+bg).astype('f4'),'blur',.3),('Weak branch removed',(strong+branch+bg).astype('f4'),'weak_retention',0.)]
rows=[];previous=list(csv.DictReader((args.evidence_root/'results/vascular_4099.csv').open()))
for name,a,family,level in cases:
    result=evaluate(a,r,ref,m)
    old=next(v for v in previous if v['family']==family and float(v['level'])==level)
    for key in ['Q','SSIM','L1']:assert abs(result[key]-float(old[key]))<1e-6,(key,result[key],old[key])
    rows.append(dict(name=name,**result))
x=cases[1][1];hx=contrast(x,sp);hr=ref['hr'];result=rows[1]
parts={}
for key in ['weak','strong']:
    mask=m[key];a=hx*mask;b=hr*mask
    # Accumulate actual 3D overlap contributions along Y for the animation.
    parts[key]=(2*np.minimum(a,b).sum((0,2),dtype='f8'),(a+b).sum((0,2),dtype='f8'))
trace=dict(reference='Manuscript vascular control; seed 4099',candidate='Gaussian blur, sigma 0.30 mm applied to vessel signal; background retained',shape_zyx=list(r.shape),spacing_mm=sp.tolist(),gain=1,local_contrast_sigma_mm=.4,hessian_scales_mm=[.2,.35,.5],support_thresholds=[.1,.3],noise_multipliers=[3,6],boundary_margin_mm=1,component_min_volume_mm3=.064,component_min_extent_mm=1,weak_strong_split=float(m['split']),support_voxels=int(m['mask'].sum()),weak_voxels=int(m['weak'].sum()),strong_voxels=int(m['strong'].sum()),formula='h(I)=max(I-G_0.4mm*I,0); D_s=2 sum min(g hX,hR) / sum(g hX+hR), over reference mask M_s; Q=100 sqrt(D_weak D_strong)',scores=rows,metrics_domain='Full 3D volumes. SSIM includes all valid full-volume window centres; MIPs are display only.',code_sha256={p:hashlib.sha256((args.evidence_root/p).read_bytes()).hexdigest() for p in ['unified_metrics.py','reference_foreground.py','run_all.py']})
(root/'data/q-calculation.json').write_text(json.dumps(trace,indent=2)+'\n')
np.savez_compressed(qa/'q_intermediates.npz',reference=r,candidate=x,hr=hr,hx=hx,vesselness=ref['v'],weak=m['weak'],strong=m['strong'])
W,H=1280,720;bgc='#080f17';ink='#edf4fa';muted='#97adbf';teal='#86d6df';amber='#e8b876';violet='#bba3e4'
fonts={size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size) for size in [15,17,19,21,23,27,34,42,60]}
bold={size:ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',size) for size in [19,23,34,42,60]}
def text(d,xy,s,size=19,color=ink,b=False):d.text(xy,s,font=(bold if b else fonts)[size],fill=color)
def rgb(a,cap=None,tint=None):
    v=a.max(0)[::-1];v=np.clip(v/(float(cap) if cap else max(float(v.max()),1e-9)),0,1)
    color=np.ones(3) if tint is None else np.array(tint)/255
    return Image.fromarray(np.uint8(np.rint(v[...,None]*color*255))).resize((272,362),Image.Resampling.NEAREST if a.dtype==bool else Image.Resampling.BILINEAR)
rawcap=float(r.max());hcap=float(hr.max())
group=np.zeros((*hr.shape[1:],3),dtype='f4');group[m['weak'].max(0)]=np.array([134,214,223]);group[m['strong'].max(0)]=np.array([232,184,118])
groupim=Image.fromarray(np.uint8(group[::-1])).resize((272,362),Image.Resampling.NEAREST)
overlap=np.minimum(hx,hr)*m['mask']
images=[
 [rgb(r,rawcap),rgb(x,rawcap),rgb(np.abs(x-r),float(np.max(abs(x-r))),[232,184,118])],
 [rgb(r,rawcap),rgb(gaussian_filter(r,.4/sp),rawcap),rgb(hr,hcap,[134,214,223])],
 [rgb(ref['v'],1,[134,214,223]),rgb(m['mask'],1,[134,214,223]),groupim],
 [rgb(hr*m['mask'],hcap,[134,214,223]),rgb(hx*m['mask'],hcap,[232,184,118]),rgb(overlap,hcap,[187,163,228])],
 [rgb(a,rawcap) for _,a,_,_ in cases]]
titles=['Start with a paired reference and candidate','Extract positive local contrast','Define structural support from the reference','Measure retention in both signal groups','Read structural quality alongside full-field metrics']
subtitles=['Manuscript vascular control  /  Gaussian blur 0.30 mm  /  fixed amplitude scale',
 'Suppress the smooth local background with a Gaussian at 0.40 mm.',
 'Hessian response -> connected support -> split at median reference contrast',
 'Reference support stays fixed. Accumulate voxel contributions in three dimensions.',
 'Three controlled changes reveal complementary sensitivities.']
labels=[['REFERENCE / R','CANDIDATE / X','ABSOLUTE DIFFERENCE'],['REFERENCE / R','LOCAL BACKGROUND / G * R','POSITIVE CONTRAST / h(R)'],['MULTISCALE HESSIAN','REFERENCE SUPPORT / M','WEAK   +   STRONG'],['REFERENCE CONTRAST','CANDIDATE CONTRAST','SHARED CONTRAST / min'],[v[0].upper() for v in cases]]
formula=['Same 3D grid  |  96 x 128 x 96 voxels  |  0.20 mm spacing  |  g = 1',
 'h(I) = max[ I - G(0.40 mm) * I, 0 ]     |     Apply the same operation to R and X',
 'Mweak: h(R) <= median       Mstrong: h(R) > median       |       within M only',
 'Ds = 2 SUM min(g h(X), h(R)) / SUM(g h(X) + h(R))      |      Q = 100 sqrt(Dweak Dstrong)',
 'Q: structural retention     |     PSNR / full-image SSIM / L1: full-field agreement']
chapters=['01  PAIR','02  CONTRAST','03  SUPPORT','04  OVERLAP','05  COMPLEMENT']
def frame(stage,p):
    im=Image.new('RGB',(W,H),bgc);d=ImageDraw.Draw(im)
    text(d,(40,20),'PACTHub   /   Q, STEP BY STEP',15,teal)
    text(d,(40,52),titles[stage],34,ink,True);text(d,(40,102),subtitles[stage],19,muted)
    xs=[70,505,940]
    for j,xp in enumerate(xs):
        text(d,(xp,150),labels[stage][j],17,teal if j==0 else amber if j==1 else violet)
        d.rounded_rectangle((xp-9,182,xp+281,552),radius=5,fill='#020509',outline='#253441')
        tile=images[stage][j]
        if stage in [1,2,3] and j>0:
            frac=min(1,p*1.7);reveal=max(1,int(tile.height*frac))
            tile=tile.copy();tile.paste((2,5,9),(0,reveal,tile.width,tile.height))
            im.paste(tile,(xp,186));d.line((xp,186+reveal,xp+272,186+reveal),fill=teal,width=2)
        else:im.paste(tile,(xp,186))
        if j<2 and stage in [1,2,3]:text(d,(xp+327,340),('-' if j==0 else '=') if stage==1 else '→',34,muted)
        d.rectangle((xp+199,512,xp+267,546),fill='#020509');text(d,(xp+207,514),'3 mm',15,ink)
        d.line((xp+215,541,xp+215+3/.2*272/96,541),fill='white',width=2)
    if stage==3:
        stop=max(1,int(min(1,p*1.65)*128));ds=[]
        for key in ['weak','strong']:
            num,den=parts[key];ds.append(float(num[-stop:].sum()/max(den[-stop:].sum(),1e-15)))
        text(d,(80,560),f'Dweak  {ds[0]:.3f}',23,teal,True);text(d,(515,560),f'Dstrong  {ds[1]:.3f}',23,amber,True)
        text(d,(950,557),f'Q  {100*np.sqrt(ds[0]*ds[1]):.2f}',27,violet)
    elif stage==4:
        for j,row in enumerate(rows):
            text(d,(xs[j],560),f'Q {row["Q"]:.2f}   SSIM {row["SSIM"]:.3f}',23,teal,True)
            text(d,(xs[j],591),f'PSNR {row["PSNR"]:.2f} dB   L1 {row["L1"]:.4f}',17,muted)
    else:text(d,(40,571),'3D numerical calculation  /  MIP illustration',17,muted)
    text(d,(40,627),formula[stage],17,ink)
    for j,c in enumerate(chapters):
        xx=40+j*246;d.rectangle((xx,677,xx+226,680),fill='#253441')
        if j<=stage:d.rectangle((xx,677,xx+int(226*(p if j==stage else 1)),680),fill=teal)
        text(d,(xx,691),c,15,teal if j==stage else muted)
    return im
fps=24;seconds=7;total=5*seconds*fps
cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'q-theory.mp4')]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for st in range(5):
    frame(st,1).save(qa/f'q_stage_{st+1}.png')
    for k in range(seconds*fps):proc.stdin.write(frame(st,k/(seconds*fps-1)).tobytes())
    print('VIDEO_STAGE',st+1,flush=True)
proc.stdin.close();assert proc.wait()==0
frame(3,1).save(root/'assets/images/showcase/q-poster.webp',lossless=True,method=6)
en=['Pair the reference and blurred candidate on the same three-dimensional grid, using gain one.','Compute positive local contrast by subtracting a 0.4 millimetre Gaussian background.','Use only the reference to identify tubular support, then split it into weak and strong contrast groups.','Measure shared contrast in each group. Q is 100 times the geometric mean of the two overlap scores.','Q complements PSNR, full-image SSIM and L1. The three controls retain background and structural changes separately.']
zh=['在同一三维网格上比较参考体和高斯模糊结果，强度系数为一。','减去 0.4 毫米高斯平滑背景，保留正的局部对比度。','仅从参考体建立管状结构区域，按参考对比度中位数分为弱、强两组。','分别累计两组的共有对比度，Q 等于两组重叠分数几何平均值的 100 倍。','Q 补充 PSNR、全图 SSIM 和 L1，分别反映结构保留与整体一致性。']
for lang,lines in [('en',en),('zh',zh)]:
    vtt='WEBVTT\n\n'
    for i,line in enumerate(lines):vtt+=f'00:{i*7//60:02d}:{i*7%60:02d}.000 --> 00:{(i+1)*7//60:02d}:{(i+1)*7%60:02d}.000\n{line}\n\n'
    (out/f'q-theory.{lang}.vtt').write_text(vtt,encoding='utf-8')
print('VIDEO_COMPLETE',json.dumps(rows),flush=True)
