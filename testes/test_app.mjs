import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';
const source=await readFile(new URL('./web/app.js',import.meta.url),'utf8');
for(const flow of ['mari','aulas-praticas','auditoria-situacao-polos'])test(`${flow} belongs to dedicated script, no legacy listeners`,()=>{
 vm.runInNewContext(source,{document:{body:{dataset:{flow}},querySelector(){throw Error('Unexpected legacy listener');}}});
});
async function staticApp() {
 const nodes=new Map(),pending=[],blobs=[];
 for(const id of ['form','record','reference-date','generate','status','download','preview','result-label','record-label','date-control'])nodes.set('#'+id,{value:'',textContent:'',listeners:{},attrs:{},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this[k];delete this.attrs[k];},addEventListener(t,f){this.listeners[t]=f;},reportValidity(){return true;}});
 const window={addEventListener(t,f){this[t]=f;}};
 for(const id of ['record','reference-date'])Object.defineProperty(nodes.get('#'+id),'value',{get(){throw Error('Static model must not read fields');}});
 vm.runInNewContext(source,{document:{body:{dataset:{flow:'fast-track-infra-2026'}},querySelector:id=>nodes.get(id),querySelectorAll:()=>[]},window,URLSearchParams,Blob,URL:{createObjectURL(b){blobs.push(b);return 'blob:test';},revokeObjectURL(){}},fetch(url){assert.ok(!url.includes('/options/'));return new Promise((resolve,reject)=>pending.push({url,resolve,reject}));}});
 return {nodes,pending,blobs,window,submit:()=>nodes.get('#form').listeners.submit({preventDefault(){}})};
}
test('Fast Track remains static, exact download bytes and snapshot label',async()=>{
 const a=await staticApp(),p=a.submit();assert.equal(a.pending[0].url,'/api/render/fast-track-infra-2026?');
 a.pending[0].resolve({ok:true,text:async()=>'<html>Static</html>'});await p;
 assert.equal(await a.blobs[0].text(),'<html>Static</html>');assert.equal(a.nodes.get('#download').attrs['aria-disabled'],'false');assert.equal(a.nodes.get('#result-label').textContent,'Agenda Fast Track Infra 2026');
});
test('Fast Track ignores stale errors/finally after navigation and allows current error retry',async()=>{
 const a=await staticApp(),p=a.submit();a.window.pagehide();a.pending[0].reject(Error('stale'));await p;assert.notEqual(a.nodes.get('#status').textContent,'stale');
 const current=a.submit();a.pending[1].reject(Error('current'));await current;assert.equal(a.nodes.get('#status').textContent,'current');assert.equal(a.nodes.get('#generate').disabled,false);
});
