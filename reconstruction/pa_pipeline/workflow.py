from pathlib import Path
import copy,time,dataclasses
import numpy as np
from .config import load_sample,core_config,save,snapshot,MB_BASELINE
from .geometry import apply_geometry
from .bp_interface import bp_available,require_bp_backend,prepare_bp_profile
from .legacy.common import prepare_config,reconstruct_prepared,save_result
from .legacy.mb import MBOptions,prepare_mb,reconstruct_mb_prepared
from .select import choose_fov,choose_speed,with_config

def run(sample,output,*,methods=('bp',),backend='cuda',device=0):
 start=time.perf_counter();cfg,metadata=load_sample(sample);cfg=prepare_bp_profile(cfg)
 if not methods or set(methods)-{'bp','mb'}:raise ValueError('Methods must be bp and/or mb')
 if 'bp' in methods or any(cfg['defaults'][key]['enabled'] for key in ('fov_detection','speed_selection')):
  require_bp_backend()
 if 'mb' in methods:
  if 'mb' not in cfg['defaults']:raise ValueError('Add defaults.mb in reconstruction_parameters.json using configure --with-mb')
  missing=set(MB_BASELINE)-set(cfg['defaults']['mb'])
  if missing:raise ValueError('Missing defaults.mb fields: '+', '.join(sorted(missing)))
  mb_options=MBOptions(**cfg['defaults']['mb']);mb_options.validate()
 if backend=='cuda' and bp_available():
  import cupy as cp
  cp.cuda.Device(device).use()
 out=Path(output);out.mkdir(parents=True,exist_ok=False)
 result=dict(status='running',acquisition_id=metadata['acquisition_id'],methods=list(methods),input_contract=cfg['_input_contract'],stages={})
 save(out/'result.json',result)
 try:
  prepared=prepare_config(core_config(cfg));apply_geometry(prepared,cfg)
  save(out/'pulse_energy.json',prepared.pulse_energy.tolist())
  for name,selector in [('fov_detection',choose_fov),('speed_selection',choose_speed)]:
   if cfg['defaults'][name]['enabled']:
    folder=out/name;folder.mkdir()
    cfg,record=selector(prepared,cfg,folder,backend);result['stages'][name]=record
   else:result['stages'][name]=dict(status='recorded_parameters',enabled=False)
  effective=copy.deepcopy(cfg)
  effective['defaults']['fov_detection']['enabled']=False;effective['defaults']['speed_selection']['enabled']=False
  snapshot(effective,metadata,out/'profile')
  volume=cfg['defaults'].get('output',{}).get('save_volume',True)
  prepared=with_config(prepared,effective)
  if 'bp' in methods:
   bp=reconstruct_prepared(prepared,backend=backend,return_volume=volume)
   bp.parameters['schema_version']=cfg['schema_version']
   bp.parameters['actual_reconstruction']=dict(method='BP',preprocessing='recorded Butterworth/energy/crop order',geometry_registration=bool(cfg.get('frame_registration')))
   save_result(bp,out/'BP');result['stages']['bp']=dict(shape_zyx=[len(a) for a in bp.axes_xyz[::-1]],timing=bp.timing)
  if 'mb' in methods:
   mb_cfg=core_config(effective)
   source_projection=copy.deepcopy(mb_cfg['defaults']['projection'])
   mb_cfg['defaults']['projection'].update(plane='xy',method='maximum',z_policy='full_grid')
   prepared_mb=prepare_mb(mb_cfg,options=mb_options)
   prepared_mb.shared.parameters['mb_preprocessing']['source_replay_file']='../profile/reconstruction_parameters.json'
   apply_geometry(prepared_mb.shared,effective)
   mb,summary=reconstruct_mb_prepared(prepared_mb,device=device,return_volume=True)
   if source_projection['z_policy']!='full_grid':
    z=mb.axes_xyz[2]
    if source_projection['z_policy']=='physical_range':lo,hi=source_projection['z_range_mm'];keep=(z>=lo)&(z<=hi)
    elif source_projection['z_policy']=='index_range':lo,hi=source_projection['z_indices_1based_inclusive'];keep=(np.arange(len(z))>=lo-1)&(np.arange(len(z))<hi)
    else:raise ValueError('Unsupported MB projection policy')
    if not keep.any():raise ValueError('Empty MB projection interval')
    mb.mip_yx=mb.volume_zyx[keep].max(axis=0)
   mb.parameters['defaults']['projection']=source_projection;mb.parameters['schema_version']=cfg['schema_version']
   if not volume:mb.volume_zyx=None
   save_result(mb,out/'MB');save(out/'MB/iteration_history.json',summary)
   result['stages']['mb']=dict(shape_zyx=[len(a) for a in mb.axes_xyz[::-1]],timing=mb.timing,score=summary['history'][-1],preprocessing='same recorded band, matched centered FIR after crop')
   if bp_available():
    # For direct algorithm comparisons use a second BP on the exactly same MB input.
    prepared_mb.shared.parameters['defaults']['projection']=source_projection
    shared_bp=reconstruct_prepared(prepared_mb.shared,backend=backend,return_volume=volume)
    shared_bp.parameters['schema_version']=cfg['schema_version']
    shared_bp.parameters['actual_reconstruction']=dict(method='BP',preprocessing='identical RF, mask and FIR as MB')
    save_result(shared_bp,out/'BP_matched');result['stages']['bp_matched']=dict(identical_mb_input=True,identical_axes=all(np.array_equal(a,b) for a,b in zip(mb.axes_xyz,shared_bp.axes_xyz)))
   else:
    result['stages']['bp_matched']=dict(status='skipped',reason='No local BP core connected')
  result.update(status='complete',seconds=time.perf_counter()-start,geometry=cfg['defaults']['geometry'],grid=cfg['defaults']['grid'],speed_m_s=cfg['defaults']['reconstruction']['single_speed_m_s'],source_data_modified=False)
  save(out/'result.json',result)
  return result
 except Exception as e:
  result.update(status='failed',error=str(e),seconds=time.perf_counter()-start);save(out/'result.json',result);raise
