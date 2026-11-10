'use strict';
if (document.body.dataset.flow === 'aulas-praticas') {
  const flow = 'aulas-praticas', $ = id => document.querySelector(`#${id}`);
  const form = $('form'), record = $('record'), generate = $('generate'), frame = $('preview'), download = $('download');
  let version = 0, ready = false, blobUrl = null, labs = [], recipientPolos = [];
  function node(tag, text) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; }
  function message(text, error = false) { $('status').textContent = text; $('status').setAttribute('role', error ? 'alert' : 'status'); }
  function invalidate() {
    version++;
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    blobUrl = null; download.removeAttribute('href'); download.setAttribute('aria-disabled', 'true'); download.tabIndex = -1;
    frame.removeAttribute('src'); $('result-label').textContent = 'Nenhum HTML gerado'; generate.disabled = !ready;
  }
  const editor = node('fieldset'); editor.id = 'aulas-editor'; editor.disabled = true;
  editor.append(node('legend', 'Revisar dados do polo'),
    node('p', 'Complete as lacunas antes de gerar. Prazos são manuais e começam vazios. Ausência não é zero nem ausência de auditoria. Não há gravação nas bases ou no navegador.'));
  const warnings = node('p'); warnings.id = 'source-warnings'; warnings.setAttribute('role', 'note');
  (document.querySelector('#step-editor') || form).append(warnings, editor);
  function control(id, label, type = 'text', parent = editor) {
    const input = node('input'); input.id = id; input.type = type; input.required = true; input.maxLength = 300;
    if (type === 'number') { input.min = '0'; input.step = '1'; }
    const caption = node('label', label); caption.htmlFor = id; parent.append(caption, input); return input;
  }
  const dates = {prazo_praticas: control('prazo_praticas', 'Prazo de práticas — manual', 'date'), prazo_auditoria: control('prazo_auditoria', 'Prazo de auditoria — manual', 'date')};
  const applicable = control('aulas-aplicaveis', 'Práticas aplicáveis (desmarque somente se não aplicáveis)', 'checkbox'); applicable.required = false;
  const counts = {};
  for (const key of ['previstas', 'comprovadas', 'pendentes']) counts[key] = control(`aulas-${key}`, `Práticas ${key} (revise ou complete)`, 'number');
  const labStatus = node('select'); labStatus.id = 'aulas-labs-status'; labStatus.required = true;
  for (const [label, value] of [['Selecione a cobertura', ''], ['Revisar laboratórios', 'informado'], ['Não aplicável (confirmado)', 'nao_aplicavel']]) labStatus.add(new Option(label, value));
  const labCaption = node('label', 'Cobertura de laboratórios — ausência na fonte não comprova ausência de auditoria'); labCaption.htmlFor = labStatus.id;
  const listing = node('div'); editor.append(labCaption, labStatus, listing);
  const add = node('button', 'Adicionar laboratório'); add.type = 'button'; add.id = 'aulas-add-lab'; editor.append(add);
  const reviewed = control('aulas-reviewed', 'Confirmo os dados e a aplicabilidade do polo', 'checkbox');
  function update() {
    dates.prazo_praticas.disabled = !applicable.checked; dates.prazo_praticas.required = applicable.checked;
    dates.prazo_auditoria.disabled = labStatus.value === 'nao_aplicavel'; dates.prazo_auditoria.required = !dates.prazo_auditoria.disabled;
    for (const n of Object.values(counts)) { n.disabled = !applicable.checked; n.required = applicable.checked; }
    for (const row of labs) for (const n of Object.values(row)) { n.disabled = labStatus.value !== 'informado'; n.required = !n.disabled; }
    add.disabled = labStatus.value !== 'informado';
  }
  function addLab(data = {}) {
    const section = node('fieldset'); section.append(node('legend', `Laboratório ${labs.length + 1}`));
    const row = {};
    for (const [key, label] of [['nome', 'Laboratório'], ['parecer', 'Parecer (informe o resultado real; não inferido)']]) {
      row[key] = control(`aulas-lab-${labs.length}-${key}`, label, 'text', section); row[key].value = data[key] ?? ''; row[key].dataset.field = key;
    }
    listing.append(section); labs.push(row); update();
  }
  add.addEventListener('click', () => { addLab(); reviewed.checked = false; invalidate(); message('Laboratório adicionado. Complete e confirme novamente.'); });
  for (const type of ['input', 'change']) form.addEventListener(type, event => {
    if (event.target === record) { if (type === 'change') return loadDraft(); ready = false; editor.disabled = true; }
    if (event.target !== reviewed) reviewed.checked = false;
    invalidate(); update(); message('Dados alterados. Revise e confirme novamente antes de gerar.');
  });
  async function loadDraft() {
    ready = false; invalidate(); editor.disabled = true; warnings.textContent = '';
    const current = version, id = record.value;
    if (!id) { message('Selecione um polo.'); return; }
    try {
      const response = await fetch(`/api/draft/${flow}?${new URLSearchParams({id})}`, {cache: 'no-store'}), data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar o polo');
      if (current !== version) return;
      for (const [key, input] of Object.entries(dates)) input.value = data.draft[key];
      for (const [key, input] of Object.entries(counts)) input.value = data.draft.praticas[key] ?? '';
      applicable.checked = data.draft.praticas_aplicaveis; labStatus.value = data.draft.labs_status; reviewed.checked = false;
      labs = []; listing.replaceChildren(); for (const lab of data.draft.labs_lista) addLab(lab);
      recipientPolos = data.draft.destinatarios.map(row => row.polo);
      window.CCAAContacts.mount(editor, data.draft, data.auditores);
      window.CCAAContacts.sync(recipientPolos);
      warnings.textContent = (data.warnings || []).join('\n'); ready = true; editor.disabled = false; update();
      window.CCAASteps?.show?.(2);
      message('Revise os dados e preencha os suplementos antes de confirmar e gerar.');
    } catch (error) { if (current === version) message(error.message, true); }
    finally { if (current === version) generate.disabled = !ready; }
  }
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!ready || !form.reportValidity()) return;
    invalidate(); const current = version, id = record.value, label = record.selectedOptions[0].textContent;
    const draft = {reviewed: reviewed.checked, praticas_aplicaveis: applicable.checked, labs_status: labStatus.value,
      destinatarios: window.CCAAContacts.read(recipientPolos),
      praticas: Object.fromEntries(Object.entries(counts).map(([key, input]) => [key, input.value === '' ? null : Number(input.value)])),
      labs_lista: labs.map(row => Object.fromEntries(Object.entries(row).map(([key, input]) => [key, input.value]))),
      ...Object.fromEntries(Object.entries(dates).map(([key, input]) => [key, input.value]))};
    generate.disabled = true; message('Gerando HTML com os dados revisados…');
    try {
      const response = await fetch(`/api/render/${flow}`, {method: 'POST', cache: 'no-store', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, draft})});
      if (!response.ok) { const data = await response.json(); throw new Error(data.error || 'Não foi possível gerar'); }
      const html = await response.text(); if (current !== version) return;
      const preview = response.headers.get('X-Preview-URL');
      if (!/^\/api\/preview\/[a-z0-9_-]+$/i.test(preview || '')) throw new Error('Resposta sem endereço seguro de prévia');
      frame.src = preview; blobUrl = URL.createObjectURL(new Blob([html], {type: 'text/html;charset=utf-8'}));
      download.href = blobUrl; download.download = `ccaa-${flow}-${id.replace(/[^a-z0-9_-]/gi, '_')}.html`;
      download.setAttribute('aria-disabled', 'false'); download.tabIndex = 0; $('result-label').textContent = label;
      message('HTML gerado. Confira a prévia ou baixe o arquivo. Nenhum email foi enviado.');
    } catch (error) { if (current === version) message(error.message, true); }
    finally { if (current === version) generate.disabled = !ready; }
  });
  $('date-control').hidden = true; $('reference-date').disabled = true; $('record-label').textContent = 'Polo';
  for (const link of document.querySelectorAll('[data-nav]')) if (link.dataset.nav === flow) link.setAttribute('aria-current', 'page');
  window.addEventListener('pagehide', () => { ready = false; invalidate(); });
  async function loadOptions() {
    const current = version;
    try {
      const response = await fetch(`/api/options/${flow}`, {cache: 'no-store'}), data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar as bases');
      if (current !== version) return;
      record.replaceChildren(new Option('Selecione um polo', ''));
      for (const item of data.options) record.add(new Option(item.label, item.id));
      record.disabled = !data.options.length; message('Selecione um polo para revisar e completar os dados.');
    } catch (error) { if (current === version) message(error.message, true); }
  }
  loadOptions();
}
