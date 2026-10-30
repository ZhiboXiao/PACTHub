'use strict';
(() => {
  const dialog=document.getElementById('workflow-video-dialog');
  if(!dialog)return;
  const video=document.getElementById('workflow-video');
  const title=document.getElementById('workflow-video-title');
  const caption=document.getElementById('workflow-caption-text');
  const chapters=document.getElementById('workflow-chapters');
  const toggle=document.getElementById('workflow-toggle');
  const range=document.getElementById('workflow-range');
  const now=document.getElementById('workflow-current');
  const length=document.getElementById('workflow-duration');
  const note=document.getElementById('workflow-note');
  const download=document.getElementById('workflow-download');
  const films={
    calibration:{src:'assets/media/fov-sound-speed.mp4?v=20261026-finalfov',data:'data/calibration-video.json?v=20261026-finalfov',poster:'assets/images/showcase/calibration-poster.webp?v=20261026-finalfov',duration:32,title:'film.calibrationTitle',note:'film.calibrationNote'},
    q:{src:'assets/media/q-calculation.mp4?v=20261026-testimage',data:'data/q-video.json?v=20261026-testimage',poster:'assets/images/showcase/q-film-thumbnail.webp?v=20261026-testimage',duration:51,title:'q.title',note:'q.note'}
  };
  const cache=new Map();let active=null,opener=null,record=null,pendingSeek=null,serial=0;
  const t=(key)=>window.PACTI18N.t(key);
  const stamp=(v)=>`${String(Math.floor(v/60)).padStart(2,'0')}:${String(Math.floor(v%60)).padStart(2,'0')}`;
  function render(){
    if(!active)return;
    const config=films[active],total=Number.isFinite(video.duration)?video.duration:config.duration;
    const time=Math.min(video.currentTime,Math.max(0,total-.001));
    title.textContent=t(config.title);note.textContent=t(config.note);
    toggle.textContent=t(video.paused||video.ended?'q.play':'q.pause');
    now.textContent=stamp(video.currentTime);length.textContent=stamp(total);
    range.max=String(total);range.value=String(video.currentTime);range.setAttribute('aria-valuetext',`${stamp(video.currentTime)} / ${stamp(total)}`);
    const cue=record?.captions.find(item=>time>=item.start&&time<item.end);
    caption.textContent=cue?window.PACTI18N.localize(cue.text):t('film.captionLoading');
    [...chapters.children].forEach((button,index)=>{
      const item=record.chapters[index],selected=time>=item.start&&time<item.end;
      button.textContent=t(item.key);button.classList.toggle('active',selected);button.setAttribute('aria-pressed',String(selected));
    });
  }
  const play=()=>video.play().catch(()=>render());
  function seek(time){
    if(video.readyState>=1)video.currentTime=time;
    else pendingSeek=time;
    render();
  }
  function open(key,button){
    if(!films[key])return;
    const config=films[key],token=++serial;
    active=key;opener=button;record=null;pendingSeek=null;chapters.replaceChildren();
    video.pause();video.poster=config.poster;video.src=config.src;
    download.href=config.src;download.download=config.src.split('/').pop().split('?')[0];
    dialog.showModal();document.body.classList.add('workflow-video-open');render();
    video.load();play();
    if(!cache.has(key))cache.set(key,fetch(config.data).then(response=>{if(!response.ok)throw new Error('Captions unavailable');return response.json();}).catch(error=>{cache.delete(key);throw error;}));
    cache.get(key).then(data=>{
      if(token!==serial||!dialog.open)return;
      record=data;
      chapters.replaceChildren(...data.chapters.map(item=>{
        const button=document.createElement('button');button.type='button';button.textContent=t(item.key);
        button.addEventListener('click',()=>{seek(item.start);play();});return button;
      }));render();
    }).catch(()=>{if(token===serial)caption.textContent=t('film.captionUnavailable');});
  }
  document.querySelectorAll('[data-workflow-film]').forEach(button=>button.addEventListener('click',()=>open(button.dataset.workflowFilm,button)));
  document.getElementById('workflow-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
  dialog.addEventListener('close',()=>{
    serial++;video.pause();active=null;record=null;pendingSeek=null;
    video.removeAttribute('src');video.load();document.body.classList.remove('workflow-video-open');
    opener?.focus({preventScroll:true});
  });
  toggle.addEventListener('click',()=>{if(video.paused)play();else video.pause();});
  document.getElementById('workflow-restart').addEventListener('click',()=>{seek(0);play();});
  range.addEventListener('input',()=>{seek(Number(range.value));render();});
  video.addEventListener('loadedmetadata',()=>{if(pendingSeek!==null){video.currentTime=pendingSeek;pendingSeek=null;}render();});
  ['timeupdate','play','pause','seeked','ended'].forEach(event=>video.addEventListener(event,render));
  document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();});
  document.addEventListener('pact:languagechange',render);
  const fullscreen=document.getElementById('workflow-fullscreen'),shell=dialog.querySelector('.workflow-video-shell');
  if(!shell.requestFullscreen)fullscreen.hidden=true;
  fullscreen.addEventListener('click',()=>{if(document.fullscreenElement)document.exitFullscreen();else shell.requestFullscreen().catch(()=>{});});
  video.controls=false;dialog.querySelector('.workflow-controls').hidden=false;
})();
