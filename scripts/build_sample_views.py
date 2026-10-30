"""Prepare tight sample views, calibrated scale bars, and scan 3D ray casting."""
from pathlib import Path
import argparse,json,itertools,hashlib
import numpy as np,cv2,h5py,vtk
from vtk.util.numpy_support import numpy_to_vtk,vtk_to_numpy
from PIL import Image
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--scan-volume',type=Path,required=True);ap.add_argument('--qa-dir',type=Path,required=True)
args=ap.parse_args();root=Path(__file__).resolve().parents[1];R=args.source_root;A=root/'assets/images/showcase'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
camrec=load(R/'author_volume_display.json')['render'];up=np.array(camrec['camera_view_up']);normal=np.array(camrec['camera_position'])-camrec['camera_focal_point'];normal/=np.linalg.norm(normal);right=np.cross(up,normal)
# Transfer the labelled 5-mm bar from the original PPT through the audited
# manuscript-to-render camera scale. Do not invent native physical axes.
original_bar_pixels=1471*(228790/1971164)
camera_fit=load(R/'qa/author_view_camera.json')['isotropic_view_scale_from_reference']
author_px_per_mm=original_bar_pixels*camera_fit/5
author_display_mm_per_voxel=(1500/(2*camrec['parallel_scale']))/author_px_per_mm
author_calibration=dict(method='Transfer original Figure 6b 5-mm scale bar through matched volume-box projection',original_bar_emu=228790,original_image_width_emu=1971164,original_image_width_pixels=1471,original_bar_pixels=original_bar_pixels,matched_camera_scale=camera_fit,current_render_pixels_per_mm=author_px_per_mm,display_mm_per_voxel_inferred=author_display_mm_per_voxel,native_coordinate_axes_available=False)
# The scan uses the identical display slab and exact full-resolution Frangi
# volume as the existing depth MIP. Rotate once and crop the shared XY field.
with h5py.File(args.scan_volume) as f:
    v=f['volume_zyx'][:];axes=[f[k+'_mm'][:] for k in 'xyz']
record=load(R/'source_data/scan_sum_20261025/display_record.json')[-1]
h,w=v.shape[1:];M=cv2.getRotationMatrix2D(((18-axes[0][0])/.1,(-32-axes[1][0])/.1),-2,1)
# Crop specified in final screen coordinates; same for grayscale and depth.
crop=[70,45,590,1010];l,t,r,b=crop
for k in range(len(v)):v[k]=cv2.warpAffine(v[k],M,(w,h),flags=cv2.INTER_LINEAR)
v=v[:,h-b:h-t,l:r];spacing=np.array([.1,.1,.1]);size=spacing*(np.array(v.shape[::-1])-1)
data=vtk.vtkImageData();data.SetDimensions(*v.shape[::-1]);data.SetSpacing(*spacing)
data.GetPointData().SetScalars(numpy_to_vtk(np.ascontiguousarray(v[::-1,::-1,::-1]).ravel(),deep=True,array_type=vtk.VTK_FLOAT))
mapper=vtk.vtkGPUVolumeRayCastMapper();mapper.SetInputData(data);mapper.SetBlendModeToMaximumIntensity();mapper.AutoAdjustSampleDistancesOff();mapper.SetSampleDistance(.065)
col=vtk.vtkColorTransferFunction();col.AddRGBPoint(0,0,0,0);col.AddRGBPoint(record['amplitude_cap'],1,1,1)
opacity=vtk.vtkPiecewiseFunction();opacity.AddPoint(0,1);opacity.AddPoint(float(v.max()),1)
prop=vtk.vtkVolumeProperty();prop.SetColor(col);prop.SetScalarOpacity(opacity);prop.SetInterpolationTypeToLinear();prop.ShadeOff()
actor=vtk.vtkVolume();actor.SetMapper(mapper);actor.SetProperty(prop)
ren=vtk.vtkRenderer();ren.SetBackground(0,0,0);ren.AddVolume(actor);centre=size/2
cam=ren.GetActiveCamera();cam.SetFocalPoint(*centre);cam.SetPosition(*(centre+normal*max(size)*5));cam.SetViewUp(*up);cam.ParallelProjectionOn()
corners=np.array(list(itertools.product(*[[0,q] for q in size])))-centre
width=np.ptp(corners@right);height=np.ptp(corners@up);H=1300;W=round(H*width/height);cam.SetParallelScale(float(height*.52));ppm=H/(2*cam.GetParallelScale())
outline=vtk.vtkOutlineFilter();outline.SetInputData(data);om=vtk.vtkPolyDataMapper();om.SetInputConnection(outline.GetOutputPort());oa=vtk.vtkActor();oa.SetMapper(om);oa.GetProperty().SetColor(1,.66,0);oa.GetProperty().SetLineWidth(1.8)
win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetMultiSamples(0);win.SetSize(W,H);win.AddRenderer(ren)
over=vtk.vtkRenderer();over.SetLayer(1);over.SetActiveCamera(cam);over.AddActor(oa);win.SetNumberOfLayers(2);win.AddRenderer(over);ren.ResetCameraClippingRange();win.Render()
filt=vtk.vtkWindowToImageFilter();filt.SetInput(win);filt.SetInputBufferTypeToRGB();filt.ReadFrontBufferOff();filt.Update();pix=vtk_to_numpy(filt.GetOutput().GetPointData().GetScalars()).reshape(H,W,3)[::-1]
yy,xx=np.where(pix.max(2)>8);box=[max(0,int(xx.min())-12),max(0,int(yy.min())-12),min(W,int(xx.max())+13),min(H,int(yy.max())+13)]
scan3d=Image.fromarray(pix).crop(box);win.Finalize()
scan3d.save(args.qa_dir/'scan_3d_unannotated.png')
samples=load(root/'data/samples.json');spec={r['specimen']:r for r in load(R/'specimen_volume_display.json')};provenance=load(root/'data/display-provenance.json');assets=[]
ids={'mouse-rotation':'20241213_150841','mouse-scan':'20260114_192341_Scan1','leaf':'20241115_104329','hand':'20241128_194710'}
sources={'mouse-rotation':{'depth':'rotation_depth.png','gray':'author_gray.png','volume':'rotation_3d.png'},'mouse-scan':{'depth':'selected_scan/sum_scan_depth.png','gray':'selected_scan/sum_scan_gray.png'},'leaf':{'depth':'leaf_depth.png','gray':'leaf_gray.png','volume':'leaf_3d.png'},'hand':{'depth':'hand_depth.png','gray':'hand_gray.png','volume':'hand_3d.png'}}
for s in samples:
    if s['id'] not in sources:continue
    ident=s['id'];s['acquisition_id']=ids[ident];s['display']['scale_bars']={}
    if ident=='mouse-scan':s['views']['volume']='assets/images/showcase/mouse-scan-volume.webp';s['display']['xy_crop_pixels']=crop;s['display']['crop_frame']='Screen XY after 2-degree physical CCW rotation';s['display']['cropped_extent_xy_mm']=[float(axes[0][l]),float(axes[0][r-1]),float(axes[1][h-b]),float(axes[1][h-t-1])]
    if ident=='mouse-rotation':s['display']['scale_calibration']=author_calibration
    for view in ['depth','gray','volume']:
        src=R/'assets'/sources[ident].get(view,'')
        im=scan3d if ident=='mouse-scan' and view=='volume' else Image.open(src).convert('RGB')
        if ident=='mouse-scan':
            if view!='volume':im=im.crop(crop)
            pxmm=ppm if view=='volume' else 10
        elif ident=='mouse-rotation':pxmm=author_px_per_mm if view=='volume' else 1/author_display_mm_per_voxel
        else:
            rec=spec[ident]
            if view=='volume':
                sizes=np.array(rec['spacing_xyz_mm'])*(np.array(rec['shape_zyx'][::-1])-1)
                cor=np.array(list(itertools.product(*[[0,q] for q in sizes])))
                pxmm=1300/(np.ptp(cor@up)*1.04)
            else:pxmm=1/rec['spacing_xyz_mm'][0]
        length=10 if ident=='mouse-scan' else 5
        bar=dict(length_mm=length,length_pixels=length*pxmm,pixels_per_mm=pxmm,position='lower right of preview frame; calibrated HTML overlay')
        dst=root/s['views'][view];im.save(dst,lossless=True,method=6);s['display']['scale_bars'][view]=bar
        assets.append(dict(file=s['views'][view],sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),source=src.name if src.is_file() else 'scan_processed.h5',dimensions=list(im.size),conversion='Existing display; recorded XY crop for scan; scale rendered as calibrated HTML overlay',scale_bar=bar))
    dump(root/'data'/f'{ident}.json',s)
