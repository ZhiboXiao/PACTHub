"""Explicit source-mode9 defaults adapter; does not execute arbitrary MATLAB.

Use the sample's copied source program. Unknown branches fail closed. Source
scan geometry/fusion is separate from the already validated unified BP kernel.
"""
import copy
import hashlib
from pathlib import Path
import re
import numpy as np

from . import fusion
from .core.config import require_ready


def source_defaults(script):
    path=Path(script);text=path.read_text(encoding='utf-8-sig')
    clean='\n'.join(line.split('%')[0] for line in text.splitlines())
    head=clean.split('switch reconstruct_mode',1)[0]
    def number(name,body=head):
        found=re.findall(r'^\s*'+re.escape(name)+r'\s*=\s*([-+\d.eE]+)\s*;',body,re.M)
        if len(found)!=1:raise ValueError('Missing/ambiguous source scalar: '+name)
        value=float(found[0])
        if not np.isfinite(value):raise ValueError('Nonfinite source scalar: '+name)
        return value
    keys=['reconstruct_mode','VM_out','fs','step_x','step_y','step_length_x','step_length_y',
          'Nframex_scan','Nframey_scan','GaussianMask_FWHM','x_size','y_size','z_size',
          'center_x','center_y','center_z','resolution_factor','theta_z','Is_Gating','Is_Denoising']
    p={key:number(key) for key in keys}
    if p['reconstruct_mode']!=9:raise ValueError('This explicit adapter supports active mode9 only')
    match=re.search(r'(?ms)^\s*case\s+9\b(.*?)(?=^\s*case\s+\d+\b|\Z)',clean)
    if not match:raise ValueError('Missing mode9')
    body=match[1];compact=re.sub(r'\s+','',body).replace('...','')
    for statement in ['VM_in=VM_out;', 'frame_idx=1+((xframe-1)*Nframey_scan+(yframe-1))*4;',
            'pa_total=pa_total+subplus(pa_img3);', 'current_weight=GaussianMask*single(static_Nframe);',
            'idx_y=totalsize_y-(yframe-1)*step_length_y*resolution_factor-SubWinSize_y:totalsize_y-(yframe-1)*step_length_y*resolution_factor;',
            'idx_x=(xframe-1)*step_length_x*resolution_factor+1:(xframe-1)*step_length_x*resolution_factor+1+SubWinSize_x;',
            'theta_z=(static_frames(frame)-1)*delta_angle;', 'delta_angle=-11000*0.800/11000;']:
        if statement not in compact:raise ValueError('Unsupported mode9 statement: '+statement)
    for name in ['center_x','center_y','center_z','VM_out','step_length_x','step_length_y','resolution_factor']:
        if re.search(r'(?m)^\s*'+name+r'\s*=',body):
            raise ValueError('Mode9 dynamically changes '+name+'; explicit adapter needed')
    for axis in 'xyz':
        if f'Npixel_{axis}={axis}_size*resolution_factor+1;' not in re.sub(r'\s+','',head):
            raise ValueError('Unrecognized source grid')
    for key in ['Nframex_scan','Nframey_scan','step_x','step_y']:
        if p[key]<1 or not p[key].is_integer():raise ValueError('Invalid integer source parameter '+key)
        p[key]=int(p[key])
    for key in ['step_length_x','step_length_y','resolution_factor','GaussianMask_FWHM','VM_out','fs']:
        if p[key]<=0:raise ValueError('Nonpositive source parameter '+key)
    p.update(effective_speed_m_s=p['VM_out'],delta_angle_deg=-.8,
             source_script=str(path),source_script_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
             default_policy='active source program; explicit overrides must be recorded',
             source_post_stitch_display_rotation_deg=number('theta',body),
             bp_policy='existing_unified_signed_joint_BP',
             fusion_method=fusion.SOURCE_MODE9)
    return p


def trajectory(group_ids,p):
    nx,ny=p['Nframex_scan'],p['Nframey_scan']
    if len(group_ids)!=nx*ny or len(set(group_ids))!=len(group_ids):
        raise ValueError('Full acquisition list must match source Nx*Ny')
    result=[]
    for x in range(0,nx,p['step_x']):
        for y in range(0,ny,p['step_y']):
            result.append(dict(group_id=group_ids[x*ny+y],source_group_index_1based=x*ny+y+1,
                               x_index_1based=x+1,y_index_1based=y+1,
                               placement_mm=[x*p['step_length_x'],-y*p['step_length_y'],0]))
    return result


