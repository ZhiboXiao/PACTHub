/* Aligned, full-field comparison. Original image bytes are never modified. */
'use strict';
(() => {
  const slider = document.getElementById('enhancement-slider');
  if (!slider) return;
  let value = 50, pointer = null;
  const render = () => {
    slider.style.setProperty('--comparison-position', value + '%');
    slider.setAttribute('aria-valuenow', String(value));
    slider.setAttribute('aria-valuetext', window.PACTI18N.t('enhancement.value', { value, after: 100 - value }));
  };
  const setValue = (next) => { value = Math.max(0, Math.min(100, Math.round(next))); render(); };
  const position = (event) => {
    const rect = slider.getBoundingClientRect();
    if (rect.width > 0) setValue((event.clientX - rect.left) / rect.width * 100);
  };
  slider.addEventListener('pointerdown', (event) => {
    if (event.isPrimary === false || (event.button !== undefined && event.button !== 0)) return;
    pointer = event.pointerId; slider.setPointerCapture(pointer); slider.focus({ preventScroll: true }); position(event);
  });
  slider.addEventListener('pointermove', (event) => { if (event.pointerId === pointer) position(event); });
  const finish = (event) => { if (event.pointerId === pointer) pointer = null; };
  slider.addEventListener('pointerup', finish);
  slider.addEventListener('pointercancel', finish);
  slider.addEventListener('lostpointercapture', finish);
  slider.addEventListener('keydown', (event) => {
    const delta = event.shiftKey ? 10 : 1;
    const keys = { ArrowLeft: value - delta, ArrowDown: value - delta, ArrowRight: value + delta, ArrowUp: value + delta, Home: 0, End: 100, PageDown: value - 10, PageUp: value + 10 };
    if (Object.prototype.hasOwnProperty.call(keys, event.key)) { event.preventDefault(); setValue(keys[event.key]); }
  });
  document.addEventListener('pact:languagechange', render);
  render();
})();
