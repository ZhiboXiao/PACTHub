'use strict';
(() => {
  const root=document.getElementById('parameter-explorer');if(!root)return;
  const names=['signal','frames','grid','geometry'],duration=28;
  const scene=document.getElementById('demo-scene'),readout=document.getElementById('demo-readout'),play=document.getElementById('demo-play');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),t=key=>window.PACTI18N.t(key);
  const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp=v=>Math.max(0,Math.min(1,v)),ease=v=>{v=clamp(v);return v*v*(3-2*v);};
  const num=v=>Number(v.toFixed(3)).toString(),arr=a=>'['+a.map(num).join(', ')+']';
  const label=(x,y,value,cls='')=>`<text x="${x}" y="${y}" class="${cls}">${esc(value)}</text>`;
  const line=(a,b,c,d,cls='')=>`<line x1="${a}" y1="${b}" x2="${c}" y2="${d}" class="${cls}"/>`;
  let data=null,time=reduced.matches?6.8:0,mode=reduced.matches?'interactive':'intro',playing=!reduced.matches,visible=false,raf=0,last=null,active=-1,stepEnd=7;
  function frequency(p){
    const [lo,hi]=data.defaults.signal.filter.band_hz.map(v=>v/1e6),fs=data.defaults.signal.sampling_frequency_hz/1e6;
    const x=v=>60+580*v/(fs/2),edge=lo+(hi-lo)*ease((p-.12)/.62);let s='';
    for(let v=0;v<=fs/2;v+=5)s+=line(x(v),80,x(v),265,'demo-chart-grid')+label(x(v),294,v,'demo-axis-value');
    s+=line(60,265,640,265,'demo-chart-axis')+`<rect x="${x(lo)}" y="105" width="${x(hi)-x(lo)}" height="160" class="demo-band-target"/><rect id="demo-band" data-edge-mhz="${edge}" x="${x(lo)}" y="105" width="${x(edge)-x(lo)}" height="160" class="demo-band-fill"/>`;
    s+=line(x(edge),89,x(edge),273,'demo-sweep-line')+label(x(lo),82,lo,'demo-frequency-label')+label(x(hi),82,hi+' MHz','demo-frequency-label')+label(640,326,t('workflow.hz'),'demo-axis-unit');
    readout.innerHTML=`<strong>${lo}–${hi} <span>MHz</span></strong><code>fₛ = ${fs} MHz</code>`;return s;
  }
  function frames(p){
    const f=data.defaults.frames,n=Math.min(f.count,Math.floor(clamp((p-.12)/.65)*f.count+.00001)),selected=f.indices_1based.slice(0,n);let s='';
    for(let i=1;i<=f.available_count;i++){
      const x=57+((i-1)%10)*60,y=53+Math.floor((i-1)/10)*53,on=selected.includes(i);
      s+=`<g data-frame="${i}" data-selected="${on}" class="demo-exposure ${on?'is-selected':''} ${i===selected.at(-1)?'is-latest':''}"><rect x="${x}" y="${y}" width="47" height="37" rx="4"/>${label(x+23.5,y+24,String(i).padStart(2,'0'))}</g>`;
    }
    readout.innerHTML=`<strong><span id="demo-selected-count">${n}</span> / ${f.available_count} <span>${esc(t('workflow.framesUnit'))}</span></strong><code>count: ${f.count}</code>`;
    return s+label(57,340,'indices_1based','demo-mini-label');
  }
  const project=([x,y,z])=>[350+3*(.92*x+.72*z),190+3*(-.98*y+.18*x-.5*z)];
  const point=p=>project(p).map(v=>v.toFixed(2)).join(',');
  function cube(scale,center,angle,ghost=false){
    const [sx,sy,sz]=data.defaults.grid.space_mm.map(v=>v*scale/2),r=angle*Math.PI/180;
    const transform=([x,y,z])=>[x*Math.cos(r)-y*Math.sin(r)+center[0],x*Math.sin(r)+y*Math.cos(r)+center[1],z+center[2]];
    const v=[[-sx,-sy,-sz],[sx,-sy,-sz],[sx,sy,-sz],[-sx,sy,-sz],[-sx,-sy,sz],[sx,-sy,sz],[sx,sy,sz],[-sx,sy,sz]].map(transform);
    const edges=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
    let s=`<g class="${ghost?'demo-cube-ghost':'demo-cube'}"${ghost?'':` id="demo-cube" data-center="${center.join(',')}" data-rz="${angle}" data-scale="${scale}"`}>`;
    if(!ghost)for(const f of [[0,1,5,4],[1,2,6,5],[2,3,7,6]])s+=`<polygon points="${f.map(i=>point(v[i])).join(' ')}"/>`;
    for(const [a,b] of edges)s+=line(...project(v[a]),...project(v[b]));
    if(!ghost){
      for(let n=1;n<8;n++){const y=-sy+2*sy*n/8;s+=line(...project(transform([-sx,y,sz])),...project(transform([sx,y,sz])),'demo-cube-grid');}
      for(let n=1;n<4;n++){const x=-sx+2*sx*n/4;s+=line(...project(transform([x,-sy,sz])),...project(transform([x,sy,sz])),'demo-cube-grid');}
    }
    return s+'</g>';
  }
  function grid(p){
    const g=data.defaults.grid,scale=.001+.999*ease((p-.12)/.6),opacity=clamp((p-.55)/.18);
    readout.innerHTML=`<strong>${g.space_mm.join(' × ')} <span>mm</span></strong><code>${g.shape_xyz.join(' × ')} voxels</code>`;
    return cube(scale,[0,0,0],0)+`<g opacity="${opacity}">`+label(95,188,`Y · ${g.space_mm[1]} mm`,'demo-dimension')+label(290,345,`X · ${g.space_mm[0]} mm`,'demo-dimension')+label(483,89,`Z · ${g.space_mm[2]} mm`,'demo-dimension')+'</g>';
  }
  function geometry(p){
    const center=data.defaults.grid.center_mm.map(v=>v*ease((p-.12)/.45)),angle=data.defaults.geometry.additional_z_rotation_deg*ease((p-.25)/.5);let s='';
    for(const a of [[-55,0,0,55,0,0],[0,-50,0,0,50,0],[0,0,-25,0,0,25]])s+=line(...project(a.slice(0,3)),...project(a.slice(3)),'demo-world-axis');
    s+=cube(1,[0,0,0],0,true)+cube(1,center,angle);const o=project([0,0,0]),c=project(center);
    s+=`<circle cx="${o[0]}" cy="${o[1]}" r="4" class="demo-origin"/><circle cx="${c[0]}" cy="${c[1]}" r="4" class="demo-target"/>`;
    readout.innerHTML=`<strong>Rz <span>${num(angle)}°</span></strong><code>grid.center_mm: ${arr(center)}</code>`;
    return s+label(56,329,t('workflow.schematic'),'demo-mini-label');
  }
  function controls(){
    root.dataset.mode=mode;root.dataset.playing=String(playing);
    play.textContent=t(playing?'workflow.pause':'workflow.play');play.setAttribute('aria-pressed',String(playing));play.hidden=mode==='interactive'&&!playing;
    document.getElementById('demo-mode').textContent=t(mode==='intro'?'workflow.auto':'workflow.interactive');
    document.getElementById('demo-explore').hidden=mode==='interactive';
    root.querySelectorAll('[data-parameter]').forEach(b=>{b.disabled=mode==='intro';});
  }
  function render(){
    if(!data)return;const index=Math.min(3,Math.floor(time/7)),p=(time-index*7)/7;
    root.dataset.stage=names[index];root.dataset.progress=p.toFixed(4);
    if(index!==active){
      active=index;
      root.querySelectorAll('[data-parameter]').forEach((b,i)=>{b.classList.toggle('is-active',i===index);b.setAttribute('aria-pressed',String(i===index));b.setAttribute('aria-expanded',String(i===index));});
      root.querySelectorAll('[data-json-panel]').forEach(el=>{el.hidden=el.dataset.jsonPanel!==names[index];});
    }
    root.querySelectorAll('.demo-click').forEach((el,i)=>{el.style.opacity=i===index&&p>.06&&p<.2?Math.sin(Math.PI*clamp((p-.06)/.14)):0;el.style.transform=`scale(${.6+.7*clamp((p-.06)/.14)})`;});
    const cursor=document.getElementById('demo-cursor'),group=root.querySelector('.demo-groups'),buttons=[...root.querySelectorAll('[data-parameter]')];
    const box=group.getBoundingClientRect(),from=buttons[Math.max(0,index-1)].getBoundingClientRect(),to=buttons[index].getBoundingClientRect(),travel=ease(p/.09);
    cursor.style.transform=`translate(${(from.left+from.width*.62-box.left)*(1-travel)+(to.left+to.width*.62-box.left)*travel}px,${(from.top+from.height*.65-box.top)*(1-travel)+(to.top+to.height*.65-box.top)*travel}px)`;
    cursor.style.opacity=mode==='intro'&&p<.27?clamp((.27-p)/.06):0;
    const fadeIn=ease((p-.08)/.1),fadeOut=mode==='intro'&&index<3?ease((1-p)/.06):1;
    root.querySelector('.demo-json-deck').style.opacity=fadeIn;
    root.querySelector('.demo-scene-heading').style.opacity=fadeIn*fadeOut;
    scene.style.opacity=fadeIn*fadeOut;readout.style.opacity=fadeIn*fadeOut;
    document.getElementById('demo-step-title').textContent=t('workflow.'+names[index]);
    scene.innerHTML=`<svg viewBox="0 0 700 360" role="img" aria-label="${esc(t('workflow.'+names[index]))}">${[frequency,frames,grid,geometry][index](p)}</svg>`;
    document.getElementById('demo-clock').textContent=`00:${String(Math.min(28,Math.floor(time+.0001))).padStart(2,'0')} / 00:28`;controls();
  }
  function halt(){if(raf)cancelAnimationFrame(raf);raf=0;last=null;}
  function tick(now){
    raf=0;if(!playing||!visible||document.hidden||!data){last=null;return;}
    if(last!==null)time+=Math.min(.15,(now-last)/1000);
    if(mode==='intro'&&time>=duration){time=duration;mode='interactive';playing=false;last=null;render();return;}
    if(mode==='interactive'&&time>=stepEnd){time=stepEnd-.000001;playing=false;last=null;render();return;}
    last=now;render();raf=requestAnimationFrame(tick);
  }
  function schedule(){if(playing&&visible&&!document.hidden&&data&&!raf){last=null;raf=requestAnimationFrame(tick);}}
  function pause(){playing=false;halt();controls();}
  function formatJSON(value,depth=0){
    if(Array.isArray(value)&&value.every(v=>v===null||typeof v!=='object'))return '['+value.map(v=>JSON.stringify(v)).join(', ')+']';
    if(value&&typeof value==='object'){
      const isArray=Array.isArray(value),open=isArray?'[':'{',close=isArray?']':'}',pad='  '.repeat(depth+1);
      const parts=Object.entries(value).map(([key,v])=>pad+(isArray?'':JSON.stringify(key)+': ')+formatJSON(v,depth+1));
      return open+'\n'+parts.join(',\n')+'\n'+'  '.repeat(depth)+close;
    }
    return JSON.stringify(value);
  }
  function syntax(value){
    const source=formatJSON(value),pattern=/"(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
    let html='',lastIndex=0;
    for(const m of source.matchAll(pattern)){
      html+=esc(source.slice(lastIndex,m.index));const token=m[0],kind=token.endsWith(':')?'key':token.startsWith('"')?'string':/[a-z]/.test(token)?'literal':'number';
      html+=`<span class="json-${kind}">${esc(token)}</span>`;lastIndex=m.index+token.length;
    }
    return html+esc(source.slice(lastIndex));
  }
  function showParameters(){
    const first={signal:['filter','sampling_frequency_hz','polarity','energy_normalization'],frames:['indices_1based','count','available_count','compound_mode'],grid:['space_mm','shape_xyz','center_mm','resolution_px_mm'],geometry:['additional_z_rotation_deg','frame_angle_step_parameter_deg','transform_order','coordinate_unit']};
    for(const name of names){
      const panel=root.querySelector(`[data-json-panel="${name}"]`),entries=data.defaults[name];panel.replaceChildren();
      const keys=[...first[name].filter(key=>key in entries),...Object.keys(entries).filter(key=>!first[name].includes(key))];
      for(const key of keys){const value=entries[key];
        if(Array.isArray(value)&&value.length>40){
          const details=document.createElement('details'),summary=document.createElement('summary');details.dataset.field=key;
          summary.textContent=`${key}: [${value.length}${Array.isArray(value[0])?' × '+value[0].length:''}]`;details.append(summary);
          details.addEventListener('toggle',()=>{if(details.open){pause();if(!details.querySelector('pre')){const pre=document.createElement('pre');pre.innerHTML=syntax(value);details.append(pre);}}});panel.append(details);
        }else{
          const pre=document.createElement('pre');pre.dataset.field=key;if(key===keys[0])pre.classList.add('demo-primary');
          pre.innerHTML=syntax({[key]:value}).slice(2,-2).replace(/^  /gm,'');panel.append(pre);
        }
      }
      panel.addEventListener('wheel',pause,{passive:true});panel.addEventListener('touchstart',pause,{passive:true});panel.addEventListener('keydown',event=>{if(['ArrowDown','ArrowUp','PageDown','PageUp','Home','End'].includes(event.key))pause();});
    }
  }
  root.addEventListener('click',e=>{const b=e.target.closest('[data-parameter]');if(b&&mode==='interactive'){time=names.indexOf(b.dataset.parameter)*7;stepEnd=time+7;playing=true;last=null;root.querySelector(`[data-json-panel="${b.dataset.parameter}"]`).scrollTop=0;render();schedule();}});
  play.addEventListener('click',()=>{playing=!playing;if(playing)schedule();else halt();controls();});
  document.getElementById('demo-restart').addEventListener('click',()=>{time=0;mode='intro';playing=true;last=null;render();schedule();});
  document.getElementById('demo-explore').addEventListener('click',()=>{mode='interactive';pause();time=Math.min(28,Math.floor(time/7)*7+6.8);render();});
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)schedule();else halt();},{threshold:.12}).observe(root);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)halt();else schedule();});document.addEventListener('pact:languagechange',render);
  reduced.addEventListener('change',e=>{if(e.matches){mode='interactive';pause();time=Math.min(28,Math.floor(time/7)*7+6.8);render();}});
  fetch('data/parameter-explorer.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('workflow');return r.json();}).then(record=>{
    data=record;document.getElementById('parameter-sample').textContent=data.sample_id;showParameters();render();schedule();
  }).catch(()=>{scene.textContent=t('workflow.error');play.disabled=true;document.getElementById('demo-restart').disabled=true;});
})();
