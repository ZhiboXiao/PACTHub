'use strict';
(() => {
  const section = document.getElementById('cite');
  if (!section) return;
  const t = key => window.PACTI18N.t(key);
  const safeLink = value => {
    try {
      const url = new URL(value, location.href);
      return typeof value === 'string' && value.trim() && ['http:', 'https:'].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  };
  function render(records) {
    if (!records) return;
    const dataset = records.dataset;
    if (dataset?.citation) document.getElementById('citation-dataset').textContent = dataset.citation;
    const paper = records.paper;
    const actions = document.getElementById('dataset-paper-actions');
    const title = document.getElementById('dataset-paper-title');
    let citation = document.getElementById('citation-dataset-paper');
    const status = document.getElementById('dataset-paper-status');
    const pending = document.getElementById('dataset-paper-pending');
    const published = paper?.status === 'published' && paper.title && paper.citation && safeLink(paper.url);
    document.getElementById('dataset-paper').classList.toggle('paper-forthcoming', !published);
    actions.replaceChildren(); actions.hidden = !published; pending.hidden = !!published;
    if (!published) {
      title.dataset.i18n = 'cite.paperTitle'; title.textContent = t('cite.paperTitle');
      if (citation) citation.hidden = true;
      status.dataset.i18n = 'cite.forthcoming'; status.textContent = t('cite.forthcoming');
      return;
    }
    if (!citation) {
      citation = document.createElement('p');
      citation.id = 'citation-dataset-paper'; citation.className = 'dataset-citation-text';
      actions.before(citation);
    }
    citation.hidden = false;
    [title, citation, status].forEach(el => el.removeAttribute('data-i18n'));
    title.textContent = paper.title; citation.textContent = paper.citation; status.textContent = 'arXiv';
    const link = document.createElement('a');
    link.href = safeLink(paper.url); link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.textContent = t('cite.readPaper') + ' ↗'; actions.append(link);
    const copy = document.createElement('button'); copy.type = 'button'; copy.dataset.copyDataset = 'paper';
    copy.textContent = t('cite.copy'); actions.append(copy);
    if (safeLink(paper.bibtex_file)) {
      const bib = document.createElement('a'); bib.href = safeLink(paper.bibtex_file);
      bib.download = ''; bib.textContent = 'BibTeX ↓'; actions.append(bib);
    }
  }
  section.addEventListener('click', async event => {
    const button = event.target.closest('[data-copy-dataset]');
    if (!button) return;
    const paper = button.dataset.copyDataset === 'paper';
    const citation = document.getElementById(paper ? 'citation-dataset-paper' : 'citation-dataset');
    const feedback = document.getElementById(paper ? 'paper-copy-feedback' : 'dataset-copy-feedback');
    try {
      await navigator.clipboard.writeText(citation.textContent.trim());
      feedback.dataset.message = 'pub.copied';
    } catch {
      const range = document.createRange(); range.selectNodeContents(citation);
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
      feedback.dataset.message = 'pub.selected';
    }
    feedback.textContent = t(feedback.dataset.message);
  });
  document.addEventListener('pact:languagechange', () => {
    section.querySelectorAll('[data-message]').forEach(el => { el.textContent = t(el.dataset.message); });
  });
  window.PACTCitation = { render };
})();
