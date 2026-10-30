"""Only sample_metadata.json and reconstruction_parameters.json supply settings."""
from pathlib import Path
import copy,json,hashlib,os
import numpy as np
from scipy.io import loadmat
import h5py
from .legacy.core.config import read_json,require_ready,selected_pa,axes

SCHEMAS={'1.0.0','1.0.0+starnet-rigid-v3'}
MB_BASELINE=dict(sensor_radius_mm=1.75,radial_order=3,angular_order=16,fir_order=128,fir_beta=8.0,
 mask_first_samples=0,matched_channel_demean=False,iterations=5,power_iterations=2,
 l1_relative=.02,tv_relative=.005,l2_relative=.003,sensor_batch_size=1024)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def resolve(value,base):
 p=Path(value);return str(p if p.is_absolute() else (Path(base)/p).resolve())
def load_sample(sample,*,check_data=True):
 directory=Path(sample).resolve();directory=directory.parent if directory.name=='reconstruction_parameters.json' else directory
 paths=[directory/'sample_metadata.json',directory/'reconstruction_parameters.json']
 metadata,cfg=[read_json(p) for p in paths]
 if cfg.get('schema_version') not in SCHEMAS:raise ValueError('Unsupported schema_version: '+str(cfg.get('schema_version')))
 inp=cfg['inputs'];export=cfg.get('export_metadata',{})
 if export.get('acquisition_id',metadata['acquisition_id'])!=metadata['acquisition_id']:raise ValueError('Acquisition ID mismatch between the two JSON files')
 if metadata.get('reconstruction_parameters_available') is False:raise ValueError('This acquisition has no resolved reconstruction parameters')
 if metadata.get('signal_storage_axes')!='FTC':raise ValueError('Expected published FTC HDF5 storage, described by sample_metadata.json')
 if inp.get('pa_variable')!='pa_data':raise ValueError('inputs.pa_variable must be pa_data for this published format')
 if inp.get('modality') not in ('PA-only','PA+US','PA/US'):raise ValueError('No PA modality in supplied configuration')
 if any(inp.get(k) is False for k in ('adc_scaling_already_applied','channel_mapping_already_applied','channel_polarity_already_applied')):
  raise ValueError('Input is not the standardized PA data declared by this interface')
 inp['pa_files']=[resolve(p,directory) for p in inp['pa_files']]
 for group in inp['acquisition_groups']:
  if group.get('pa_file'):group['pa_file']=resolve(group['pa_file'],directory)
 pa=selected_pa(cfg)
 if pa.name!=Path(metadata['PA_path']).name:raise ValueError('PA filename disagrees with sample metadata')
 if inp.get('detector_file'):inp['detector_file']=resolve(inp['detector_file'],directory)
 # Public export removes this old implementation tag; the validated PA contract restores it in memory.
 inp['entrypoint']='split_pa_file'
 cfg['_input_contract']=dict(parameter_files=[str(p) for p in paths],parameter_sha256=[digest(p) for p in paths],
  acquisition_id=metadata['acquisition_id'],signal_shape=metadata['signal_shape'],signal_dtype=metadata['signal_dtype'],storage_axes='FTC')
 unsupported=[]
 for section,key in [('signal','channel_calibration_file'),('fov_detection','segmentation_parameters_file'),('speed_selection','roi_file'),('speed_selection','algorithm_parameters_file'),('boundary','file'),('boundary','surface_parameters_file')]:
  if cfg['defaults'].get(section,{}).get(key):unsupported.append('defaults.'+section+'.'+key)
 if inp.get('channel_mapping_file'):unsupported.append('inputs.channel_mapping_file')
 if unsupported:raise ValueError('Additional parameter-file references must be inlined before running: '+', '.join(unsupported))
 if check_data:
  runtime=core_config(cfg);require_ready(runtime)
  with h5py.File(pa,'r') as h:
   a=h[inp['pa_variable']]
   if list(a.shape)!=metadata['signal_shape'] or str(a.dtype)!=metadata['signal_dtype']:raise ValueError('PA shape/dtype does not match sample_metadata.json')
   if a.ndim!=3 or a.shape[-1]!=1024 or a.shape[0]!=metadata['PA_frames']:raise ValueError('PA frame/channel contract mismatch')
   if max(cfg['defaults']['frames']['indices_1based'])>a.shape[0]:raise ValueError('Selected frame exceeds available PA frames')
  detector_array(cfg)
  update_grid_metadata(cfg)
 return cfg,metadata

