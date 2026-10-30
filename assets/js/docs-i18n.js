'use strict';
(() => {
  function render() {
    document.querySelectorAll('[data-lang-section]').forEach(el => el.hidden = el.dataset.langSection !== window.PACTI18N.language);
  }
  document.addEventListener('pact:languagechange', render); render();
})();
