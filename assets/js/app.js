/* Static website index. No remote API, tracking, framework or build dependency. */
'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const state = { loaded: false, samples: [], category: 'all', split: 'all', query: '', current: null, citation: '', citationStatus: 'citation.unavailable', config: null, loadError: null, failedPreviews: new Set() };
  const { t, localize } = window.PACTI18N;
  const label = (key) => t(key);
  const bind = (el, key, params = {}) => {
    el.dataset.i18n = key; el.setAttribute('data-i18n-params', JSON.stringify(params)); el.textContent = t(key, params);
  };
  const contentText = (value) => localize(value);
  const localizedString = (value) => typeof value === 'string' || (value && typeof value === 'object' && !Array.isArray(value) && ['zh', 'en'].some((key) => typeof value[key] === 'string' && value[key].trim()));
  const node = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  // JSON is editable content, not executable markup. Reject unsafe URL schemes.
  function safeUrl(value, image = false) {
    if (typeof value !== 'string' || !value.trim() || value.startsWith('//')) return null;
    if (image && /^data:image\/(?:png|jpeg|webp|svg\+xml);base64,[a-z0-9+/=]+$/i.test(value)) return value;
    try {
      const u = new URL(value, document.baseURI);
      return ['https:', 'http:'].includes(u.protocol) ? u.href : null;
    } catch { return null; }
  }
  // Only the background-video loader accepts video data URLs from offline builds.
  function safeVideoUrl(value) {
    if (typeof value !== 'string') return null;
    const clean = value.trim();
    if (/^data:video\/(?:mp4|webm);base64,[a-z0-9+/=]+$/i.test(clean)) return clean;
    if (!clean || clean.startsWith('//') || clean.startsWith('\\')) return null;
    return safeUrl(clean);
  }
  function setupHeroMedia(settings) {
    const config = settings && typeof settings === 'object' ? settings : {};
    const hero = $('top'), video = $('hero-video'), poster = $('hero-poster');
    const toggle = $('hero-video-toggle'), status = $('hero-media-status');
    if (!video || !toggle) return;
    const sources = [
      { src: safeVideoUrl(config.webm_url), type: 'video/webm' },
      { src: safeVideoUrl(config.mp4_url), type: 'video/mp4' },
    ].filter((source) => source.src);
    const posterURL = safeUrl(config.poster_url, true);
    if (posterURL) { poster.src = posterURL; video.poster = posterURL; }
    if (typeof config.object_position === 'string' && /^(?:\d{1,3}(?:\.\d+)?%|center|left|right|top|bottom)(?: (?:\d{1,3}(?:\.\d+)?%|center|left|right|top|bottom))?$/.test(config.object_position)) {
      poster.style.objectPosition = config.object_position; video.style.objectPosition = config.object_position;
    }
    if (contentText(config.media_label).trim()) $('hero-media-label').textContent = contentText(config.media_label);
    if (!sources.length) { bind(status, 'video.static'); return; }
    // No src in the initial HTML: reduced-motion and data-saving preferences
    // are checked before any video download or automatic playback is requested.
    const motion = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    let wanted = !motion?.matches && !navigator.connection?.saveData;
    let inView = true, attached = false, failed = false, request = 0;
    const failedSources = new Set();
    const shouldPlay = () => wanted && !document.hidden && inView;
    video.muted = true; video.defaultMuted = true; video.loop = true; video.playsInline = true;
    video.autoplay = false; // The controller below owns autoplay and pause intent.
    toggle.hidden = false;
    function showControl(playing) {
      $('hero-video-icon').textContent = playing ? 'Ⅱ' : '▶';
      bind($('hero-video-button-label'), playing ? 'video.pause' : (failed ? 'video.retry' : 'video.play'));
      const key = playing ? 'video.pauseAria' : (failed ? 'video.retryAria' : 'video.playAria');
      toggle.setAttribute('data-i18n-aria-label', key); toggle.setAttribute('aria-label', t(key));
    }
    function attach() {
      if (attached) return;
      video.replaceChildren(...sources.map((source) => {
        const el = node('source'); el.src = source.src; el.type = source.type;
        // Source failures do not bubble to video. Some browsers also leave the
        // play promise pending when every source fails, so handle exhaustion.
        el.addEventListener('error', () => {
          failedSources.add(el);
          if (failedSources.size === sources.length) showMediaError();
        });
        return el;
      }));
      attached = true; video.load();
    }
    function sync() {
      const current = ++request;
      if (!shouldPlay()) { video.pause(); showControl(false); return; }
      if (failed) { failedSources.clear(); failed = false; video.load(); }
      attach();
      // Repeated visibility/observer notifications need not trigger a new
      // playing event when media is already running. Preserve its live status.
      if (!video.paused && hero.dataset.videoReady === 'true') { showControl(true); return; }
      bind(status, 'video.loading');
      // Make a second click cancel a pending play request as well as playing media.
      showControl(true);
      try {
        const started = video.play();
        if (started && typeof started.then === 'function') started.then(() => {
          if (!shouldPlay()) { video.pause(); return; }
          if (current !== request) return;
          // Only the playing event reveals the video. A resolved promise alone
          // does not prove that a decoded frame is available.
        }).catch(() => {
          if (current !== request) return;
          wanted = false; video.pause(); showControl(false);
          bind(status, 'video.blocked');
        });
      } catch {
        if (current !== request) return;
        wanted = false; video.pause(); showControl(false);
        bind(status, 'video.notStarted');
      }
    }
    toggle.addEventListener('click', () => {
      wanted = !wanted;
      if (!wanted) bind(status, 'video.paused');
      sync();
    });
    video.addEventListener('playing', () => {
      if (!shouldPlay()) { video.pause(); return; }
      hero.dataset.videoReady = 'true'; failed = false; showControl(true); bind(status, 'video.playing');
    });
    video.addEventListener('pause', () => showControl(false));
    function showMediaError() {
      ++request; wanted = false; failed = true; hero.dataset.videoReady = 'false'; video.pause(); showControl(false);
      bind(status, 'video.failed');
    }
    video.addEventListener('error', showMediaError);
    document.addEventListener('visibilitychange', sync);
    if (typeof window.IntersectionObserver === 'function') {
      const observer = new window.IntersectionObserver((entries) => { inView = entries[0]?.isIntersecting !== false; sync(); }, { threshold: 0 });
      observer.observe(hero);
    }
    const onMotionChange = () => {
      if (motion.matches) { wanted = false; bind(status, 'video.motion'); }
      sync();
    };
    if (motion?.addEventListener) motion.addEventListener('change', onMotionChange);
    else if (motion?.addListener) motion.addListener(onMotionChange);
    if (!wanted) bind(status, 'video.preference');
    sync();
  }

  function valueText(value, suffix = '') {
    if (value === null || value === undefined || value === '') return t('missing');
    if (typeof value === 'object' && !Array.isArray(value) && !contentText(value)) return t('missing');
    return (Array.isArray(value) ? value.join(' × ') : (typeof value === 'object' ? contentText(value) : String(value))) + suffix;
  }
  function samplePreview(sample, original = false) {
    const media = node('div', 'sample-image' + (original ? ' original-view' : ''));
    const preview = safeUrl(sample.preview, true);
    if (!preview || state.failedPreviews.has(sample.preview)) {
      media.append(node('span', 'image-caption', t(preview ? 'sample.previewError' : 'sample.noPreview')));
      return media;
    }
    const img = node('img'); img.src = preview;
    img.alt = sample.is_demo ? t('sample.demoAlt', { title: contentText(sample.title) }) : t('sample.alt', { title: contentText(sample.title) });
    img.loading = 'lazy';
    img.addEventListener('error', () => { state.failedPreviews.add(sample.preview); media.replaceChildren(node('span', 'image-caption', t('sample.previewError'))); }, { once: true });
    const layout = sample.preview_layout;
    // Endpoint-preserving display gamma: no source pixels are rewritten.
    const gamma = layout?.display_gamma;
    if (!original && [0.8, 0.95, 0.97].includes(gamma)) img.style.filter = `url("#sample-gamma-${Math.round(gamma * 100)}")`;
    if (layout && !original) {
      const [x, y, width, height] = layout.crop;
      const rotated = layout.rotation_deg === 90;
      const rw = rotated ? layout.source_height : layout.source_width;
      const rh = rotated ? layout.source_width : layout.source_height;
      const scale = Math.min(2 / width, 1 / height);
      const window = node('div', 'sample-crop-window');
      window.style.width = `${width * scale * 50}%`;
      window.style.height = `${height * scale * 100}%`;
      img.style.width = `${layout.source_width / width * 100}%`;
      img.style.height = `${layout.source_height / height * 100}%`;
      img.style.left = `${(rw / 2 - x) / width * 100}%`;
      img.style.top = `${(rh / 2 - y) / height * 100}%`;
      img.style.transform = `translate(-50%, -50%) rotate(${layout.rotation_deg}deg)`;
      img.width = layout.source_width; img.height = layout.source_height;
      window.append(img); media.append(window);
    } else { media.append(img); }
    return media;
  }
  function sampleCard(sample) {
    const card = node('article', 'sample-card');
    const media = samplePreview(sample);
    const preview = safeUrl(sample.preview, true);
    if (sample.is_demo) media.append(node('span', 'demo-tag', t('sample.demo')));
    const content = node('div', 'sample-content');
    const top = node('div', 'sample-topline');
    top.append(node('span', '', sample.id), node('span', 'split-tag', label(sample.split)));
    const specs = node('div', 'sample-specs');
    specs.append(node('span', '', sample.dimensions ? valueText(sample.dimensions) + ' ' + t('sample.voxels') : t(sample.preview_layout?.display_gamma < 1 ? 'sample.displayAdjusted' : 'sample.imageProvided')));
    const footer = node('div', 'sample-footer');
    footer.append(node('span', 'sample-category', label(sample.category)));
    const detail = node('button', 'detail-button', t('sample.detail')); detail.type = 'button';
    detail.setAttribute('aria-label', t('sample.detailAria', { id: sample.id, title: contentText(sample.title) }));
    detail.append(node('span', '', '↗')); detail.addEventListener('click', () => openDetail(sample));
    footer.append(detail); content.append(top, node('h3', '', contentText(sample.title)), specs, footer); card.append(media, content); return card;
  }
  function searchTexts(value) { return typeof value === 'string' ? [value] : [value?.zh || '', value?.en || '']; }
  function render() {
    if (!state.loaded) return; // Preserve loading/failure message and Retry during filter input.
    const terms = state.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const matches = state.samples.filter((s) => {
      const haystack = [s.id, ...searchTexts(s.title), ...searchTexts(s.description), ...(s.tags || [])].join(' ').toLocaleLowerCase();
      return (state.category === 'all' || s.category === state.category) && (state.split === 'all' || s.split === state.split) && terms.every((term) => haystack.includes(term));
    });
    $('sample-grid').replaceChildren(...matches.map(sampleCard));
    bind($('results-count'), 'sample.count', { count: matches.length, total: state.samples.length });
    $('empty-state').hidden = matches.length > 0;
    $('load-error').hidden = true;
  }
  function addPair(grid, key, value) {
    const row = node('div'); row.append(node('dt', '', key), node('dd', '', value)); grid.append(row);
  }
  function openDetail(sample, preserveOpen = false) {
    state.current = sample;
    const box = $('detail-content');
    const heading = node('div', 'detail-heading');
    if (sample.is_demo) heading.append(node('span', 'demo-tag', t('sample.demoMetadata')));
    const headingTitle = node('h2', '', `${sample.id} / ${contentText(sample.title)}`); headingTitle.id = 'detail-title'; heading.append(headingTitle);
    const grid = node('dl', 'detail-grid');
    addPair(grid, t('sample.category'), label(sample.category));
    addPair(grid, t('sample.split'), label(sample.split));
    addPair(grid, t('sample.dimensions'), valueText(sample.dimensions));
    addPair(grid, t('sample.axes'), valueText(sample.axis_order));
    addPair(grid, t('sample.spacing'), valueText(sample.spacing_mm));
    addPair(grid, t('sample.wavelength'), valueText(sample.wavelength_nm));
    addPair(grid, t('sample.intensity'), valueText(sample.intensity_unit));
    addPair(grid, t('sample.version'), valueText(sample.data_version));
    const note = node('p', 'detail-note', contentText(sample.description));
    const provenance = node('div', 'detail-provenance');
    provenance.append(node('h3', '', t('sample.provenance')));
    for (const [key, label] of Object.entries({ source_id: t('sample.source'), acquisition: t('sample.acquisition'), reconstruction: t('sample.reconstruction'), standardization_reference: t('sample.standardization') })) provenance.append(node('p', '', `${label}: ${valueText(sample.provenance?.[key])}`));
    const files = node('div', 'detail-provenance'); files.append(node('h3', '', t('sample.files')));
    const validFiles = (Array.isArray(sample.files) ? sample.files : []).filter((file) => file && typeof file === 'object' && safeUrl(file.url));
    if (!validFiles.length) files.append(node('p', '', t('sample.noFiles')));
    for (const file of validFiles) {
      const line = node('p'); const a = node('a', 'text-link', file.name); a.href = safeUrl(file.url); a.rel = 'noopener noreferrer';
      line.append(a); files.append(line, node('p', '', `SHA-256: ${valueText(file.sha256)}`));
    }
    const figure = node('figure', 'detail-preview');
    if (!preserveOpen) state.currentOriginal = false;
    let original = Boolean(state.currentOriginal);
    const preview = samplePreview(sample, original);
    const toggle = node('button', 'text-link preview-toggle', t(original ? 'sample.showFramed' : 'sample.showOriginal'));
    toggle.type = 'button'; toggle.setAttribute('aria-pressed', String(original));
    toggle.addEventListener('click', () => {
      original = !original; state.currentOriginal = original;
      figure.replaceChildren(samplePreview(sample, original), toggle);
      toggle.textContent = t(original ? 'sample.showFramed' : 'sample.showOriginal');
      toggle.setAttribute('aria-pressed', String(original)); toggle.focus();
    });
    figure.append(preview, toggle);
    box.replaceChildren(heading, figure, grid, note, provenance, files);
    $('download-sample').textContent = sample.is_demo ? t('sample.exportDemo') : t('sample.export');
    document.querySelector('.dialog-footer > span').textContent = validFiles.length ? t('sample.fileCount', { count: validFiles.length }) : t('sample.metadataOnly');
    if (!preserveOpen) {
      $('sample-dialog').showModal(); document.body.classList.add('modal-open');
      $('sample-dialog').scrollTop = 0; $('close-dialog').focus();
    }
  }
  function closeDetail() { $('sample-dialog').close(); }
  $('close-dialog').addEventListener('click', closeDetail);
  $('sample-dialog').addEventListener('close', () => document.body.classList.remove('modal-open'));
  $('sample-dialog').addEventListener('click', (event) => {
    if (event.target !== $('sample-dialog')) return;
    const rect = event.target.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeDetail();
  });
  $('download-sample').addEventListener('click', () => {
    if (!state.current) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(state.current, null, 2) + '\n'], { type: 'application/json' }));
    const link = node('a'); link.href = url; link.download = `${state.current.id}.json`; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  function setCategory(value) {
    state.category = value;
    document.querySelectorAll('[data-category]').forEach((b) => { const active = b.dataset.category === value; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active)); });
  }
  $('category-filters').addEventListener('click', (event) => {
    const button = event.target.closest('[data-category]');
    if (button) { setCategory(button.dataset.category); render(); }
  });
  function renderCategories() {
    const categories = ['all', ...new Set(state.samples.map((s) => s.category))];
    if (!categories.includes(state.category)) state.category = 'all';
    $('category-filters').replaceChildren(...categories.map((value) => {
      const b = node('button', 'filter-chip', label(value));
      b.type = 'button'; b.dataset.category = value; return b;
    }));
    setCategory(state.category);
  }
  $('sample-search').addEventListener('input', (e) => { state.query = e.target.value; render(); });
  $('split-filter').addEventListener('change', (e) => { state.split = e.target.value; render(); });
  $('clear-filters').addEventListener('click', () => { state.query = ''; state.split = 'all'; setCategory('all'); $('sample-search').value = ''; $('split-filter').value = 'all'; render(); $('sample-search').focus(); });
  const menu = $('menu-toggle');
  function setMenu(open) { menu.setAttribute('aria-expanded', String(open)); $('primary-nav').classList.toggle('open', open); }
  menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
  $('primary-nav').querySelectorAll('a').forEach((a) => a.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') { setMenu(false); menu.focus(); } });
  function resource(label, url) {
    const valid = safeUrl(url);
    const el = node(valid ? 'a' : 'button', 'button button-secondary', valid ? label + ' ↗' : t('resource.pending', { label }));
    if (valid) { el.href = valid; el.rel = 'noopener noreferrer'; } else { el.type = 'button'; el.disabled = true; }
    return el;
  }
  function applyConfig(config, initialize = false) {
    if (!config || typeof config !== 'object' || Array.isArray(config)) throw new Error('CONFIG_INVALID');
    state.config = config;
    if (contentText(config.site_title).trim()) {
      document.querySelectorAll('[data-site-title]').forEach((el) => { el.textContent = contentText(config.site_title); });
      document.title = contentText(config.site_title) + ' · ' + t('meta.suffix');
    }
    if (initialize) setupHeroMedia(config.hero);
    if (contentText(config.hero?.media_label).trim()) $('hero-media-label').textContent = contentText(config.hero.media_label);
    // The global preview banner and sample-level indicators are independent.
    $('demo-banner').hidden = config.demo_mode === false;
    const fill = (id, value) => { const text = contentText(value); if (text.trim()) $(id).textContent = text; };
    fill('hero-description', config.description);
    fill('overview-summary', config.overview_summary);
    fill('algorithm-name', config.algorithm?.name);
    fill('algorithm-summary', config.algorithm?.summary);
    fill('algorithm-status', config.algorithm?.status);
    $('algorithm-resources').replaceChildren(resource(t('resource.repository'), config.algorithm?.repository_url), resource(t('resource.weights'), config.algorithm?.weights_url));
    if (Array.isArray(config.downloads)) {
      const cards = config.downloads.map((item) => {
        const card = node('article', 'download-card'); const enabled = Boolean(safeUrl(item.url));
        card.append(node('span', 'status-pill', enabled ? t('resource.available') : t('resource.unreleased')), node('h3', '', contentText(item.title)), node('p', '', contentText(item.description)));
        const meta = node('div', 'download-meta');
        if (item.version) meta.append(node('span', '', t('resource.version', { version: item.version })));
        if (item.size_label) meta.append(node('span', '', contentText(item.size_label)));
        if (meta.childElementCount) card.append(meta);
        if (item.sha256) { const checksum = node('p', '', `SHA-256: ${item.sha256}`); checksum.style.overflowWrap = 'anywhere'; card.append(checksum); }
        const action = resource(t('resource.download'), item.url);
        if (!enabled) action.textContent = t('resource.preparing');
        card.append(action); return card;
      });
      $('download-grid').replaceChildren(...cards);
    }
    fill('paper-title', config.paper?.title);
    fill('paper-summary', config.paper?.summary);
    const paperLinks = [resource(t('resource.paper'), config.paper?.url)];
    if (typeof config.doi === 'string' && /^10\.\d{4,9}\/\S+$/.test(config.doi)) paperLinks.push(resource('DOI', `https://doi.org/${config.doi}`));
    $('paper-resources').replaceChildren(...paperLinks);
    if (typeof config.citation === 'string' && config.citation.trim()) {
      state.citation = config.citation; $('citation-note').textContent = config.citation;
      if (initialize) state.citationStatus = 'citation.ready'; bind($('citation-status'), state.citationStatus); $('copy-citation').disabled = false;
    }
    $('license-status').textContent = config.license ? t('license.named', { license: contentText(config.license) }) : t('license.pending');
    if (Array.isArray(config.team?.members) && config.team.members.length) {
      $('team-members').replaceChildren(...config.team.members.filter((member) => member && contentText(member.name).trim()).map((member) => {
        const box = node('div', 'team-member'); const heading = node('h3'); const url = safeUrl(member.url);
        if (url) { const link = node('a', '', contentText(member.name)); link.href = url; link.rel = 'noopener noreferrer'; heading.append(link); }
        else heading.textContent = contentText(member.name);
        box.append(heading, node('p', '', [member.affiliation, member.role].map(contentText).filter(Boolean).join(' · '))); return box;
      }));
    }
    fill('contribution-summary', config.team?.contribution);
    $('contribution-resources').replaceChildren(resource(t('resource.contribute'), config.team?.contribution_url));
  }
  $('copy-citation').addEventListener('click', async () => {
    if (!state.citation) return;
    try {
      await navigator.clipboard.writeText(state.citation);
      state.citationStatus = 'citation.copied'; bind($('citation-status'), state.citationStatus);
    } catch {
      const range = document.createRange(); range.selectNodeContents($('citation-note'));
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
      state.citationStatus = 'citation.selected'; bind($('citation-status'), state.citationStatus);
    }
  });
  async function readJSON(path, embeddedId) {
    const embedded = $(embeddedId);
    if (embedded) return JSON.parse(embedded.textContent);
    const response = await fetch(path, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  async function loadSamples() {
    state.loaded = false;
    $('load-error').hidden = true; $('empty-state').hidden = true; bind($('results-count'), 'load.loading'); state.loadError = null;
    try {
      const samples = await readJSON('data/samples.json', 'embedded-samples');
      if (!Array.isArray(samples) || !samples.every((s) => s && typeof s.id === 'string' && localizedString(s.title) && typeof s.category === 'string' && Array.isArray(s.tags))) throw new Error('INDEX_INVALID');
      state.samples = samples; state.loaded = true; renderCategories(); render();
    } catch (error) {
      state.loaded = false; state.samples = []; $('sample-grid').replaceChildren(); bind($('results-count'), 'load.failed'); $('load-error').hidden = false;
      state.loadError = error.message === 'INDEX_INVALID' ? 'load.invalid' : (/^HTTP \d{3}$/.test(error.message) ? error.message : 'load.general');
      renderLoadError();
    }
  }
  $('retry-load').addEventListener('click', loadSamples);
  readJSON('data/site-config.json', 'embedded-config').then((config) => applyConfig(config, true)).catch(() => {
    const warning = node('p', 'detail-note'); bind(warning, 'config.warning'); $('release').append(warning);
  });
  function renderLoadError() {
    if (!state.loadError) return;
    bind($('error-detail'), 'load.detail', { reason: state.loadError.startsWith('HTTP ') ? state.loadError : t(state.loadError) });
  }
  document.addEventListener('pact:languagechange', () => {
    if (state.config) applyConfig(state.config);
    if (state.loaded) { renderCategories(); render(); }
    renderLoadError();
    if ($('sample-dialog').open && state.current) openDetail(state.current, true);
  });
  loadSamples();
})();
