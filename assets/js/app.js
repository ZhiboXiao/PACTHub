/* Static website index. No remote API, tracking, framework or build dependency. */
'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const state = { loaded: false, samples: [], category: 'all', mode: 'all', view: 'volume', query: '', current: null, config: null, loadError: null, failedPreviews: new Set() };
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
    const baseConfig = settings && typeof settings === 'object' ? settings : {};
    const requestedVariant = new URLSearchParams(window.location.search).get('hero');
    const variantName = baseConfig.variants?.[requestedVariant] ? requestedVariant : (baseConfig.default_variant || 'compact');
    const config = { ...baseConfig, ...baseConfig.variants?.[variantName] };
    const hero = $('top'), video = $('hero-video'), poster = $('hero-poster');
    if (hero) hero.dataset.heroVariant = variantName;
    const toggle = $('hero-video-toggle'), status = $('hero-media-status');
    if (!video || !toggle) return;
    const heroViewport = window.matchMedia?.('(max-width: 900px)');
    let compactHero = heroViewport?.matches;
    const chooseSources = () => [
      { src: safeVideoUrl(compactHero && config.mobile_webm_url || config.webm_url), type: 'video/webm' },
      { src: safeVideoUrl(compactHero && config.mobile_mp4_url || config.mp4_url), type: 'video/mp4' },
    ].filter((source) => source.src);
    let sources = chooseSources();
    const updatePoster = () => {
      const posterURL = safeUrl(compactHero && config.mobile_poster_url || config.poster_url, true);
      if (posterURL) { poster.src = posterURL; video.poster = posterURL; }
    };
    updatePoster();
    if (typeof config.object_position === 'string' && /^(?:\d{1,3}(?:\.\d+)?%|center|left|right|top|bottom)(?: (?:\d{1,3}(?:\.\d+)?%|center|left|right|top|bottom))?$/.test(config.object_position)) {
      poster.style.objectPosition = config.object_position; video.style.objectPosition = config.object_position;
    }
    if (!sources.length) { bind(status, 'video.static'); return; }
    // No src in the initial HTML: reduced-motion and data-saving preferences
    // are checked before any video download or automatic playback is requested.
    const motion = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    let wanted = !motion?.matches && !navigator.connection?.saveData;
    let inView = true, attached = false, failed = false, request = 0;
    const failedSources = new Set();
    const shouldPlay = () => wanted && !document.hidden && inView;
    const loopStart = Number.isFinite(config.loop_start_seconds) && config.loop_start_seconds > 0 ? config.loop_start_seconds : 0;
    video.muted = true; video.defaultMuted = true; video.loop = !loopStart; video.playsInline = true;
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
    video.addEventListener('ended', () => {
      if (!loopStart) return;
      // Play the scientific 3D introduction once; subsequent loops retain
      // the original physiological motion and the crossfaded loop boundary.
      video.currentTime = loopStart < video.duration ? loopStart : 0;
      sync();
    });
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
    heroViewport?.addEventListener('change', (event) => {
      const resumeTime = video.currentTime;
      compactHero = event.matches;
      sources = chooseSources(); updatePoster();
      video.pause(); attached = false; failed = false; failedSources.clear();
      hero.dataset.videoReady = 'false';
      video.addEventListener('loadedmetadata', () => {
        if (Number.isFinite(video.duration)) video.currentTime = Math.min(resumeTime, Math.max(0, video.duration - .05));
      }, { once: true });
      sync();
    });
    if (!wanted) bind(status, 'video.preference');
    sync();
  }

  function valueText(value, suffix = '') {
    if (value === null || value === undefined || value === '') return t('missing');
    if (typeof value === 'object' && !Array.isArray(value) && !contentText(value)) return t('missing');
    return (Array.isArray(value) ? value.map(v => typeof v === 'number' && !Number.isInteger(v) ? Number(v.toPrecision(5)) : v).join(' × ') : (typeof value === 'object' ? contentText(value) : String(value))) + suffix;
  }
  function updateScale(media) {
    const img = media.querySelector('img'), scale = media.querySelector('.sample-scale');
    if (!img?.naturalWidth || !scale || !media.clientHeight) return;
    const fit = Math.min(media.clientWidth / img.naturalWidth, media.clientHeight / img.naturalHeight);
    scale.querySelector('i').style.width = `${Number(scale.dataset.lengthPixels) * fit}px`;
    scale.hidden = false;
  }
  const scaleObserver = new ResizeObserver(entries => entries.forEach(({ target }) => updateScale(target)));
  function releaseScales(container) {
    container.querySelectorAll('.sample-image').forEach(media => scaleObserver.unobserve(media));
  }
  function samplePreview(sample, view = state.view) {
    const media = node('div', 'sample-image');
    const path = sample.views?.[view] || sample.preview;
    const preview = safeUrl(path, true);
    if (!preview || state.failedPreviews.has(path)) {
      media.append(node('span', 'image-caption', t(preview ? 'sample.previewError' : 'sample.noPreview'))); return media;
    }
    const img = node('img');
    const imageURL = new URL(preview);
    if (sample.display?.asset_revision && ['http:', 'https:'].includes(imageURL.protocol)) imageURL.searchParams.set('v', sample.display.asset_revision);
    img.src = imageURL.href; img.alt = contentText(sample.title) + ' / ' + t('view.' + view); img.loading = 'lazy';
    img.addEventListener('error', () => { state.failedPreviews.add(path); scaleObserver.unobserve(media); media.replaceChildren(node('span', 'image-caption', t('sample.previewError'))); }, { once: true });
    media.append(img);
    const calibration = sample.display?.scale_bars?.[view];
    if (calibration) {
      const scale = node('span', 'sample-scale'); scale.hidden = true;
      scale.dataset.lengthPixels = calibration.length_pixels;
      scale.append(node('span', '', `${calibration.length_mm} mm`), node('i'));
      media.append(scale);
      img.addEventListener('load', () => updateScale(media));
      scaleObserver.observe(media);
    }
    return media;
  }
  function acquisitionLabel(sample) {
    const ids = [...new Set((sample.acquisition_groups || []).flatMap(group => group.acquisitions.map(entry => entry.id)))].sort();
    return ids.length > 1 ? `${ids[0]} - ${ids[ids.length - 1]}` : ids[0] || sample.acquisition_name || sample.acquisition_id;
  }
  function sampleCard(sample) {
    const card = node('article', 'sample-card');
    if (sample.display?.compact_preview) card.classList.add('compact-preview');
    const media = samplePreview(sample);
    const preview = safeUrl(sample.preview, true);
    const content = node('div', 'sample-content');
    const top = node('div', 'sample-topline');
    top.append(node('span', '', acquisitionLabel(sample)), node('span', 'sample-mode', sample.acquisition_summary ? contentText(sample.acquisition_summary) : label(sample.mode)));
    const footer = node('div', 'sample-footer');
    footer.append(node('h3', '', contentText(sample.title)));
    const detail = node('button', 'detail-button', t('sample.detail')); detail.type = 'button';
    detail.setAttribute('aria-label', t('sample.detailAria', { id: sample.id, title: contentText(sample.title) }));
    detail.append(node('span', '', '↗')); detail.addEventListener('click', () => openDetail(sample));
    footer.append(detail); content.append(top, footer); card.append(media, content); return card;
  }
  function searchTexts(value) { return typeof value === 'string' ? [value] : [value?.zh || '', value?.en || '']; }
  function render() {
    if (!state.loaded) return; // Preserve loading/failure message and Retry during filter input.
    const terms = state.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const matches = state.samples.filter((s) => {
      const acquisitionTerms = (s.acquisition_groups || []).flatMap(group => group.acquisitions.flatMap(entry => [entry.id, entry.file]));
      const haystack = [s.id, s.acquisition_id, s.acquisition_name || '', ...acquisitionTerms, ...searchTexts(s.acquisition_summary), ...searchTexts(s.title), ...searchTexts(s.description), ...(s.tags || [])].join(' ').toLocaleLowerCase();
      return (state.category === 'all' || s.category === state.category) && (state.mode === 'all' || s.mode === state.mode) && terms.every((term) => haystack.includes(term));
    });
    releaseScales($('sample-grid'));
    $('sample-grid').replaceChildren(...matches.map(sampleCard));
    bind($('results-count'), 'sample.count', { count: matches.length, total: state.samples.length });
    $('empty-state').hidden = matches.length > 0;
    $('load-error').hidden = true;
  }
  function addPair(grid, key, value) {
    const row = node('div'); row.append(node('dt', '', key), node('dd', '', value)); grid.append(row);
  }
  function openZoom(sample, initialView) {
    const dialog = node('dialog', 'image-zoom-dialog');
    dialog.setAttribute('aria-labelledby', 'zoom-title');
    const header = node('header', 'zoom-header');
    const title = node('h2', '', contentText(sample.title)); title.id = 'zoom-title';
    const close = node('button', 'zoom-close', '×'); close.type = 'button'; close.setAttribute('aria-label', t('zoom.close'));
    close.addEventListener('click', () => dialog.close()); header.append(title, close);
    const toolbar = node('div', 'zoom-toolbar'), views = node('div', 'view-switch');
    views.setAttribute('role', 'group'); views.setAttribute('aria-label', t('sample.viewNote'));
    const tools = node('div', 'zoom-tools'), minus = node('button', '', '−'), plus = node('button', '', '+');
    const reset = node('button', '', t('zoom.reset')), output = node('output', 'zoom-level', '100%');
    minus.setAttribute('aria-label', t('zoom.out')); plus.setAttribute('aria-label', t('zoom.in'));
    for (const b of [minus, plus, reset]) b.type = 'button';
    tools.append(minus, output, plus, reset); toolbar.append(views, tools);
    const viewport = node('div', 'zoom-viewport'); viewport.tabIndex = 0; viewport.setAttribute('aria-label', t('zoom.hint'));
    const hint = node('p', 'zoom-hint', t('zoom.hint'));
    dialog.append(header, toolbar, viewport, hint); document.body.append(dialog);
    let zoom = 1, x = 0, y = 0, drag = null, media, scale, calibration;
    function draw() {
      const maxX = viewport.clientWidth * (zoom - 1) / 2, maxY = viewport.clientHeight * (zoom - 1) / 2;
      x = Math.max(-maxX, Math.min(maxX, x)); y = Math.max(-maxY, Math.min(maxY, y));
      media.style.transform = `translate(${x}px, ${y}px) scale(${zoom})`;
      output.value = `${Math.round(zoom * 100)}%`; minus.disabled = zoom <= 1; plus.disabled = zoom >= 8;
      viewport.classList.toggle('is-zoomed', zoom > 1);
      const img = media.querySelector('img');
      if (scale && img?.naturalWidth) {
        const fit = Math.min(viewport.clientWidth / img.naturalWidth, viewport.clientHeight / img.naturalHeight);
        let length = calibration.length_mm, width = calibration.length_pixels * fit * zoom;
        // Keep the ruler in its fixed corner and readable at every magnification.
        while (width > Math.min(200, viewport.clientWidth * .28)) { width /= 2; length /= 2; }
        scale.querySelector('i').style.width = `${width}px`;
        scale.querySelector('span').textContent = `${Number(length.toPrecision(4))} mm`; scale.hidden = false;
      }
    }
    function changeZoom(next, point = [0, 0]) {
      next = Math.max(1, Math.min(8, next)); const factor = next / zoom;
      x = point[0] - (point[0] - x) * factor; y = point[1] - (point[1] - y) * factor; zoom = next; draw();
    }
    function showView(view) {
      if (media) releaseScales(viewport);
      zoom = 1; x = y = 0; drag = null;
      views.replaceChildren(...Object.keys(sample.views).map(key => {
        const b = node('button', key === view ? 'active' : '', t('view.' + key)); b.type = 'button';
        b.setAttribute('aria-pressed', String(key === view));
        b.addEventListener('click', () => { showView(key); views.querySelector('[aria-pressed="true"]').focus(); }); return b;
      }));
      media = samplePreview(sample, view); scaleObserver.unobserve(media);
      calibration = sample.display?.scale_bars?.[view]; scale = media.querySelector('.sample-scale');
      viewport.replaceChildren(media); if (scale) viewport.append(scale);
      const img = media.querySelector('img');
      if (img) { img.draggable = false; img.loading = 'eager'; img.addEventListener('load', draw); }
      draw();
    }
    minus.addEventListener('click', () => changeZoom(zoom / 1.5)); plus.addEventListener('click', () => changeZoom(zoom * 1.5));
    reset.addEventListener('click', () => { x = y = 0; changeZoom(1); });
    viewport.addEventListener('wheel', e => {
      e.preventDefault(); const r = viewport.getBoundingClientRect();
      changeZoom(zoom * Math.exp(-e.deltaY * .002), [e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2]);
    }, { passive: false });
    viewport.addEventListener('pointerdown', e => {
      if (e.button !== 0 || zoom <= 1) return;
      drag = { id: e.pointerId, px: e.clientX, py: e.clientY, x, y }; viewport.setPointerCapture(e.pointerId); viewport.classList.add('is-dragging');
    });
    viewport.addEventListener('pointermove', e => {
      if (!drag || drag.id !== e.pointerId) return;
      x = drag.x + e.clientX - drag.px; y = drag.y + e.clientY - drag.py; draw();
    });
    for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) viewport.addEventListener(type, () => { drag = null; viewport.classList.remove('is-dragging'); });
    viewport.addEventListener('dblclick', () => { x = y = 0; changeZoom(zoom > 1 ? 1 : 2); });
    dialog.addEventListener('keydown', e => {
      if (['+', '=', '-', '0'].includes(e.key)) { e.preventDefault(); if (e.key === '0') { x = y = 0; changeZoom(1); } else changeZoom(zoom * (e.key === '-' ? 1 / 1.5 : 1.5)); }
      if (e.key.startsWith('Arrow') && zoom > 1) {
        e.preventDefault(); x += e.key === 'ArrowLeft' ? 40 : e.key === 'ArrowRight' ? -40 : 0;
        y += e.key === 'ArrowUp' ? 40 : e.key === 'ArrowDown' ? -40 : 0; draw();
      }
    });
    const observer = new ResizeObserver(() => { if (media) draw(); }); observer.observe(viewport);
    dialog.addEventListener('close', () => { observer.disconnect(); releaseScales(viewport); dialog.remove(); });
    showView(initialView); dialog.showModal(); draw(); close.focus();
  }
  function openDetail(sample, preserveOpen = false) {
    state.current = sample;
    const box = $('detail-content');
    const heading = node('div', 'detail-heading');
    const headingTitle = node('h2', '', `${sample.id} / ${contentText(sample.title)}`); headingTitle.id = 'detail-title'; heading.append(headingTitle);
    const grid = node('dl', 'detail-grid');
    addPair(grid, t('sample.category'), label(sample.category));
    addPair(grid, t('sample.mode'), sample.acquisition_summary ? contentText(sample.acquisition_summary) : label(sample.mode));
    addPair(grid, t('sample.dimensions'), valueText(sample.dimensions));
    addPair(grid, t('sample.axes'), valueText(sample.axis_order));
    const calibratedSpacing = sample.display?.scale_calibration && Array.isArray(sample.spacing_mm);
    addPair(grid, t(calibratedSpacing ? 'sample.displaySpacing' : 'sample.spacing'), calibratedSpacing ? `≈ ${sample.spacing_mm.map(x => x.toFixed(3)).join(' × ')}` : valueText(sample.spacing_mm));
    addPair(grid, t('sample.wavelength'), sample.wavelength_description ? contentText(sample.wavelength_description) : valueText(sample.wavelength_nm));
    addPair(grid, t('sample.intensity'), valueText(sample.intensity_unit));
    if (sample.acquisition_groups?.length) {
      const entry = node('div', 'detail-acquisitions');
      entry.append(node('dt', '', t('sample.candidateIds')), node('dd', 'acquisition-range', acquisitionLabel(sample)));
      grid.append(entry);
    } else {
      addPair(grid, t('sample.version'), acquisitionLabel(sample));
    }
    const note = node('p', 'detail-note', contentText(sample.description));
    const figure = node('figure', 'detail-preview');
    if (!preserveOpen) state.currentView = state.view;
    const controls = node('div', 'view-switch'); controls.setAttribute('role', 'group');
    const caption = node('figcaption', 'preview-caption', t('sample.viewNote'));
    function showView(view) {
      state.currentView = view;
      controls.replaceChildren(...Object.keys(sample.views).map(key => {
        const button = node('button', key === view ? 'active' : '', t('view.' + key)); button.type = 'button';
        button.setAttribute('aria-pressed', String(key === view));
        button.addEventListener('click', () => { showView(key); controls.querySelector('[aria-pressed="true"]').focus(); }); return button;
      }));
      releaseScales(figure);
      const media = samplePreview(sample, view); media.classList.add('zoomable-preview');
      media.setAttribute('role', 'button'); media.tabIndex = 0; media.setAttribute('aria-label', t('zoom.open'));
      media.addEventListener('click', () => openZoom(sample, view));
      media.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openZoom(sample, view); } });
      const enlarge = node('button', 'zoom-launch', t('zoom.open')); enlarge.type = 'button';
      enlarge.addEventListener('click', () => openZoom(sample, view));
      figure.replaceChildren(controls, media, enlarge, caption);
    }
    showView(state.currentView);
    releaseScales(box);
    box.replaceChildren(heading, figure, grid, note);
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
  $('gallery-views').addEventListener('click', event => {
    const button = event.target.closest('[data-view]'); if (!button) return;
    state.view = button.dataset.view;
    $('gallery-views').querySelectorAll('button').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    document.querySelector('.depth-legend').hidden = state.view !== 'depth'; render();
  });
  $('sample-search').addEventListener('input', (e) => { state.query = e.target.value; render(); });
  $('mode-filter').addEventListener('change', (e) => { state.mode = e.target.value; render(); });
  $('clear-filters').addEventListener('click', () => { state.query = ''; state.mode = 'all'; setCategory('all'); $('sample-search').value = ''; $('mode-filter').value = 'all'; render(); $('sample-search').focus(); });
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
    const scale = config.dataset_scale;
    if (scale) {
      const format = new Intl.NumberFormat('en-US');
      for (const key of ['samples', 'exposures']) {
        const el = $('hero-' + key + '-count');
        if (el && Number.isSafeInteger(scale[key]) && scale[key] >= 0) el.textContent = format.format(scale[key]);
      }
    }
    const fill = (id, value) => { const text = contentText(value); if (text.trim() && $(id)) $(id).textContent = text; };
    if (Array.isArray(config.downloads)) {
      const cards = config.downloads.map((item) => {
        const card = node('article', 'download-card'); const enabled = Boolean(safeUrl(item.url));
        card.append(node('h3', '', contentText(item.title)), node('p', '', contentText(item.description)));
        const meta = node('div', 'download-meta');
        if (item.version) meta.append(node('span', '', t('resource.version', { version: item.version })));
        if (item.size_label) meta.append(node('span', '', contentText(item.size_label)));
        if (meta.childElementCount) card.append(meta);
        if (item.sha256) { const checksum = node('p', '', `SHA-256: ${item.sha256}`); checksum.style.overflowWrap = 'anywhere'; card.append(checksum); }
        const action = resource(contentText(item.action_label) || t('resource.download'), item.url);
        if (enabled && item.open_in_new_tab === true) action.target = '_blank';
        if (enabled && item.download_filename) {
          action.download = item.download_filename;
          action.textContent = (contentText(item.action_label) || t('resource.download')) + ' ↓';
        }
        if (!enabled) action.textContent = t('resource.preparing');
        card.append(action); return card;
      });
      $('download-grid').replaceChildren(...cards);
    }
    $('license-status').textContent = config.dataset_citations?.dataset?.license === 'CC BY 4.0' ? t('cite.license') : (config.license ? t('license.named', { license: contentText(config.license) }) : t('license.pending'));
    window.PACTCitation?.render(config.dataset_citations);
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