def group_parameters(base,p,group_id,pa_file,preparation,detector_file,overrides=None):
    """Source acquisition/geometry defaults plus existing unified BP semantics."""
    c=copy.deepcopy(base);c.pop('scan',None);d=c['defaults'];inp=c['inputs']
    inp.update(entrypoint='split_pa_file',selected_group_id=group_id,pa_files=[str(pa_file)],
               detector_file=str(detector_file),preprocessing_script=preparation['filter_function'],
               acquisition_groups=[dict(group_id=group_id,pa_file=str(pa_file))])
    s=d['signal'];s.update(sampling_frequency_hz=p['fs']*1e6,
        predelay_samples=preparation['reference_predelay_samples'],time_samples_1based=[1,4096],
        crop_stage='after_filter_and_energy_normalization',polarity=-1,analytic_signal=False,
        nan_policy='replace_with_zero',additional_denoising=False,bad_channels_1based=[],
        channel_calibration_file=None,channels_1based_range_inclusive=[1,1024])
    s['filter']=dict(enabled=bool(p['Is_Denoising']),kind='butterworth_bandpass',
                     band_hz=[1.44e6,5.76e6],order_argument=4,zero_phase=True)
    s['energy_normalization']=dict(enabled=False,method='max_over_time_of_channel_mean',
                                  window_samples_1based=[1,100],signal_scale=1)
    ids=[int(i) for i in preparation['frames_1based']]
    d['frames'].update(mode='explicit_indices',count=len(ids),indices_1based=ids,
        available_count=preparation['available_PA_frames'],compound_mode='joint_signed_weighted_BP',
        gating='source_mode9_mean_correlation_top20_including_ties_excluding_first10')
    d['geometry'].update(coordinate_unit='mm',detector_axes=['x','y','z'],detector_axis_signs=[1,1,-1],
        base_coordinate_offset_mm=[.555,.39,0],base_coordinate_dtype='float32',
        base_z_rotation_deg=p['theta_z'],frame_angle_step_parameter_deg=-p['delta_angle_deg'],
        frame_angle_formula='-(i_fr_stat-1)*delta_angle + 0',additional_z_rotation_deg=0.,
        rotation_origin_mm=[0,0,0],sensor_axis_model='toward_origin',
        transform_order=['base_Rz','frame_Rz','additional_Rz'])
    space=[p[axis+'_size'] for axis in 'xyz'];center=[p['center_'+axis] for axis in 'xyz']
    d['grid'].update(center_mm=center,space_mm=space,resolution_px_mm=p['resolution_factor'],
        sampling_rule='source_intervals_plus_one',grid_rule='N=FOV*resolution+1; inclusive endpoints',
        shape_xyz=None,extent_xyz_mm=None,actual_spacing_mm=None,coordinate_frame='source_BP_physical_xyz_mm')
    d['reconstruction'].update(enabled=True,mode='single_speed',single_speed_m_s=p['effective_speed_m_s'],
        receive_half_angle_deg=45.,angle_compensation=True,distance_weight='inverse_squared_distance',
        apodization='polynomial_(2cos2_minus_1)^2',time_interpolation='nearest_sample_round',
        postprocess='weighted_mean_then_nonnegative')
    d['projection'].update(plane='xy',method='maximum',z_policy='full_grid',z_range_mm=None,z_indices_1based_inclusive=None)
    for name in ['fov_detection','boundary','speed_selection','us']:d[name]['enabled']=False
    overrides=overrides or {}
    for key,value in overrides.items():
        if key!='single_speed_m_s':raise ValueError('Unreviewed source-default override: '+key)
        if not np.isfinite(value) or value<=0:raise ValueError('Invalid sound-speed override')
        d['reconstruction'][key]=value
    c['source_scan_defaults']=copy.deepcopy(p);c['explicit_overrides']=copy.deepcopy(overrides)
    c['validation'].update(execution_hold=False,conflicts=[],missing_pa_inputs=[],pa_defaults_complete=True,
        warnings=['wavelength_unknown' if inp.get('wavelength_nm') is None else '',
                  'source scan/grid with unified BP; NOT source per-frame rectification or source CUDA parity'])
    require_ready(c)
    return c


def scan_profile(sample_id,p,all_group_ids,configs):
    """Complete source placement profile; no arbitrary dataset-wide old defaults."""
    from .scan_profile import load_scan_profile
    groups=trajectory(all_group_ids,p)
    for g in groups:
        if g['group_id'] not in configs:raise ValueError('Missing prepared acquisition '+g['group_id'])
        g['parameters']=copy.deepcopy(configs[g['group_id']])
    center=np.asarray([p['center_'+a] for a in 'xyz']);space=np.asarray([p[a+'_size'] for a in 'xyz'])
    shifts=np.asarray([g['placement_mm'] for g in groups])
    lo=center-space/2+shifts.min(axis=0);hi=center+space/2+shifts.max(axis=0)
    intervals=(hi-lo)*p['resolution_factor']
    if not np.allclose(intervals,np.round(intervals),atol=1e-8,rtol=0):raise ValueError('Noninteger source scan canvas')
    plan=dict(schema_version='pa.scan/1.0',sample_id=sample_id,reference_group_id=groups[0]['group_id'],
        shared_z_rotation_deg=0.,groups=groups,output_axes_xyz=[[float(a),float(b),int(round(n))+1] for a,b,n in zip(lo,hi,intervals)],
        fusion=dict(method=fusion.SOURCE_MODE9,gaussian_fwhm_mm=p['GaussianMask_FWHM'],input_representation='normalized_compound'),
        crop=dict(method='max_fully_covered_rectangle',required_center_mm=center.tolist()),
        source=copy.deepcopy(p),display=dict(source_post_stitch_rotation_deg=p['source_post_stitch_display_rotation_deg'],
            applied_to_quantitative_volume=False,reason='preserve physical axes; no post-BP image rotation per dataset policy'),
        training=dict(keep_entire_scan_in_one_split=True,physical_GT=False,head_tail_status='unresolved'))
    return load_scan_profile(plan)
