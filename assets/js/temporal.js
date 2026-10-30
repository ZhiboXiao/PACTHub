/* Interactive measurements use calibrated compact MIPs, before display windowing. */
'use strict';
(() => {
  const $=id=>document.getElementById(id), {t,localize}=window.PACTI18N;
  const colors=['#f7f8f8','#8a8f98','#d0d6e0','#b8b8b8','#ffffff','#a0a0a0'];
  const patterns=['','8 5','2 4','12 4 2 4','16 6','5 3 1 3'];
  const dash=r=>patterns[colors.indexOf(r.color)] || '';
  const NS='http://www.w3.org/2000/svg', states=new Map();
  const state={series:[],active:0,frame:0,mode:'relative_mean',playing:false,speed:1,timer:null};
  let worker,revision=0,scheduled=false,drag=null,clip,cursor,plotId=0;
  let nearView=false;
  const prefetched=new Set();
  const current=()=>state.series[state.active], ui=()=>states.get(current().id);
  const node=(tag,cls,text)=>{const e=document.createElement(tag);e.className=cls||'';if(text!==undefined)e.textContent=text;return e;};
  const svg=(tag,attrs={},text)=>{const e=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;};
  const finite=n=>typeof n==='number'&&Number.isFinite(n);
  const fmt=n=>!finite(n)?'—':state.mode==='relative_mean'?n.toFixed(2)+'×':n.toFixed(4);
  const x=time=>104+time/current().duration_minutes*528;
  function updatePlay(){ $('temporal-play').textContent=(state.playing?'Ⅱ ':'▶ ')+t(state.playing?'temporal.pause':'temporal.play');$('temporal-play').setAttribute('aria-pressed',String(state.playing)); }
  function stop(){clearTimeout(state.timer);state.playing=false;updatePlay();}
  function status(key){$('temporal-roi-status').textContent=t(key);}
  function addROI(bounds){const u=ui(),id=++u.next;const used=new Set(u.rois.map(r=>r.color));u.rois.push({id,bounds:[...bounds],visible:true,color:colors.find(c=>!used.has(c))});u.selected=id;return u.rois.at(-1);}
  function examples(){const u=ui();u.rois=[];u.next=0;current().interactive_mips.default_rois_xyxy.forEach(b=>addROI(b));renderROIs();renderRows();query();}
  function renderROIs(){
    const overlay=$('temporal-rois'),s=current(),u=ui(),[,h,w]=s.interactive_mips.shape_tyx;
    overlay.replaceChildren();overlay.classList.toggle('ready',u.ready);overlay.setAttribute('aria-busy',String(!u.ready));
    u.rois.forEach(r=>{
      const [x0,y0,x1,y1]=r.bounds,box=node('div','roi-box'+(u.selected===r.id?' selected':'')+(!r.visible?' muted':''));
      box.dataset.roi=r.id;box.dataset.bounds=r.bounds.join(',');box.tabIndex=0;box.setAttribute('role','group');box.setAttribute('aria-label',t('temporal.region')+' '+r.id);
      box.style.cssText=`--roi:${r.color};left:${x0/w*100}%;top:${y0/h*100}%;width:${(x1-x0)/w*100}%;height:${(y1-y0)/h*100}%`;
      box.style.borderStyle=dash(r)?'dashed':'solid';
      box.append(node('span','roi-badge',r.id));
      for(const corner of ['nw','ne','sw','se']){const handle=node('span','roi-handle '+corner);handle.dataset.handle=corner;box.append(handle);}
      overlay.append(box);
    });
  }
  function renderRows(){
    const u=ui(),s=current(),[,h,w]=s.interactive_mips.shape_tyx,axes=s.interactive_mips.display_axis_edges_mm;
    $('temporal-readouts').replaceChildren(...u.rois.map(r=>{
      const row=node('div','roi-readout'+(!r.visible?' muted':''));row.dataset.roi=r.id;row.style.setProperty('--roi',r.color);row.style.setProperty('--roi-style',dash(r)?'dashed':'solid');
      const toggle=node('button','roi-select',t('temporal.region')+' '+r.id);toggle.type='button';toggle.setAttribute('aria-pressed',String(r.visible));toggle.title=t(r.visible?'temporal.hide':'temporal.show');
      toggle.addEventListener('click',()=>{r.visible=!r.visible;u.selected=r.id;renderROIs();renderRows();buildChart();showValues();});
      const remove=node('button','roi-remove','×');remove.type='button';remove.setAttribute('aria-label',t('temporal.remove')+' '+r.id);remove.addEventListener('click',()=>removeROI(r.id));
      const head=node('div','roi-readout-head');head.append(toggle,remove);
      const [a,b,c,d]=r.bounds,mmX=Math.abs(axes.x[1]-axes.x[0])*(c-a)/w,mmY=Math.abs(axes.y[1]-axes.y[0])*(d-b)/h;
      const details=node('small','roi-dimensions',`${mmX.toFixed(1)} × ${mmY.toFixed(1)} mm`);
      const value=node('strong','roi-value',fmt(r.result?.[state.mode]?.[state.frame]));value.dataset.mean=r.result?.mean_linear?.[state.frame]??'';
      row.append(head,details,value);return row;
    }));
    $('temporal-roi-count').textContent=`${u.rois.length} / 6`;
    $('temporal-roi-clear').disabled=!u.rois.length;
  }
  function removeROI(id){ui().rois=ui().rois.filter(r=>r.id!==id);renderROIs();renderRows();query();buildChart();}
  function query(){
    if(!ui().ready||scheduled)return;
    scheduled=true;requestAnimationFrame(()=>{scheduled=false;const u=ui();if(!u.ready)return;u.revision=++revision;worker.postMessage({type:'query',series:current().id,revision,rois:u.rois.map(({id,bounds})=>({id,bounds}))});});
  }
  function buildChart(){
    const chart=$('temporal-chart'),s=current(),u=ui();chart.replaceChildren();chart.setAttribute('aria-label',t('temporal.chartAlt'));chart.append(svg('title',{},t('temporal.chartAlt')));
    const values=u.rois.filter(r=>r.visible).flatMap(r=>r.result?.[state.mode]||[]).filter(finite);
    const maximum=values.length?Math.max(...values):1,maximumAbs=Math.max(maximum,1e-12)*1.13;
    const y=v=>270-v/maximumAbs*232,id='trace-reveal-'+(++plotId),defs=svg('defs'),cp=svg('clipPath',{id});
    clip=svg('rect',{x:100,y:0,width:4,height:280});cp.append(clip);defs.append(cp);chart.append(defs);
    for(let i=0;i<=4;i++){const v=maximumAbs*i/4,yy=y(v);chart.append(svg('line',{x1:104,x2:632,y1:yy,y2:yy,stroke:'#23252a','stroke-dasharray':'3 5'}),svg('text',{x:88,y:yy+4,'text-anchor':'end',class:'chart-tick'},state.mode==='relative_mean'?v.toFixed(1):v.toFixed(3)));const time=s.duration_minutes*i/4;chart.append(svg('text',{x:x(time),y:293,'text-anchor':'middle',class:'chart-tick'},time.toFixed(1)));}
    chart.append(svg('text',{x:104,y:24,class:'chart-label'},t(state.mode==='relative_mean'?'temporal.relativeAxis':'temporal.linearAxis')),svg('text',{x:632,y:343,'text-anchor':'end',class:'chart-label'},t('temporal.timeAxis')));
    for(const r of u.rois.filter(r=>r.visible&&r.result)){
      const a=r.result[state.mode];let gap=true;const d=a.map((v,j)=>{if(!finite(v)){gap=true;return '';}const part=`${gap?'M':'L'} ${x(s.frames[j].time_min)} ${y(v)}`;gap=false;return part;}).join(' ');
      chart.append(svg('path',{d,fill:'none',stroke:r.color,'stroke-dasharray':dash(r),'stroke-width':1.5,opacity:.24}));
      const group=svg('g',{'clip-path':`url(#${id})`});group.append(svg('path',{d,fill:'none',stroke:r.color,'stroke-dasharray':dash(r),'stroke-width':2.5,'stroke-linejoin':'round'}));a.forEach((v,j)=>{if(finite(v))group.append(svg('circle',{cx:x(s.frames[j].time_min),cy:y(v),r:3,fill:r.color,stroke:'#0f1011','stroke-width':1}));});chart.append(group);
    }
    if(!values.length)chart.append(svg('text',{x:344,y:150,'text-anchor':'middle',class:'chart-label'},t(u.rois.length?'temporal.noValues':'temporal.empty')));
    cursor=svg('line',{x1:104,x2:104,y1:30,y2:270,stroke:'#d0d6e0',opacity:.65});chart.append(cursor);showValues();
  }
  function showValues(animate=false){
    if(!current())return;const time=current().frames[state.frame].time_min;
    if(clip){clip.style.transition=animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'width 650ms linear':'none';clip.style.width=(x(time)-96)+'px';cursor.setAttribute('x1',x(time));cursor.setAttribute('x2',x(time));}
    for(const r of ui().rois){const value=$('temporal-readouts').querySelector(`[data-roi="${r.id}"] .roi-value`);if(value){value.textContent=fmt(r.result?.[state.mode]?.[state.frame]);value.dataset.mean=r.result?.mean_linear?.[state.frame]??'';}}
  }
  function showFrame(animate=false){
    const s=current(),f=s.frames[state.frame];$('temporal-image').src=f.image+'?v='+s.interactive_mips.sha256.slice(0,10);$('temporal-image').alt=`${localize(s.title)} · ${f.time_min.toFixed(2)} min`;
    $('temporal-frame').textContent=`${String(state.frame+1).padStart(2,'0')} / ${s.frames.length}`;$('temporal-time').textContent=f.time_min.toFixed(2)+' min';$('temporal-acquisition').textContent=f.acquisition_id;
    $('temporal-range').value=state.frame;$('temporal-range').style.setProperty('--progress',`${state.frame/Math.max(1,s.frames.length-1)*100}%`);$('temporal-range').setAttribute('aria-valuetext',`${f.time_min.toFixed(2)} min; ${state.frame+1}/${s.frames.length}`);showValues(animate);
  }
  function schedule(){state.timer=setTimeout(()=>{if(!state.playing)return;if(state.frame===current().frames.length-1){stop();return;}state.frame++;showFrame(true);schedule();},1500/state.speed);}
  function ensureSeries(){
    if(!nearView||!worker||!current())return;
    const s=current();
    worker.postMessage({type:'load',series:s.id,source:s.interactive_mips});
    if(!prefetched.has(s.id)){
      prefetched.add(s.id);
      s.frames.forEach(f=>{const image=new Image();image.src=f.image+'?v='+s.interactive_mips.sha256.slice(0,10);});
    }
  }
  function selectSeries(index,frame=0){
    stop();state.active=index;state.frame=frame;drag=null;const s=current();if(!states.has(s.id))states.set(s.id,{ready:false,rois:[],next:0,revision:0,selected:null});
    const [,height,width]=s.interactive_mips.shape_tyx;
    $('temporal-image').width=width;$('temporal-image').height=height;
    $('temporal-image').parentElement.style.aspectRatio=`${width} / ${height}`;
    const u=ui();$('temporal-series').value=s.id;$('temporal-range').max=s.frames.length-1;$('temporal-duration').textContent=`0 – ${s.duration_minutes.toFixed(1)} min`;
    $('temporal-summary').textContent=t('temporal.summary',{frames:s.frames.length,exposures:s.exposure_count,minutes:s.duration_minutes.toFixed(1)})+(s.wavelength_nm?` · ${s.wavelength_nm} nm`:'');
    $('temporal-roi-examples').disabled=!u.ready;status(u.ready?'temporal.drawHint':'temporal.loadingMips');renderROIs();renderRows();buildChart();showFrame();
    ensureSeries();
  }
  function point(e){const rect=$('temporal-rois').getBoundingClientRect(),[,h,w]=current().interactive_mips.shape_tyx;return [Math.max(0,Math.min(w,Math.round((e.clientX-rect.left)/rect.width*w))),Math.max(0,Math.min(h,Math.round((e.clientY-rect.top)/rect.height*h)))];}
  const overlay=$('temporal-rois');
  overlay.addEventListener('pointerdown',e=>{
    if(!ui().ready||e.button!==0)return;const box=e.target.closest('[data-roi]'),p=point(e);let r=box?ui().rois.find(r=>r.id===Number(box.dataset.roi)):null;
    if(!r){if(ui().rois.length>=6){status('temporal.limit');return;}const [,h,w]=current().interactive_mips.shape_tyx;r=addROI([Math.min(p[0],w-4),Math.min(p[1],h-4),Math.min(p[0]+4,w),Math.min(p[1]+4,h)]);}
    drag={id:r.id,start:p,origin:[...r.bounds],mode:box?(e.target.dataset.handle||'move'):'draw',pointer:e.pointerId};ui().selected=r.id;overlay.setPointerCapture(e.pointerId);e.preventDefault();renderROIs();renderRows();query();status('temporal.drawHint');
  });
  overlay.addEventListener('pointermove',e=>{
    if(!drag||e.pointerId!==drag.pointer)return;const p=point(e),[,h,w]=current().interactive_mips.shape_tyx,r=ui().rois.find(r=>r.id===drag.id);if(!r)return;
    let [a,b,c,d]=drag.origin;const dx=p[0]-drag.start[0],dy=p[1]-drag.start[1];
    if(drag.mode==='move'){const mx=Math.max(-a,Math.min(w-c,dx)),my=Math.max(-b,Math.min(h-d,dy));a+=mx;c+=mx;b+=my;d+=my;}
    else if(drag.mode==='draw'){a=Math.min(drag.start[0],p[0],w-4);b=Math.min(drag.start[1],p[1],h-4);c=Math.max(a+4,drag.start[0],p[0]);d=Math.max(b+4,drag.start[1],p[1]);}
    else{if(drag.mode.includes('w'))a=Math.min(p[0],c-4);if(drag.mode.includes('e'))c=Math.max(p[0],a+4);if(drag.mode.includes('n'))b=Math.min(p[1],d-4);if(drag.mode.includes('s'))d=Math.max(p[1],b+4);}
    r.bounds=[a,b,c,d];renderROIs();renderRows();query();
  });
  function endDrag(e){if(drag&&drag.pointer===e.pointerId){drag=null;query();}}
  overlay.addEventListener('pointerup',endDrag);overlay.addEventListener('pointercancel',endDrag);
  overlay.addEventListener('keydown',e=>{
    const box=e.target.closest('[data-roi]');if(!box)return;const r=ui().rois.find(r=>r.id===Number(box.dataset.roi));if(!r)return;
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();removeROI(r.id);return;}
    const step=e.shiftKey?10:1,moves={ArrowLeft:[-step,0],ArrowRight:[step,0],ArrowUp:[0,-step],ArrowDown:[0,step]};if(!moves[e.key])return;e.preventDefault();
    const [,h,w]=current().interactive_mips.shape_tyx,[a,b,c,d]=r.bounds,[mx,my]=moves[e.key],dx=Math.max(-a,Math.min(w-c,mx)),dy=Math.max(-b,Math.min(h-d,my));r.bounds=[a+dx,b+dy,c+dx,d+dy];renderROIs();renderRows();overlay.querySelector(`[data-roi="${r.id}"]`).focus();query();
  });
  $('temporal-roi-clear').addEventListener('click',()=>{ui().rois=[];renderROIs();renderRows();query();buildChart();});
  $('temporal-roi-examples').addEventListener('click',examples);
  $('temporal-play').addEventListener('click',()=>{if(state.playing){stop();return;}if(state.frame===current().frames.length-1){state.frame=0;showFrame();}state.playing=true;updatePlay();schedule();});
  $('temporal-restart').addEventListener('click',()=>{stop();state.frame=0;showFrame();});
  $('temporal-range').addEventListener('input',e=>{stop();state.frame=Number(e.target.value);showFrame();});
  $('temporal-series').addEventListener('change',e=>selectSeries(state.series.findIndex(s=>s.id===e.target.value)));
  $('temporal-unit').addEventListener('change',e=>{state.mode=e.target.value;buildChart();showValues();});
  $('temporal-speed').addEventListener('change',e=>{state.speed=Number(e.target.value);if(state.playing){clearTimeout(state.timer);schedule();}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  document.addEventListener('pact:languagechange',()=>{if(!state.series.length)return;state.series.forEach((s,i)=>$('temporal-series').options[i].textContent=localize(s.title));selectSeries(state.active,state.frame);});
  $('temporal-image').loading='lazy';
  new IntersectionObserver(entries=>{nearView=entries[0].isIntersecting;if(nearView)ensureSeries();},{rootMargin:'400px 0px'}).observe($('applications'));
  fetch('data/temporal.json?v=20261027-compact').then(r=>{if(!r.ok)throw Error('Temporal data unavailable');return r.json();}).then(data=>{
    state.series=data.series;worker=new Worker('assets/js/temporal-quant-worker.js?v=20261027-compact');
    worker.onmessage=({data:m})=>{
      const u=states.get(m.series);if(!u)return;
      if(m.type==='ready'){u.ready=true;if(m.series===current().id){$('temporal-roi-examples').disabled=false;status('temporal.drawHint');if(!u.initialized){u.initialized=true;examples();}else{renderROIs();query();}}}
      if(m.type==='indexing'&&m.series===current().id)status('temporal.preparing');
      if(m.type==='error'&&m.series===current().id){u.ready=false;renderROIs();status('temporal.dataError');}
      if(m.type==='result'&&m.revision===u.revision){m.results.forEach(result=>{const r=u.rois.find(r=>r.id===result.id);if(r)r.result=result;});if(m.series===current().id){renderRows();buildChart();}}
    };
    worker.onerror=()=>status('temporal.dataError');
    $('temporal-series').replaceChildren(...state.series.map(s=>new Option(localize(s.title),s.id)));selectSeries(0);$('temporal-loading').hidden=true;$('temporal-player').hidden=false;
  }).catch(()=>{$('temporal-loading').textContent=t('temporal.error');});
})();
