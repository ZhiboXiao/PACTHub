/* Compact linear MIPs -> exact integer summed-area tables -> calibrated ROI means. */
'use strict';
const cache=new Map(), pending=new Map();
async function loadSeries(id,source){
  if(cache.has(id))return cache.get(id);
  if(pending.has(id))return pending.get(id);
  const task=(async()=>{
    const url=new URL(source.url,new URL('../../',self.location.href));url.searchParams.set('v',source.sha256.slice(0,12));
    const response=await fetch(url);
    if(!response.ok)throw Error('MIP_FETCH');
    const packed=await response.arrayBuffer();
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',packed)),v=>v.toString(16).padStart(2,'0')).join('');
    if(hash!==source.sha256)throw Error('MIP_HASH');
    const buffer=await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    const header=new DataView(buffer);
    const magic=header.getUint32(0,true),flags=header.getUint32(16,true);
    const quantized=magic===0x324d4150&&flags===8;
    if(!quantized&&(magic!==0x314d4150||flags!==1))throw Error('MIP_FORMAT');
    const n=header.getUint32(4,true),h=header.getUint32(8,true),w=header.getUint32(12,true),size=w*h,stride=w+1;
    const start=quantized?36:20,bytes=quantized?1:4;
    const scale=quantized?header.getFloat64(20,true):1,offset=quantized?header.getFloat64(28,true):0;
    if(JSON.stringify([n,h,w])!==JSON.stringify(source.shape_tyx)||buffer.byteLength!==start+size*(bytes*n+1))throw Error('MIP_SIZE');
    if(!Number.isFinite(scale)||scale<=0||!Number.isFinite(offset)||(quantized&&size*255>0xffffffff))throw Error('MIP_SCALE');
    postMessage({type:'indexing',series:id});
    const pixels=quantized?new Uint8Array(buffer,start,size*n):new Float32Array(buffer,start,size*n);
    const valid=new Uint8Array(buffer,start+size*n*bytes,size);
    const count=new Uint32Array((w+1)*(h+1)),sums=[];
    for(let y=0;y<h;y++){
      let row=0;
      for(let x=0;x<w;x++){row+=valid[y*w+x];count[(y+1)*stride+x+1]=count[y*stride+x+1]+row;}
    }
    for(let t=0;t<n;t++){
      const sum=quantized?new Uint32Array((w+1)*(h+1)):new Float64Array((w+1)*(h+1)),frameOffset=t*size;
      for(let y=0;y<h;y++){
        let row=0;
        for(let x=0;x<w;x++){
          const p=y*w+x,v=pixels[frameOffset+p];
          if(!Number.isFinite(v))throw Error('MIP_NONFINITE');
          row+=valid[p]?v:0;
          sum[(y+1)*stride+x+1]=sum[y*stride+x+1]+row;
        }
      }
      sums.push(sum);
    }
    const result={n,h,w,stride,count,sums,scale,offset};cache.set(id,result);return result;
  })();
  pending.set(id,task);
  try{return await task;}finally{pending.delete(id);}
}
function rectangle(sum,stride,[x0,y0,x1,y1]){
  return sum[y1*stride+x1]-sum[y0*stride+x1]-sum[y1*stride+x0]+sum[y0*stride+x0];
}
self.onmessage=async({data})=>{
  try{
    if(data.type==='load'){
      const a=await loadSeries(data.series,data.source);
      postMessage({type:'ready',series:data.series,width:a.w,height:a.h,frames:a.n});
    }else if(data.type==='query'){
      const a=cache.get(data.series);if(!a)throw Error('MIP_NOT_READY');
      const results=data.rois.map(roi=>{
        const [x0,y0,x1,y1]=roi.bounds;
        if(!roi.bounds.every(Number.isInteger)||x0<0||y0<0||x1>a.w||y1>a.h||x0>=x1||y0>=y1)throw Error('ROI_BOUNDS');
        const count=rectangle(a.count,a.stride,roi.bounds);
        const mean=a.sums.map(sum=>count?rectangle(sum,a.stride,roi.bounds)/count*a.scale+a.offset:null);
        const relative=mean.map(v=>mean[0]>0&&v!==null?v/mean[0]:null);
        return {id:roi.id,pixel_count:count,valid_fraction:count/((x1-x0)*(y1-y0)),mean_linear:mean,relative_mean:relative};
      });
      postMessage({type:'result',series:data.series,revision:data.revision,results});
    }
  }catch(error){postMessage({type:'error',series:data.series,message:error.message});}
};