dump(root/'data/samples.json',samples)
# Overview uses a lateral orientation to fill the landscape preview; retain the
# complete cropped field instead of stretching the anatomy.
for src,name,pxmm in [(R/'assets/selected_scan/sum_scan_depth.png','overview-structure.webp',10),(root/'assets/images/temporal/wholebody-15.webp','overview-temporal.webp',10)]:
    if 'structure' in name:im=Image.open(src).crop(crop).transpose(Image.Transpose.ROTATE_90)
    else:
        # Read the floating-point registered last frame to avoid rotating labels.
        ar=np.load(args.qa_dir/'wholebody_registered.npz')['registered'][-1]
        cap=load(root/'data/temporal.json')['series'][0]['display_window'][1]
        im=Image.fromarray(np.uint8(np.rint(np.clip(np.rot90(ar[::-1],2)/cap,0,1)*255))).transpose(Image.Transpose.ROTATE_90)
    im.save(A/name,lossless=True,method=6)
    assets.append(dict(file='assets/images/showcase/'+name,sha256=hashlib.sha256((A/name).read_bytes()).hexdigest(),dimensions=list(im.size),conversion='90-degree lateral overview; no anisotropic stretching; no scale annotation'))
im=Image.open(R/'assets/hand_3d.png').transpose(Image.Transpose.ROTATE_90)
im.save(A/'overview-reconstruction.webp',lossless=True,method=6)
assets.append(dict(file='assets/images/showcase/overview-reconstruction.webp',sha256=hashlib.sha256((A/'overview-reconstruction.webp').read_bytes()).hexdigest(),dimensions=list(im.size),conversion='90-degree image-plane camera roll for landscape overview; no scale annotation'))
replaced={a['file'] for a in assets}
provenance['assets']=[a for a in provenance['assets'] if a['file'] not in replaced]+assets;provenance['temporal']='Rigidly registered linear BP MIPs; fixed sequence window; ROI readouts computed after one rigid resampling, before image encoding.'
dump(root/'data/display-provenance.json',provenance)
dump(root/'data/scan-volume-view.json',dict(sample_id=ids['mouse-scan'],shape_zyx=list(v.shape),spacing_xyz_mm=spacing.tolist(),camera_direction=normal.tolist(),camera_view_up=up.tolist(),method='Maximum-intensity ray casting of exact 0.7 raw + 0.3 Frangi summed volume',xy_display_rotation_deg=2,shared_xy_crop_pixels=crop,z_slab_mm=[1.9,21.9],scale_pixels_per_mm=ppm,source_sha256=hashlib.sha256(args.scan_volume.read_bytes()).hexdigest(),view='Same oblique camera direction as author mouse, leaf and hand'))
print('SAMPLE_VIEWS_COMPLETE',author_calibration,flush=True)
