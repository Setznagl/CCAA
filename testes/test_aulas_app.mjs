import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';
const source = await readFile(new URL('./web/aulas.js', import.meta.url), 'utf8').catch(() => '');
const flush = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor(tag='div') { this.tagName=tag;this.children=[];this.listeners={};this.dataset={};this.attrs={};this.value='';this.checked=false;this.selectedOptions=[{textContent:'Polo A'}]; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; }
  add(n) { this.append(n); }
  setAttribute(k,v) { this.attrs[k]=v; }
  removeAttribute(k) { delete this.attrs[k];delete this[k]; }
  addEventListener(t,f) { this.listeners[t]=f; }
  reportValidity() { return true; }
}
const all = root => [root,...root.children.flatMap(all)];
const draft = () => ({praticas:{previstas:null,comprovadas:0,pendentes:null},praticas_aplicaveis:true,labs_lista:[],labs_status:'',prazo_praticas:'',prazo_auditoria:''});
const json = data => ({ok:true,json:async()=>data});
const rendered = text => ({ok:true,text:async()=>text,headers:{get:()=>'/api/preview/abc'}});
async function setup() {
  const root=new Element(), pending=[],blobs=[],revoked=[],window=new Element();
  for(const id of ['form','record','record-controls','record-label','date-control','reference-date','generate','status','download','preview','result-label']) {const n=new Element();n.id=id;root.append(n);}
  const find=id=>all(root).find(n=>n.id===id);
  const context=vm.createContext({document:{body:{dataset:{flow:'aulas-praticas'}},querySelector:s=>find(s.slice(1)),querySelectorAll:()=>[],createElement:t=>new Element(t)},window,Blob,URLSearchParams,Option:Element,URL:{createObjectURL(b){blobs.push(b);return 'blob:test';},revokeObjectURL(u){revoked.push(u);}},fetch:(url,options)=>new Promise((resolve,reject)=>pending.push({url,options,resolve,reject}))});
  vm.runInContext(await readFile(new URL('./web/app.js',import.meta.url),'utf8'),context);
  vm.runInContext(source,context);
  assert.equal(pending.length,1,'Dedicated editor must initialize');
  pending[0].resolve(json({options:[]}));await flush();
  const app={find,pending,blobs,revoked,window,edit(n,value,type='input'){if(n.type==='checkbox')n.checked=value;else n.value=value;return find('form').listeners[type]({target:n});},submit(){return find('form').listeners.submit({preventDefault(){}});}};
  const load=app.edit(find('record'),'A','change');
  pending.at(-1).resolve(json({draft:{praticas:{previstas:null,comprovadas:0,pendentes:null},praticas_aplicaveis:true,labs_lista:[],labs_status:'',prazo_praticas:'',prazo_auditoria:''},warnings:['Ausência não comprova auditoria']}));await load;
  return app;
}
test('obsolete drafts cannot overwrite new polo fields or warnings',async()=>{
 const a=await setup();
 const old=a.edit(a.find('record'),'A','change'),r=a.pending.at(-1);
 const current=a.edit(a.find('record'),'B','change'),n=a.pending.at(-1);
 n.resolve(json({draft:{...draft(),prazo_praticas:'2026-12-19'},warnings:['Atual']}));await current;
 r.resolve(json({draft:draft(),warnings:['ERRADO']}));await old;
 assert.equal(a.find('prazo_praticas').value,'2026-12-19');assert.equal(a.find('source-warnings').textContent,'Atual');
});
test('older render after newer success preserves captured polo label and bytes',async()=>{
 const a=await setup();const old=a.submit(),r=a.pending.at(-1);
 a.edit(a.find('prazo_praticas'),'2026-12-20');const current=a.submit(),n=a.pending.at(-1);
 a.find('record').value='B';a.find('record').selectedOptions=[{textContent:'Polo B'}];
 n.resolve(rendered('new'));await current;r.resolve(rendered('old'));await old;
 assert.equal(a.find('result-label').textContent,'Polo A');assert.equal(await a.blobs[0].text(),'new');assert.equal(a.blobs.length,1);assert.equal(a.find('download').download,'ccaa-aulas-praticas-A.html');
});
test('each editable field invalidates pending generation, confirmation and preview',async()=>{
 const a=await setup();
 for(const id of ['prazo_praticas','prazo_auditoria','aulas-previstas','aulas-comprovadas','aulas-pendentes','aulas-aplicaveis','aulas-labs-status','aulas-reviewed']) {
  const p=a.submit(),r=a.pending.at(-1);a.edit(a.find(id),a.find(id).type==='checkbox'?false:'');const status=a.find('status').textContent;r.resolve(rendered('stale'));await p;
  assert.equal(a.find('download').attrs['aria-disabled'],'true');assert.equal(a.find('preview').src,undefined);assert.equal(a.find('status').textContent,status);assert.equal(a.find('generate').disabled,false);
 }
});
test('current HTTP errors are actionable and invalid snapshot addresses never enable download',async()=>{
 const a=await setup();const p=a.submit();a.pending.at(-1).resolve({ok:false,json:async()=>({error:'Current error'})});await p;
 assert.equal(a.find('status').textContent,'Current error');assert.equal(a.find('status').attrs.role,'alert');assert.equal(a.find('generate').disabled,false);
 const retry=a.submit();a.pending.at(-1).resolve({...rendered('wrong'),headers:{get:()=>'/external'}});await retry;assert.equal(a.find('download').href,undefined);assert.equal(a.blobs.length,0);
});
test('empty supplements remain inputs and POST uses opaque snapshot, editing invalidates bytes',async()=>{
  const a=await setup();
  for(const id of ['prazo_praticas','prazo_auditoria','aulas-previstas','aulas-pendentes'])assert.equal(a.find(id).value,'');
  assert.equal(a.find('aulas-comprovadas').value,0);
  const p=a.submit(),r=a.pending.at(-1);
  assert.equal(r.url,'/api/render/aulas-praticas');assert.equal(r.options.method,'POST');
  assert.equal(JSON.parse(r.options.body).draft.praticas.previstas,null);
  r.resolve(rendered('exact'));await p;
  assert.equal(a.find('preview').src,'/api/preview/abc');assert.equal(await a.blobs[0].text(),'exact');
  a.edit(a.find('prazo_praticas'),'2026-12-01');
  assert.equal(a.find('preview').src,undefined);assert.equal(a.find('download').href,undefined);assert.equal(a.revoked.length,1);
});
for(const outcome of ['success','error','http-error'])test(`stale ${outcome} cannot replace a newer pending/result, including finally`,async()=>{
 const a=await setup();
 const old=a.submit(),r=a.pending.at(-1);a.edit(a.find('prazo_praticas'),'2026-12-01');const current=a.submit(),n=a.pending.at(-1),status=a.find('status').textContent;
 if(outcome==='success')r.resolve(rendered('old'));else if(outcome==='error')r.reject(new Error('old'));else r.resolve({ok:false,json:async()=>({error:'old'})});await old;
 assert.equal(a.find('status').textContent,status);assert.equal(a.find('generate').disabled,true);
 n.resolve(rendered('new'));await current;assert.equal(await a.blobs[0].text(),'new');
 const hidden=a.submit();a.window.listeners.pagehide();a.pending.at(-1).resolve(rendered('hidden'));await hidden;assert.equal(a.find('download').href,undefined);
});
