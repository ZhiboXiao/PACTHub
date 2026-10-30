'use strict';
(() => {
  const video=document.getElementById('q-video');
  if(!video)return;
  const buttons=[...document.querySelectorAll('[data-q-time]')];
  const toggle=document.getElementById('q-video-toggle');
  const label=document.getElementById('q-play-label');
  const icon=document.getElementById('q-play-icon');
  const range=document.getElementById('q-video-range');
  const caption=document.getElementById('q-caption-text');
  const now=document.getElementById('q-current-time');
  const duration=document.getElementById('q-duration');
  let cues=[],pendingSeek=null;
  const stamp=value=>`${String(Math.floor(value/60)).padStart(2,'0')}:${String(Math.floor(value%60)).padStart(2,'0')}`;
  function render(){
    const length=Number.isFinite(video.duration)?video.duration:51;
    const time=Math.min(video.currentTime,Math.max(0,length-.001));
    let chapter=0;
    buttons.forEach((button,index)=>{if(time>=Number(button.dataset.qTime))chapter=index;});
    buttons.forEach((button,index)=>{
      button.classList.toggle('active',index===chapter);
      button.setAttribute('aria-pressed',String(index===chapter));
    });
    const cue=cues.find(item=>time>=item.start&&time<item.end);
    const text=cue?window.PACTI18N.localize(cue.text):'';
    if(caption.textContent!==text)caption.textContent=text;
    const playing=!video.paused&&!video.ended;
    label.textContent=window.PACTI18N.t(playing?'q.pause':'q.play');
    icon.textContent=playing?'Ⅱ':'▶';
    toggle.setAttribute('aria-label',label.textContent);
    now.textContent=stamp(video.currentTime);
    duration.textContent=stamp(length);
    range.max=String(length);
    range.value=String(video.currentTime);
    range.style.setProperty('--q-progress',`${100*video.currentTime/length}%`);
    range.setAttribute('aria-valuetext',`${stamp(video.currentTime)} / ${stamp(length)}`);
  }
  function seek(time){
    if(video.readyState>=1)video.currentTime=time;
    else{pendingSeek=time;video.load();}
  }
  function play(){video.play().catch(render);}
  buttons.forEach(button=>button.addEventListener('click',()=>{
    seek(Number(button.dataset.qTime));play();
  }));
  toggle.addEventListener('click',()=>{if(video.paused)play();else video.pause();});
  document.getElementById('q-video-restart').addEventListener('click',()=>{seek(0);play();});
  range.addEventListener('input',()=>{seek(Number(range.value));render();});
  video.addEventListener('loadedmetadata',()=>{
    if(pendingSeek!==null){video.currentTime=pendingSeek;pendingSeek=null;}
    render();
  });
  ['timeupdate','play','pause','seeked','ended'].forEach(name=>video.addEventListener(name,render));
  document.addEventListener('pact:languagechange',render);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();});
  fetch('data/q-video.json?v=20261026-flip').then(response=>{
    if(!response.ok)throw new Error('Q captions could not be loaded');
    return response.json();
  }).then(data=>{cues=data.captions;render();}).catch(()=>{caption.parentElement.hidden=true;});
  video.controls=false;
  document.querySelector('.q-video-controls').hidden=false;
  render();
})();
