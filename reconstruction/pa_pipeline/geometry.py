"""Apply inline frame transforms to positions and physical receive directions."""
import numpy as np
from .legacy.core.signals import detector_positions,rz

def sensor_axes(sensors):
 sensors=np.asarray(sensors,dtype=np.float64)
 lengths=np.linalg.norm(sensors,axis=1,keepdims=True)
 if np.any(lengths==0):raise ValueError('Origin detector has no radial normal')
 return (-sensors/lengths).astype('f4')


def registered_geometry(cfg):
 ids=cfg['defaults']['frames']['indices_1based'];original=detector_positions(cfg,ids).astype('f4')
 ext=cfg.get('frame_registration')
 if not ext:return original.reshape(-1,3),None
 extra=rz(cfg['defaults']['geometry']['additional_z_rotation_deg']);sensors=original.copy();normals=np.empty_like(sensors)
 for j,f in enumerate(ids):
  tr=ext['transforms'][str(f)];r=np.asarray(tr['R'],dtype='f8');t=np.asarray(tr['t_mm'],dtype='f8')
  if np.array_equal(r,np.eye(3)) and not np.any(t):normals[j]=sensor_axes(original[j]);continue
  rotation=extra@r@extra.T;translation=extra@t
  sensors[j]=((original[j].astype('f8')-translation)@rotation).astype('f4')
  origin=(-translation@rotation).astype('f4');direction=origin-sensors[j]
  normals[j]=direction/np.linalg.norm(direction,axis=1,keepdims=True)
 return sensors.reshape(-1,3),normals.reshape(-1,3)

def apply_geometry(prepared,cfg):
 prepared.sensor_xyz_mm,prepared.sensor_axis_xyz=registered_geometry(cfg)
 return prepared
