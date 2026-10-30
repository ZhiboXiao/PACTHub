"""Extract representative fields from the shipped reconstruction example."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reconstruction/examples/embedded_two_json'
p = json.loads((SOURCE / 'reconstruction_parameters.json').read_text(encoding='utf-8'))
sections = ['signal', 'frames', 'grid', 'geometry']
record = {
    'source': 'reconstruction/examples/embedded_two_json/reconstruction_parameters.json',
    'source_sha256': hashlib.sha256((SOURCE / 'reconstruction_parameters.json').read_bytes()).hexdigest(),
    'schema_version': p['schema_version'], 'sample_id': p['sample_id'],
    'defaults': {section: p['defaults'][section] for section in sections},
}
(ROOT/'data/parameter-explorer.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Parameter explorer: representative fields extracted from',record['sample_id'])
