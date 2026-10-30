"""Reconstruct consecutive 1..20 leaf exposures and render numerical projections.

Uses the released sample's signal, geometry, grid and speed parameters. Run on
the requested GPU host with pa_recon and its CUDA dependencies on PYTHONPATH.
"""
from pathlib import Path
import argparse, copy, hashlib, itertools, json, time
import numpy as np
from scipy.ndimage import map_coordinates
from pa_recon.common import PreparedPA, reconstruct_prepared
from pa_recon.core.signals import read_frames, detector_positions, filter_coefficients, preprocess_frame
from pa_recon.core.config import selected_pa

UP=np.array([-.14457087885019915,-.9526931319918457,-.26734819476489574])
NORMAL=np.array([.4531633284897209,-.3039338682272307,.8380138432368225])
CROP=[25,160,375,640]

def oblique_projection(volume, spacing):
    """Parallel maximum-intensity ray casting; same camera as sample gallery."""
    v=np.ascontiguousarray(volume[::-1,::-1,::-1])
    spacing=np.asarray(spacing);size=(np.array(volume.shape[::-1])-1)*spacing
    up=UP/np.linalg.norm(UP);normal=NORMAL/np.linalg.norm(NORMAL)
    right=np.cross(up,normal);right/=np.linalg.norm(right)
    corners=np.array(list(itertools.product(*[[-q/2,q/2] for q in size])))
    ww=np.ptp(corners@right)*1.04;hh=np.ptp(corners@up)*1.04
    pitch=max(ww/520,hh/720);width=int(np.ceil(ww/pitch));height=int(np.ceil(hh/pitch))
    xx,yy=np.meshgrid((np.arange(width,dtype='f4')-(width-1)/2)*pitch,
                     ((height-1)/2-np.arange(height,dtype='f4'))*pitch)
    centre=np.asarray(size/2,dtype='f4')
    base=centre[:,None,None]+np.asarray(right,dtype='f4')[:,None,None]*xx+np.asarray(up,dtype='f4')[:,None,None]*yy
    depth=corners@normal
    planes=np.arange(depth.min()-.1,depth.max()+.1,min(spacing)*.75,dtype='f4')
    output=np.zeros((height,width),dtype='f4')
    for offset in range(0,len(planes),12):
        dz=planes[offset:offset+12]
        xyz=(base[:,None]+np.asarray(normal,dtype='f4')[:,None,None,None]*dz[None,:,None,None])/np.asarray(spacing,dtype='f4')[:,None,None,None]
        block=map_coordinates(v,np.ascontiguousarray(xyz[::-1]),order=1,mode='constant',cval=0,prefilter=False)
        np.maximum(output,block.max(0),out=output)
    answer=output.copy()
    assert np.isfinite(answer).all() and answer.max()<=float(v.max())+1e-6
    del v,output,base,xyz,block
    return answer,pitch

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker',type=int,default=0)
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(args.parameters.read_text());assert cfg['sample_id']=='20241115_104329'
    ids=list(range(1,21))
    cfg['defaults']['frames'].update(mode='explicit_indices',count=20,indices_1based=ids)
    lo,hi=cfg['defaults']['signal']['time_samples_1based']
    buffer=np.empty((20*1024,hi-lo+1),dtype='f4');energies=[]
    coefficients=filter_coefficients(cfg)
    for j,(_,raw) in enumerate(read_frames(selected_pa(cfg),ids)):
        processed,energy=preprocess_frame(raw,cfg,coefficients)
        buffer[j*1024:(j+1)*1024]=processed.T;energies.append(energy)
    xyz=detector_positions(cfg,ids).reshape(-1,3).astype('f4')
    print('READY',args.worker,flush=True)
    for n in range(1,21):
        if (n-1)%args.workers!=args.worker:continue
        out=args.output/f'leaf_{n:02d}.npz'
        if out.exists():continue
        started=time.time();c=copy.deepcopy(cfg)
        c['defaults']['frames'].update(count=n,indices_1based=ids[:n])
        result=reconstruct_prepared(PreparedPA(buffer[:n*1024],xyz[:n*1024],c,np.asarray(energies[:n]),{}),return_volume=True)
        l,t,r,b=CROP;v=result.volume_zyx[:,t:b,l:r]
        axes=[result.axes_xyz[0][l:r],result.axes_xyz[1][t:b],result.axes_xyz[2]]
        spacing=[float(a[1]-a[0]) for a in axes]
        angled,pitch=oblique_projection(v,spacing)
        np.savez_compressed(out,mip=np.ascontiguousarray(v.max(0)[::-1]),oblique=angled,
                            x=axes[0],y=axes[1],z=axes[2],oblique_pitch_mm=pitch)
        record=dict(sample_id=cfg['sample_id'],count=n,frames_1based=ids[:n],
            source_parameters_sha256=hashlib.sha256(args.parameters.read_bytes()).hexdigest(),
            signal=c['defaults']['signal'],geometry=c['defaults']['geometry'],grid=c['defaults']['grid'],
            reconstruction=c['defaults']['reconstruction'],crop_xyxy=CROP,shape_zyx=list(v.shape),
            extent_xyz_mm=[[float(a[0]),float(a[-1])] for a in axes],
            camera=dict(direction=NORMAL.tolist(),view_up=UP.tolist(),axis_flips='XYZ',projection='parallel maximum-intensity ray casting',pixel_pitch_mm=pitch),
            postfilter=None,added_gain=False,elapsed_seconds=time.time()-started)
        out.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n')
        if n==20:
            import h5py
            with h5py.File(args.output/'leaf_20_volume.h5','w') as h:
                h.create_dataset('volume_zyx',data=v,compression='gzip',compression_opts=2)
                for k,a in zip('xyz',axes):h.create_dataset(k+'_mm',data=a)
        del result,v
        print('DONE',n,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
