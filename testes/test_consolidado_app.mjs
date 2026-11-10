import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';

const source = await readFile(new URL('./web/consolidado.js', import.meta.url), 'utf8').catch(() => '');
const flush = () => new Promise(resolve => setImmediate(resolve));

test('page exposes fourth navigation route and dedicated-script insertion point', async () => {
  const page = await readFile(new URL('./web/page.html', import.meta.url), 'utf8');
  assert.match(page, /href="\/auditoria-situacao-polos"/);
  assert.match(page, /__EXTRA_SCRIPT__/);
});
class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.listeners = {}; this.dataset = {}; this.attrs = {}; this.value = ''; this.textContent = ''; }
  append(...nodes) { for (const node of nodes) node.parent = this; this.children.push(...nodes); }
  remove() { this.parent.children = this.parent.children.filter(node => node !== this); }
  replaceChildren(...nodes) { this.children = nodes; }
  add(node) { this.append(node); }
  setAttribute(key, value) { this.attrs[key] = value; }
  removeAttribute(key) { delete this.attrs[key]; delete this[key]; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  reportValidity() { return true; }
  get selectedOptions() { return this.children.filter(node => node.value === this.value); }
}
function all(root) { return [root, ...root.children.flatMap(all)]; }
async function setup() {
  const root = new Element();
  for (const id of ['form', 'record', 'record-controls', 'record-label', 'date-control', 'reference-date', 'generate', 'status', 'download', 'preview', 'result-label']) {
    const node = new Element(id === 'form' ? 'form' : 'div'); node.id = id; root.append(node);
  }
  const find = id => all(root).find(node => node.id === id);
  const pending = [], blobs = [], revoked = [];
  const window = new Element();
  vm.runInNewContext(source, {
    document: {body: {dataset: {flow: 'auditoria-situacao-polos'}}, querySelector: selector => find(selector.slice(1)), querySelectorAll: () => [], createElement: tag => new Element(tag)},
    window, Blob, URLSearchParams,
    Option: function(text, value) { const node = new Element('option'); node.value = value; node.textContent = text; return node; },
    URL: {createObjectURL(blob) { blobs.push(blob); return `blob:${blobs.length}`; }, revokeObjectURL(url) { revoked.push(url); }},
    fetch: (url, options) => new Promise((resolve, reject) => pending.push({url, options, resolve, reject})),
  });
  const app = {
    find, pending, blobs, revoked, window,
    controls: () => all(root).filter(node => node.tagName === 'input'),
    fields: (section, field) => all(root).filter(node => node.dataset.section === section && node.dataset.field === field),
    remove(section, index) { return all(root).filter(node => node.dataset.remove === section)[index].listeners.click(); },
    click: id => find(id).listeners.click(),
    edit(node, value, type = 'input') { node.value = value; return find('form').listeners[type]({target: node}); },
    select(value) { return this.edit(find('record'), value, 'change'); },
    submit() { return find('form').listeners.submit({preventDefault() {}}); },
  };
  assert.equal(pending.length, 1, 'dedicated script must load options');
  pending[0].resolve(json({options: [{id: 'A', label: 'Gestor A', polo_count: 2}, {id: 'manual', label: 'Manual', polo_count: 0}]}));
  await flush();
  return app;
}
const json = data => ({ok: true, json: async () => data});
const rendered = (html = '<html>real</html>', preview = '/api/preview/token') => ({ok: true, text: async () => html, headers: {get: () => preview}});
const draft = () => ({gestor: 'Gestor A', ciclo: '261', polos: ['Polo A', 'Polo B'], checklist: [{polo: 'Polo A', nota: null, status: '', observacao: '', auditor: ''}], agenda: [{polo: 'Polo A', tipo: 'Regular', ambiente: 'Sala', data: '2026-05-22', auditor: 'Ana', status: 'Realizada'}], praticas: [{polo: 'Polo A', previstas: 48, comprovadas: 0, pendentes: 48}], laboratorios: [{polo: 'Polo B', laboratorio: 'Lab', parecer: 'Reprovado'}], reprovados_sem_retorno: null, prazo_praticas: '', prazo_auditorias: '', link_relatorio: 'https://example.com', link_atendimento: '', contatos: [{funcao: 'Auditoria', nome: '', email: 'a@example.com', telefone: ''}]});
async function loaded() {
  const app = await setup();
  const load = app.select('A');
  app.pending[1].resolve(json({draft: draft(), warnings: ['Base antiga; preencher lacunas'], source_cycles: ['261']}));
  await load;
  return app;
}

