import assert from 'node:assert/strict';
import {mkdir, readFile} from 'node:fs/promises';
const {chromium} = await import(process.env.CCAA_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.CCAA_TEST_URL || 'http://127.0.0.1:8878';
const evidence = process.env.CCAA_EVIDENCE || '/opt/data/cache/scratch/ccaa-gerencial-evidence';
await mkdir(evidence, {recursive: true});
const browser = await chromium.launch({headless: true,
  executablePath: process.env.AGENT_BROWSER_EXECUTABLE_PATH || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome'});
try {
  const context = await browser.newContext({viewport: {width: 1440, height: 1050}, acceptDownloads: true});
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  const errors = [], external = [], results = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== base) external.push(request.url());
  });
  for (const flow of ['mari', 'aulas-praticas', 'auditoria-situacao-polos', 'fast-track-infra-2026']) {
    await page.goto(base + '/' + flow);
    const fixed = flow === 'fast-track-infra-2026';
    let chosen;
    if (fixed) {
      assert.equal(await page.locator('input:visible,select:visible').count(), 0);
    } else {
      await page.locator('#record:not([disabled])').waitFor();
      const options = (await (await context.request.get(base + '/api/options/' + flow)).json()).options;
      const candidates = options.filter(o => o.id !== 'manual').sort((a, b) => b.polo_count - a.polo_count);
      for (const candidate of candidates.slice(0, 100)) {
        const data = await (await context.request.get(`${base}/api/draft/${flow}?id=${candidate.id}`)).json();
        if (flow === 'mari' && candidate.polo_count > 1 && data.draft.destinatarios.some(r => !r.academico_nome)) {
          chosen = {candidate, data}; break;
        }
        if (flow === 'aulas-praticas' || (flow === 'auditoria-situacao-polos' && candidate.polo_count <= 3 && data.draft.agenda.some(r => r.status.includes('data agendada como referência')))) {
          chosen = {candidate, data}; break;
        }
      }
      assert.ok(chosen, 'representative source record exists');
      await page.locator('#record').selectOption(chosen.candidate.id);
      await page.locator('#recipient-review').waitFor();
      assert.equal(await page.locator('#step-panel-1').isHidden(), true);
      if (flow === 'mari') {
        assert.equal(await page.locator('#mari-email').count(), 0, 'no obsolete GO email field');
        assert.ok((await page.locator('#mari-go').inputValue()).length);
        assert.ok(await page.locator('[data-field=grupo]').evaluateAll(fields => fields.every(f => f.value)));
        assert.equal(await page.locator('[data-field=date]').count(), chosen.data.draft.rows.length);
      }
      if (flow === 'auditoria-situacao-polos') {
        assert.deepEqual(await page.locator('[data-section=agenda][data-field=data]').evaluateAll(fields => fields.map(f => f.value)),
          chosen.data.draft.agenda.map(row => row.data), 'source dates reach native date inputs');
        assert.deepEqual(await page.locator('[data-section=agenda][data-field=status]').evaluateAll(fields => fields.map(f => f.value)),
          chosen.data.draft.agenda.map(row => row.status), 'date provenance reaches the form');
      }
      const missingAcademics = page.locator('#recipient-review select');
      const count = await missingAcademics.count();
      if (count) assert.equal(await page.locator('#form').evaluate(f => f.checkValidity()), false);
      for (let index = 0; index < count; index++) await missingAcademics.nth(index).selectOption(chosen.data.auditores[index % chosen.data.auditores.length].nome);
      if (flow === 'mari') {
        const polo = chosen.data.draft.destinatarios.find(r => !r.academico_nome)?.polo;
        if (polo) {
          const occurrenceIds = chosen.data.draft.rows.filter(r => r.polo === polo).map(r => r.id);
          const selectedChoice = await page.locator('[data-recipient-polo]').evaluateAll((sections, polo) => {
            const section = sections.find(s => s.dataset.recipientPolo === polo);
            return section.querySelector('select').value;
          }, polo);
          for (const id of occurrenceIds) await page.locator('#mari-selected-' + id).uncheck();
          assert.equal(await page.locator('[data-recipient-polo]').evaluateAll((sections, polo) => {
            const section = sections.find(s => s.dataset.recipientPolo === polo);
            return section.hidden && section.disabled;
          }, polo), true);
          for (const id of occurrenceIds) await page.locator('#mari-selected-' + id).check();
          assert.equal(await page.locator('[data-recipient-polo]').evaluateAll((sections, polo) => {
            const section = sections.find(s => s.dataset.recipientPolo === polo);
            return section.querySelector('select').value;
          }, polo), selectedChoice);
        }
      }
      for (const input of await page.locator('#recipient-review input').all()) {
        if (await input.getAttribute('required') !== null) {
          const field = await input.getAttribute('data-recipient-field');
          await input.fill(field.includes('email') ? 'qa@example.test' : 'Gestor QA');
        }
      }
      if (flow === 'mari') {
        for (const input of await page.locator('[data-field=date]').all()) if (!await input.inputValue()) await input.fill('2026-12-01T09:00');
        await page.locator('#mari-reviewed').check();
      } else if (flow === 'aulas-praticas') {
        await page.locator('#prazo_praticas').fill('2026-12-15');
        await page.locator('#prazo_auditoria').fill('2026-12-16');
        for (const id of ['previstas', 'comprovadas', 'pendentes']) {
          if (!await page.locator('#aulas-' + id).inputValue()) await page.locator('#aulas-' + id).fill('0');
        }
        if (!await page.locator('#aulas-labs-status').inputValue()) await page.locator('#aulas-labs-status').selectOption('nao_aplicavel');
        for (const input of await page.locator('#aulas-editor [data-field]').all()) if (!await input.inputValue()) await input.fill('Revisão QA manual');
        await page.locator('#aulas-reviewed').check();
      } else if (chosen.data.draft.contatos.length) {
        await page.locator('[data-section=contatos][data-field=telefone]').first().fill('123456789');
      }
    }
    assert.equal(await page.locator('#form').evaluate(f => f.checkValidity()), true, flow + ' valid form');
    const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === '/api/render/' + flow);
    await page.locator('#generate').click();
    const response = await responsePromise;
    const html = await response.text();
    assert.equal(response.status(), 200, html);
    if (flow === 'auditoria-situacao-polos') {
      const reference = chosen.data.draft.agenda.find(row => row.status.includes('data agendada como referência'));
      assert.ok(reference.data, 'reference date is filled');
      assert.ok(html.includes(reference.data) && html.includes(reference.status), 'date and provenance reach the generated email');
    }
    await page.waitForFunction(() => document.querySelector('#download').getAttribute('aria-disabled') === 'false');
    if (!fixed) {
      const payload = response.request().postDataJSON();
      assert.equal(response.request().method(), 'POST');
      assert.ok(!response.url().includes('?'), 'manual data never in URL');
      assert.ok(payload.draft.destinatarios.every(r => r.academico_nome && r.academico_email));
      if (flow === 'mari') assert.equal(new Set(payload.draft.destinatarios.map(r => r.polo)).size, chosen.candidate.polo_count);
      if (flow === 'auditoria-situacao-polos' && chosen.data.draft.contatos.length) {
        assert.equal(payload.draft.contatos[0].origem, chosen.data.draft.contatos[0].origem, 'editing retains source contact identity');
        assert.equal(payload.draft.contatos[0].telefone, '123456789');
      }
      const rejected = structuredClone(payload); rejected.draft.destinatarios[0].academico_nome = 'AUDITOR NAO CADASTRADO';
      assert.equal((await context.request.post(base + '/api/render/' + flow, {data: rejected})).status(), 400);
      const snapshot = response.headers()['x-preview-url'];
      assert.equal(await (await context.request.get(base + snapshot)).text(), html);
    } else {
      assert.equal(html, await readFile(new URL('../fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html', import.meta.url), 'utf8'));
    }
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#download').click(); const download = await downloadPromise;
    await download.saveAs(`${evidence}/${flow}.html`);
    assert.equal(await readFile(`${evidence}/${flow}.html`, 'utf8'), html);
    for (const [width, height] of [[1440, 1050], [390, 844]]) {
      await page.setViewportSize({width, height});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await page.locator('#recipient-review').count().then(async n => {if (n) await page.locator('#recipient-review').scrollIntoViewIfNeeded();});
      await page.screenshot({path: `${evidence}/${flow}-${width}.png`});
    }
    await page.setViewportSize({width: 1440, height: 1050});
    if (flow === 'mari') {
      await page.locator('[data-field=grupo]').first().fill('Revisão QA');
      assert.equal(await page.locator('#download').getAttribute('aria-disabled'), 'true');
      assert.equal(await page.locator('#preview').getAttribute('src'), null);
      assert.equal(await page.locator('#mari-reviewed').isChecked(), false);
    }
    if (flow === 'auditoria-situacao-polos') {
      const before = await page.locator('[data-section=polos][data-field=polo]').count();
      await page.locator('#add-polos').click();
      await page.locator('[data-section=polos][data-field=polo]').last().fill('Polo QA sem fonte');
      assert.equal(await page.locator('#form').evaluate(f => f.checkValidity()), false, 'new pole exposes manual recipient requirements');
      await page.locator('[data-section=polos][data-field=polo]').last().locator('..').locator('..').locator('button').click();
      assert.equal(await page.locator('[data-section=polos][data-field=polo]').count(), before);
      assert.equal(await page.locator('#form').evaluate(f => f.checkValidity()), true, 'removed pole no longer blocks validation');
    }
    results.push({flow, generated: true, downloadMatches: true, mobileDesktop: true});
  }
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
  console.log(JSON.stringify({results, javascriptErrors: errors, externalRequests: external}));
} finally {await browser.close();}
