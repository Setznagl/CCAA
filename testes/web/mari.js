'use strict';
if (document.body.dataset.flow === 'mari') {
  const $ = id => document.querySelector(`#${id}`);
  const form = $('form'), record = $('record'), generate = $('generate');
  const download = $('download'), frame = $('preview'), status = $('status');
  let version = 0, ready = false, blobUrl = null, rows = [], groups = new Map();
  function node(tag, text) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function input(id, label, type, value = '') {
    const control = node('input'); control.id = id; control.type = type; control.value = value;
    control.setAttribute('aria-label', label);
    if (type !== 'checkbox') { control.required = true; control.maxLength = type === 'email' ? 254 : 300; }
    return control;
  }
  function caption(label, control) {
    const wrapper = node('label', label); wrapper.htmlFor = control.id;
    return wrapper;
  }
  function message(text, error = false) {
    status.textContent = text; status.setAttribute('role', error ? 'alert' : 'status');
  }
  function invalidate() {
    version++;
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    blobUrl = null;
    download.removeAttribute('href'); download.setAttribute('aria-disabled', 'true'); download.tabIndex = -1;
    frame.removeAttribute('src'); $('result-label').textContent = 'Nenhum HTML gerado';
    generate.disabled = !ready;
  }
  const warnings = node('p'); warnings.id = 'source-warnings'; warnings.setAttribute('role', 'note');
  const editor = node('fieldset'); editor.id = 'mari-editor'; editor.disabled = true;
  editor.append(node('legend', 'Revisar agenda e completar dados ausentes'));
  const name = input('mari-go', 'Nome do gestor do polo', 'text');
  editor.append(caption('Gestor do polo — preenchido pela base', name), name,
    node('p', 'Todas as datas e laboratórios vêm selecionados, sem filtro semanal automático. Desmarque as linhas fora do período desejado. Grupo econômico é informado uma vez por polo. Nenhum dado manual será salvo nas bases ou no navegador.'));
  const count = node('p'); count.id = 'mari-selection-count'; count.setAttribute('aria-live', 'polite');
  const listing = node('div'); listing.id = 'mari-rows';
  const reviewed = input('mari-reviewed', 'Confirmo gestor, destinatários, grupos e linhas/período selecionados', 'checkbox'); reviewed.required = true;
  editor.append(count, listing, caption('Confirmo gestor, destinatários, grupos e linhas/período selecionados', reviewed), reviewed);
  (document.querySelector('#step-editor') || form).append(warnings, editor);
  function updateSelection() {
    const selected = rows.filter(row => row.selected.checked);
    count.textContent = `${new Set(selected.map(row => row.source.polo)).size} polo(s) distinto(s); ${selected.length} linha(s) de laboratório selecionada(s).`;
    for (const row of rows) { row.date.disabled = !row.selected.checked; row.date.required = row.selected.checked; }
    for (const [polo, group] of groups) {
      group.disabled = !selected.some(row => row.source.polo === polo); group.required = !group.disabled;
    }
    window.CCAAContacts.sync(selected.map(row => row.source.polo));
  }
  function populate(draft, auditores) {
    name.value = draft.label || ''; reviewed.checked = false;
    rows = []; groups = new Map(); listing.replaceChildren();
    for (const data of draft.rows) {
      if (!groups.has(data.polo)) {
        const section = node('fieldset'); section.append(node('legend', data.polo));
        const group = input(`mari-group-${groups.size}`, `Grupo econômico — ${data.polo}`, 'text', data.grupo || '');
        group.dataset.field = 'grupo'; section.append(caption('Grupo econômico — preenchido pela base; revise se necessário', group), group);
        groups.set(data.polo, group); listing.append(section);
      }
      // Spreadsheet text remains text, never interpolated HTML.
      const line = node('div');
      const selected = input(`mari-selected-${data.id}`, `Incluir ${data.polo} — ${data.laboratorio}`, 'checkbox');
      selected.checked = data.selected === true; selected.dataset.field = 'selected';
      const date = input(`mari-date-${data.id}`, `Data/hora — ${data.polo} — ${data.laboratorio}`, 'datetime-local', data.date);
      date.dataset.field = 'date';
      line.append(caption(`Incluir — ${data.polo} — ${data.laboratorio || 'Laboratório não informado'}`, selected), selected,
        caption('Data e hora agendada (revise ou complete)', date), date);
      listing.append(line);
      rows.push({source: data, selected, date});
    }
    window.CCAAContacts.mount(editor, draft, auditores);
    updateSelection();
  }
  async function loadDraft() {
    ready = false; invalidate(); editor.disabled = true; $('reference-date').disabled = true; warnings.textContent = '';
    const current = version, id = record.value;
    if (!id) { message('Selecione o gestor do polo ou a revisão manual.'); return; }
    message('Carregando agenda para revisão…');
    try {
      const response = await fetch(`/api/draft/mari?${new URLSearchParams({id})}`, {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar a agenda');
      if (current !== version) return;
      populate(data.draft, data.auditores);
      warnings.textContent = [`Origem: databases/09-11-26; semestre(s) da fonte: ${(data.source_cycles || []).join(', ') || 'não informado'}.`, ...(data.warnings || [])].join('\n');
      ready = true; editor.disabled = false; $('reference-date').disabled = false;
      window.CCAASteps?.show?.(2);
      message('Revise as linhas e complete os campos pendentes antes de confirmar e gerar.');
    } catch (error) {
      if (current === version) message(error.message, true);
    } finally {
      if (current === version) generate.disabled = !ready;
    }
  }
  for (const type of ['input', 'change']) form.addEventListener(type, event => {
    if (event.target === record) {
      if (type === 'change') return loadDraft();
      ready = false; editor.disabled = true;
    }
    if (event.target !== reviewed) reviewed.checked = false;
    invalidate(); updateSelection();
    message('Dados alterados. Revise e confirme novamente antes de gerar.');
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!ready || !form.reportValidity()) return;
    invalidate();
    const current = version, id = record.value, date = $('reference-date').value;
    const draft = {label: name.value, reviewed: reviewed.checked,
      destinatarios: window.CCAAContacts.read(rows.filter(row => row.selected.checked).map(row => row.source.polo)),
      rows: rows.map(row => ({...row.source, selected: row.selected.checked, date: row.date.value, grupo: groups.get(row.source.polo).value}))};
    generate.disabled = true; message('Gerando HTML com a agenda revisada…');
    try {
      const response = await fetch('/api/render/mari', {method: 'POST', cache: 'no-store', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, date, draft})});
      if (!response.ok) { const data = await response.json(); throw new Error(data.error || 'Não foi possível gerar o HTML'); }
      const html = await response.text();
      if (current !== version) return;
      const preview = response.headers.get('X-Preview-URL');
      if (!/^\/api\/preview\/[a-z0-9_-]+$/i.test(preview || '')) throw new Error('Resposta sem endereço seguro de prévia. Gere novamente.');
      frame.src = preview;
      blobUrl = URL.createObjectURL(new Blob([html], {type: 'text/html;charset=utf-8'}));
      download.href = blobUrl; download.download = `ccaa-mari-${date}.html`;
      download.setAttribute('aria-disabled', 'false'); download.tabIndex = 0;
      $('result-label').textContent = draft.label;
      message('HTML gerado. Confira todas as datas e laboratórios. Nenhum email foi enviado.');
    } catch (error) {
      if (current === version) message(error.message, true);
    } finally {
      if (current === version) generate.disabled = !ready;
    }
  });
  $('record-label').textContent = 'Gestor do polo / carteira de auditorias programadas';
  $('date-control').hidden = false; $('reference-date').disabled = true;
  for (const link of document.querySelectorAll('[data-nav]')) if (link.dataset.nav === 'mari') link.setAttribute('aria-current', 'page');
  window.addEventListener('pagehide', () => { ready = false; invalidate(); });
  async function loadOptions() {
    const current = version;
    generate.disabled = true;
    try {
      const response = await fetch('/api/options/mari', {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar as bases');
      if (current !== version) return;
      record.replaceChildren(new Option('Selecione o gestor do polo ou a revisão manual', ''));
      for (const item of data.options) record.add(new Option(`${item.label} — ${item.polo_count} polo(s)`, item.id));
      $('reference-date').value = data.today;
      record.disabled = !data.options.length;
      message('Selecione o gestor para revisar as auditorias de todos os seus polos. Nenhum filtro automático de semana é aplicado.');
    } catch (error) {
      if (current === version) message(error.message, true);
    }
  }
  loadOptions();
}