test('complete editable draft posts exact fields, nullable numbers, snapshot preview and identical download', async () => {
  const app = await loaded();
  assert.equal(app.find('reference-date').disabled, true, 'hidden required legacy date must not block native validation');
  assert.equal(app.find('gestor').value, 'Gestor A');
  assert.equal(app.fields('agenda', 'status')[0].value, 'Realizada');
  assert.match(app.find('source-warnings').textContent, /261/);
  assert.match(app.find('source-warnings').textContent, /Base antiga/);
  app.edit(app.find('ciclo'), '262');
  app.edit(app.fields('checklist', 'observacao')[0], '<script>texto manual</script>');
  const request = app.submit();
  const sent = app.pending[2];
  assert.equal(sent.url, '/api/render/auditoria-situacao-polos');
  assert.equal(sent.options.method, 'POST');
  const body = JSON.parse(sent.options.body);
  assert.equal(body.id, 'A');
  assert.equal(body.draft.ciclo, '262');
  assert.equal(body.draft.checklist[0].nota, null);
  assert.equal(body.draft.praticas[0].comprovadas, 0);
  assert.equal(body.draft.reprovados_sem_retorno, null);
  assert.equal(body.draft.checklist[0].observacao, '<script>texto manual</script>');
  assert.deepEqual(Object.keys(body.draft).sort(), Object.keys(draft()).sort());
  sent.resolve(rendered()); await request;
  assert.equal(app.find('preview').src, '/api/preview/token');
  assert.equal(await app.blobs[0].text(), '<html>real</html>');
  assert.equal(app.find('download').attrs['aria-disabled'], 'false');
  assert.match(app.find('source-warnings').textContent, /261/);
});


test('roster changes clear the portfolio indicator for manual review', async () => {
  for (const action of ['remove', 'edit', 'add']) {
    const app = await loaded();
    app.edit(app.find('reprovados_sem_retorno'), '7');
    if (action === 'remove') app.remove('polos', 1);
    if (action === 'edit') app.edit(app.fields('polos', 'polo')[0], 'Outro polo');
    if (action === 'add') app.click('add-polos');
    assert.equal(app.find('reprovados_sem_retorno').value, '', action);
  }
});

test('add/remove manual rows in every table and omit data outside edited roster', async () => {
  const app = await loaded();
  for (const section of ['polos', 'checklist', 'agenda', 'praticas', 'laboratorios', 'contatos']) {
    const field = section === 'contatos' ? 'funcao' : 'polo';
    const count = app.fields(section, field).length;
    assert.ok(app.find(`add-${section}`), `missing add button for ${section}`);
    app.click(`add-${section}`);
    assert.equal(app.fields(section, field).length, count + 1);
    app.remove(section, count);
    assert.equal(app.fields(section, field).length, count);
  }
  app.remove('polos', 1);
  app.click('add-polos');
  app.edit(app.fields('polos', 'polo')[1], 'Polo manual');
  app.click('add-praticas');
  app.edit(app.fields('praticas', 'polo')[1], 'Polo manual');
  app.edit(app.fields('praticas', 'previstas')[1], '12');
  const request = app.submit();
  const sent = app.pending.at(-1);
  const payload = JSON.parse(sent.options.body).draft;
  assert.deepEqual(payload.polos, ['Polo A', 'Polo manual']);
  assert.deepEqual(payload.laboratorios, []);
  assert.equal(payload.praticas[1].previstas, 12);
  sent.resolve(rendered()); await request;
});

for (const type of ['input', 'change']) test(`${type}: every scalar and table field blocks obsolete render success/error/finally`, async () => {
  const app = await loaded();
  for (const control of app.controls()) {
    for (const outcome of ['success', 'error', 'http-error']) {
      const old = app.submit(), oldResponse = app.pending.at(-1);
      app.edit(control, control.value, type);
      const current = app.submit(), currentResponse = app.pending.at(-1);
      const message = app.find('status').textContent;
      if (outcome === 'success') oldResponse.resolve(rendered('old'));
      if (outcome === 'error') oldResponse.reject(new Error('old error'));
      if (outcome === 'http-error') oldResponse.resolve({ok: false, json: async () => ({error: 'old HTTP error'})});
      await old;
      assert.equal(app.find('status').textContent, message);
      assert.equal(app.find('generate').disabled, true);
      assert.equal(app.find('download').attrs['aria-disabled'], 'true');
      currentResponse.resolve(rendered('current')); await current;
      assert.equal(await app.blobs.at(-1).text(), 'current');
      app.edit(control, control.value, type);
      assert.equal(app.find('download').href, undefined);
      assert.equal(app.find('preview').src, undefined);
    }
  }
  assert.equal(app.revoked.length, app.blobs.length);
});

