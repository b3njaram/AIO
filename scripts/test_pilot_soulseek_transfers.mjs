import assert from 'node:assert/strict';
import {enabled,validate,enqueue,list} from './pilot-soulseek-transfers.mjs';
const env={JOBBI_LOCAL_SOULSEEK:'true',SLSKD_URL:'http://slskd:5030',SLSKD_API_KEY:'a'.repeat(48)};
const item={username:'fixture-peer',filename:'Fixture\\owned.wav',size:4096,artist:'Fixture',title:'Owned test audio'};
const id='12345678-1234-1234-1234-123456789abc';
assert(enabled(env));assert(!enabled({...env,SLSKD_URL:'https://other.invalid'}));
for(const change of [{filename:'../owned.wav'},{filename:'not-audio.exe'},{username:'x/y'},{size:0}])assert.throws(()=>validate({...item,...change}));
let called=0;
const fake=async(url,opt)=>{
  called++;assert.equal(url,'http://slskd:5030/api/v0/transfers/downloads/fixture-peer');
  assert.equal(opt.headers['X-API-Key'],env.SLSKD_API_KEY);
  assert.equal(opt.redirect,'error');assert.deepEqual(JSON.parse(opt.body),[{filename:item.filename,size:item.size}]);
  return new Response(JSON.stringify({enqueued:[{...item,id}],failed:[]}),{status:201});
};
assert.deepEqual(await enqueue(item,env,fake),{id,queued:true,libraryImported:false});assert.equal(called,1);
await assert.rejects(enqueue(item,env,async()=>new Response(JSON.stringify({enqueued:[],failed:[{}]}),{status:201})));
await assert.rejects(enqueue(item,env,async()=>new Response('x'.repeat(1000001),{status:201})));
const result=await list(env,async(url,opt)=>{
 assert.equal(url,'http://slskd:5030/api/v0/transfers/downloads');
 return new Response(JSON.stringify([{username:item.username,directories:[{files:[{...item,id,state:'InProgress',percentComplete:42,exception:'private details'}]}]}]));
});
assert.equal(result[0].percentage,42);assert.equal(result[0].libraryImported,false);assert(!JSON.stringify(result).includes('private details'));
console.log('PASS local selected-file transfer contract; no external network');
