import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';

const source = await readFile(new URL('./web/app.js', import.meta.url), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

async function setup(flow = 'mari') {
  const nodes = new Map();
  const pending = [];
  const blobs = [];
  const revoked = [];
  const requests = [];
  function element() {
    return {
      value: '', textContent: '', disabled: false, dataset: {}, attrs: {}, listeners: {},
      setAttribute(key, value) { this.attrs[key] = value; },
      removeAttribute(key) { delete this[key]; delete this.attrs[key]; },
      addEventListener(type, listener) { this.listeners[type] = listener; },
      replaceChildren() {}, add() {}, reportValidity() { return true; },
      selectedOptions: [{textContent: 'Registro A'}],
    };
  }
  for (const id of ['form', 'record', 'reference-date', 'generate', 'status', 'download', 'preview', 'result-label', 'record-label', 'date-control']) nodes.set(`#${id}`, element());
  const window = element();
  vm.runInNewContext(source, {
    document: {body: {dataset: {flow}}, querySelector: id => nodes.get(id), querySelectorAll: () => []},
    window, Option: function () {}, URLSearchParams, Blob,
    URL: {createObjectURL(blob) { blobs.push(blob); return `blob:${blobs.length}`; }, revokeObjectURL(url) { revoked.push(url); }},
    fetch(url) {
      requests.push(url);
      if (url.startsWith('/api/options/')) return Promise.resolve({ok: true, json: async () => ({options: [{id: 'A', label: 'Registro A', polo_count: 1}], today: '2026-09-11'})});
      return new Promise((resolve, reject) => pending.push({url, resolve, reject}));
    },
  });
  await flush();
  const get = id => nodes.get(`#${id}`);
  get('record').value = 'A';
  return {
    get, pending, blobs, revoked, window, requests,
    submit: () => get('form').listeners.submit({preventDefault() {}}),
    change(id, value) {
      get(id).value = value;
      if (id === 'record') get(id).selectedOptions = [{textContent: `Registro ${value}`}];
      get('form').listeners.change();
    },
  };
}
const success = html => ({ok: true, text: async () => html});

test('consolidado is owned by its dedicated script without legacy listeners or requests', async () => {
  const app = await setup('auditoria-situacao-polos');
  assert.deepEqual(app.requests, []);
  assert.deepEqual(app.get('form').listeners, {});
});

test('static Fast Track generates without reading controls or requesting data options', async () => {
  const app = await setup('fast-track-infra-2026');
  assert.deepEqual(app.requests, []);
  for (const id of ['record', 'reference-date']) {
    Object.defineProperty(app.get(id), 'value', {get() { throw new Error('Static preview must not read fields'); }});
  }
  const request = app.submit();
  assert.equal(app.pending[0].url, '/api/render/fast-track-infra-2026?');
  app.pending[0].resolve(success('<html>Fast Track</html>'));
  await request;
  assert.equal(app.get('result-label').textContent, 'Agenda Fast Track Infra 2026');
  assert.equal(app.get('download').attrs['aria-disabled'], 'false');
  assert.equal(await app.blobs[0].text(), '<html>Fast Track</html>');
});

for (const [field, value] of [['record', 'B'], ['reference-date', '2026-09-12']]) {
  test(`${field}: change during request keeps stale response from enabling download`, async () => {
    const app = await setup();
    const request = app.submit();
    app.change(field, value);
    const message = app.get('status').textContent;
    app.pending[0].resolve(success('old'));
    await request;
    assert.equal(app.get('download').attrs['aria-disabled'], 'true');
    assert.equal(app.get('download').href, undefined);
    assert.equal(app.get('preview').src, undefined);
    assert.equal(app.get('result-label').textContent, '');
    assert.equal(app.get('status').textContent, message);
    assert.equal(app.blobs.length, 0);
    assert.equal(app.get('generate').disabled, false);
  });
}

for (const outcome of ['success', 'error', 'http-error']) {
  test(`obsolete ${outcome} cannot overwrite newer request or result`, async () => {
    const app = await setup();
    const old = app.submit();
    app.change('record', 'B');
    const current = app.submit();
    const generating = app.get('status').textContent;
    if (outcome === 'success') app.pending[0].resolve(success('old'));
    else if (outcome === 'error') app.pending[0].reject(new Error('old failure'));
    else app.pending[0].resolve({ok: false, json: async () => ({error: 'old HTTP failure'})});
    await old;
    assert.equal(app.get('status').textContent, generating);
    assert.equal(app.get('generate').disabled, true);
    app.pending[1].resolve(success('new'));
    await current;
    assert.equal(app.get('result-label').textContent, 'Registro B');
    assert.equal(await app.blobs[0].text(), 'new');
    assert.equal(app.get('download').download, 'ccaa-mari-B.html');
  });
}

test('older response after newer success leaves the result intact', async () => {
  const app = await setup();
  const old = app.submit();
  app.change('record', 'B');
  const current = app.submit();
  app.pending[1].resolve(success('new'));
  await current;
  const href = app.get('download').href;
  app.pending[0].resolve(success('old'));
  await old;
  assert.equal(app.get('download').href, href);
  assert.equal(app.get('result-label').textContent, 'Registro B');
  assert.equal(app.blobs.length, 1);
});

test('normal path uses submitted selection/date snapshot and invalidates existing download', async () => {
  const app = await setup();
  const request = app.submit();
  // Change the live controls without a change event to verify the captured snapshot.
  app.get('record').value = 'B';
  app.get('record').selectedOptions = [{textContent: 'Registro B'}];
  app.get('reference-date').value = '2026-09-12';
  app.pending[0].resolve(success('<html>A</html>'));
  await request;
  assert.equal(app.pending[0].url, '/api/render/mari?id=A&date=2026-09-11');
  assert.equal(app.get('preview').src, app.pending[0].url);
  assert.equal(app.get('result-label').textContent, 'Registro A');
  assert.equal(app.get('download').download, 'ccaa-mari-A.html');
  assert.equal(app.get('download').attrs['aria-disabled'], 'false');
  assert.equal(app.get('generate').disabled, false);
  assert.equal(await app.blobs[0].text(), '<html>A</html>');
  app.change('reference-date', '2026-09-13');
  assert.equal(app.get('download').href, undefined);
  assert.deepEqual(app.revoked, ['blob:1']);
});

test('current request errors remain visible and allow retry', async () => {
  const app = await setup();
  const request = app.submit();
  app.pending[0].reject(new Error('current failure'));
  await request;
  assert.equal(app.get('status').textContent, 'current failure');
  assert.equal(app.get('status').attrs.role, 'alert');
  assert.equal(app.get('generate').disabled, false);
  assert.equal(app.get('download').attrs['aria-disabled'], 'true');
});