for (const outcome of ['success', 'error', 'http-error']) test(`draft selection race: obsolete ${outcome} cannot overwrite current fields, warnings or busy state`, async () => {
  const app = await loaded();
  const old = app.select('A'), oldResponse = app.pending.at(-1);
  const current = app.select('manual'), currentResponse = app.pending.at(-1);
  const message = app.find('status').textContent;
  if (outcome === 'success') oldResponse.resolve(json({draft: {...draft(), gestor: 'WRONG'}, warnings: ['WRONG'], source_cycles: ['262']}));
  if (outcome === 'error') oldResponse.reject(new Error('WRONG'));
  if (outcome === 'http-error') oldResponse.resolve({ok: false, json: async () => ({error: 'WRONG'})});
  await old;
  assert.equal(app.find('status').textContent, message);
  assert.equal(app.find('generate').disabled, true);
  currentResponse.resolve(json({draft: {...draft(), gestor: 'Manual'}, warnings: ['Manual'], source_cycles: ['261']})); await current;
  assert.equal(app.find('gestor').value, 'Manual');
  assert.match(app.find('source-warnings').textContent, /Manual/);
  assert.doesNotMatch(app.find('source-warnings').textContent, /WRONG/);
});

test('old draft after newer success and manual edit leaves every field intact', async () => {
  const app = await loaded();
  const old = app.select('A'), oldResponse = app.pending.at(-1);
  const current = app.select('manual');
  app.pending.at(-1).resolve(json({draft: draft(), source_cycles: ['261'], warnings: ['Current']})); await current;
  for (const control of app.controls()) app.edit(control, control.type === 'number' ? '7' : 'Manual');
  const expectedValues = app.controls().map(control => control.value);
  oldResponse.resolve(json({draft: draft(), warnings: ['WRONG'], source_cycles: ['262']})); await old;
  assert.deepEqual(app.controls().map(control => control.value), expectedValues);
  assert.match(app.find('source-warnings').textContent, /Current/);
});

test('older render after new success and pagehide cannot replace or revive result', async () => {
  const app = await loaded();
  const old = app.submit(), oldResponse = app.pending.at(-1);
  app.edit(app.find('gestor'), 'Novo');
  const current = app.submit(); app.pending.at(-1).resolve(rendered('new')); await current;
  const href = app.find('download').href;
  oldResponse.resolve(rendered('old')); await old;
  assert.equal(app.find('download').href, href);
  assert.equal(app.find('result-label').textContent, 'Novo');
  const pending = app.submit();
  app.window.listeners.pagehide(); app.pending.at(-1).resolve(rendered('after hide')); await pending;
  assert.equal(app.find('download').href, undefined);
});

test('roster/table mutations and manager selection invalidate in-flight renders immediately', async () => {
  for (const mutate of [app => app.click('add-polos'), app => app.remove('polos', 0), app => app.click('add-agenda'), app => app.remove('agenda', 0), app => app.select('manual')]) {
    const app = await loaded();
    const request = app.submit(), response = app.pending.at(-1);
    mutate(app);
    response.resolve(rendered('obsolete')); await request;
    assert.equal(app.find('download').href, undefined);
    assert.equal(app.blobs.length, 0);
  }
});

test('manual option accepts fully empty tables without inventing values', async () => {
  const app = await setup();
  const request = app.select('manual');
  app.pending.at(-1).resolve(json({draft: {gestor: '', ciclo: '261', polos: []}, source_cycles: [], warnings: ['Sem bases']})); await request;
  for (const section of ['polos', 'agenda', 'checklist', 'praticas', 'laboratorios']) assert.equal(app.fields(section, 'polo').length, 0);
  assert.equal(app.find('reprovados_sem_retorno').value, '');
  assert.equal(app.find('prazo_praticas').value, '');
  app.edit(app.find('gestor'), 'Manual');
  app.click('add-polos'); app.edit(app.fields('polos', 'polo')[0], 'Polo manual');
  const render = app.submit(); const sent = app.pending.at(-1);
  assert.equal(JSON.parse(sent.options.body).id, 'manual');
  sent.resolve(rendered()); await render;
});

test('current render errors and missing/unsafe snapshot header leave download blocked and permit retry', async () => {
  const app = await loaded();
  for (const response of [{ok: false, json: async () => ({error: 'Invalid draft'})}, rendered('x', null), rendered('x', 'https://evil.example/preview')]) {
    const request = app.submit(); app.pending.at(-1).resolve(response); await request;
    assert.equal(app.find('status').attrs.role, 'alert');
    assert.equal(app.find('download').attrs['aria-disabled'], 'true');
    assert.equal(app.find('generate').disabled, false);
  }
});
