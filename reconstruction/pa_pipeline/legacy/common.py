"""Shared numeric API. No dataset-name, wavelength, frame-count or speed defaults."""
from dataclasses import dataclass
import copy
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image
from .core.config import require_ready, axes
from .core.signals import prepare
from ..bp_interface import reconstruct


@dataclass
class PreparedPA:
    data_ct: np.ndarray
    sensor_xyz_mm: np.ndarray
    parameters: dict
    pulse_energy: np.ndarray
    timing: dict
    sensor_axis_xyz: np.ndarray | None = None


@dataclass
class Reconstruction:
    mip_yx: np.ndarray
    axes_xyz: list
    parameters: dict
    timing: dict
    volume_zyx: np.ndarray | None = None


def json_save(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def sample_config(sample):
    if isinstance(sample,dict):return copy.deepcopy(sample)
    raise TypeError('Backend expects the validated in-memory configuration from pa_pipeline.config.load_sample')


def prepare_config(cfg):
    if 'mb_preprocessing' in cfg:
        raise ValueError('Already processed MB/shared parameters: replay profile/reconstruction_parameters.json through the pipeline')
    require_ready(cfg)
    data,sensors,energies,timing=prepare(cfg)
    return PreparedPA(data,sensors,copy.deepcopy(cfg),energies,timing)


def reconstruct_prepared(prepared, *, backend='cuda', return_volume=False):
    """Fixed forward BP on preprocessed CT data. This is NOT an autograd operation."""
    if not isinstance(prepared,PreparedPA):raise TypeError('Expected PreparedPA')
    # Explicitly reject tensors carrying a training graph instead of silently detaching.
    if getattr(prepared.data_ct,'requires_grad',False):
        raise ValueError('Current fixed BP has no backward; a trainable BP interface is required')
    cfg=prepared.parameters;require_ready(cfg)
    data=np.asarray(prepared.data_ct);sensors=np.asarray(prepared.sensor_xyz_mm)
    n=cfg['defaults']['frames']['count']*1024
    lo,hi=cfg['defaults']['signal']['time_samples_1based']
    if data.shape!=(n,hi-lo+1) or sensors.shape!=(n,3):raise ValueError('Prepared signal/geometry shape mismatch')
    if not np.isfinite(data).all() or not np.isfinite(sensors).all():raise ValueError('Nonfinite BP input')
    ax=axes(cfg);sink=np.empty(tuple(len(v) for v in ax[::-1]),'f4') if return_volume else None
    started=time.perf_counter()
    mip,ax=reconstruct(data,sensors,cfg,backend=backend,volume_sink=sink,normals=prepared.sensor_axis_xyz)
    timing=dict(prepared.timing,bp_with_transfer_s=time.perf_counter()-started)
    return Reconstruction(mip,ax,copy.deepcopy(cfg),timing,sink)


def png(path, values, cap=None):
    cap=float(np.max(values)) if cap is None else float(cap)
    encoded=np.uint16(np.clip(values/max(cap,1e-30),0,1)*65535)
    path=Path(path);Image.fromarray(encoded).save(path)
    Image.fromarray((encoded//257).astype('u1')).save(path.with_name(path.stem+'_preview.png'))
    return cap


def save_result(result, output, *, already_created=False, run_started=None):
    export_started=time.perf_counter()
    output=Path(output)
    if not already_created:output.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(output/'mip.npz',mip=result.mip_yx,
        axis_x=result.axes_xyz[0],axis_y=result.axes_xyz[1],axis_z=result.axes_xyz[2])
    cap=png(output/'xymip.png',result.mip_yx)
    if result.volume_zyx is not None:
        import h5py
        with h5py.File(output/'volume.h5','w') as h:
            h.attrs['axis_order']='ZYX';h.create_dataset('volume',data=result.volume_zyx)
            for k,v in zip('xyz',result.axes_xyz):h.create_dataset('axis_'+k,data=v)
    json_save(output/'effective_parameters.json',result.parameters)
    result.timing['export_s']=time.perf_counter()-export_started
    if run_started is not None:
        result.timing['whole_sample_s']=time.perf_counter()-run_started
    json_save(output/'result.json',dict(status='complete',timing=result.timing,
        preview_scale_max=cap,numeric_intensity='linear_float_unscaled',physical_GT=False,
        mip_axes='YX',volume_axes='ZYX',autograd=False))
