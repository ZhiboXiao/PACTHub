"""Build the public showcase from the audited paper display data.

Usage: python scripts/prepare_showcase.py --source-root PATH_TO_PAPER_FIGURES
Dependencies: numpy, Pillow. No RF or private filesystem paths are published.
"""
from pathlib import Path
import argparse, json, hashlib, csv
import numpy as np
from PIL import Image

ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True)
R=ap.parse_args().source_root;ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'assets/images/showcase';T=ROOT/'assets/images/temporal'
for p in [A,T]:p.mkdir(parents=True,exist_ok=True)
def pair(zh,en):return dict(zh=zh,en=en)
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
asset_records=[]
def convert(src,name):
    image=Image.open(src).convert('RGB');dst=A/(name+'.webp')
    image.save(dst,lossless=True,method=6)
    asset_records.append(dict(file=str(dst.relative_to(ROOT)).replace('\\','/'),source=src.name,source_sha256=sha(src),sha256=sha(dst),dimensions=list(image.size),conversion='Lossless RGB WebP; no added contrast, crop or colour transform'))
    return str(dst.relative_to(ROOT)).replace('\\','/')
spec={v['specimen']:v for v in json.loads((R/'specimen_volume_display.json').read_text())}
author=json.loads((R/'author_volume_display.json').read_text())
scan=json.loads((R/'source_data/scan_sum_20261025/display_record.json').read_text())[-1]
items=[
 ('mouse-rotation',pair('小鼠 · 旋转成像','Mouse · rotation'),'animal','rotation',{'depth':'rotation_depth.png','gray':'author_gray.png','volume':'rotation_3d.png'},
  pair('作者提供的三维小鼠处理体，以轴向深度投影与斜向三维视图呈现血管空间分布。','Author-supplied processed mouse volume, shown as axial depth projections and an oblique 3D view.'),
  '3D-PanoPACT / wholebody_pa_img_processed.mat',author['shape_zyx'],None,
  pair('旋转采集；作者保存的处理后三维体','Rotation acquisition; author-saved processed volume'),
  pair('沿用作者处理体；轴向 MIP 与斜向最大强度体绘制','Author processing retained; axial MIP and oblique maximum-intensity ray casting')),
 ('mouse-scan',pair('小鼠 · 扫描与旋转','Mouse · scan + rotation'),'animal','scan',{'depth':'selected_scan/sum_scan_depth.png','gray':'selected_scan/sum_scan_gray.png'},
  pair('70 个位置扩展全身覆盖。两种带通 BP 三维体等权相加，深度显示保留 0.3 Frangi。','Seventy positions extend whole-body coverage. Two bandpass BP volumes are added with equal weights; depth display retains a 0.3 Frangi contribution.'),
  '20260114_192341_Scan1',[265,1051,641],[.1,.1,.1],
  pair('7×10 位置；6×8 mm 步距；每位置 20 次曝光','7×10 positions; 6×8 mm steps; 20 exposures per position'),
  pair('1508.5 m/s BP；1.44–5.76 + 0.5–8 MHz；等权逐体素相加','1508.5 m/s BP; 1.44–5.76 + 0.5–8 MHz; unit-weight voxelwise sum')),
 ('leaf',pair('叶片 · 分支结构','Leaf · branching structure'),'phantom','rotation',{'depth':'leaf_depth.png','gray':'leaf_gray.png','volume':'leaf_3d.png'},
  pair('叶脉网络提供多尺度分支与细弱结构，用于观察结构连续性与空间覆盖。','A leaf-vein network provides branching and weak structures at multiple scales for examining continuity and coverage.'),
  '20241115_104329',None,None,pair('20 次曝光 BP 体','20-exposure BP volume'),pair('BP；原有物理 XY 裁剪；保留完整 Z','BP; established physical XY crop; all Z slices retained')),
 ('hand',pair('人手 · 血管网络','Hand · vascular network'),'human','rotation',{'depth':'hand_depth.png','gray':'hand_gray.png','volume':'hand_3d.png'},
  pair('人手血管的深度投影与三维展示，与小鼠和叶片采用一致的深度色系。','Depth projections and 3D views of human-hand vasculature use the same depth palette as the mouse and leaf.'),
  '20241128_194710',None,None,pair('20 次曝光 BP 体','20-exposure BP volume'),pair('BP；原有物理 XY 裁剪；保留完整 Z','BP; established physical XY crop; all Z slices retained'))
]
samples=[]
for ident,title,category,mode,images,description,source,shape,spacing,acquisition,reconstruction in items:
    views={k:convert(R/'assets'/f,ident+'-'+k) for k,f in images.items()}
    if ident in spec:
        info=spec[ident]; shape=info['shape_zyx'];spacing=list(reversed(info['spacing_xyz_mm']))
        window=info['display_window'];z=info['extent_xyz_mm'][2];crop=info['crop_xyxy'];gain=False
    elif ident=='mouse-scan':window=[scan['amplitude_floor'],scan['amplitude_cap']];z=[1.9,21.9];crop=None;gain=False
    else:window=[author['mip_display']['lower'],author['mip_display']['upper']];z=None;crop=None;gain=False
    display=dict(palette='3D-PanoPACT Trunk',depth_scale='Relative position within the displayed Z slab, 0–1',z_extent_mm=z,
        intensity_window=window,gamma=1,added_fluence_gain=gain,xy_crop_pixels=crop,rotation_deg=2 if ident=='mouse-scan' else 0,
        view_notes=pair('灰度为强度；颜色为相对深度。各样本独立线性窗。','Grayscale encodes intensity; colour encodes relative depth. Each specimen has an independent linear window.'))
    samples.append(dict(id=ident,title=title,is_demo=False,category=category,mode=mode,split='unspecified',tags=[category,mode,'3D','BP'],
      description=description,preview=views['depth'],views=views,dimensions=shape,axis_order=['z','y','x'],spacing_mm=spacing,
      wavelength_nm=None,intensity_unit='a.u.',data_version='showcase-2026-10-25',display=display,
      provenance=dict(source_id=source,acquisition=acquisition,reconstruction=reconstruction,standardization_reference='docs/data-guide.html'),files=[]))
    write(ROOT/'data'/(ident+'.json'),samples[-1])
