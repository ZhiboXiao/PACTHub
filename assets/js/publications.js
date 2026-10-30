'use strict';
(() => {
  const section=document.getElementById('publication');
  const dialog=document.getElementById('paper-page-dialog');
  if(!section||!dialog)return;
  const image=document.getElementById('paper-page-image');
  const body=dialog.querySelector('.paper-page-body');
  const hint=document.getElementById('paper-page-hint');
  let trigger=null;
  const t=key=>window.PACTI18N.t(key);
  function updateHint(){hint.textContent=t(body.classList.contains('is-zoomed')?'pub.fit':'pub.zoom');}
  section.querySelectorAll('[data-paper-preview]').forEach(button=>button.addEventListener('click',()=>{
    trigger=button;
    image.src=button.dataset.paperPreview;
    image.alt=button.querySelector('img').alt;
    body.classList.remove('is-zoomed');updateHint();
    dialog.showModal();document.body.classList.add('modal-open');
    body.scrollTop=0;body.scrollLeft=0;
  }));
  function toggleZoom(){body.classList.toggle('is-zoomed');updateHint();}
  image.addEventListener('click',toggleZoom);
  image.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleZoom();}});
  document.getElementById('paper-page-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{
    if(event.target!==dialog)return;
    const r=dialog.getBoundingClientRect();
    if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();
  });
  dialog.addEventListener('close',()=>{document.body.classList.remove('modal-open');trigger?.focus();});
  section.querySelectorAll('[data-copy-publication]').forEach(button=>button.addEventListener('click',async()=>{
    const id=button.dataset.copyPublication;
    const citation=document.getElementById('citation-'+id);
    const feedback=section.querySelector(`[data-copy-feedback="${id}"]`);
    try{
      await navigator.clipboard.writeText(citation.textContent);
      feedback.dataset.message='pub.copied';
    }catch{
      citation.closest('details').open=true;
      const range=document.createRange();range.selectNodeContents(citation);
      const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
      feedback.dataset.message='pub.selected';
    }
    feedback.textContent=t(feedback.dataset.message);
  }));
  document.addEventListener('pact:languagechange',()=>{
    updateHint();
    section.querySelectorAll('[data-copy-feedback]').forEach(el=>{if(el.dataset.message)el.textContent=t(el.dataset.message);});
  });
  updateHint();
})();
