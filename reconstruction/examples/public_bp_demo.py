"""UBP of the uniform-sphere analytical pressure in Xu & Wang (2005), Sec. IV."""
from pathlib import Path
import sys,argparse,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pa_pipeline.backends.literature_ubp import ubp_volume,ubp_points,implementation_record

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=['cpu','cuda'],default='cpu')
    parser.add_argument('--out',required=True)
    args=parser.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    count=192;k=np.arange(count)+.5;z=1-2*k/count;phi=k*np.pi*(3-np.sqrt(5))
    detectors=12*np.column_stack([np.sqrt(1-z*z)*np.cos(phi),np.sqrt(1-z*z)*np.sin(phi),z])
    normals=-detectors/12;source=np.array([.4,-.2,.6]);radius=.7;speed=1500.
    times=np.arange(1000)/80e6;distance=np.linalg.norm(detectors-source,axis=1)
    delta=distance[:,None]-1000*speed*times[None]
    pressure=np.where(np.abs(delta)<=radius,delta/(2*distance[:,None]),0).astype('f4')
    axis=np.linspace(-1.5,1.5,31)
    volume=ubp_volume(pressure,times,detectors,normals,[axis]*3,sound_speed_m_s=speed,backend=args.backend)
    center=ubp_points(pressure,times,detectors,normals,source[None],sound_speed_m_s=speed,backend=args.backend)[0]
    np.savez_compressed(out/'sphere.npz',volume_zyx=volume,x=axis,y=axis,z=axis,source_xyz=source,radius_mm=radius)
    record=dict(**implementation_record(args.backend),analytic_source='uniform sphere, Xu & Wang 2005 Sec. IV',
                expected_center_amplitude=1.,reconstructed_center_amplitude=float(center),signed_min=float(volume.min()),signed_max=float(volume.max()))
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
