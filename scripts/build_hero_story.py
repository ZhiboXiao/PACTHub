"""Render the public Figure 5b volume, then join the original breathing movie.

The orbit rotates numeric volume data about its longitudinal Y axis. After
standing up, a duplicate slides right and becomes the existing depth image.
Input MAT and MP4 files are opened read-only. All masks are display-only.
"""
from pathlib import Path
import argparse, hashlib, json, math, subprocess, time
import cv2
import h5py
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

ROOT=Path(__file__).resolve().parents[1]
FPS=30
INTRO=23.0
SIDE=1200
LOW,HIGH=.020,.400
AFFINE=np.array([[1.028,0,-17.7],[0,1.028,-22.7]],np.float32)
LAYOUTS={
 'desktop':dict(size=(1920,1080),pair=(975,140,.96),start=(960,540),zoom=2.34),
 'mobile':dict(size=(1080,1080),pair=(12,3,1.23),start=(540,540),zoom=1.25),
}
VARIANTS={
 'horizontal':dict(screen_angle_deg=0,mount_deg=-90,desktop_zoom=2.34,mobile_zoom=1.25),
 'diagonal':dict(screen_angle_deg=20,mount_deg=-110,desktop_zoom=2.00,mobile_zoom=1.18),
}

def ease(x):
    x=np.clip(x,0,1)
    return x*x*x*(x*(x*6-15)+10)

def lut(n):
    phase=-(np.arange(n+2)-(n+2)/2)/(n+2)*1.75*np.pi
    peaks=np.array([5/16,-3/16,-.9])*np.pi
    rgb=np.empty((n+2,3))
    for c,(width,mean) in enumerate(zip([1.4,1,.4],[.7,.7,.5])):
        rgb[:,c]=(1-2*(1-mean)*(np.cos(phase-(np.pi+peaks[c]))/2+.5)**width
                  if width>1 else 2*(mean-.5)+2*(1-mean)*(np.cos(phase-peaks[c])/2+.5)**(1/width))
    return rgb[1:-1]

def envelope(amp,threshold,close=35,dilate=10,feather=5):
    seed=ndi.gaussian_filter(amp.astype('float32'),1.1)>threshold
    seed=cv2.morphologyEx(seed.astype('uint8'),cv2.MORPH_CLOSE,
          cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(close,close)))
    labels,count=ndi.label(seed)
    sizes=np.bincount(labels.ravel());sizes[0]=0
    mask=ndi.binary_fill_holes(labels==sizes.argmax()).astype('uint8')
    mask=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*dilate+1,2*dilate+1)))
    return np.clip(ndi.distance_transform_edt(mask)/feather,0,1).astype('float32')

