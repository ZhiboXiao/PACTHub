import argparse,copy,json
from pathlib import Path
from .config import load_sample,inspect_sample,snapshot,detector_array,MB_BASELINE
from .workflow import run

def main():
 p=argparse.ArgumentParser(description='PAdata -> preprocessing -> FOV -> sound speed -> BP / MB; two parameter JSONs.')
 sub=p.add_subparsers(dest='command',required=True)
 plan=sub.add_parser('inspect');plan.add_argument('sample');plan.add_argument('--metadata-only',action='store_true')
 config=sub.add_parser('configure');config.add_argument('sample');config.add_argument('--out',required=True);config.add_argument('--embed-detectors',action='store_true');config.add_argument('--with-mb',action='store_true');config.add_argument('--auto-fov',action='store_true');config.add_argument('--auto-speed',action='store_true')
 calc=sub.add_parser('run');calc.add_argument('sample');calc.add_argument('--out',required=True);calc.add_argument('--methods',nargs='+',choices=['bp','mb'],default=['bp']);calc.add_argument('--backend',choices=['cpu','cuda'],default='cuda');calc.add_argument('--device',type=int,default=0)
 a=p.parse_args()
 if a.command=='inspect':
  report=inspect_sample(a.sample,check_data=not a.metadata_only);print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='ready_for_bp' else 2
 if a.command=='configure':
  cfg,meta=load_sample(a.sample,check_data=False)
  if a.embed_detectors:cfg['defaults']['geometry']['detector_xyz_mm']=detector_array(cfg).tolist();cfg['inputs']['detector_file']=None
  if a.with_mb:
   cfg['defaults'].setdefault('mb',copy.deepcopy(MB_BASELINE))
   cfg.setdefault('parameter_sources',{})['defaults.mb']='Supplied V3 baseline: disk diameter 3.5 mm, 5 iterations; inspect/edit this JSON before applying to a different receiver.'
  if a.auto_fov:cfg['defaults']['fov_detection'].update(enabled=True,apply_to_run=True)
  if a.auto_speed:cfg['defaults']['speed_selection'].update(enabled=True,apply_method='full_global_normalized_gradient',automatic_speed_writeback=False)
  dest=snapshot(cfg,meta,a.out);print(dest);return 0
 report=run(a.sample,a.out,methods=a.methods,backend=a.backend,device=a.device)
 print(json.dumps(dict(status=report['status'],output=str(Path(a.out).resolve()),seconds=report['seconds']),ensure_ascii=False,indent=2));return 0
