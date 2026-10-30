"""Export the exact existing 0.7 raw + 0.3 Frangi display volume on server140.

Uses the manuscript display implementation without changing its algorithm.
Only adds an HDF5 export before the existing projection step.
"""
from pathlib import Path
import os,sys,shutil,h5py,numpy as np
os.environ['CUDA_VISIBLE_DEVICES']='GPU-0488969f-25ad-da5d-2bc2-8067a3a8ef15'
base=Path('/dataset2/xiaoyang/XZB/PA_Spherial_Struct/Pipeline')
source=base/'paper_figures_three_stage_20261023/prepare_new_anatomy.py'
out=base/'pacthub_views_20261025';out.mkdir(exist_ok=True)
for name in ['process_scan_display.py','depth_lut_rgb.npy']:
    shutil.copy2(base/'scan_bandpass_sum_20261025'/name,out/name)
code=source.read_text()
needle='amp=cp.asnumpy(disp.max(0))'
addition="with h5py.File(OUT/'scan_processed.h5','w') as export:\n  export.create_dataset('volume_zyx',data=cp.asnumpy(disp),compression='lzf')\n  for key,axis in zip('xyz',[x,y,z[sl]]):export.create_dataset(key+'_mm',data=axis)\n "
assert code.count(needle)==1
code=code.replace(needle,addition+needle)
ns={'__file__':str(out/'prepare_new_anatomy.py'),'__name__':'display_export'}
exec(compile(code,str(source),'exec'),ns)
with h5py.File(base/'scan_bandpass_sum_20261025/scan_sum.h5') as f:
    vol=f['volume_yxz'][:].transpose(2,0,1)
    axes=[f[k+'_mm'][:] for k in 'xyz']
ns['depth'](vol,axes,'sum',[1.9,21.9])
print('EXPORTED',out/'scan_processed.h5',flush=True)