def prepare(args):
    with h5py.File(args.source,'r') as f:
        # MATLAB [Y,X,Z] becomes HDF5 [Z,X,Y]. The released X axis is
        # reversed relative to the Figure 5b / current movie frontal display.
        native=f['frontal_view_img'][:]
        v=np.maximum(native.transpose(0,2,1)[:,:,::-1],0).copy()
    amp=v.max(0)
    support=envelope(amp,.022,close=43,dilate=8,feather=6)
    v*=support[None]
    bright=np.clip((v.max(0)-LOW)/(HIGH-LOW),0,1)
    gray=np.uint8(np.rint(bright*255))
    colour=np.uint8(np.rint(lut(v.shape[0])[v.argmax(0)]*bright[...,None]*255))
    front=cv2.warpAffine(cv2.cvtColor(gray,cv2.COLOR_GRAY2RGB),AFFINE,(428,870))
    depth=cv2.warpAffine(colour,AFFINE,(386,870))
    pair=np.zeros((870,856,3),np.uint8)
    pair[:,:428]=front;pair[:,470:]=depth
    Image.fromarray(pair).save(args.work_dir/'static_pair.png')
    Image.fromarray(colour).save(args.work_dir/'released_depth.png')
    Image.fromarray(np.uint8(support*255)).save(args.work_dir/'volume_display_mask.png')
    capture=cv2.VideoCapture(str(args.movie))
    count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT));rate=capture.get(cv2.CAP_PROP_FPS)
    maximum=np.zeros_like(pair)
    for i in range(0,count,10):
        capture.set(cv2.CAP_PROP_POS_FRAMES,i);ok,frame=capture.read()
        if ok:maximum=np.maximum(maximum,cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    capture.release()
    masks=[]
    for left,right in [(0,428),(470,856)]:
        image=maximum[:,left:right]
        masks.append(envelope(image.max(2),27,close=37,dilate=9,feather=5))
    np.savez_compressed(args.work_dir/'display_masks.npz',volume_xy=support,movie_gray=masks[0],movie_depth=masks[1])
    return v,pair,masks,count/rate

def rotation_at(t,mount_deg):
    stand=float(ease((t-13)/5))
    swing=12*math.sin(2*math.pi*(max(1,min(t,13))-1)/6)
    z=math.radians(mount_deg*(1-stand));y=math.radians(swing*(1-stand))
    rz=np.array([[math.cos(z),-math.sin(z),0],[math.sin(z),math.cos(z),0],[0,0,1]])
    ry=np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
    # Ry acts in specimen coordinates BEFORE screen placement. Thus the
    # specimen's Y direction is fixed on screen throughout the two cycles.
    return rz@ry

class Renderer:
    def __init__(self,v,mount_deg):
        self.mount_deg=mount_deg
        self.data=vtk.vtkImageData();self.data.SetDimensions(*v.shape[::-1]);self.data.SetSpacing(1,1,1)
        self.data.GetPointData().SetScalars(numpy_to_vtk(np.ascontiguousarray(v[:,::-1,:]).ravel(),deep=True,array_type=vtk.VTK_FLOAT))
        self.centre=(np.array(v.shape[::-1])-1)/2
        mapper=vtk.vtkGPUVolumeRayCastMapper();mapper.SetInputData(self.data);mapper.SetBlendModeToMaximumIntensity()
        mapper.AutoAdjustSampleDistancesOff();mapper.SetSampleDistance(.85)
        colour=vtk.vtkColorTransferFunction();colour.AddRGBPoint(LOW,0,0,0);colour.AddRGBPoint(HIGH,1,1,1)
        opacity=vtk.vtkPiecewiseFunction();opacity.AddPoint(0,1);opacity.AddPoint(float(v.max()),1)
        prop=vtk.vtkVolumeProperty();prop.SetColor(colour);prop.SetScalarOpacity(opacity);prop.SetInterpolationTypeToLinear();prop.ShadeOff()
        self.actor=vtk.vtkVolume();self.actor.SetMapper(mapper);self.actor.SetProperty(prop)
        self.ren=vtk.vtkRenderer();self.ren.SetBackground(0,0,0);self.ren.AddVolume(self.actor)
        self.cam=self.ren.GetActiveCamera();self.cam.ParallelProjectionOn()
        self.cam.SetFocalPoint(*self.centre);self.cam.SetPosition(*(self.centre+[0,0,5000]));self.cam.SetViewUp(0,1,0);self.cam.SetParallelScale(SIDE/2)
        self.win=vtk.vtkRenderWindow();self.win.SetOffScreenRendering(1);self.win.SetMultiSamples(0);self.win.SetSize(SIDE,SIDE);self.win.AddRenderer(self.ren)
        self.capture=vtk.vtkWindowToImageFilter();self.capture.SetInput(self.win);self.capture.SetInputBufferTypeToRGB();self.capture.ReadFrontBufferOff()

    def frame(self,t):
        rotation=rotation_at(t,self.mount_deg)
        m=np.eye(4);m[:3,:3]=rotation;m[:3,3]=self.centre-rotation@self.centre
        matrix=vtk.vtkMatrix4x4()
        for r in range(4):
            for c in range(4):matrix.SetElement(r,c,float(m[r,c]))
        self.actor.SetUserMatrix(matrix);self.ren.ResetCameraClippingRange();self.win.Render();self.capture.Modified();self.capture.Update()
        return np.ascontiguousarray(vtk_to_numpy(self.capture.GetOutput().GetPointData().GetScalars()).reshape(SIDE,SIDE,3)[::-1])

def clean_movie(frame,masks):
    out=np.zeros_like(frame)
    out[:,:428]=np.uint8(np.rint(frame[:,:428].astype('float32')*masks[0][...,None]))
    # The old depth panel has a constant brown pedestal (median border 12,10,0).
    corrected=np.maximum(frame[:,470:].astype('float32')-[12,10,0],0)
    out[:,470:]=np.uint8(np.rint(corrected*masks[1][...,None]))
    return out

def place_pair(pair,layout):
    x,y,s=layout['pair']
    return cv2.warpAffine(pair,np.float32([[s,0,x],[0,s,y]]),layout['size'],flags=cv2.INTER_LINEAR)

def duplicate_scene(t,pair,layout):
    left=pair.copy();left[:,470:]=0
    canvas=place_pair(left,layout)
    travel=float(ease((t-19)/1.8))
    colour=float(ease((t-19.6)/1.4))
    duplicate=np.uint8(np.rint(pair[:,:386]*(1-colour)+pair[:,470:]*colour))
    x,y,s=layout['pair']
    overlay=cv2.warpAffine(duplicate,np.float32([[s,0,x+470*s*travel],[0,s,y]]),layout['size'])
    return np.maximum(canvas,overlay)

def pose_canvas(render,t,layout):
    u=ease((t-13)/5)
    x,y,s=layout['pair']
    final=np.array([x+s*(187*1.028-17.7),y+s*(437*1.028-22.7)])
    centre=np.array(layout['start'])*(1-u)+final*u
    zoom=layout['zoom']*(1-u)+s*1.028*u
    matrix=np.float32([[zoom,0,centre[0]-SIDE/2*zoom],[0,zoom,centre[1]-SIDE/2*zoom]])
    canvas=cv2.warpAffine(render,matrix,layout['size'])
    return np.uint8(canvas*float(ease(t/.8)))

def encode_cmd(path,size):
    return ['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{size[0]}x{size[1]}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-threads','4','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--movie',type=Path,required=True);ap.add_argument('--work-dir',type=Path,required=True);ap.add_argument('--variant',choices=VARIANTS,default='horizontal');ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    args.work_dir.mkdir(parents=True,exist_ok=True)
    variant=VARIANTS[args.variant]
    for name in LAYOUTS:LAYOUTS[name]['zoom']=variant[name+'_zoom']
    v,pair,masks,dynamic_duration=prepare(args)
    renderer=Renderer(v,variant['mount_deg']);del v
    cap=cv2.VideoCapture(str(args.movie));ok,bgr=cap.read();first=clean_movie(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB),masks)
    cap.release()
    # The duplicate ends on the actual depth movie's first frame, so its
    # colours and anatomy continue directly into motion.
    pair[:,470:]=first[:,470:]
    Image.fromarray(first).save(args.work_dir/'clean_movie_first.png')
    final_render=renderer.frame(18)
    keytimes=[0.8,2.5,5.5,8.5,11.5,15.5,18.5,19.5,20.5,21.5,23,28]
    sheet=Image.new('RGB',(1440,12//3*292),'#090b0e');draw=ImageDraw.Draw(sheet)
    for i,t in enumerate(keytimes):
        if t<18:image=pose_canvas(renderer.frame(t),t,LAYOUTS['desktop'])
        elif t<19:image=pose_canvas(final_render,t,LAYOUTS['desktop'])
        elif t<21:image=duplicate_scene(t,pair,LAYOUTS['desktop'])
        elif t<INTRO:image=place_pair(np.uint8(np.rint(pair*(1-ease((t-21)/2))+first*ease((t-21)/2))),LAYOUTS['desktop'])
        else:image=place_pair(first,LAYOUTS['desktop'])
        im=Image.fromarray(image);im.save(args.work_dir/f'keyframe_{t:g}.png')
        sheet.paste(im.resize((480,270)),((i%3)*480,(i//3)*292));draw.text(((i%3)*480+12,(i//3)*292+274),f'{t:g} s',fill='#bec8d9')
        print(f'Preview {t:g}s',flush=True)
    sheet.save(args.work_dir/'storyboard.png')
    if args.preview:renderer.win.Finalize();return
    outputs={k:ROOT/'assets/media'/f'hero-fig5b-{args.variant}-{k}.mp4' for k in LAYOUTS}
    encoders={k:subprocess.Popen(encode_cmd(outputs[k],v['size']),stdin=subprocess.PIPE) for k,v in LAYOUTS.items()}
    cap=cv2.VideoCapture(str(args.movie));loop_frames=[]
    for i in range(24):
        ok,bgr=cap.read();loop_frames.append(clean_movie(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB),masks))
    cap.set(cv2.CAP_PROP_POS_FRAMES,0)
    start=time.monotonic();duration=INTRO+dynamic_duration
    try:
        for index in range(round(duration*FPS)):
            t=index/FPS
            render=renderer.frame(t) if t<18 else final_render
            movie=None
            if t>=INTRO:
                ok,bgr=cap.read()
                if not ok:raise RuntimeError(f'Movie ended at {t}s')
                movie=clean_movie(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB),masks)
                tail=t-INTRO-(dynamic_duration-.8)
                if tail>=0:
                    j=min(round(tail*FPS),len(loop_frames)-1);alpha=float(ease(tail/.8))
                    movie=np.uint8(np.rint(movie*(1-alpha)+loop_frames[j]*alpha))
            for name,layout in LAYOUTS.items():
                if t<19:
                    canvas=pose_canvas(render,t,layout)
                    if t>=18:
                        canonical=place_pair(pair.copy(),layout);x,y,s=layout['pair'];canonical[:,int(x+470*s):]=0
                        blend=float(ease((t-18)/.8));canvas=np.uint8(np.rint(canvas*(1-blend)+canonical*blend))
                elif t<21:canvas=duplicate_scene(t,pair,layout)
                elif t<INTRO:
                    u=float(ease((t-21)/2));canvas=place_pair(np.uint8(np.rint(pair*(1-u)+first*u)),layout)
                else:canvas=place_pair(movie,layout)
                encoders[name].stdin.write(canvas.tobytes())
                if index==24:Image.fromarray(canvas).save(ROOT/'assets/images'/f'hero-fig5b-{args.variant}-{name}.webp',quality=94)
            if index%90==0:print(f'{index}/{round(duration*FPS)} frames, {time.monotonic()-start:.1f}s',flush=True)
        for proc in encoders.values():
            proc.stdin.close()
            if proc.wait()!=0:raise RuntimeError('Encoding failed')
    except BaseException:
        for proc in encoders.values():proc.kill()
        raise
    finally:cap.release();renderer.win.Finalize()
    record={
      'source':{'file':args.source.as_posix(),'variable':'frontal_view_img','native_hdf5_shape':[250,375,875],
                'sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
                'release_doi':'10.6084/m9.figshare.28443374.v3','release_url':'https://figshare.com/articles/dataset/3D-PanoPACT_Data_Code/28443374/3','license':'CC BY 4.0','figure':'Figure 5b','article_doi':'10.1038/s41467-025-65054-x'},
      'presentation':{'orientation':'Native [Z,X,Y] -> [Z,Y,X], display X reversed to match Figure 5b; PE/TE screen-left, LL/RL screen-right during horizontal pose.',
       'gray_window':[LOW,HIGH],'extra_frangi':False,'extra_fluence_gain':False,'depth_palette':'Author colorMIP trunk LUT',
       'orbit':{'axis':'Specimen Y (long axis)','y_swing_deg':12,'cycles':2,'cycle_seconds':6,'camera_tilt_deg':0,'fixed_screen_angle_deg':variant['screen_angle_deg']},
       'background':'Fixed temporal-union display envelopes; depth-movie pedestal RGB [12,10,0] subtracted; no alteration of source MAT or original movie.',
       'depth_transition':'A duplicate slides from the gray position to the right and becomes the existing depth image. No particles.',
       'timeline_seconds':{'orbit':[0,13],'stand_and_move':[13,18],'front_hold':[18,19],'duplicate_and_move':[19,21],'crossfade':[21,INTRO],'original_dynamic_movie':[INTRO,duration]},
       'loop_start_seconds':INTRO+.8,'original_dynamic_movie':args.movie.resolve().relative_to(ROOT).as_posix(),'layouts':LAYOUTS},
      'outputs':{k:{'file':p.relative_to(ROOT).as_posix(),'size_bytes':p.stat().st_size} for k,p in outputs.items()}
    }
    (ROOT/f'data/hero-story-{args.variant}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(record['outputs']),flush=True)

if __name__=='__main__':main()
