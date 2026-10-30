"""Render genuine article first pages and rebuild section 06 from verified records.

Usage: python scripts/build_publications.py --panopact FILE --panopaus FILE --liver FILE
PDFs remain outside the website; only page-one images and citations are exported.
"""
from pathlib import Path
import argparse, hashlib, html, json, re
import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def esc(value):
    return html.escape(str(value), quote=True)

def main():
    ap = argparse.ArgumentParser()
    for key in ['panopact', 'panopaus', 'liver']:
        ap.add_argument('--' + key, type=Path, required=True)
    args = ap.parse_args()
    records_path = ROOT / 'data/publications.json'
    records = json.loads(records_path.read_text(encoding='utf-8'))
    image_dir = ROOT / 'assets/images/publications'
    cite_dir = ROOT / 'assets/citations'
    image_dir.mkdir(parents=True, exist_ok=True)
    cite_dir.mkdir(parents=True, exist_ok=True)
    cards, bibs = [], []
    for record in records:
        key = record['id']
        source = getattr(args, key)
        doc = pymupdf.open(source)
        page = doc[0]
        page_text = re.sub(r'\s+', '', page.get_text()).lower()
        assert record['doi'].lower() in page_text, (key, 'DOI missing on first page')
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1800 / page.rect.width, 1800 / page.rect.width), alpha=False)
        im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        full = image_dir / (key + '-page1.webp')
        thumb = image_dir / (key + '-thumb.webp')
        im.save(full, lossless=True, method=6)
        small = im.copy()
        small.thumbnail((600, 900), Image.Resampling.LANCZOS)
        small.save(thumb, quality=94, method=6)
        record['first_page'] = dict(
            image=full.relative_to(ROOT).as_posix(),
            thumbnail=thumb.relative_to(ROOT).as_posix(),
            width=im.width, height=im.height,
            source_pdf_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            image_sha256=hashlib.sha256(full.read_bytes()).hexdigest(),
            thumbnail_sha256=hashlib.sha256(thumb.read_bytes()).hexdigest(),
            page=1, crop='complete published first page',
        )
        authors = record['authors']
        short = ', '.join(a['family'] + ' ' + ''.join(n[0] for n in a['given'].replace('.', '').split()) for a in authors)
        location = record['volume'] + ('(' + record['issue'] + ')' if record.get('issue') else '') + ':' + record['article_number']
        record['citation'] = f"{short}. {record['title']}. {record['journal']}. {record['year']};{location}. doi:{record['doi']}."
        record['bibtex_file'] = f'assets/citations/{key}.bib'
        fields = dict(title='{' + record['title'] + '}', author=' and '.join(a['family'] + ', ' + a['given'] for a in authors),
                      journal=record['journal'], year=record['year'], volume=record['volume'],
                      pages=record['article_number'], doi=record['doi'], url=record['url'])
        if record.get('issue'):
            fields['number'] = record['issue']
        bib = '@article{' + record['bibtex_key'] + ',\n' + ',\n'.join('  ' + k + ' = {' + str(v) + '}' for k, v in fields.items()) + '\n}\n'
        (ROOT / record['bibtex_file']).write_text(bib, encoding='utf-8')
        bibs.append(bib)
        author_line = ', '.join(a['given'] + ' ' + a['family'] for a in authors[:3]) + ', et al.'
        cards.append(f'''<article class="publication-card" data-publication="{key}">
  <button type="button" class="publication-preview" data-paper-preview="{record['first_page']['image']}" aria-label="View first page: {esc(record['title'])}">
    <img src="{record['first_page']['thumbnail']}" alt="First page of {esc(record['title'])}" width="{small.width}" height="{small.height}" loading="lazy" decoding="async">
    <span class="publication-preview-hint"><span data-i18n="pub.preview">View first page</span> <span aria-hidden="true">⤢</span></span>
  </button>
  <div class="publication-copy">
    <div class="publication-meta"><span>{esc(record['journal'])}</span><time datetime="{record['publication_date']}">{record['year']}</time></div>
    <p class="publication-topic" data-i18n="pub.topic.{key}">{esc(record['topic']['en'])}</p>
    <h3><a href="{record['url']}" target="_blank" rel="noopener noreferrer">{esc(record['title'])}</a></h3>
    <p class="publication-authors">{esc(author_line)}</p>
    <p class="publication-location">{esc(record['journal'])} {esc(location)} ({record['year']})</p>
    <a class="publication-doi" href="{record['url']}" target="_blank" rel="noopener noreferrer">doi:{record['doi']}</a>
    <div class="publication-actions"><a href="{record['url']}" target="_blank" rel="noopener noreferrer"><span data-i18n="pub.read">Read article</span> ↗</a><button type="button" data-copy-publication="{key}" data-i18n="pub.copy">Copy citation</button><a href="{record['bibtex_file']}" download>BibTeX ↓</a></div>
    <details class="publication-citation"><summary data-i18n="pub.citation">Full citation</summary><p id="citation-{key}">{esc(record['citation'])}</p></details>
    <p class="publication-feedback" data-copy-feedback="{key}" role="status" aria-live="polite"></p>
  </div>
</article>''')
    records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (cite_dir / 'pacthub-related-papers.bib').write_text('\n'.join(bibs), encoding='utf-8')
    section = '''<section class="container section-block publications-section" id="publication" aria-labelledby="publication-title">
  <div class="section-heading horizontal"><div><p class="eyebrow" data-i18n="ui.091">06 / PUBLICATIONS</p><h2 id="publication-title" data-i18n="pub.title">The research behind the data.</h2></div><p data-i18n="pub.intro">Three papers on panoramic imaging, whole-body anatomy and longitudinal biological applications.</p></div>
  <div class="publications-grid">''' + '\n'.join(cards) + '''</div>
  <div class="publications-foot"><p><span data-i18n="pub.credit">Article first pages © their respective authors.</span> <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a></p><a class="text-link" href="assets/citations/pacthub-related-papers.bib" download><span data-i18n="pub.all">Download all citations</span> ↓</a></div>
</section>'''
    index = ROOT / 'index.html'
    content = index.read_text(encoding='utf-8')
    start = content.rfind('<section', 0, content.index('id="publication"'))
    end = content.index('</section>', start) + len('</section>')
    index.write_text(content[:start] + section + content[end:], encoding='utf-8')
    print('Built three first-page previews, verified DOI text, full citations and BibTeX.')

if __name__ == '__main__':
    main()
