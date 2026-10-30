"""Rigid XY registration of displayed linear BP MIPs, before image encoding.

Run after prepare_showcase.py. No per-frame intensity normalization is applied
to the quantitative arrays. Feature normalization is only used for alignment.
"""
from pathlib import Path
import argparse, json, csv, hashlib
import numpy as np
import cv2
from PIL import Image, ImageDraw
from display_utils import scale_bar

ap=argparse.ArgumentParser()
ap.add_argument('--source-root',type=Path,required=True)
ap.add_argument('--qa-dir',type=Path,required=True)
args=ap.parse_args(); root=Path(__file__).resolve().parents[1]
args.qa_dir.mkdir(parents=True,exist_ok=True)
data=json.loads((root/'data/temporal.json').read_text(encoding='utf-8'))
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def feature(a):
    a=np.sqrt(np.clip(a/np.percentile(a,99.8),0,1)).astype('f4')
    a=np.maximum(cv2.GaussianBlur(a,(0,0),1)-cv2.GaussianBlur(a,(0,0),12),0)
    return (a/max(float(a.max()),1e-10)).astype('f4')
def warp(a,m):return cv2.warpAffine(a,m,(a.shape[1],a.shape[0]),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
def corr(a,b,mask):return float(np.corrcoef(a[mask],b[mask])[0,1])
csvrows=[]; audits=[]
for s,folder in zip(data['series'],['dynamic_mouse2','dynamic_first20']):
    original=np.load(args.source_root/'source_data'/folder/'mips.npz')
    a=original['xy'].astype('f4'); x,y=original['x'],original['y'];h,w=a.shape[1:]
    records=json.loads((args.source_root/'source_data'/folder/'record.json').read_text())['records']
    ref=feature(a[0]); yy,xx=np.indices(ref.shape)
    metricmask=(xx>30)&(xx<w-30)&(yy>40)&(yy<h-40)
    aligned=[];valid=[];transforms=[]
    for i,im in enumerate(a):
        f=feature(im); best=None
        # Euclidean transform: rotation about Z plus XY translation, no scaling.
        for angle in ([0] if i==0 else [0,-8,8]):
            m=cv2.getRotationMatrix2D((w/2,h/2),angle,1).astype('f4')
            try:
                if i:
                    for scale in [4,2,1]:
                        r=cv2.resize(ref,(w//scale,h//scale),interpolation=cv2.INTER_AREA)
                        q=cv2.resize(f,(w//scale,h//scale),interpolation=cv2.INTER_AREA)
                        ms=m.copy();ms[:,2]/=scale
                        ecc,ms=cv2.findTransformECC(r,q,ms,cv2.MOTION_EUCLIDEAN,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,160,1e-6),None,5)
                        m=ms.copy();m[:,2]*=scale
                score=corr(ref,warp(f,m),metricmask)
                if best is None or score>best[0]:best=(score,m.copy())
            except cv2.error:continue
        if best is None:raise RuntimeError(f'Registration failed: {s["id"]} {i}')
        score,m=best; forward=cv2.invertAffineTransform(m)
        deg=float(np.degrees(np.arctan2(forward[1,0],forward[0,0])))
        centre=np.array([w/2,h/2]);shift=forward[:,:2]@centre+forward[:,2]-centre
        if abs(deg)>25 or np.linalg.norm(shift)>80:raise ValueError(('Unexpected rigid motion',i,deg,shift))
        aligned.append(warp(im,m));valid.append(warp(np.ones((h,w),'f4'),m)>.999)
        tr=dict(acquisition_id=records[i]['group_id'],rotation_z_deg=deg,center_shift_xy_pixels=shift.tolist(),center_shift_xy_mm=(shift*[np.median(np.diff(x)),np.median(np.diff(y))]).tolist(),output_to_input_matrix=m.tolist(),input_to_reference_matrix=forward.tolist(),feature_ncc_before=corr(ref,f,metricmask),feature_ncc_after=score)
        transforms.append(tr);print(s['id'],i,round(deg,3),np.round(shift,2),round(tr['feature_ncc_before'],3),round(score,3),flush=True)
    aligned=np.stack(aligned);common=np.all(valid,axis=0);X,Y=np.meshgrid(x,y)
    rotate_display=s['id']=='wholebody'
    for i,(im,frame) in enumerate(zip(aligned,s['frames'])):
        screen=np.uint8(np.rint(np.clip(im[::-1]/s['display_window'][1],0,1)*255))
        if rotate_display:screen=np.rot90(screen,2).copy()
        if s.get('display_flip_y'):screen=screen[::-1].copy()
        annotated,bar=scale_bar(Image.fromarray(screen),1/float(np.median(np.diff(x))),5,font_fraction=.06)
        annotated.save(root/frame['image'],lossless=True,method=6)
        frame['acquisition_id']=records[i]['group_id']
    s['scale_bar']=bar
    for r in s['regions']:
        l,rt,b,t=r['bounds_xy_mm'];mask=(X>=l)&(X<=rt)&(Y>=b)&(Y<=t)
        coverage=float(common[mask].mean());mask &= common
        assert coverage>.95,(s['id'],r['id'],coverage)
        mean=aligned[:,mask].mean(1,dtype='f8');r.update(pixel_count=int(mask.sum()),common_valid_fraction=coverage,mean_linear=mean.tolist(),relative_mean=(mean/mean[0]).tolist())
        for i,tm in enumerate(s['frames']):csvrows.append(dict(series=s['id'],time_min=tm['time_min'],roi=r['id'],mean_linear=mean[i],relative_to_first=mean[i]/mean[0]))
    if rotate_display:
        names=[('中央上部','Upper central'),('中央下部','Lower central'),('图像右侧腹部','Image-right abdomen'),('图像左侧腹部','Image-left abdomen')]
        for r,(zh,en) in zip(s['regions'],names):r['label']=dict(zh=zh,en=en)
    s['display_rotation_deg']=180 if rotate_display else 0
    s['registration']=dict(model='Rigid XY (Z rotation + translation)',reference_acquisition=records[0]['group_id'],reference_frame=0,method='Multiscale Euclidean ECC on local-contrast features',interpolation='Bilinear; a single resampling of each original linear MIP',intensity_normalization=False,common_valid_fraction=float(common.mean()),transforms=transforms)
    s['quantification']='Mean of registered linear BP MIPs in fixed reference-coordinate ROIs, restricted to the same valid pixels at every timepoint. Relative values divide by the first acquisition.'
    np.savez_compressed(args.qa_dir/(s['id']+'_registered.npz'),registered=aligned,original=a,common_valid=common,x=x,y=y)
    # Diagnostic colour overlay: reference red, moving cyan, agreement white.
    chosen=[0,len(a)//3,2*len(a)//3,len(a)-1];canvas=Image.new('RGB',(4*300,2*620),(8,16,24));d=ImageDraw.Draw(canvas)
    for col,i in enumerate(chosen):
        for row,im in enumerate([a[i],aligned[i]]):
            rr=np.clip(a[0]/s['display_window'][1],0,1);qq=np.clip(im/s['display_window'][1],0,1)
            rgb=np.uint8(np.stack([rr,qq,qq],-1)[::-1]*255)
            if rotate_display:rgb=np.rot90(rgb,2).copy()
            if s.get('display_flip_y'):rgb=rgb[::-1].copy()
            tile=Image.fromarray(rgb);tile.thumbnail((288,572));canvas.paste(tile,(col*300+(300-tile.width)//2,row*620+35))
            d.text((col*300+12,row*620+8),f'{"BEFORE" if row==0 else "REGISTERED"} / {s["frames"][i]["time_min"]:.2f} min',fill='white')
    canvas.save(args.qa_dir/(s['id']+'_registration.png'))
    audits.append(dict(series=s['id'],timepoints=len(a),mean_feature_ncc_before=float(np.mean([v['feature_ncc_before'] for v in transforms[1:]])),mean_feature_ncc_after=float(np.mean([v['feature_ncc_after'] for v in transforms[1:]])),rotation_range_deg=[min(v['rotation_z_deg'] for v in transforms),max(v['rotation_z_deg'] for v in transforms)],max_center_shift_mm=max(np.linalg.norm(v['center_shift_xy_mm']) for v in transforms),minimum_roi_valid_fraction=min(r['common_valid_fraction'] for r in s['regions'])))
dump(root/'data/temporal.json',data);dump(root/'data/registration-summary.json',audits)
with (root/'data/temporal-readouts.csv').open('w',newline='',encoding='utf-8') as f:
    wr=csv.DictWriter(f,fieldnames=csvrows[0]);wr.writeheader();wr.writerows(csvrows)
print(json.dumps(audits,indent=2),flush=True)
