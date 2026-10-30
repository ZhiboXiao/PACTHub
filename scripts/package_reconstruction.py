"""Build or verify the website's source-only reconstruction download."""
from pathlib import Path
import argparse, hashlib, io, json, re, zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'reconstruction'

def build(check=False):
    files = [PACKAGE / name for name in [
        'reconstruct.py', 'pyproject.toml', 'requirements.txt', 'README.md',
        'README_CN.md', 'BP_INTERFACE.md', 'PUBLIC_BP.md', 'PUBLIC_BP_SOURCES.md', 'BP_REFERENCES.bib', 'PIPELINE_PSEUDOCODE.md', 'validation_report.json',
    ]]
    for folder in ['pa_pipeline', 'tests', 'examples']:
        files += [p for p in (PACKAGE / folder).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    forbidden = {'bp.py', 'adpat_device.cu', 'bp_reference.py', 'test_bp_reference.py'}
    blocked = [p for p in files if p.name in forbidden]
    if blocked:
        raise SystemExit('Proprietary BP cores are confidential; remove them before packaging: '+', '.join(str(p) for p in blocked))
    blobs = {p.relative_to(PACKAGE).as_posix(): p.read_bytes() for p in files}
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(blobs.items())}
    hash_bytes = (json.dumps(hashes, indent=2) + '\n').encode()
    blobs['SOURCE_HASHES.json'] = hash_bytes
    version = re.search(r'^version = "([^"]+)"', (PACKAGE / 'pyproject.toml').read_text(), re.M)[1]
    target = ROOT / 'assets/downloads' / f'pacthub-workflow-v{version}.zip'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name, content in sorted(blobs.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    payload = output.getvalue()
    if check:
        if not target.is_file():
            raise SystemExit('Code download is stale: run python scripts/package_reconstruction.py')
        # ZIP headers and compression bytes can vary between operating systems.
        # Verify the full file set and uncompressed bytes, including source hashes.
        with zipfile.ZipFile(target) as z:
            if len(z.namelist()) != len(set(z.namelist())):
                raise SystemExit('Code download contains duplicate file names')
            actual = {name: z.read(name) for name in z.namelist()}
        if actual != blobs:
            changed = sorted(name for name in set(actual) | set(blobs)
                             if actual.get(name) != blobs.get(name))
            raise SystemExit('Code download is stale: ' + ', '.join(changed))
        if (PACKAGE / 'SOURCE_HASHES.json').read_bytes() != hash_bytes:
            raise SystemExit('Source hashes are stale: run python scripts/package_reconstruction.py')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        (PACKAGE / 'SOURCE_HASHES.json').write_bytes(hash_bytes)
    print(f'{"VERIFIED" if check else "BUILT"}: {target.name}; {len(blobs)} files; {len(payload):,} bytes')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
