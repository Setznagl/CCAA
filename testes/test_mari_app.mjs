import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';
const source = await readFile(new URL('./web/mari.js', import.meta.url), 'utf8').catch(() => '');
const flush = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.listeners={}; this.dataset={}; this.attrs={}; this.value=''; this.checked=false; this.textContent=''; }
  append(...nodes) { for(const n of nodes) n.parent=this; this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; }
  add(n) { this.append(n); }
  setAttribute(k,v) { this.attrs[k]=v; }
  removeAttribute(k) { delete this.attrs[k]; delete this[k]; }
  addEventListener(t,f) { this.listeners[t]=f; }
  reportValidity() { return true; }
}
const all = root => [root,...root.children.flatMap(all)];
const json = data => ({ok:true,json:async()=>data});
const rendered = (text='new',url='/api/preview/abc') => ({ok:true,text:async()=>text,headers:{get:()=>url}});
const draft = () => ({label:'GO A',email:'',reviewed:false,rows:[
  {id:'1',polo:'Polo A',laboratorio:'Lab 1',date:'2026-11-01T09:00',grupo:'',selected:true},
  {id:'2',polo:'Polo A',laboratorio:'Lab 2',date:'2026-11-03T10:00',grupo:'',selected:true},
  {id:'3',polo:'Polo B',laboratorio:'Lab 3',date:'',grupo:'',selected:true}]});
async function setup() {
  const root=new Element();
  for(const id of ['form','record','record-controls','record-label','date-control','reference-date','generate','status','download','preview','result-label']) { const n=new Element();n.id=id;root.append(n); }
  const find=id=>all(root).find(n=>n.id===id), pending=[],blobs=[],revoked=[],window=new Element();
  const context = vm.createContext({
    document:{body:{dataset:{flow:'mari'}},querySelector:s=>find(s.slice(1)),querySelectorAll:()=>[],createElement:t=>new Element(t)},
    window,Blob,URLSearchParams,Option:function(text,value){const n=new Element('option');n.textContent=text;n.value=value;return n;},
    URL:{createObjectURL(b){blobs.push(b);return `blob:${blobs.length}`;},revokeObjectURL(u){revoked.push(u);}},
    fetch:(url,options)=>new Promise((resolve,reject)=>pending.push({url,options,resolve,reject})),
  });
  vm.runInContext(await readFile(new URL('./web/app.js', import.meta.url), 'utf8'), context);
  vm.runInContext(source, context);
  assert.equal(pending.length,1,'Mari must initialize its dedicated review editor');
  assert.equal(find('reference-date').disabled,true,'reference date must not invalidate initial source loading');
  pending[0].resolve(json({today:'2026-11-10',options:[{id:'A',label:'GO A',polo_count:2},{id:'B',label:'Revisão manual',polo_count:1}]})); await flush();
  const app={find,pending,blobs,revoked,window,controls:()=>all(root).filter(n=>n.tagName==='input'),
    fields:field=>all(root).filter(n=>n.dataset.field===field),
    edit(node,value,type='input'){ if(node.type==='checkbox') node.checked=value;else node.value=value;return find('form').listeners[type]({target:node}); },
    select(id){return this.edit(find('record'),id,'change');},
    submit(){return find('form').listeners.submit({preventDefault(){}});}};
  const load=app.select('A');pending.at(-1).resolve(json({draft:draft(),source_cycles:['262'],warnings:['Todas as datas; sem filtro de semana']}));await load;
  return app;
}
test('review form preserves every lab/date, distinct poles and empty supplements; only POST carries manual data',async()=>{
  const app=await setup();
  assert.equal(app.fields('date').length,3);
  assert.equal(app.fields('grupo').length,2,'one economic group input per distinct polo');
  assert.equal(app.find('mari-email').value,'');
  assert.equal(app.find('mari-reviewed').checked,false);
  assert.match(app.find('source-warnings').textContent,/262/);
  assert.match(app.find('mari-selection-count').textContent,/2 polo/);
  app.edit(app.find('mari-go'),'GO <Manual>');app.edit(app.find('mari-email'),'go@example.org');
  for(const field of app.fields('grupo')) app.edit(field,'Grupo <Manual>');
  app.edit(app.find('mari-reviewed'),true);
  const request=app.submit(),sent=app.pending.at(-1);
  assert.equal(sent.url,'/api/render/mari');assert.equal(sent.options.method,'POST');
  const body=JSON.parse(sent.options.body);
  assert.equal(body.draft.rows.length,3);assert.equal(body.draft.rows[1].date,'2026-11-03T10:00');
  assert.equal(body.draft.rows[1].grupo,'Grupo <Manual>');assert.equal(body.draft.reviewed,true);
  assert.equal(body.date,'2026-11-10');assert.equal(body.draft.email,'go@example.org');
  sent.resolve(rendered('<html>exact</html>'));await request;
  assert.equal(app.find('preview').src,'/api/preview/abc');assert.equal(await app.blobs[0].text(),'<html>exact</html>');
  assert.equal(app.find('result-label').textContent,'GO <Manual>');
  app.edit(app.fields('selected')[2],false,'change');
  assert.equal(app.fields('date')[2].disabled,true);assert.equal(app.find('mari-reviewed').checked,false);
  assert.equal(app.find('preview').src,undefined);assert.equal(app.find('download').href,undefined);assert.equal(app.revoked.length,1);
});
for(const outcome of ['success','error','http-error']) test(`every input invalidates stale ${outcome}, including catch and finally`,async()=>{
  const app=await setup();
  for(const field of [...app.controls(),app.find('reference-date')]) {
    const old=app.submit(),response=app.pending.at(-1);
    app.edit(field,field.type==='checkbox'?field.checked:field.value);
    const current=app.submit(),currentResponse=app.pending.at(-1),message=app.find('status').textContent;
    if(outcome==='success')response.resolve(rendered('old'));
    if(outcome==='error')response.reject(new Error('old error'));
    if(outcome==='http-error')response.resolve({ok:false,json:async()=>({error:'old HTTP error'})});
    await old;
    assert.equal(app.find('status').textContent,message);assert.equal(app.find('generate').disabled,true);
    assert.equal(app.find('download').attrs['aria-disabled'],'true');
    currentResponse.resolve(rendered());await current;
  }
});
test('old draft and render cannot overwrite a new selection or revive after pagehide',async()=>{
  const app=await setup();
  const oldLoad=app.select('A'),oldResponse=app.pending.at(-1);
  const newLoad=app.select('B');app.pending.at(-1).resolve(json({draft:{...draft(),label:'Novo'},warnings:['Atual'],source_cycles:['262']}));await newLoad;
  oldResponse.resolve(json({draft:draft(),warnings:['WRONG'],source_cycles:['261']}));await oldLoad;
  assert.equal(app.find('mari-go').value,'Novo');assert.doesNotMatch(app.find('source-warnings').textContent,/WRONG/);
  const old=app.submit(),response=app.pending.at(-1);app.edit(app.find('mari-go'),'Atual');
  const current=app.submit();app.pending.at(-1).resolve(rendered());await current;
  response.resolve(rendered('old'));await old;assert.equal(app.find('result-label').textContent,'Atual');
  const hidden=app.submit();app.window.listeners.pagehide();app.pending.at(-1).resolve(rendered('hidden'));await hidden;
  assert.equal(app.find('download').href,undefined);
});
