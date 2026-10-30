import unittest,tempfile,copy,json,hashlib
from pathlib import Path
import numpy as np
import h5py
from scipy.io import savemat
from pa_pipeline.config import load_sample,core_config,save,refresh_grid,MB_BASELINE,snapshot
from pa_pipeline.geometry import registered_geometry
from pa_pipeline.legacy.core.signals import read_frames,detector_positions
from pa_pipeline.bp_interface import set_bp_backend,bp_available
from pa_pipeline.legacy.common import prepare_config,reconstruct_prepared
from pa_pipeline.legacy.mb import prepare_mb,MBOptions,disk_quadrature
from pa_pipeline.workflow import run

ROOT=Path(__file__).resolve().parents[1]
class PipelineTests(unittest.TestCase):
 def setUp(self):
  set_bp_backend(None)
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.cfg=json.loads((ROOT/'examples/legacy_template/reconstruction_parameters.json').read_text(encoding='utf-8'))
  self.meta=json.loads((ROOT/'examples/legacy_template/sample_metadata.json').read_text(encoding='utf-8'))
  c=self.cfg;d=c['defaults'];c['inputs'].update(pa_files=['PA.h5'],acquisition_groups=[dict(group_id='test',pa_file='PA.h5')],selected_group_id='test',detector_file=None,pa_variable='pa_data')
  c['sample_id']='test';c['export_metadata']['acquisition_id']='test'
  self.meta.update(acquisition_id='test',PA_path='PA.h5',signal_shape=[3,512,1024],signal_dtype='float32',PA_frames=3)
  theta=np.linspace(0,2*np.pi,1024,endpoint=False);detector=np.c_[8*np.cos(theta),8*np.sin(theta),np.full(1024,-6.)]
  d['geometry'].update(detector_xyz_mm=detector.tolist(),detector_axis_signs=[1,1,1],base_coordinate_offset_mm=[0,0,0],base_z_rotation_deg=0.,frame_angle_step_parameter_deg=0.,frame_angle_formula='-(i_fr_stat-1)*delta_angle + 0',additional_z_rotation_deg=0.,base_coordinate_dtype='float64')
  d['frames'].update(indices_1based=[1,3],count=2,available_count=3)
  d['signal'].update(predelay_samples=0.,polarity=1,time_samples_1based=[1,512]);d['signal']['filter']['enabled']=False;d['signal']['energy_normalization'].update(enabled=False,signal_scale=1.)
  d['reconstruction']['single_speed_m_s']=1500.;d['projection']['z_policy']='full_grid';d['output']['save_volume']=True
  refresh_grid(c,center_mm=[0.,0.,0.],space_mm=[2.,2.,2.],resolution_px_mm=2.)
  self.raw=np.zeros((3,512,1024),dtype='f4');self.raw[:,266,:]=np.array([1,2,3])[:,None]
  with h5py.File(self.root/'PA.h5','w') as f:f['pa_data']=self.raw
  self.write()
 def tearDown(self):set_bp_backend(None);self.tmp.cleanup()
 def write(self):save(self.root/'reconstruction_parameters.json',self.cfg);save(self.root/'sample_metadata.json',self.meta)
 def test_public_export_without_entrypoint(self):
  c,m=load_sample(self.root);self.assertEqual(c['inputs']['entrypoint'],'split_pa_file');self.assertEqual(m['acquisition_id'],'test')
 def test_exact_original_frame_order(self):
  values=list(read_frames(self.root/'PA.h5',[3,1]));self.assertEqual([r[0] for r in values],[3,1]);np.testing.assert_array_equal(values[0][1],self.raw[2])
 def test_metadata_shape_rejected(self):
  self.meta['signal_shape'][0]=4;self.write()
  with self.assertRaisesRegex(ValueError,'shape/dtype'):load_sample(self.root)
 def test_mismatched_identity_rejected(self):
  self.meta['acquisition_id']='other';self.write()
  with self.assertRaisesRegex(ValueError,'ID mismatch'):load_sample(self.root)
 def test_inline_and_mat_detector_agree(self):
  c,_=load_sample(self.root);a=detector_positions(c,[1,3]);savemat(self.root/'detector.mat',dict(detector=np.asarray(c['defaults']['geometry'].pop('detector_xyz_mm'))));c['inputs']['detector_file']=str(self.root/'detector.mat');np.testing.assert_array_equal(a,detector_positions(c,[1,3]))
 def test_extra_parameters_are_not_read(self):
  self.cfg['defaults']['speed_selection']['algorithm_parameters_file']='secret.json';self.write()
  with self.assertRaisesRegex(ValueError,'must be inlined'):load_sample(self.root)
 def test_unresolved_parameters_retained(self):
  self.cfg['validation']['execution_hold']=True;self.write()
  with self.assertRaisesRegex(ValueError,'Recorded execution hold'):load_sample(self.root)
 def test_rigid_geometry_preserves_physical_angles(self):
  c,_=load_sample(self.root);origin=detector_positions(c,[1,3]).reshape(-1,3).astype('f4');theta=.13;r=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1.]])
  t=np.array([1.2,-.7,.4]);c['frame_registration']=dict(convention='p_moving_native=R@p_reference_native+t_mm',transforms={str(f):dict(R=r.tolist(),t_mm=t.tolist()) for f in [1,3]});c['schema_version']='1.0.0+starnet-rigid-v3';core_config(c)
  pos,norm=registered_geometry(c);expected=(origin-t)@r;np.testing.assert_allclose(pos,expected,atol=1e-6);np.testing.assert_allclose(norm,(-origin/np.linalg.norm(origin,axis=1)[:,None])@r,atol=2e-7)
 def test_missing_registration_rejected(self):
  self.cfg['schema_version']='1.0.0+starnet-rigid-v3';self.cfg['frame_registration']=dict(convention='p_moving_native=R@p_reference_native+t_mm',transforms={});self.write()
  with self.assertRaisesRegex(ValueError,'Missing inline registration'):load_sample(self.root)
 def test_mb_inline_coordinate_input(self):
  c,_=load_sample(self.root);p=prepare_mb(core_config(c),options=MBOptions(**MB_BASELINE));self.assertEqual(p.shared.data_ct.shape,(2048,512));self.assertEqual(p.kernel.tolist(),[1.])
 def test_disk_quadrature_normal(self):
  s=np.array([[0.,0.,-10.]]);n=np.array([[1.,0.,0.]]);off,w=disk_quadrature(s,1.75,3,16,normals=n);np.testing.assert_allclose(off[0],0,atol=1e-12);self.assertAlmostEqual(float(w.sum()),1.,places=6)
 def test_pipeline_interface_replay_and_source_unchanged(self):
  # Constant-output callback tests the interface only; it is not a BP algorithm.
  def interface_stub(data,sensors,cfg,backend='cpu',speed=None,volume_sink=None,normals=None):
   from pa_pipeline.legacy.core.config import axes
   ax=axes(cfg)
   if volume_sink is not None:volume_sink.fill(1.)
   return np.ones((len(ax[1]),len(ax[0])),dtype='f4'),ax
  set_bp_backend(interface_stub)
  before=(self.root/'reconstruction_parameters.json').read_bytes();r=run(self.root,self.root/'run',backend='cpu');self.assertEqual(r['status'],'complete');self.assertEqual(before,(self.root/'reconstruction_parameters.json').read_bytes())
  loaded,_=load_sample(self.root/'run/profile');self.assertEqual(loaded['defaults']['frames']['indices_1based'],[1,3])
  np.testing.assert_allclose(loaded['defaults']['grid']['actual_spacing_mm'],[2/3]*3,atol=1e-7)
  with h5py.File(self.root/'run/BP/volume.h5') as h:vol=h['volume'][:]
  self.assertGreater(float(vol.max()),0);self.assertEqual(vol.shape,(4,4,4));self.assertEqual(set(p.name for p in (self.root/'run/profile').iterdir()),{'sample_metadata.json','reconstruction_parameters.json'})
  refresh_grid(loaded,resolution_px_mm=3.);np.testing.assert_allclose(loaded['defaults']['grid']['actual_spacing_mm'],[2/5]*3,atol=1e-7)
 def test_missing_bp_stops_before_output(self):
  self.assertFalse(bp_available())
  with self.assertRaisesRegex(RuntimeError,'BP backend is disabled'):
   run(self.root,self.root/'absent',backend='cpu')
  self.assertFalse((self.root/'absent').exists())
 def test_mb_only_skips_unavailable_bp(self):
  from unittest.mock import patch
  from pa_pipeline.legacy.common import Reconstruction
  from pa_pipeline.legacy.core.config import axes
  self.cfg['defaults']['mb']=copy.deepcopy(MB_BASELINE);self.write()
  def solver_stub(prepared,device=0,return_volume=True):
   cfg=prepared.shared.parameters;ax=axes(cfg)
   volume=np.ones(tuple(len(a) for a in ax[::-1]),dtype='f4')
   return Reconstruction(volume.max(axis=0),ax,copy.deepcopy(cfg),{},volume),dict(history=[dict(test_stub=True)])
  with patch('pa_pipeline.workflow.reconstruct_mb_prepared',side_effect=solver_stub):
   record=run(self.root,self.root/'mb',methods=('mb',),backend='cpu')
  self.assertEqual(record['status'],'complete')
  self.assertEqual(record['stages']['bp_matched']['status'],'skipped')
  self.assertTrue((self.root/'mb/MB/volume.h5').is_file())
  self.assertFalse((self.root/'mb/BP_matched').exists())
 def test_public_bp_dataset_replay(self):
  from pa_pipeline.bp_interface import public_reconstruct
  set_bp_backend(public_reconstruct)
  before=(self.root/'reconstruction_parameters.json').read_bytes()
  result=run(self.root,self.root/'public',backend='cpu')
  self.assertEqual(result['status'],'complete')
  self.assertEqual(before,(self.root/'reconstruction_parameters.json').read_bytes())
  replay,_=load_sample(self.root/'public/profile')
  self.assertEqual(replay['defaults']['reconstruction']['algorithm'],'xu_wang_2005_ubp')
  with h5py.File(self.root/'public/BP/volume.h5') as h:
   self.assertTrue(np.isfinite(h['volume'][:]).all())
   self.assertGreater(float(np.abs(h['volume'][:]).max()),0)
 def test_stale_grid_rejected(self):
  self.cfg['defaults']['grid']['center_mm'][0]=3;self.write()
  with self.assertRaisesRegex(ValueError,'Stale grid extent'):load_sample(self.root)
if __name__=='__main__':unittest.main()