def core_config(cfg):
 c=copy.deepcopy(cfg)
 if c.get('validation',{}).get('execution_hold') or not c['defaults']['reconstruction'].get('enabled'):
  raise ValueError('Recorded execution hold: reconstruction parameters are unresolved; '+str(c.get('validation',{}).get('conflicts',[])))
 if c['schema_version']=='1.0.0+starnet-rigid-v3':
  ext=c.get('frame_registration',{})
  if ext.get('convention')!='p_moving_native=R@p_reference_native+t_mm':raise ValueError('Unsupported registration convention')
  for frame in c['defaults']['frames']['indices_1based']:
   row=ext.get('transforms',{}).get(str(frame))
   if not row:raise ValueError(f'Missing inline registration for frame {frame}')
   r=np.asarray(row['R']);t=np.asarray(row['t_mm'])
   if r.shape!=(3,3) or t.shape!=(3,) or not np.isfinite(np.r_[r.ravel(),t]).all() or not np.allclose(r.T@r,np.eye(3),atol=2e-5) or abs(np.linalg.det(r)-1)>2e-5:raise ValueError('Invalid rigid registration matrix')
  c['schema_version']='1.0.0'
 for stage in ['fov_detection','speed_selection']:c['defaults'][stage]['enabled']=False
 return c

def detector_array(cfg):
 inline=cfg['defaults']['geometry'].get('detector_xyz_mm')
 if inline is not None:a=np.asarray(inline,dtype='f8')
 else:
  path=cfg['inputs'].get('detector_file')
  if not path:raise ValueError('Missing detector coordinates: provide inputs.detector_file or defaults.geometry.detector_xyz_mm')
  if h5py.is_hdf5(path):
   with h5py.File(path) as h:a=h['detector'][:].T.astype('f8')
  else:a=np.asarray(loadmat(path,variable_names=['detector'])['detector'],dtype='f8')
 if a.shape!=(1024,3) or not np.isfinite(a).all():raise ValueError('Expected finite 1024×3 detector coordinates in mm')
 return a

def update_grid_metadata(cfg):
 ax=axes(cfg)
 cfg['defaults']['grid'].update(shape_xyz=[len(a) for a in ax],extent_xyz_mm=[[float(a[0]),float(a[-1])] for a in ax],
  actual_spacing_mm=[(float(a[-1])-float(a[0]))/(len(a)-1) for a in ax])
 return cfg

def refresh_grid(cfg,**changes):
 cfg['defaults']['grid'].update(changes);cfg['defaults']['grid'].update(shape_xyz=None,extent_xyz_mm=None)
 return update_grid_metadata(cfg)

def snapshot(cfg,metadata,directory):
 c=copy.deepcopy(cfg);c.pop('_input_contract',None)
 c['inputs'].pop('entrypoint',None)
 c['inputs']['sample_directory']='.'
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
 def relative(path):
  try:return os.path.relpath(path,directory).replace('\\','/')
  except ValueError:return str(path)
 c['inputs']['pa_files']=[relative(p) for p in c['inputs']['pa_files']]
 for group in c['inputs']['acquisition_groups']:
  if group.get('pa_file'):group['pa_file']=relative(group['pa_file'])
 if c['inputs'].get('detector_file'):c['inputs']['detector_file']=relative(c['inputs']['detector_file'])
 save(directory/'reconstruction_parameters.json',c);save(directory/'sample_metadata.json',metadata)
 return directory

def inspect_sample(sample,*,check_data=True):
 try:
  cfg,m=load_sample(sample,check_data=check_data)
  d=cfg['defaults'];v=cfg.get('validation',{})
  issues=[]
  if v.get('execution_hold') or not d['reconstruction']['enabled']:issues.append('Recorded execution hold / reconstruction disabled')
  issues.extend(str(x) for x in v.get('conflicts',[]))
  if d.get('mb') is None:issues.append('MB needs defaults.mb in the same reconstruction_parameters.json')
  return dict(status='ready_for_bp' if not v.get('execution_hold') and d['reconstruction']['enabled'] else 'unresolved',sample_id=m['acquisition_id'],schema=cfg['schema_version'],
   parameter_files=cfg['_input_contract']['parameter_files'],data_files=[str(selected_pa(cfg))]+([cfg['inputs']['detector_file']] if d['geometry'].get('detector_xyz_mm') is None else []),
   selected_frames=d['frames']['indices_1based'],shape_zyx=[len(a) for a in axes(cfg)[::-1]] if d['grid'].get('center_mm') is not None else None,
   fov_mm=d['grid'],speed_m_s=d['reconstruction']['single_speed_m_s'],mb_available='mb' in d,issues=issues)
 except Exception as e:return dict(status='unresolved',error=str(e),sample=str(sample))
