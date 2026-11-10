import assert from 'node:assert/strict';
const {chromium} = await import(process.env.CCAA_PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({headless: true,
  executablePath: process.env.AGENT_BROWSER_EXECUTABLE_PATH || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome'});
try {
  const page = await browser.newPage();
  await page.setContent('<form id="form"></form>');
  await page.addScriptTag({path: new URL('./web/contacts.js', import.meta.url).pathname});
  await page.evaluate(() => {
    window.CCAAContacts.mount(document.querySelector('form'), {destinatarios: [{
      polo: 'Polo A', gestor: 'Gestor A', email: '', negocios_nome: 'Negócios', negocios_email: 'negocios@example.test',
      infra_nome: 'Infra', infra_email: 'infra@example.test', academico_nome: '', academico_email: ''
    }]}, [{nome: 'Auditor A', email: 'auditor@example.test'}, {nome: 'Auditor B', email: 'outro@example.test'}]);
    window.CCAAContacts.sync(['Polo A']);
  });
  await page.locator('[data-recipient-field=email]').fill('invalido');
  await page.locator('select').selectOption('Auditor A');
  await page.evaluate(() => { window.CCAAContacts.sync(['Polo A', 'Polo B']); window.CCAAContacts.sync(['Polo A']); });
  const email = page.locator('[data-recipient-polo="Polo A"] [data-recipient-field=email]');
  assert.equal(await email.count(), 1, 'a manual email must remain editable after changing the roster');
  assert.equal(await email.inputValue(), 'invalido');
  await email.fill('corrigido@example.test');
  const academic = page.locator('[data-recipient-polo="Polo A"] select');
  assert.equal(await academic.count(), 1, 'an academic choice must remain changeable');
  await academic.selectOption('Auditor B');
  const draft = await page.evaluate(() => window.CCAAContacts.read(['Polo A']));
  assert.equal(draft[0].email, 'corrigido@example.test');
  assert.equal(draft[0].academico_nome, 'Auditor B');
  assert.equal(draft[0].academico_email, 'outro@example.test');
  assert.equal(await page.locator('form').evaluate(form => form.checkValidity()), true);
  console.log('manual recipient fields stay editable across roster edits: OK');
} finally {await browser.close();}