write(ROOT/'data/samples.json',samples)
# The palette is data-defined, not a generic CSS rainbow.
lut=np.load(R/'source_data/selected_scan/depth_lut_rgb.npy').astype('uint8')
Image.fromarray(np.repeat(lut[None,:,:],8,axis=0)).save(A/'depth-lut.png')
# Author-volume hero, with the complete foreground and enclosing 3D box retained.
hero=Image.new('RGB',(1040,900),'black')
for i,name in enumerate(['mouse-rotation-volume.webp','mouse-rotation-depth.webp']):
    im=Image.open(A/name);im.thumbnail((495,850),Image.Resampling.LANCZOS);hero.paste(im,(i*520+(520-im.width)//2,(900-im.height)//2))
hero.save(A/'hero-pair.webp',lossless=True,method=6)

original=json.loads((R/'dynamic_display.json').read_text());series=[];csvrows=[]
for c,folder,ident,title in zip(original['cases'],['dynamic_mouse2','dynamic_first20'],['wholebody','abdominal'],
    [pair('全身连续成像','Whole-body time series'),pair('腹部连续成像 · 800 nm','Abdominal time series · 800 nm')]):
    data=np.load(R/'source_data'/folder/'mips.npz');a=data['xy'];x,y=data['x'],data['y'];X,Y=np.meshgrid(x,y)
    assert len(a)==len(c['time_minutes']) and np.isfinite(a).all()
    frames=[]
    for i,v in enumerate(a):
        path=T/f'{ident}-{i:02d}.webp';image=np.uint8(np.rint(np.clip(v[::-1]/c['cap'],0,1)*255));Image.fromarray(image).save(path,lossless=True,method=6)
        frames.append(dict(time_min=c['time_minutes'][i],image=str(path.relative_to(ROOT)).replace('\\','/')))
    regions=[]
    labels=[pair('中央下部','Lower central'),pair('中央上部','Upper central'),pair('图像左侧腹部','Image-left abdomen'),pair('图像右侧腹部','Image-right abdomen')]
    bounds=[v['bounds_xy_mm'] for v in c['rois']]+[[-16,-8,-18,-6],[8,16,-18,-6]]
    for i,(b,label) in enumerate(zip(bounds,labels)):
        l,r,bt,tp=b;mask=(X>=l)&(X<=r)&(Y>=bt)&(Y<=tp);mean=a[:,mask].mean(1,dtype=np.float64);relative=mean/mean[0]
        if i<2:assert np.allclose(mean,c['rois'][i]['mean_linear'],rtol=1e-12,atol=1e-12)
        regions.append(dict(id=f'roi-{i+1}',label=label,bounds_xy_mm=b,pixel_count=int(mask.sum()),mean_linear=mean.tolist(),relative_mean=relative.tolist(),anatomical_label_verified=False))
        for j,tm in enumerate(c['time_minutes']):csvrows.append(dict(series=ident,time_min=tm,roi=f'roi-{i+1}',mean_linear=mean[j],relative_to_first=relative[j]))
    series.append(dict(id=ident,title=title,source_series=c['source_series'],frames=frames,regions=regions,extent_xy_mm=c['extent_xy_mm'],
       exposure_count=20,speed_m_s=c['speed_m_s'],wavelength_nm=800 if ident=='abdominal' else None,
       display_window=[0,c['cap']],gamma=1,shared_window_across_time=True,duration_minutes=c['duration_minutes'],display_flip_y=ident=='abdominal',
       measured_timepoints=len(a),available_acquisitions=c['source_available'],quantification='Mean of the original linear BP MIP inside fixed physical XY regions; relative values divide by the first acquisition',
       units='a.u.',time_origin='First recorded acquisition; injection time is not specified',source_sha256=sha(R/'source_data'/folder/'mips.npz')))
write(ROOT/'data/temporal.json',dict(series=series,presentation='Images and markers step through measured acquisitions. Curves progressively reveal measured points; connecting segments are visual guides. Playback timing is compressed.'))
with (ROOT/'data/temporal-readouts.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=csvrows[0]);w.writeheader();w.writerows(csvrows)
write(ROOT/'data/display-provenance.json',dict(version='2026-10-25',assets=asset_records,
    relative_depth='One Trunk LUT across specimens, normalized to each displayed depth slab. Absolute specimen depths are not equated.',
    temporal='Fixed linear display cap within each series; ROI readouts use original floating-point MIPs, before image encoding.',
    inputs=[dict(file='author_volume_display.json',sha256=sha(R/'author_volume_display.json')),dict(file='specimen_volume_display.json',sha256=sha(R/'specimen_volume_display.json')),dict(file='dynamic_display.json',sha256=sha(R/'dynamic_display.json'))]))
print('Built',len(samples),'specimens,',sum(len(s['frames']) for s in series),'measured temporal frames and',len(csvrows),'ROI readings.')
