import assert from 'node:assert/strict';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium} = await import(process.env.CCAA_PLAYWRIGHT_MODULE || 'playwright');

const here = path.dirname(fileURLToPath(import.meta.url));
const base = process.env.CCAA_TEST_URL || 'http://127.0.0.1:8876';
const chosen = process.argv[2] || 'all';
const flows = chosen === 'all' ? ['mari', 'aulas-praticas', 'fast-track-infra-2026'] : [chosen];
const evidence = path.join(here, 'evidence');
await mkdir(evidence, {recursive: true});
const browser = await chromium.launch({executablePath: process.env.AGENT_BROWSER_EXECUTABLE_PATH || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome', headless: true});
const results = [];
try {
  for (const flow of flows) {
    const context = await browser.newContext({viewport: {width: 1440, height: 1050}, acceptDownloads: true});
    const page = await context.newPage();
    const errors = [];
    const external = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      requests.push(request.url());
      if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== new URL(base).origin) external.push(request.url());
    });
    await page.goto(`${base}/${flow}`);
    const staticPreview = flow === 'fast-track-infra-2026';
    let data = {options: [], today: ''};
    let item = {id: 'modelo', label: 'Prezado(a) Gestor(a),'};
    if (staticPreview) {
      assert.equal(await page.locator('input:visible, select:visible').count(), 0);
      assert.equal(await page.locator('#form').evaluate(form => form.checkValidity()), true);
      assert.equal(await page.locator('#generate').isEnabled(), true);
    } else {
    await page.locator('#record:not([disabled])').waitFor({timeout: 120000});
    const response = await context.request.get(`${base}/api/options/${flow}`);
    assert.equal(response.status(), 200);
    data = await response.json();
    item = flow === 'mari' ? data.options.find(x => x.label.toUpperCase().includes('ADIEL')) : data.options.find(x => x.id === '11815820');
    assert.ok(item, 'Registro real disponível');
    await page.locator('#record').selectOption(item.id);
    if (flow === 'mari') await page.locator('#reference-date').fill('2026-09-11');
    }
    await page.locator('#generate').focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => document.querySelector('#status').textContent.startsWith('HTML gerado.'));
    const frame = page.frameLocator('#preview');
    await frame.locator('body').filter({hasText: item.label}).waitFor();
    assert.equal(await frame.locator('body').evaluate(element => getComputedStyle(element).margin), '0px', 'A prévia mantém os estilos inline do HTML original');
    assert.equal(await page.locator('#preview').getAttribute('sandbox'), '');
    assert.equal(await page.locator('#download').getAttribute('aria-disabled'), 'false');
    const downloaded = page.waitForEvent('download');
    await page.locator('#download').click();
    const file = await downloaded;
    const output = path.join(evidence, `${flow}-downloaded.html`);
    await file.saveAs(output);
    const date = flow === 'mari' ? '2026-09-11' : data.today;
    const expectedResponse = await context.request.get(`${base}/api/render/${flow}?${new URLSearchParams(staticPreview ? {} : {id: item.id, date})}`);
    assert.equal(expectedResponse.status(), 200);
    const expected = await expectedResponse.text();
    assert.equal(await readFile(output, 'utf8'), expected, 'Download é o HTML cru, sem painel de teste');
    if (flow === 'aulas-praticas') {
      const text = await frame.locator('body').innerText();
      assert.ok(text.includes('319') && text.includes('142') && text.includes('177'));
    } else if (flow === 'mari') {
      assert.ok((await frame.locator('body').innerText()).includes('PORANGATU'));
    } else {
      const text = await frame.locator('body').innerText();
      assert.ok(text.includes('31/08') && text.includes('3,0') && text.includes('CONSEQUÊNCIA DO NÃO CUMPRIMENTO'));
      assert.equal(await frame.locator('script, input, select, form').count(), 0);
      assert.equal(await frame.locator('img').count(), 2);
      assert.equal(await frame.locator('img').evaluateAll(async images => {
        await Promise.all(images.map(image => image.decode()));
        return images.every(image => image.naturalWidth > 0 && image.src.startsWith('data:image/'));
      }), true);
      assert.equal(requests.some(url => url.includes('/api/options/')), false);
      assert.equal(await readFile(output, 'utf8'), await readFile(path.join(here, '../fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html'), 'utf8'));
    }
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Sem overflow na página desktop');
    await page.screenshot({path: path.join(evidence, `${flow}-desktop.png`), fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Sem overflow na página móvel');
    await page.screenshot({path: path.join(evidence, `${flow}-mobile.png`), fullPage: true});
    await page.setViewportSize({width: 1440, height: 1050});
    if (!staticPreview) {
    await page.locator('#record').selectOption('');
    assert.equal(await page.locator('#download').getAttribute('aria-disabled'), 'true', 'Mudança invalida download anterior');
    await page.locator('#generate').click();
    assert.equal(await page.locator('#record').evaluate(element => element.validity.valueMissing), true);
    }
    assert.deepEqual(errors, [], 'Sem erros JavaScript');
    assert.deepEqual(external, [], 'Sem requisições externas');
    results.push({flow, option_count: data.options.length, generated_id: item.id, download_matches: true, desktop_and_mobile: true, no_external_requests: true, javascript_errors: errors});
    await context.close();
  }
} finally {
  await browser.close();
}
await writeFile(path.join(evidence, `browser-${chosen}.json`), JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
