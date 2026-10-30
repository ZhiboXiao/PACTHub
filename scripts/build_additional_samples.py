"""Measured and official-release specimens with one shared physical display grid."""
from pathlib import Path
import argparse,hashlib,itertools,json
import h5py,numpy as np,vtk,cv2
from vtk.util.numpy_support import numpy_to_vtk,vtk_to_numpy
from PIL import Image,ImageDraw,ImageFont
ap=argparse.ArgumentParser();ap.add_argument('--dataset-root',type=Path,required=True);ap.add_argument('--paper-root',type=Path,required=True);ap.add_argument('--official-root',type=Path,required=True);ap.add_argument('--qa-dir',type=Path,required=True)
ap.add_argument('--only',nargs='+',help='Regenerate only these specimen IDs; retain the other numerical views and records.')
args=ap.parse_args();root=Path(__file__).resolve().parents[1];qa=args.qa_dir;qa.mkdir(exist_ok=True,parents=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
pair=lambda zh,en:dict(zh=zh,en=en)
items=[
 ('mouse-brain','3DPanoPACT-Fig3','Animal',None,None,'小鼠脑 · 全脑血管','Mouse brain · whole-brain vessels','Brain_Anatomy_functions_Fig.3_Fig.4/whole_brain_STINT_processed.mat','3D-PanoPACT 官方发布的全脑三维处理体，展示皮层与深层血管网络。','The official 3D-PanoPACT whole-brain processed volume reveals cortical and deeper vascular networks.'),
 ('mouse-body','3DPanoPACT-Fig5d','Animal',None,None,'小鼠 · 背侧全躯干','Mouse · dorsal whole trunk','Whole-trunk_Dynamics_Reconstruction_Fig.5/backside_view_time_point.mat','3D-PanoPACT 官方发布的背侧全躯干三维体，展示长血管主干与密集分支。','The official 3D-PanoPACT dorsal whole-trunk volume displays long vascular trunks and dense peripheral branching.'),
 ('mouse-liver','3DPanoPACT-Fig2a','Animal',None,None,'小鼠肝脏 · 单次曝光','Mouse liver · single exposure','Real-time_liver_dynamics_Fig.2/liver_singleframe_processed.mat','3D-PanoPACT 官方发布的单帧肝脏三维结果，展示器官内部的分支血管。','The official 3D-PanoPACT single-frame liver volume reveals branching vessels within an organ.'),
 ('square-phantom','20230920_150300','Phantom',[100,305,240,435],None,'方形靶仿体 · 多尺度结构','Square-target phantom · multiple scales','3D-PACT-DATA/FollowingExperiments/LowFrequencyTarget/WithRotation','三个不同大小的方形靶展示实体内部与边缘的光声响应。三种视图来自同一组 20 次曝光 BP 重建。','Three square targets of different sizes show photoacoustic responses within and along the edges of solid objects. All views use the same 20-exposure BP volume.')]
camera=load(args.paper_root/'author_volume_display.json')['render'];up=np.asarray(camera['camera_view_up']);normal=np.array(camera['camera_position'])-camera['camera_focal_point'];normal/=np.linalg.norm(normal);right=np.cross(up,normal)
def colour(n):
 phase=-(np.arange(n+2)-(n+2)/2)/(n+2)*1.75*np.pi;peaks=np.array([5/16,-3/16,-.9])*np.pi;rgb=np.empty((n+2,3))
 for c,(width,mean) in enumerate(zip([1.4,1,.4],[.7,.7,.5])):
  rgb[:,c]=1-2*(1-mean)*(np.cos(phase-(np.pi+peaks[c]))/2+.5)**width if width>1 else 2*(mean-.5)+2*(1-mean)*(np.cos(phase-peaks[c])/2+.5)**(1/width)
 return rgb[1:-1]
samples=load(root/'data/samples.json');prov=load(root/'data/display-provenance.json');records=[];assets=[]
plans={a['id']:a for a in load(root/'scripts/additional_specimen_views.json')}
extra_ids={'mouse-brain','mouse-body','mouse-liver','zebrafish','brain-ex-vivo','network-phantom','square-phantom'}
if args.only:
 selected=set(args.only);assert selected<={i[0] for i in items},selected
 items=[i for i in items if i[0] in selected]
 extra_ids=selected|{'zebrafish','brain-ex-vivo','network-phantom'}
 removed_gids={s['acquisition_id'] for s in samples if s['id'] in extra_ids}
 records=[r for r in load(root/'data/additional-specimens.json') if r['sample_id'] not in removed_gids]
samples=[s for s in samples if s['id'] not in extra_ids]
prov['assets']=[a for a in prov['assets'] if not any('/'+ident+'-' in a['file'] for ident in extra_ids)]
for ident,gid,category,crop,wl,zh,en,source,desczh,descen in items:
 plan=plans[ident];assert plan['gid']==gid
 official=plan.get('source_kind')=='official_release'
 z0,z1=plan['native_z_slice'];l,t,r,b=plan['crop_rotated_xyxy']
 # Rotate the numeric volume once, directly into the final shared display grid.
 # No independent image-plane crop or rotation is applied to any rendered view.
 M=np.asarray(plan['affine_source_to_full_display_index'],dtype='f8');M[:,2]-=[l,t]
 if official:
  volume_path=args.official_root/source
  with h5py.File(volume_path) as f:
   a=f[plan['variable']];native_shape=[a.shape[0],a.shape[2],a.shape[1]];native=a[z0:z1].transpose(0,2,1)
  # Reorient the numeric volume before all projections; preserve handedness.
  if plan.get('flip_axes_zyx'):native=np.flip(native,axis=tuple(plan['flip_axes_zyx']))
  native=np.maximum(native,0);spacing=np.asarray(plan['spacing_xyz_mm']);zaxis=np.arange(z0,z1)*spacing[2]
  reconstruction=dict(method=plan.get('reconstruction_method','Author-released STINT processed volume'),frame_count=plan.get('frame_count'),extra_filter=None,extra_fluence_gain=False)
 else:
  p=args.dataset_root/category/gid[:8]/gid/'Image_PA/GT20';params=load(p/'effective_parameters.json')['defaults'];result=load(p/'result.json');volume_path=p/'volume.h5'
  with h5py.File(volume_path) as f:
   native=f['volume'][z0:z1];zaxis=f['axis_z'][z0:z1];native_shape=list(f['volume'].shape)
  spacing=np.array(plan.get('spacing_xyz_mm',[.1,.1,float(np.abs(np.diff(zaxis)).mean())]))
  reconstruction=dict(method='BP',frame_count=result['frame_count'],frames_1based=result['frames_1based'],sound_speed_mps=result['speed_m_s'],sampling_frequency_hz=params['signal']['sampling_frequency_hz'],filter=params['signal']['filter'],postprocess=params['reconstruction']['postprocess'])
 v=np.stack([cv2.warpAffine(z,M,(r-l,b-t),flags=cv2.INTER_LINEAR) for z in native]);del native
 if plan.get('post_crop_flip_axes_zyx'):
  v=np.flip(v,axis=tuple(plan['post_crop_flip_axes_zyx'])).copy()
 if plan.get('preserve_full_volume'):
  assert [z0,z1,l,t,r,b]==[0,native_shape[0],0,0,native_shape[2],native_shape[1]],'Full-volume specimen must retain every XYZ index'
  assert list(v.shape)==native_shape
 assert np.isfinite(v).all() and v.min()>=0
 origin=plan['rotated_origin_xy_mm'];axes=[origin[0]+np.arange(l,r)*spacing[0],origin[1]+np.arange(t,b)*spacing[1],zaxis]
 size=spacing*(np.array(v.shape[::-1])-1)
 amp=v.max(0);lo,cap=plan['window'];bright=np.clip((amp-lo)/(cap-lo),0,1)
 images={'gray':Image.fromarray(np.uint8(np.rint(bright[::-1]*255))).convert('RGB'),'depth':Image.fromarray(np.uint8(np.rint((colour(v.shape[0])[v.argmax(0)]*bright[...,None])[::-1]*255)))}
 data=vtk.vtkImageData();data.SetDimensions(*v.shape[::-1]);data.SetSpacing(*spacing);data.GetPointData().SetScalars(numpy_to_vtk(np.ascontiguousarray(v[::-1,::-1,::-1]).ravel(),deep=True,array_type=vtk.VTK_FLOAT))
 mapper=vtk.vtkGPUVolumeRayCastMapper();mapper.SetInputData(data);mapper.SetBlendModeToMaximumIntensity();mapper.AutoAdjustSampleDistancesOff();mapper.SetSampleDistance(float(spacing.min()*.65))
 col=vtk.vtkColorTransferFunction();col.AddRGBPoint(lo,0,0,0);col.AddRGBPoint(cap,1,1,1);opacity=vtk.vtkPiecewiseFunction();opacity.AddPoint(0,1);opacity.AddPoint(float(v.max()),1)
 prop=vtk.vtkVolumeProperty();prop.SetColor(col);prop.SetScalarOpacity(opacity);prop.SetInterpolationTypeToLinear();prop.ShadeOff();actor=vtk.vtkVolume();actor.SetMapper(mapper);actor.SetProperty(prop)
 ren=vtk.vtkRenderer();ren.SetBackground(0,0,0);ren.AddVolume(actor);centre=size/2;cam=ren.GetActiveCamera();cam.SetFocalPoint(*centre);cam.SetPosition(*(centre+normal*max(size)*5));cam.SetViewUp(*up);cam.ParallelProjectionOn()
 corners=np.array(list(itertools.product(*[[0,q] for q in size])))-centre;width=np.ptp(corners@right);height=np.ptp(corners@up);H=1000;W=round(H*width/height);cam.SetParallelScale(float(height*.52));ppm=H/(2*cam.GetParallelScale())
 outline=vtk.vtkOutlineFilter();outline.SetInputData(data);om=vtk.vtkPolyDataMapper();om.SetInputConnection(outline.GetOutputPort());oa=vtk.vtkActor();oa.SetMapper(om);oa.GetProperty().SetColor(1,.66,0);oa.GetProperty().SetLineWidth(1.5)
 win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetMultiSamples(0);win.SetSize(W,H);win.AddRenderer(ren);over=vtk.vtkRenderer();over.SetLayer(1);over.SetActiveCamera(cam);over.AddActor(oa);win.SetNumberOfLayers(2);win.AddRenderer(over);ren.ResetCameraClippingRange();win.Render()
 filt=vtk.vtkWindowToImageFilter();filt.SetInput(win);filt.SetInputBufferTypeToRGB();filt.ReadFrontBufferOff();filt.Update();pix=vtk_to_numpy(filt.GetOutput().GetPointData().GetScalars()).reshape(H,W,3)[::-1];yy,xx=np.where(pix.max(2)>8);box=[max(0,int(xx.min())-12),max(0,int(yy.min())-12),min(W,int(xx.max())+13),min(H,int(yy.max())+13)];images['volume']=Image.fromarray(pix).crop(box);win.Finalize()
 views={};bars={}
 for view in ['depth','gray','volume']:
  im=images[view]
  filename=f'assets/images/showcase/{ident}-{view}.webp';im.save(root/filename,lossless=True,method=6);views[view]=filename;pxmm=ppm if view=='volume' else 1/spacing[0]
  bar_mm=plan.get('scale_bar_mm',5)
  bars[view]=dict(length_mm=bar_mm,length_pixels=bar_mm*pxmm,pixels_per_mm=pxmm,position='lower right of preview frame; calibrated HTML overlay')
  assets.append(dict(file=filename,sha256=sha(root/filename),dimensions=list(im.size),conversion=('Linear author-released volume display' if official else 'Linear BP display')+'; calibrated HTML scale overlay',scale_bar=bars[view]))
 extent=[[float(a[0]),float(a[-1])] for a in axes]
 # Share the same physical bounds for all three views, including the selected Z slab.
 record=dict(sample_id=gid,source_id=source,source_volume_sha256=sha(volume_path),parameter_sha256=None if official else sha(p/'effective_parameters.json'),native_shape_zyx=native_shape,displayed_shape_zyx=list(v.shape),crop_xyxy=plan['crop_rotated_xyxy'],crop_coordinates='Rotated display frame, lower-origin Y; shared XYZ field for all views',extent_xyz_mm=extent,spacing_xyz_mm=spacing.tolist(),view_extent_xyz_mm={key:extent for key in views},rotation_ccw_deg=plan['rotation_ccw_deg'],rotation_centre_xy_mm=plan['rotation_centre_xy_mm'],source_pixel_to_display_pixel=M.tolist(),native_z_slice=[z0,z1],interpolation='Exact axis permutation and crop' if official else 'One bilinear XY resampling per native Z slice',intensity_window=[lo,cap],window_reference='Fixed pre-crop specimen window; no brightness refit after rotation or crop',gamma=1,camera_direction=normal.tolist(),camera_view_up=up.tolist(),camera_parallel_scale_mm=cam.GetParallelScale(),volume_render_crop=box,reconstruction=reconstruction)
 if official:record.update(official_release=plan['release'],scale_calibration=plan['scale_calibration'],flip_axes_zyx=plan.get('flip_axes_zyx',[]),native_axis_coordinates_mm=None)
 if plan.get('preserve_full_volume'):record['spatial_crop_applied']=False
 if plan.get('post_crop_flip_axes_zyx'):record['post_crop_flip_axes_zyx']=plan['post_crop_flip_axes_zyx']
 records.append(record)
 mode=plan.get('acquisition_mode','scan' if ident=='mouse-body' else 'rotation')
 item=dict(id=ident,title=pair(zh,en),is_demo=False,category='ex-vivo' if ident=='brain-ex-vivo' else category.lower(),mode=mode,split='unspecified',tags=[category.lower(),mode,'3D','official release' if official else 'BP'],description=pair(desczh,descen),preview=views['depth'],views=views,dimensions=list(v.shape),axis_order=['z','y','x'],spacing_mm=spacing[::-1].tolist(),wavelength_nm=wl,intensity_unit='a.u.',data_version='figshare-v3' if official else 'showcase-2026-10-25',acquisition_id=gid,
  display=dict(palette='3D-PanoPACT Trunk',depth_scale='Relative position within the displayed Z slab, 0–1',z_extent_mm=extent[2],extent_xyz_mm=extent,view_extent_xyz_mm={key:extent for key in views},intensity_window=[lo,cap],gamma=1,added_fluence_gain=False,xy_crop_pixels=plan['crop_rotated_xyxy'],crop_frame='Rotated physical display frame; common XYZ crop for depth, gray and volume',rotation_deg=plan['rotation_ccw_deg'],rotation_convention='Positive is counterclockwise in the displayed XY image',compact_preview=True,asset_revision=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()[:12],scale_bars=bars,view_notes=pair('三种视图使用同一旋转、同一 XYZ 物理范围和线性窗。','All three views share one rotation, XYZ field and linear window.')),
  provenance=dict(source_id=source,acquisition=pair(f'官方发布样本 {gid}；Figshare v3',f'Official release specimen {gid}; Figshare v3') if official else pair(f'20 次曝光；采集编号 {gid}',f'20 exposures; acquisition {gid}'),reconstruction=pair('作者发布的 STINT 三维处理体','Author-released STINT processed volume') if official else pair(f'BP；声速 {result["speed_m_s"]} m/s；0.5–6 MHz 带通',f'BP; {result["speed_m_s"]} m/s; 0.5–6 MHz bandpass'),standardization_reference='docs/data-guide.html'),files=[])
 if official:
  for field in ('acquisition_name','acquisition_summary','wavelength_description','description','acquisition_groups'):
   if field in plan:item[field]=plan[field]
  if item.get('acquisition_name'):
   item['provenance']['acquisition']=pair(item['acquisition_name']+'；'+item['acquisition_summary']['zh'],item['acquisition_name']+'; '+item['acquisition_summary']['en'])
  item['provenance']['reconstruction']=plan.get('reconstruction_label',pair('作者发布的 STINT 三维处理体','Author-released STINT processed volume'))
  item['provenance']['official_release']={**plan['release'],'source_data':dict(file=source,variable=plan['variable'],shape_hdf5=[native_shape[0],native_shape[2],native_shape[1]],sha256=record['source_volume_sha256'],size_bytes=volume_path.stat().st_size,data_type='Numeric three-dimensional reconstruction volume')};item['display']['scale_calibration']=plan['scale_calibration'];item['display']['native_axis_coordinates_mm']=None
 if plan.get('preserve_full_volume'):item['display']['spatial_crop_applied']=False
 if plan.get('post_crop_flip_axes_zyx'):item['display']['post_crop_flip_axes_zyx']=plan['post_crop_flip_axes_zyx']
 samples=[s for s in samples if s['id']!=ident];samples.append(item);dump(root/'data'/f'{ident}.json',item);print('ADDED',gid,list(v.shape),flush=True)
display_order=['mouse-rotation','mouse-scan','leaf','hand',*plans]
samples.sort(key=lambda s:display_order.index(s['id']))
record_order=[s['acquisition_id'] for s in samples]
records.sort(key=lambda r:record_order.index(r['sample_id']))
dump(root/'data/samples.json',samples);dump(root/'data/additional-specimens.json',records)
dump(root/'data/official-volume-sources.json',[dict(id=s['id'],release_id=s['acquisition_id'],**s['provenance']['official_release']) for s in samples if s['provenance'].get('official_release')])
replaced={a['file'] for a in assets};prov['assets']=[a for a in prov['assets'] if a['file'] not in replaced]+assets;dump(root/'data/display-provenance.json',prov)
sheet=Image.new('RGB',(1200,1560),'#080f17');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for j,item in enumerate(samples[-4:]):
 for i,view in enumerate(['depth','gray','volume']):
  im=Image.open(root/item['views'][view]);im.thumbnail((380,330));sheet.paste(im,(i*400+(400-im.width)//2,j*390+45+(330-im.height)//2));draw.text((i*400+15,j*390+10),item['acquisition_id']+' / '+view,font=font,fill='white')
sheet.save(qa/'additional_samples.png')
