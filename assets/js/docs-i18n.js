/* Full bilingual documentation. Hidden language sections stay out of the accessibility tree. */
'use strict';
(() => {
  const i18n = window.PACTI18N;
  if (!i18n) return;
  i18n.register({
    'docs.skip': '跳转到指南正文',
    'docs.home': '← 返回首页',
    'docs.home.aria': '返回 PACTHub 首页',
    'docs.home.footer': '返回数据集首页',
    'docs.navigation': '文档导航',
    'docs.language': '选择语言',
    'docs.description': 'PACTHub 中英双语网站指南。示例为合成 DEMO，真实研究材料待提供与核验。',
    'docs.footer': '网站框架 · 合成 DEMO 仅用于开发与交互演示；真实研究材料待接入。',
    'docs.nav.project-guide': '项目说明',
    'docs.nav.content-map': '内容地图',
    'docs.nav.data-guide': '数据接入',
    'docs.nav.algorithm-guide': '算法接入',
    'docs.nav.release-checklist': '发布清单',
    'docs.title.project-guide': '项目说明 · PACTHub',
    'docs.title.content-map': '内容地图与材料清单 · PACTHub',
    'docs.title.data-guide': '数据接入 · PACTHub',
    'docs.title.algorithm-guide': '算法接入 · PACTHub',
    'docs.title.release-checklist': '发布清单 · PACTHub'
  }, {
    'docs.skip': 'Skip to guide content',
    'docs.home': '← Back to home',
    'docs.home.aria': 'Back to the PACTHub homepage',
    'docs.home.footer': 'Back to the dataset homepage',
    'docs.navigation': 'Documentation navigation',
    'docs.language': 'Choose language',
    'docs.description': 'PACTHub Chinese/English website guides. Examples are synthetic DEMO content; actual research materials remain pending provision and verification.',
    'docs.footer': 'Website framework · Synthetic DEMO content is for development and interaction previews only. Actual research materials are pending integration.',
    'docs.nav.project-guide': 'Project guide',
    'docs.nav.content-map': 'Content map',
    'docs.nav.data-guide': 'Data integration',
    'docs.nav.algorithm-guide': 'Algorithm integration',
    'docs.nav.release-checklist': 'Release checklist',
    'docs.title.project-guide': 'Project guide · PACTHub',
    'docs.title.content-map': 'Content map and materials checklist · PACTHub',
    'docs.title.data-guide': 'Data integration · PACTHub',
    'docs.title.algorithm-guide': 'Algorithm integration · PACTHub',
    'docs.title.release-checklist': 'Release checklist · PACTHub'
  });

  function currentHashTarget() {
    try {
      return document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    } catch {
      return null;
    }
  }

  function alignHashWithLanguage() {
    const target = currentHashTarget();
    const section = target && target.closest('[data-lang-section]');
    if (!section || section.dataset.langSection === i18n.language) return;
    const anchor = target.dataset.docAnchor;
    const article = section.closest('article');
    if (!anchor || !article) return;
    const counterpart = Array.from(article.querySelectorAll('[data-doc-anchor]')).find((node) =>
      node.dataset.docAnchor === anchor && node.closest('[data-lang-section]').dataset.langSection === i18n.language
    );
    if (!counterpart) return;
    try {
      window.history.replaceState(window.history.state, '', '#' + encodeURIComponent(counterpart.id));
    } catch {
      // Sandboxed/file previews may disallow history updates. Switching still works.
    }
    if (typeof counterpart.scrollIntoView === 'function') counterpart.scrollIntoView({ block: 'start' });
  }

  function applySections() {
    let focusScope = null;
    document.querySelectorAll('[data-lang-section]').forEach((section) => {
      const selected = section.dataset.langSection === i18n.language;
      if (!selected && section.contains(document.activeElement)) focusScope = section.closest('.doc-content');
      section.hidden = !selected;
      if (selected) {
        section.removeAttribute('aria-hidden');
        section.removeAttribute('inert');
      } else {
        section.setAttribute('aria-hidden', 'true');
        section.setAttribute('inert', '');
      }
    });
    if (focusScope) {
      const button = focusScope.querySelector('[data-language="' + i18n.language + '"]');
      if (button) button.focus();
    }
    alignHashWithLanguage();
  }

  document.addEventListener('pact:languagechange', applySections);
  window.addEventListener('hashchange', alignHashWithLanguage);
  // Offline previews can add all guides to the same document or insert them later.
  if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver((records) => {
      const added = records.flatMap((record) => Array.from(record.addedNodes)).filter((node) =>
        node.nodeType === 1 && (node.matches('[data-lang-section]') || node.querySelector('[data-lang-section]'))
      );
      if (added.length) {
        i18n.apply();
        applySections();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
  applySections();
})();
