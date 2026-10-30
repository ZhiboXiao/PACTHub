import copy,time
import numpy as np
from .config import core_config,refresh_grid,save
from .geometry import apply_geometry
from .legacy.common import PreparedPA,reconstruct_prepared
from .legacy.core.signals import rz

def with_config(prepared,cfg):
 p=PreparedPA(prepared.data_ct,prepared.sensor_xyz_mm,core_config(cfg),prepared.pulse_energy,dict(prepared.timing))
 return apply_geometry(p,cfg)

def choose_fov(prepared,cfg,out,backend):
 from .selection.fov_legacy import select_fov,rectangle
 p=cfg['defaults']['fov_detection'];large=copy.deepcopy(cfg)
 old_angle=cfg['defaults']['geometry']['additional_z_rotation_deg']
 center=p.get('large_center_mm',(rz(-old_angle)@cfg['defaults']['grid']['center_mm']).tolist())
 large['defaults']['geometry']['additional_z_rotation_deg']=0.
 refresh_grid(large,center_mm=center,space_mm=p['large_space_mm'],resolution_px_mm=p['large_resolution_px_mm'])
 large['defaults']['reconstruction']['single_speed_m_s']=p.get('reference_speed_m_s') or cfg['defaults']['reconstruction']['single_speed_m_s']
 large['defaults']['projection'].update(plane='xy',method='maximum',z_policy='full_grid')
 view=reconstruct_prepared(with_config(prepared,large),backend=backend)
 np.savez_compressed(out/'fov_reference.npz',mip=view.mip_yx,axis_x=view.axes_xyz[0],axis_y=view.axes_xyz[1],axis_z=view.axes_xyz[2])
 if p.get('maximum_clipped_fraction',.01)!=.01:raise ValueError('Retained FOV implementation requires maximum_clipped_fraction=0.01')
 try:result,mask=select_fov(view.mip_yx,center,p['large_space_mm'],vessel_prior=p['vessel_continuity_prior'],sigma_upper=p['sigma_upper'])
 except ValueError as error:
  result=dict(status='insufficient_evidence',applied_to_run=False,reason=str(error));save(out/'fov_selection.json',result);return cfg,result
 target=p['target_space_mm'];result['target_space_xyz_mm']=target
 result['target_rectangle_xy_mm']=rectangle(result['center_native_mm'][:2],result['long_axis_xy'],target[1],target[0]).tolist()
 flags=[x for x in result['segmentation_flags'] if x!='foreground_exceeds_target_fov']
 if result['fitted_length_mm']>target[1] or result['fitted_width_mm']>target[0]:flags.append('foreground_exceeds_target_fov')
 result['segmentation_flags']=flags;result['applied_to_run']=bool(p.get('apply_to_run',False) and not flags)
 np.save(out/'fov_mask.npy',mask)
 if result['applied_to_run']:
  cfg['defaults']['geometry']['additional_z_rotation_deg']=result['initial_z_rotation_deg']
  refresh_grid(cfg,center_mm=result['center_rotated_mm'],space_mm=target)
 save(out/'fov_selection.json',result)
 return cfg,result

def choose_speed(prepared,cfg,out,backend):
 from .selection.speed_legacy import score_stack,score_morphology,MorphologyConfig
 p=cfg['defaults']['speed_selection'];speeds=np.asarray(cfg['defaults']['reconstruction']['sweep_m_s'],dtype=float)
 if len(speeds)<3 or not np.isfinite(speeds).all() or not np.all(np.diff(speeds)>0):raise ValueError('Sound-speed sweep requires at least three increasing finite candidates')
 if p['roi_mode']!='full_mip':raise ValueError('This interface uses full numeric MIPs for the retained autofocus methods')
 if not p['methods'] or set(p['methods'])-{'full_global_normalized_gradient','morphology_v2'}:raise ValueError('Unrecognized sound-speed method')
 sweep=copy.deepcopy(cfg)
 if p.get('resolution_px_mm') is not None:refresh_grid(sweep,resolution_px_mm=p['resolution_px_mm'])
 # Keep the same full Z support, frames, filters, geometry and intensity units across candidates.
 sweep['defaults']['projection'].update(plane='xy',method='maximum',z_policy='full_grid')
 stack=[];timing=[]
 working=with_config(prepared,sweep)
 for speed in speeds:
  working.parameters['defaults']['reconstruction']['single_speed_m_s']=float(speed)
  tick=time.perf_counter();result=reconstruct_prepared(working,backend=backend);stack.append(result.mip_yx);timing.append(time.perf_counter()-tick)
  print('SPEED',speed,'seconds',round(timing[-1],3),flush=True)
 stack=np.stack(stack);x,y,z=result.axes_xyz
 np.savez_compressed(out/'speed_sweep.npz',full_mips=stack,speeds=speeds,axis_x=x,axis_y=y,axis_z=z)
 records={}
 for method in p['methods']:
  try:
   if method=='full_global_normalized_gradient':
    values,support=score_stack(stack);curve=np.asarray(values['global_normalized_gradient']);winners=np.flatnonzero(np.isclose(curve,curve.max(),rtol=1e-12,atol=0))
    candidate=float(speeds[winners[0]]) if len(winners)==1 else None
    flags=[]
    if candidate is None:flags.append('tied_candidates')
    if candidate in (speeds[0],speeds[-1]):flags.append('range_endpoint')
    records[method]=dict(candidate=candidate,scores=curve.tolist(),flags=flags,support_pixels=int(support.sum()))
    np.save(out/'speed_gradient_support.npy',support)
   else:
    record,detail=score_morphology(stack,speeds,x,y,cfg=MorphologyConfig(**p.get('morphology_parameters',{})))
    records[method]=record
  except ValueError as error:records[method]=dict(candidate=None,flags=['insufficient_evidence'],reason=str(error))
 applied=p.get('apply_method');chosen=records.get(applied,{})
 applied_ok=bool(chosen.get('candidate') is not None and not chosen.get('flags'))
 original=cfg['defaults']['reconstruction']['single_speed_m_s']
 if applied_ok:cfg['defaults']['reconstruction']['single_speed_m_s']=float(chosen['candidate'])
 result=dict(methods=records,speeds_m_s=speeds.tolist(),seconds=timing,apply_method=applied,applied_to_run=applied_ok,
  recorded_speed_m_s=original,effective_speed_m_s=cfg['defaults']['reconstruction']['single_speed_m_s'],
  input_domain='full floating-point MIP; fixed geometry and frames',input_parameter_files_modified=False)
 save(out/'speed_selection.json',result)
 return cfg,result
