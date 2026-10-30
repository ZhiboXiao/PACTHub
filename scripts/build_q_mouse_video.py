"""Render a short measured-mouse Q calculation from the manuscript BP volumes.

The movie shows MIPs; all masks and overlap sums are calculated in three dimensions.
"""
from pathlib import Path
import argparse,csv,hashlib,json,subprocess,sys
import h5py,numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont

ap=argparse.ArgumentParser()
ap.add_argument('--evidence-root',type=Path,required=True)
ap.add_argument('--volume-root',type=Path,required=True)
ap.add_argument('--qa-dir',type=Path,required=True)
args=ap.parse_args();sys.path.insert(0,str(args.evidence_root.resolve()))
from unified_metrics import prepare,global_gain,evaluate
from reference_foreground import contrast
root=Path(__file__).resolve().parents[1];qa=args.qa_dir;qa.mkdir(parents=True,exist_ok=True)
out=root/'assets/media';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths={k:args.volume_root/k/'volume.h5' for k in ['BP_50','BP_5']}
arrays={}
for k,p in paths.items():
 with h5py.File(p) as f:
  arrays[k]=np.maximum(f['volume'][:],0).astype('f4')
  if k=='BP_50':axes=[f['axis_'+d][:] for d in 'zyx']
sp=np.array([float(np.abs(np.diff(a)).mean()) for a in axes])
r,x=arrays['BP_50'],arrays['BP_5'];ref,masks=prepare(r,sp)
with h5py.File(args.evidence_root/'results/D09_original_MB_masks.h5') as f:
 for k in ['mask','weak','strong']:assert np.array_equal(masks[k],f[k][:]),k
gain=global_gain(x,r);score=evaluate(x,r,ref,masks,gain)
old=next(row for row in csv.DictReader((args.evidence_root/'results/D09_original_MB_metrics.csv').open()) if row['key']=='BP_5')
for key in ['Q','D_weak','D_strong','SSIM','PSNR','L1','gain']:
 assert abs(score[key]-float(old[key]))<1e-6,(key,score[key],old[key])
hr=ref['hr'];hx=contrast(x,sp);bg=gaussian_filter(r,.4/sp)
parts={}
for key in ['weak','strong']:
 a=(hx*masks[key]).astype('f8')*gain;b=(hr*masks[key]).astype('f8')
 parts[key]=(2*np.minimum(a,b).sum((0,2)),(a+b).sum((0,2)))
trace=dict(reference='D09 measured mouse; 50-exposure BP',reference_display_label='GT',candidate='Same acquisition; 5-exposure BP',candidate_display_label='Test image',
 shape_zyx=list(r.shape),spacing_zyx_mm=sp.tolist(),source_sha256={k:sha(p) for k,p in paths.items()},
 local_contrast_sigma_mm=.4,global_gain=score['gain'],gain_method='One nonnegative least-squares amplitude factor over the complete paired volumes',
 support=dict(reference_only=True,voxels=int(masks['mask'].sum()),weak=int(masks['weak'].sum()),strong=int(masks['strong'].sum()),
 split=float(masks['split']),hessian_scales_mm=[.2,.35,.5],thresholds=[.1,.3],noise_multipliers=[3,6],boundary_margin_mm=1,component_min_volume_mm3=.064,component_min_extent_mm=1),
 score=score,agreement_with_manuscript=True,masks_equal_manuscript=True,
 display=dict(vertical_flip_relative_to_previous=True,projection_row_order='Native Y order; accumulation proceeds from first to last Y row',reconstruction_window='Unchanged: zero to BP50 MIP p99.5'),
 calculation_domain='3D; projections are illustrations. Animation progressively accumulates actual 3D voxel contributions along Y; playback does not represent computation speed.',
 formula='h(I)=max(I-G_0.4mm*I,0); D_s=2 sum_Ms min(g hX,hR)/sum_Ms(g hX+hR); Q=100 sqrt(D_weak D_strong)',
 code_sha256={name:sha(args.evidence_root/name) for name in ['unified_metrics.py','reference_foreground.py']})
