import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium} = await import(process.env.CCAA_PLAYWRIGHT_MODULE || 'playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const evidence = path.join(here, 'evidence');
const base = process.env.CCAA_TEST_URL || 'http://127.0.0.1:8876';
const flow = 'auditoria-situacao-polos';
await mkdir(evidence, {recursive: true});
const browser = await chromium.launch({headless: true, executablePath: process.env.AGENT_BROWSER_EXECUTABLE_PATH || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome'});
const context = await browser.newContext({viewport: {width: 1440, height: 1050}, acceptDownloads: true});
const page = await context.newPage();
page.setDefaultTimeout(15000);
const errors = [], external = [];
page.on('pageerror', error => errors.push(error.message));
page.on('request', request => { if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== new URL(base).origin) external.push(request.url()); });
const field = (section, name) => page.locator(`[data-section="${section}"][data-field="${name}"]`);
async function generate() {
  assert.equal(await page.locator('#form').evaluate(form => form.checkValidity()), true, 'Native validation must allow generation');
  const responsePromise = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/render/${flow}`));
  await page.locator('#generate').click();
  const response = await responsePromise;
  const html = await response.text();
  assert.equal(response.status(), 200, html);
  await page.waitForFunction(() => document.querySelector('#status').textContent.startsWith('HTML gerado.'));
  const snapshot = response.headers()['x-preview-url'];
  assert.match(snapshot, /^\/api\/preview\/[a-f0-9]+$/);
  assert.equal(await page.locator('#preview').getAttribute('src'), snapshot);
  const saved = await context.request.get(base + snapshot);
  assert.equal(await saved.text(), html);
  assert.match(saved.headers()['content-security-policy'], /sandbox/);
  return {html, snapshot, frame: page.frameLocator('#preview')};
}
try {
  await page.goto(base + '/' + flow);
  await page.locator('#record:not([disabled])').waitFor({timeout: 180000});
  const optionsResponse = await context.request.get(`${base}/api/options/${flow}`, {timeout: 180000});
  assert.equal(optionsResponse.status(), 200);
  const options = (await optionsResponse.json()).options;
  const record = options.find(item => item.label.toUpperCase().includes('LUCAS BIGHETTI'));
  assert.ok(record, 'Real portfolio from the local Master');
  const draftResponse = await context.request.get(`${base}/api/draft/${flow}?id=${record.id}`);
  const loaded = await draftResponse.json();
  assert.deepEqual(loaded.source_cycles, ['261']);
  assert.ok(loaded.draft.praticas.length && loaded.draft.agenda.length && loaded.draft.laboratorios.length);
  await page.locator('#record').selectOption(record.id);
  await page.waitForFunction(() => !document.querySelector('#consolidado-editor').disabled);
  assert.equal(await field('polos', 'polo').count(), record.polo_count);
  assert.equal(await page.locator('#ciclo').inputValue(), '261');
  assert.match(await page.locator('#source-warnings').textContent(), /261/);
  assert.equal(await field('checklist', 'nota').first().inputValue(), '');
  assert.equal(await page.locator('#prazo_praticas').inputValue(), '');
  const removedPolo = loaded.draft.polos.find(polo => loaded.warnings.some(w => w.startsWith(polo + ':')));
  assert.ok(removedPolo, 'Exercise omission of a polo referenced by source warnings');
  const removeIndex = loaded.draft.polos.indexOf(removedPolo);
  await page.locator('[data-remove="polos"]').nth(removeIndex).click();
  assert.equal(await page.locator('#reprovados_sem_retorno').inputValue(), '');
  await page.locator('#ciclo').fill('26.2');
  // All edits below are explicit QA overrides, not operational assertions.
  const keptIndex = loaded.draft.checklist.findIndex(row => row.polo !== removedPolo);
  await field('checklist', 'nota').nth(keptIndex).fill('73.5');
  await field('checklist', 'status').nth(keptIndex).fill('Revisão manual de teste');
  await field('checklist', 'observacao').nth(keptIndex).fill('<script>Teste de texto literal</script>');
  await field('checklist', 'auditor').nth(keptIndex).fill('Responsável informado manualmente — teste');
  await page.locator('#prazo_praticas').fill('2026-12-15');
  await page.locator('#prazo_auditorias').fill('2026-12-16');
  await page.locator('#reprovados_sem_retorno').fill('1');
  const result = await generate();
  const frame = result.frame;
  await frame.locator('body').filter({hasText: record.label}).waitFor();
  assert.equal(await frame.locator('body').evaluate(element => getComputedStyle(element).margin), '0px');
  assert.equal(await frame.locator('script, form, input, select').count(), 0);
  const renderedText = await frame.locator('body').innerText();
  assert.ok(renderedText.includes('26.2') && renderedText.includes('Fonte real: 261'));
  assert.ok(renderedText.includes('não atualiza nem certifica'));
  assert.ok(renderedText.includes('Revisão manual de teste') && renderedText.includes('73.5'));
  assert.ok(renderedText.includes('<script>Teste de texto literal</script>'));
  assert.ok(!renderedText.includes(removedPolo), 'Excluded polo must not leak through warning text');
  assert.ok(renderedText.includes('TOTAL INFORMADO'));
  const emailWidth = await frame.locator('table[width="820"]').evaluate(element => element.getBoundingClientRect().width);
  const viewportWidth = await page.locator('#preview').evaluate(element => element.clientWidth);
  assert.ok(viewportWidth >= emailWidth, `Desktop preview must fit the email: ${viewportWidth} < ${emailWidth}`);
  assert.ok(!result.html.includes('<script>'));
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#download').click();
  const downloaded = await downloadPromise;
  const output = path.join(evidence, 'consolidado-manual-overrides-downloaded.html');
  await downloaded.saveAs(output);
  assert.equal(await readFile(output, 'utf8'), result.html);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  await page.locator('#preview').scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.locator('.result').screenshot({path: path.join(evidence, 'consolidado-preview-desktop.png')});
  await page.screenshot({path: path.join(evidence, 'consolidado-desktop.png'), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'No mobile page overflow');
  await page.locator('#preview').scrollIntoViewIfNeeded();
  await page.locator('.result').screenshot({path: path.join(evidence, 'consolidado-preview-mobile.png')});
  await page.screenshot({path: path.join(evidence, 'consolidado-mobile.png'), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1050});
  await page.locator('#gestor').fill('Nome editado depois da geração');
  assert.equal(await page.locator('#download').getAttribute('aria-disabled'), 'true');
  assert.equal(await page.locator('#preview').getAttribute('src'), null);

  await page.locator('#record').selectOption('manual');
  await page.waitForFunction(() => !document.querySelector('#consolidado-editor').disabled && document.querySelector('#gestor').value === '');
  await page.locator('#gestor').fill('Preenchimento manual — teste');
  await page.locator('#ciclo').fill('262');
  await page.locator('#add-polos').click();
  await field('polos', 'polo').last().fill('Polo manual — teste');
  for (const section of ['checklist', 'agenda', 'praticas', 'laboratorios']) {
    await page.locator(`#add-${section}`).click();
    await field(section, 'polo').last().fill('Polo manual — teste');
  }
  await field('agenda', 'ambiente').last().fill('Ambiente informado manualmente');
  await field('agenda', 'status').last().fill('Agendada');
  await field('praticas', 'previstas').last().fill('10');
  await field('praticas', 'comprovadas').last().fill('0');
  await field('praticas', 'pendentes').last().fill('10');
  await field('laboratorios', 'parecer').last().fill('Pendente');
  await page.locator('#add-contatos').click();
  await field('contatos', 'funcao').last().fill('Contato de teste');
  await field('contatos', 'nome').last().fill('Nome informado manualmente');
  await field('contatos', 'email').last().fill('qa@example.test');
  const manualResult = await generate();
  assert.ok(manualResult.html.includes('Preenchimento manual — teste'));
  assert.ok(manualResult.html.includes('Ambiente informado manualmente'));
  assert.ok(manualResult.html.includes('mailto:qa@example.test'));
  assert.ok(manualResult.html.includes('Não informado'));
  assert.ok(!manualResult.html.includes(record.label));

  // Delay a real server response and edit while it is pending.
  let release, received;
  const reached = new Promise(resolve => { received = resolve; });
  await page.route(`**/api/render/${flow}`, async route => {
    const response = await route.fetch();
    const gate = new Promise(resolve => { release = resolve; });
    received();
    await gate;
    await route.fulfill({response});
  });
  await page.locator('#generate').click();
  await reached;
  await page.locator('#gestor').fill('Edição durante requisição');
  const oldStatus = await page.locator('#status').textContent();
  const completed = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/render/${flow}`));
  release();
  await completed;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(await page.locator('#download').getAttribute('aria-disabled'), 'true');
  assert.equal(await page.locator('#preview').getAttribute('src'), null);
  assert.equal(await page.locator('#status').textContent(), oldStatus);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  const report = {flow, options: options.length, source_cycles: loaded.source_cycles,
    loaded_polos: record.polo_count, selected_polos: record.polo_count - 1,
    real_data_loaded: true, manual_overrides: true, manual_from_scratch: true,
    excluded_polo_absent: true, source_cycle_preserved: true, literal_html_escaped: true,
    snapshot_and_download_identical: true, stale_render_blocked: true,
    desktop_and_mobile: true, no_external_requests: true, javascript_errors: errors};
  await writeFile(path.join(evidence, 'browser-consolidado.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { await browser.close(); }
