"""Validate published measurements, provenance and local website references."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,csv,math,hashlib,re,gzip,struct
R=Path(__file__).resolve().parents[1]
load=lambda p:json.loads((R/p).read_text(encoding='utf-8'))
samples=load('data/samples.json'); data=load('data/temporal.json')
assert len(samples)==8 and len({s['id'] for s in samples})==8
assert len({s['acquisition_id'] for s in samples})==8
for s in samples:
 assert s['is_demo'] is False
 if s['acquisition_id'].startswith('3DPanoPACT-'):
  release=s['provenance']['official_release']
  assert release['doi']=='10.6084/m9.figshare.28443374.v3'
  assert release['acquisition_timestamp'] is None
  assert s['display']['scale_calibration']['isotropic_grid_assumption'] is True
 else:assert re.match(r'^20\d{6}_\d{6}',s['acquisition_id'])
 assert set(s['views'])=={'depth','gray','volume'}
 assert set(s['display']['scale_bars'])=={'depth','gray','volume'}
 for bar in s['display']['scale_bars'].values():
  assert math.isclose(bar['length_pixels'],bar['length_mm']*bar['pixels_per_mm'])
  assert bar['position']=='lower right of preview frame; calibrated HTML overlay'
 assert all((R/p).is_file() for p in s['views'].values())
 assert s['display']['gamma']==1
 assert s==load('data/'+s['id']+'.json')
try:
 import jsonschema
 jsonschema.validate(samples,load('data/metadata.schema.json'))
except ImportError:
 print('jsonschema not installed; structural checks applied.')
rows=list(csv.DictReader((R/'data/temporal-readouts.csv').open(encoding='utf-8')))
assert len(rows)==144
for s in data['series']:
 n=len(s['frames']); times=[f['time_min'] for f in s['frames']]
 assert n==s['measured_timepoints'] and times[0]==0 and all(a<b for a,b in zip(times,times[1:]))
 assert math.isclose(times[-1],s['duration_minutes']) and s['shared_window_across_time'] and s['gamma']==1
 assert all((R/f['image']).is_file() for f in s['frames'])
 assert len({f['acquisition_id'] for f in s['frames']})==n
 assert len(s['registration']['transforms'])==n and s['registration']['intensity_normalization'] is False
 assert s['scale_bar']['length_mm']==5
 interactive=s['interactive_mips'];packed=(R/interactive['url']).read_bytes()
 assert hashlib.sha256(packed).hexdigest()==interactive['sha256']
 assert len(packed)==interactive['bytes'] and interactive['includes_scale_bar'] is False
 blob=gzip.decompress(packed);magic,nt,h,w,flags=struct.unpack('<4sIIII',blob[:20])
 assert magic==b'PAM2' and flags==8 and [nt,h,w]==interactive['shape_tyx'] and nt==n
 assert len(blob)==interactive['uncompressed_bytes']==36+nt*h*w+h*w
 scale,offset=struct.unpack_from('<2d',blob,20)
 quant=interactive['quantization']
 assert math.isfinite(scale) and scale>0 and math.isfinite(offset)
 assert quant['bits']==8 and quant['scale']==scale and quant['offset']==offset
 assert not quant['clipping'] and not quant['temporal_subsampling'] and not quant['spatial_subsampling']
 assert interactive['frame_order']==[f['acquisition_id'] for f in s['frames']]
 assert sum(blob[36+nt*h*w:])==interactive['common_valid_pixels']
 for a,b,c,d in interactive['default_rois_xyxy']:assert 0<=a<c<=w and 0<=b<d<=h
 for tr in s['registration']['transforms']:
  assert tr['feature_ncc_after']>=tr['feature_ncc_before']-1e-6
  matrix=tr['input_to_reference_matrix'];a,b=matrix[0][:2];c,d=matrix[1][:2]
  assert abs(a*d-b*c-1)<1e-5 and abs(a*a+c*c-1)<1e-5
 xmin,xmax,ymin,ymax=s['extent_xy_mm']
 for region in s['regions']:
  a,b,c,d=region['bounds_xy_mm'];assert xmin<=a<b<=xmax and ymin<=c<d<=ymax
  values=region['mean_linear'];relative=region['relative_mean']
  assert len(values)==len(relative)==n and region['pixel_count']>0
  assert all(math.isfinite(v) and v>=0 for v in values)
  assert all(math.isclose(v/values[0],r,rel_tol=1e-12) for v,r in zip(values,relative))
  for i in range(n):
   row=next(v for v in rows if v['series']==s['id'] and v['roi']==region['id'] and math.isclose(float(v['time_min']),times[i],abs_tol=1e-10))
   assert math.isclose(float(row['mean_linear']),values[i],rel_tol=1e-12)
   assert math.isclose(float(row['relative_to_first']),relative[i],rel_tol=1e-12)
assert data['series'][1]['duration_minutes']<20
assert data['series'][1]['display_flip_y'] is True
q=load('data/q-calculation.json')
assert q['gain']==1 and q['local_contrast_sigma_mm']==.4
for v in q['scores']:assert math.isclose(v['Q'],100*math.sqrt(v['D_weak']*v['D_strong']))
assert (R/'assets/media/q-calculation.mp4').stat().st_size>100000
mouse=load('data/q-mouse-calculation.json');v=mouse['score']
assert mouse['agreement_with_manuscript'] and mouse['masks_equal_manuscript']
assert mouse['reference_display_label']=='GT'
assert mouse['support']['weak']+mouse['support']['strong']==mouse['support']['voxels']
assert math.isclose(v['Q'],100*math.sqrt(v['D_weak']*v['D_strong']))
assert math.isclose(v['Q'],82.53475740607392)
assert (R/'assets/media/q-mouse.mp4').stat().st_size>100000
qfilm=load('data/q-video.json')
calibration=load('data/calibration-video.json')
assert calibration['duration_seconds']==32 and calibration['frame_count']==768
assert len(calibration['frames_1based'])==20 and len(set(calibration['frames_1based']))==20
speed=calibration['speed'];assert len(speed['speeds_m_s'])==len(speed['scores'])==23
assert speed['selected_m_s']==speed['speeds_m_s'][max(range(23),key=lambda i:speed['scores'][i])]
assert calibration['display']['window_shared_across_speeds'] and calibration['display']['gamma']==1
assert calibration['fov']['applied_to_speed_reconstruction'] is True
assert speed['grid']['space_mm']==calibration['fov']['target_space_xyz_mm']==[40,80,20]
assert speed['grid']['center_mm']==calibration['fov']['center_rotated_mm']
assert math.isclose(calibration['fov']['angle_deg'],-12.145418126852595)
assert calibration['display']['speed_shape_syx']==[23,800,400]
for kind in ['movie','poster']:
 assert hashlib.sha256((R/calibration[kind]).read_bytes()).hexdigest()==calibration[kind+'_sha256']
assert calibration['captions'][0]['start']==0 and calibration['captions'][-1]['end']==32
assert all(a['end']==b['start'] for a,b in zip(calibration['captions'],calibration['captions'][1:]))
assert [r['id'] for r in load('data/site-config.json')['downloads']]==['zenodo','full']
parameter_example=load('data/parameter-explorer.json')
parameter_source=load(parameter_example['source'])
assert hashlib.sha256((R/parameter_example['source']).read_bytes()).hexdigest()==parameter_example['source_sha256']
assert parameter_example['sample_id']==parameter_source['sample_id']
for section,fields in parameter_example['defaults'].items():
 assert fields==parameter_source['defaults'][section],section
 for key,value in fields.items():assert value==parameter_source['defaults'][section][key],(section,key)
assert len(parameter_example['defaults']['frames']['indices_1based'])==parameter_example['defaults']['frames']['count']
assert set(parameter_example['defaults'])=={'signal','frames','grid','geometry'}
dataset_citation=load('data/site-config.json')['dataset_citations']['dataset']
assert dataset_citation['doi']=='10.5281/zenodo.23496053' and dataset_citation['doi'] in (R/dataset_citation['bibtex_file']).read_text(encoding='utf-8')
assert qfilm['duration_seconds']==sum(s['duration_seconds'] for s in qfilm['sources'])==51
assert len(qfilm['chapters'])==6 and qfilm['chapters'][-1]['start']==35
assert qfilm['captions'][0]['start']==0 and qfilm['captions'][-1]['end']==51
assert all(a['end']==b['start'] for a,b in zip(qfilm['captions'],qfilm['captions'][1:]))
for part in qfilm['sources']:
 assert hashlib.sha256((R/part['file']).read_bytes()).hexdigest()==part['sha256']
assert hashlib.sha256((R/qfilm['movie']).read_bytes()).hexdigest()==qfilm['movie_sha256']
additional=load('data/additional-specimens.json')
assert len(additional)==4
for record in additional:
 sample=next(s for s in samples if s['acquisition_id']==record['sample_id'])
 assert record['displayed_shape_zyx']==sample['dimensions']
 assert set(record['view_extent_xyz_mm'])=={'depth','gray','volume'}
 for view in sample['views']:
  assert record['view_extent_xyz_mm'][view]==record['extent_xyz_mm']
  assert sample['display']['view_extent_xyz_mm'][view]==record['extent_xyz_mm']
 for bounds,spacing,size in zip(record['extent_xyz_mm'],record['spacing_xyz_mm'],record['displayed_shape_zyx'][::-1]):
  assert bounds[0]<bounds[1] and math.isclose(bounds[1]-bounds[0],spacing*(size-1),rel_tol=1e-6)
 assert record['native_z_slice'][1]-record['native_z_slice'][0]==sample['dimensions'][0]
 assert record['intensity_window']==sample['display']['intensity_window']
provenance=load('data/display-provenance.json')
film=load('data/overview-film.json')
assert film['sample_id']==next(s for s in samples if s['id']=='mouse-scan')['acquisition_id']
assert film['display_mask']['target_roi_audit']['target_mip_max_abs_change']==0
assert film['display_mask']['original_source_modified'] is False
for key in ['movie','poster']:
 assert hashlib.sha256((R/film[key]).read_bytes()).hexdigest()==film[key+'_sha256']
library=load('data/overview-library.json')['films']
assert [entry['id'] for entry in library]==['structure','motion','rotation']
for entry in library:
 assert hashlib.sha256((R/entry['movie']).read_bytes()).hexdigest()==entry['sha256']
 assert hashlib.sha256((R/entry['poster']).read_bytes()).hexdigest()==entry['poster_sha256']
 assert set(entry['title'])==set(entry['description'])=={'en','zh'}
motion=load('data/motion-cutout.json')
motion_entry=next(entry for entry in library if entry['id']=='motion')
assert motion_entry['source']=='data/motion-cutout.json'
assert motion_entry['movie']==motion['movie']
assert motion['frame_count']==474 and motion['duration_seconds']==15.8
assert motion['exterior_depth_max_before_encoding']==0
assert motion['original_source_modified'] is False
assert hashlib.sha256((R/motion['source']).read_bytes()).hexdigest()==motion['source_sha256']
rotation=load('data/leaf-compounding.json')
assert library[-1]['source']=='data/leaf-compounding.json'
assert rotation['sample_id']=='20241115_104329'
assert rotation['counts']==[n['count'] for n in rotation['numerical_outputs']]==list(range(1,21))
assert len(rotation['frames_1based'])==len(set(rotation['frames_1based']))==20
assert rotation['frames_1based']==rotation['reconstruction']['frames_1based']
assert rotation['frames_1based']==list(range(1,21))
assert rotation['detail_inset'] is False
assert rotation['array_animation']['shape']=='hemisphere'
assert rotation['array_animation']['matrix']==[4,5]
assert rotation['views']==['axial MIP']
assert rotation['common_window'] and not rotation['extra_gain']
assert 0<rotation['display_window'][0]<rotation['display_window'][1]
hero=load('data/hero-story.json');hero_config=load('data/site-config.json')['hero']
assert hero['presentation']['duration_seconds']==12 and hero_config['loop_start_seconds']==0
for mode,entry in hero['outputs'].items():
 assert hashlib.sha256((R/entry['file']).read_bytes()).hexdigest()==entry['sha256']
 key='mp4_url' if mode=='desktop' else 'mobile_mp4_url'
 assert urlsplit(hero_config[key]).path==entry['file']
sources=load('data/official-volume-sources.json')
assert len(sources)==3
assert not any(s['id']=='brain-ex-vivo' for s in samples)
for source in sources:
 sample=next(s for s in samples if s['id']==source['id'])
 record=next(r for r in additional if r['sample_id']==source['release_id'])
 assert source['source_data']==sample['provenance']['official_release']['source_data']
 assert source['source_data']['sha256']==record['source_volume_sha256']
 assert source['source_data']['shape_hdf5']==[record['native_shape_zyx'][i] for i in [0,2,1]]
 assert source['source_data']['size_bytes']>1000000
assert next(s for s in samples if s['id']=='mouse-liver')['mode']=='single'
for asset in provenance['assets']:
 assert hashlib.sha256((R/asset['file']).read_bytes()).hexdigest()==asset['sha256']
 if '/overview-' in asset['file']:assert 'scale_bar' not in asset
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.keys=[];self.ids=[];self.anchors=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and a.get('href'):self.anchors.append(a['href'])
  if 'id' in a:self.ids.append(a['id'])
  for key in ['href','src','poster']:
   if a.get(key):self.links.append(a[key])
  for key,v in attrs:
   if key=='data-i18n' or key in ['data-i18n-content','data-i18n-placeholder','data-i18n-aria-label','data-i18n-alt']:self.keys.append(v)
papers=load('data/publications.json')
assert [p['id'] for p in papers]==['panopact','panopaus','liver']
assert {p['doi'].lower() for p in papers}=={'10.1038/s41467-025-65054-x','10.3788/ai.2026.10028','10.34133/bmef.0327'}
for paper in papers:
 assert paper['title'] and len(paper['authors'])>=13 and paper['license']=='CC BY 4.0'
 assert paper['doi'] in paper['citation'] and paper['url']=='https://doi.org/'+paper['doi']
 assert paper['first_page']['page']==1 and paper['first_page']['width']==1800
 for kind in ['image','thumbnail']:
  assert hashlib.sha256((R/paper['first_page'][kind]).read_bytes()).hexdigest()==paper['first_page'][kind+'_sha256']
 bib=(R/paper['bibtex_file']).read_text(encoding='utf-8')
 assert paper['doi'] in bib and paper['title'] in bib
 assert all(a['family']+', '+a['given'] in bib for a in paper['authors'])
js=(R/'assets/js/i18n.js').read_text(encoding='utf-8');start=js.index('const messages = ')+len('const messages = ');end=js.index('\n  const storageKey',start);messages=json.loads(js[start:end].strip().removesuffix(';'))
for p in [R/'index.html',*list((R/'docs').glob('*.html'))]:
 doc=Links();doc.feed(p.read_text(encoding='utf-8'));assert len(doc.ids)==len(set(doc.ids)),p
 assert not any(urlsplit(link).path.endswith(('.json','.csv')) for link in doc.anchors),(p,doc.anchors)
 for link in doc.links:
  u=urlsplit(link)
  if not u.scheme and u.path:assert (p.parent/unquote(u.path)).is_file(),(p,link)
  if not u.path and u.fragment:assert u.fragment in doc.ids,(p,link)
 for key in doc.keys:assert key in messages,(p,key)
 assert not re.search('enhancement|Restormer|增强',p.read_text(encoding='utf-8'),re.I),p
print('PASS: 8 specimens / 24 calibrated views; 36 calibrated compact MIPs and 144 reference ROI readings; Q and calibration films; 3 overview films including consecutive leaf BP; hero; 3 publications; translations and local links; no raw JSON/CSV UI links.')
