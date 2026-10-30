'use strict';
(() => {
  const film = document.getElementById('overview-film');
  const video = document.getElementById('overview-video');
  const toggle = document.getElementById('overview-film-toggle');
  const screen = document.getElementById('overview-screen');
  const choices = [...document.querySelectorAll('[data-overview-film]')];
  if (!film || !video || !toggle || !choices.length) return;
  // Loop the collection, rather than trapping playback in one film.
  video.loop = false;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let wanted = !reducedMotion.matches;
  let inView = false, active = 'structure', entries = [], revision = 0, attached = true;
  function sync() {
    const playing = !video.paused && !video.ended;
    film.classList.toggle('is-playing', playing);
    toggle.setAttribute('aria-label', window.PACTI18N.t(playing ? 'film.pause' : 'film.play'));
    const entry = entries.find(item => item.id === active);
    if (entry) video.setAttribute('aria-label', entry.title[window.PACTI18N.language] || entry.title.en);
  }
  function play() {
    if (attached && wanted && inView && !document.hidden) video.play().catch(sync);
  }
  function choose(id, initial = false) {
    const entry = entries.find(item => item.id === id);
    if (!entry || (!initial && active === id)) return;
    active = id;
    const current = ++revision;
    attached = false;
    video.pause();
    film.classList.add('is-switching');
    choices.forEach(button => {
      const selected = button.dataset.overviewFilm === id;
      button.setAttribute('aria-selected', String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    screen.setAttribute('aria-labelledby', 'overview-tab-' + id);
    window.setTimeout(() => {
      if (current !== revision) return;
      video.removeAttribute('src');
      video.replaceChildren();
      video.poster = entry.poster + '?v=' + entry.poster_sha256.slice(0, 10);
      video.src = entry.movie + '?v=' + entry.sha256.slice(0, 10);
      video.load();
      attached = true;
      film.classList.remove('is-switching');
      sync(); play();
    }, initial || reducedMotion.matches ? 0 : 180);
  }
  choices.forEach((button, index) => {
    button.addEventListener('click', () => choose(button.dataset.overviewFilm));
    button.addEventListener('keydown', event => {
      const moves = {ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1};
      let next;
      if (event.key in moves) next = (index + moves[event.key] + choices.length) % choices.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = choices.length - 1;
      else return;
      event.preventDefault(); choices[next].focus(); choose(choices[next].dataset.overviewFilm);
    });
  });
  toggle.addEventListener('click', () => {
    wanted = video.paused;
    if (wanted) play(); else video.pause();
  });
  ['play', 'pause', 'ended'].forEach(name => video.addEventListener(name, sync));
  video.addEventListener('ended', () => {
    if (!attached || !entries.length) return;
    const index = entries.findIndex(item => item.id === active);
    choose(entries[(index + 1) % entries.length].id);
  });
  document.addEventListener('pact:languagechange', sync);
  document.addEventListener('visibilitychange', () => {if (document.hidden) video.pause(); else play();});
  reducedMotion.addEventListener('change', event => {
    wanted = !event.matches;
    if (!wanted) video.pause(); else play();
  });
  new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting && entries[0].intersectionRatio >= .2;
    if (inView) play(); else video.pause();
  }, {threshold: .2}).observe(film);
  toggle.hidden = false;
  fetch('data/overview-library.json?v=20261027-leaf-column')
    .then(response => {if (!response.ok) throw new Error('Film library unavailable'); return response.json();})
    .then(data => {entries = data.films; choose(active, true);})
    .catch(error => {console.error(error); choices.forEach(button => button.disabled = true); video.controls = true;});
  sync();
})();