(root/'data/q-mouse-calculation.json').write_text(json.dumps(trace,indent=2)+'\n')
W,H=1280,720;bgc='#080f17';ink='#edf4fa';muted='#95aabd';weak='#43a5b5';strong='#c06f4e'
fonts={n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n) for n in [14,16,18,20,24,30,36,52]}
bold={n:ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',n) for n in [18,20,24,30,36,52]}
def text(d,xy,s,size=18,color=ink,b=False):d.text(xy,s,font=(bold if b else fonts)[size],fill=color)
def gray(a,cap=None,size=(190,379)):
 v=a.max(0);cap=float(np.percentile(v,99.5)) if cap is None else cap
 return Image.fromarray(np.uint8(np.clip(v/cap,0,1)*255)).convert('RGB').resize(size,Image.Resampling.BILINEAR)
rawcap=float(np.percentile(r.max(0),99.5));tiles=[gray(r,rawcap),gray(bg),gray(hr)]
groups=np.zeros((*r.shape[1:],3),dtype='uint8');groups[masks['weak'].max(0)]=[67,165,181];groups[masks['strong'].max(0)]=[192,111,78]
tiles.append(Image.fromarray(groups).resize((190,379),Image.Resampling.NEAREST))
candidate=gray(x*gain,rawcap,(96,192))
xs=[36,277,518,759];labels=['GT','Local background','Positive contrast','Weak / strong support']
def frame(t):
 im=Image.new('RGB',(W,H),bgc);d=ImageDraw.Draw(im)
 text(d,(36,23),'PACTHub   /   06  Q IN PRACTICE',16,weak)
 text(d,(36,57),'From mouse data to structural quality.',36,ink,True)
 if t<9:status='Reference-defined support  /  Gaussian background: 0.40 mm'
 elif t<13:status='Test image against GT  /  accumulate shared contrast in both groups'
 else:status='Measured result  /  Dweak 0.7872  ·  Dstrong 0.8654  ·  Q 82.53'
 text(d,(36,112),status,20,muted)
 for j,xp in enumerate(xs):
  text(d,(xp,163),labels[j],18,ink,True)
  d.rectangle((xp-1,202,xp+191,583),outline='#263948',fill='#020509')
  reveal=1 if j==0 else np.clip((t-(j-1)*2.3-.8)/2.1,0,1)
  n=int(379*reveal)
  if n:im.paste(tiles[j].crop((0,0,190,n)),(xp,203))
  if 0<reveal<1:d.line((xp,203+n,xp+190,203+n),fill=weak,width=2)
  if j<3:text(d,(xp+210,374),'→',24,muted)
 text(d,(759,598),'Weak',16,weak);text(d,(852,598),'Strong',16,strong)
 text(d,(36,598),'0.20 mm voxels   ·   3D calculation, MIP illustration',16,muted)
 d.line((992,163,992,620),fill='#293a48',width=1)
 text(d,(1018,163),'Test image',18,ink,True)
 im.paste(candidate,(1018,203))
 text(d,(1130,210),'g = 8.846',14,muted)
 p=float(np.clip((t-9)/4,0,1));stop=max(1,round(p*r.shape[1]));ds=[]
 for k in ['weak','strong']:
  a,b=parts[k];den=b[:stop].sum();ds.append(float(a[:stop].sum()/den) if den else 0.)
 if t>=9:
  y=203+round(p*379);d.line((759,y,949,y),fill='#edf4fa',width=2)
  for j,(name,col) in enumerate([('Weak',weak),('Strong',strong)]):
   yy=419+j*56;text(d,(1018,yy),name,16,col);text(d,(1151,yy),f'{ds[j]:.4f}',18,col,True)
   d.rectangle((1018,yy+27,1237,yy+31),fill='#243543');d.rectangle((1018,yy+27,1018+round(219*ds[j]),yy+31),fill=col)
  text(d,(1018,548),'Q',30,weak,True);text(d,(1062,531),f'{100*np.sqrt(ds[0]*ds[1]):.2f}',52,ink,True)
 else:text(d,(1018,434),'Fixed reference support',16,muted)
 d.line((36,645,1240,645),fill='#263948');d.line((36,645,36+round(1204*min(t/16,1)),645),fill=weak,width=2)
 text(d,(36,665),'Measured mouse  /  BP reconstruction',16,muted)
 text(d,(795,665),'Q complements PSNR, full-image SSIM and L1.',16,muted)
 return im
cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','24','-i','-','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'q-mouse.mp4')]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for i in range(16*24):proc.stdin.write(frame(i/24).tobytes())
proc.stdin.close();assert proc.wait()==0
frame(15).save(root/'assets/images/showcase/q-mouse-poster.webp',lossless=True,method=6)
for t in [4,8,11,15]:frame(t).save(qa/f'q_mouse_{t:02d}.png')
print('MOUSE_Q_COMPLETE',json.dumps(score),flush=True)
