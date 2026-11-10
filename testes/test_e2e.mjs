import assert from 'node:assert/strict';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium} = await import(process.env.CCAA_PLAYWRIGHT_MODULE || 'playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const base = process.env.CCAA_TEST_URL || 'http://127.0.0.1:8876';
const chosen = process.argv[2] || 'all';
const flows = chosen === 'all' ? ['mari', 'aulas-praticas', 'fast-track-infra-2026', 'auditoria-situacao-polos'] : [chosen];
const evidence = path.join(here, 'evidence');
await mkdir(evidence, {recursive: true});
const browser = await chromium.launch({executablePath: process.env.AGENT_BROWSER_EXECUTABLE_PATH || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome', headless: true});
const results = [];
try {
 const context = await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true});
 const page = await context.newPage(); page.setDefaultTimeout(20000);
 const errors=[],external=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{requests.push(r.url());if(/^https?:/.test(r.url()) && new URL(r.url()).origin!==new URL(base).origin)external.push(r.url());});
 for(const flow of flows) {
  if(!page.url().startsWith(base))await page.goto(`${base}/${flow}`);
  else await page.locator(`[data-nav="${flow}"]`).click();
  await page.waitForURL(`${base}/${flow}`);
  const staticPreview=flow==='fast-track-infra-2026';
  let label='Agenda Fast Track Infra 2026', optionCount=0;
  if(staticPreview) {
   assert.equal(await page.locator('input:visible,select:visible').count(),0);
   assert.match(await page.locator('main').innerText(),/histórico|não é um prazo atualizado/);
  } else {
   await page.locator('#record:not([disabled])').waitFor({timeout:180000});
   const response=await context.request.get(`${base}/api/options/${flow}`);assert.equal(response.status(),200);
   const data=await response.json(); optionCount=data.options.length;
   let item=flow==='auditoria-situacao-polos'?data.options.find(x=>x.id==='manual'):data.options.find(x=>!x.label.toLowerCase().includes('manual'));
   if(flow==='aulas-praticas') {
    item=undefined;
    for(const candidate of data.options) {
     const source=await context.request.get(`${base}/api/draft/${flow}?id=${candidate.id}`);assert.equal(source.status(),200);
     const {draft}=await source.json();
     if(!draft.labs_lista.length && Object.values(draft.praticas).every(value=>value!==null)) {item=candidate;break;}
    }
   }
   assert.ok(item); label=item.label;
   await page.locator('#record').selectOption(item.id);
   if(flow==='mari') {
    await page.waitForFunction(()=>!document.querySelector('#mari-editor').disabled);
    assert.equal(await page.locator('#mari-email').inputValue(),'');
    assert.equal(await page.locator('#form').evaluate(f=>f.checkValidity()),false);
    if(!await page.locator('#mari-go').inputValue())await page.locator('#mari-go').fill('GO QA manual');
    label=await page.locator('#mari-go').inputValue();
    await page.locator('#mari-email').fill('qa@example.test');
    for(const input of await page.locator('[data-field="grupo"]').all())await input.fill('Grupo QA manual');
    for(const input of await page.locator('[data-field="date"]').all())if(!await input.inputValue())await input.fill('2026-12-01T09:00');
    await page.locator('#reference-date').fill('2026-11-10');
    await page.locator('#mari-reviewed').check();
   } else if(flow==='aulas-praticas') {
    await page.waitForFunction(()=>!document.querySelector('#aulas-editor').disabled);
    assert.equal(await page.locator('#prazo_praticas').inputValue(),'');assert.equal(await page.locator('#prazo_auditoria').inputValue(),'');
    assert.equal(await page.locator('#aulas-labs-status').inputValue(),'');
    assert.equal(await page.locator('#form').evaluate(f=>f.checkValidity()),false);
    const bypass=`${base}/api/render/${flow}?id=${item.id}`;
    const refused=await context.request.get(bypass);assert.equal(refused.status(),405);
    const missing=await context.request.post(`${base}/api/render/${flow}`,{data:{id:item.id,draft:{reviewed:true}}});assert.equal(missing.status(),400);
    await page.locator('#prazo_praticas').fill('2026-12-15');await page.locator('#prazo_auditoria').fill('2026-12-16');
    await page.locator('#aulas-labs-status').selectOption('informado');await page.locator('#aulas-add-lab').click();
    await page.locator('[data-field="nome"]').fill('Laboratório QA <manual>');await page.locator('[data-field="parecer"]').fill('Aprovado');
    await page.locator('#aulas-previstas').fill('20');await page.locator('#aulas-comprovadas').fill('5');await page.locator('#aulas-pendentes').fill('15');
    await page.locator('#aulas-reviewed').check();
   } else {
    await page.waitForFunction(()=>!document.querySelector('#consolidado-editor').disabled);
    await page.locator('#gestor').fill('Gestor QA manual');label='Gestor QA manual';
    await page.locator('#ciclo').fill('262');await page.locator('#add-polos').click();
    await page.locator('[data-section="polos"][data-field="polo"]').fill('Polo QA manual');
    await page.locator('#prazo_praticas').fill('2026-12-15');await page.locator('#prazo_auditorias').fill('2026-12-16');
   }
  }
  assert.equal(await page.locator('#form').evaluate(f=>f.checkValidity()),true);
  const responsePromise=page.waitForResponse(r=>r.url().includes(`/api/render/${flow}`) && (staticPreview||r.request().method()==='POST'));
  await page.locator('#generate').click();const response=await responsePromise;const expected=await response.text();assert.equal(response.status(),200,expected);
  await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('HTML gerado.'));
  const frame=page.frameLocator('#preview');await frame.locator('body').waitFor();
  const preview=await page.locator('#preview').getAttribute('src');
  assert.equal(await (await context.request.get(base+preview)).text(),expected,'snapshot equals POST bytes');
  if(!staticPreview)assert.match(preview,/^\/api\/preview\/[a-f0-9]+$/);
  const text=await frame.locator('body').innerText();
  if(flow==='aulas-praticas') {assert.ok(text.includes('15/12/2026')&&text.includes('16/12/2026')&&text.includes('25%'));assert.ok(!text.includes('31/05/2026')&&!text.includes('26/06/2026'));assert.ok(text.includes('Laboratório QA <manual>'));}
  if(staticPreview) {assert.ok(text.includes('31/08')&&text.includes('3,0'));assert.equal(expected,await readFile(path.join(here,'../fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html'),'utf8'));assert.equal(await frame.locator('img').evaluateAll(async images=>{await Promise.all(images.map(i=>i.decode()));return images.length===2&&images.every(i=>i.naturalWidth>0&&i.src.startsWith('data:image/'));}),true);}
  assert.equal(await frame.locator('body').evaluate(e=>getComputedStyle(e).margin),'0px');assert.equal(await page.locator('#preview').getAttribute('sandbox'),'');
  assert.equal(await frame.locator('script,input,select,form').count(),0);
  const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();const file=await downloadPromise;
  const output=path.join(evidence,`${flow}-downloaded.html`);await file.saveAs(output);assert.equal(await readFile(output,'utf8'),expected);
  for(const [size,name] of [[{width:1440,height:1050},'desktop'],[{width:390,height:844},'mobile']]) {
   await page.setViewportSize(size);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`no outer overflow ${flow} ${name}: ${await page.evaluate(()=>[innerWidth,document.documentElement.scrollWidth])}`);
   const geometry=await frame.locator('html').evaluate(element=>({width:innerWidth,content:element.scrollWidth}));
   if(name==='desktop')assert.ok(geometry.content<=geometry.width+1,`email fits desktop iframe: ${flow}`);
   else {
    assert.ok(geometry.content>geometry.width,`fixed email scrolls inside mobile iframe: ${flow}`);
    assert.ok(await frame.locator('html').evaluate(()=>{const root=document.scrollingElement;root.scrollLeft=100;const moved=root.scrollLeft>0;root.scrollLeft=0;return moved;}),'inner email horizontal scrolling works');
   }
   await page.locator('#preview').scrollIntoViewIfNeeded();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   await page.locator('.result').screenshot({path:path.join(evidence,`${flow}-preview-${name}.png`)});
   await page.screenshot({path:path.join(evidence,`${flow}-${name}.png`),fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1050});
  if(flow==='aulas-praticas') {
   for(const kind of ['success','error']) {
    let release,reached;const received=new Promise(r=>{reached=r;});const gate=new Promise(r=>{release=r;});
    await page.route(`**/api/render/${flow}`,async route=>{const actual=await route.fetch();reached();await gate;if(kind==='error')await route.fulfill({status:400,contentType:'application/json',body:'{"error":"stale error"}'});else await route.fulfill({response:actual});});
    await page.locator('#aulas-reviewed').check();await page.locator('#generate').click();await received;
    await page.locator('#prazo_praticas').fill(kind==='success'?'2026-12-17':'2026-12-18');const status=await page.locator('#status').textContent();
    const done=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith(`/api/render/${flow}`));release();await done;
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    assert.equal(await page.locator('#download').getAttribute('aria-disabled'),'true');assert.equal(await page.locator('#preview').getAttribute('src'),null);assert.equal(await page.locator('#status').textContent(),status);
    await page.unroute(`**/api/render/${flow}`);
   }
   await page.locator('#aulas-aplicaveis').uncheck();await page.locator('#aulas-labs-status').selectOption('nao_aplicavel');await page.locator('#prazo_praticas').evaluate(n=>n.value='');await page.locator('#prazo_auditoria').evaluate(n=>n.value='');await page.locator('#aulas-reviewed').check();
   assert.equal(await page.locator('#form').evaluate(f=>f.checkValidity()),true,'NA fields not required');
   const na=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith(`/api/render/${flow}`));await page.locator('#generate').click();assert.equal((await na).status(),200);
   await page.waitForFunction(()=>document.querySelector('#download').getAttribute('aria-disabled')==='false');
  }
  if(!staticPreview) {await page.locator('#record').selectOption('');assert.equal(await page.locator('#download').getAttribute('aria-disabled'),'true');assert.equal(await page.locator('#preview').getAttribute('src'),null);}
  results.push({flow,options:optionCount,label,snapshot_download_bytes:true,desktop_mobile:true,manual_supplements:!staticPreview,stale_real_roundtrip:flow==='aulas-praticas'});
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 assert.deepEqual(requests.filter(url=>/api\/render\/(mari|aulas-praticas|auditoria-situacao-polos)\?/.test(url)),[],'Browser generation never places manual data in query strings');
 await writeFile(path.join(evidence,`browser-${chosen}.json`),JSON.stringify({results,javascript_errors:errors,external_requests:external},null,2));
 console.log(JSON.stringify({results,javascript_errors:errors,external_requests:external},null,2));
} finally {await browser.close();}
