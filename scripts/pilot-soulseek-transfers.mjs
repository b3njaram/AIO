// Instance-local slskd transfer adapter. The existing Jobbi Music routes
// enforce administrator authentication and rate limiting; no new HTTP listener.
const BASE='http://slskd:5030/api/v0';
const AUDIO=/\.(mp3|flac|m4a|aac|ogg|opus|wav|aiff|alac)$/i;
export function enabled(env=process.env){
  return env.JOBBI_LOCAL_SOULSEEK==='true'&&env.SLSKD_URL==='http://slskd:5030'&&/^[a-f0-9]{48}$/.test(env.SLSKD_API_KEY||'');
}
export function validate(body){
  const {username,filename,size,artist,title}=body||{};
  if(typeof username!=='string'||!username.trim()||username.length>100||/[\x00-\x1f\x7f/\\]/.test(username)||
     typeof filename!=='string'||filename.length>900||/[\x00-\x1f\x7f]/.test(filename)||!AUDIO.test(filename)||filename.split(/[\\/]/).some(x=>x==='..'||x==='.')||
     !Number.isSafeInteger(size)||size<1024||size>2147483648||
     typeof artist!=='string'||!artist.trim()||artist.length>180||typeof title!=='string'||!title.trim()||title.length>180)
    throw Error('Invalid selected audio transfer');
  return {username:username.trim(),filename,size};
}
async function call(path,options={},env=process.env,fetcher=fetch){
  if(!enabled(env))throw Error('Local provider unavailable');
  const response=await fetcher(BASE+path,{...options,redirect:'error',headers:{'X-API-Key':env.SLSKD_API_KEY,'Content-Type':'application/json'},signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw Error('Local provider rejected request');
  // Bound actual streamed bytes, not just Content-Length.
  const reader=response.body.getReader();let bytes=0;const chunks=[];
  try{while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>1000000)throw Error('Transfer response too large');chunks.push(Buffer.from(value))}}
  finally{await reader.cancel().catch(()=>{});reader.releaseLock()}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
export async function enqueue(body,env=process.env,fetcher=fetch){
  const file=validate(body);
  const result=await call('/transfers/downloads/'+encodeURIComponent(file.username),{method:'POST',body:JSON.stringify([{filename:file.filename,size:file.size}])},env,fetcher);
  if(!Array.isArray(result.enqueued)||result.enqueued.length!==1||!Array.isArray(result.failed)||result.failed.length!==0)throw Error('Provider did not confirm queue acceptance');
  const item=result.enqueued[0];
  if(item.filename!==file.filename||item.username!==file.username||typeof item.id!=='string'||!/^[a-f0-9-]{36}$/i.test(item.id))throw Error('Unexpected queue result');
  return {id:item.id,queued:true,libraryImported:false};
}
export function normalize(rows){
  if(!Array.isArray(rows))throw Error('Unexpected transfer list');
  const out=[];
  for(const peer of rows){
    if(!Array.isArray(peer?.directories))continue;
    for(const dir of peer.directories){
      if(!Array.isArray(dir?.files))continue;
      for(const f of dir.files){
        if(typeof f?.filename!=='string'||f.filename.length>900||!AUDIO.test(f.filename))continue;
        const percentage=Number.isFinite(f.percentComplete)?Math.max(0,Math.min(100,Math.round(f.percentComplete))):0;
        const state=typeof f.state==='string'?f.state.slice(0,80):'Unknown';
        out.push({id:typeof f.id==='string'?f.id.slice(0,64):'',filename:f.filename,username:typeof peer.username==='string'?peer.username.slice(0,100):'',state,percentage,libraryImported:false});
        if(out.length>=120)return out;
      }
    }
  }
  return out;
}
export async function list(env=process.env,fetcher=fetch){return normalize(await call('/transfers/downloads',{},env,fetcher))}
