'use strict';
if (document.body.dataset.flow === 'auditoria-situacao-polos') {
  const flow = 'auditoria-situacao-polos';
  const $ = id => document.querySelector(`#${id}`);
  const form = $('form'), record = $('record'), generate = $('generate');
  const download = $('download'), frame = $('preview'), status = $('status');
  const scalars = [
    ['gestor', 'Gestor', 'text'], ['ciclo', 'Ciclo (261 / 26.1 ou 262 / 26.2)', 'text'],
    ['reprovados_sem_retorno', 'Reprovados sem retorno (não informado se vazio)', 'number'],
    ['prazo_praticas', 'Prazo de práticas (manual)', 'date'], ['prazo_auditorias', 'Prazo de auditorias (manual)', 'date'],
    ['link_relatorio', 'Link do relatório', 'url'], ['link_atendimento', 'Link de atendimento', 'url'],
  ];
  const sections = {
    polos: ['Carteira de polos', [['polo', 'Polo', 'text']]],
    checklist: ['Checklist', [['polo', 'Polo', 'text'], ['nota', 'Nota', 'number'], ['status', 'Status', 'text'], ['observacao', 'Observação', 'text'], ['auditor', 'Auditor', 'text']]],
    agenda: ['Agenda de auditorias', [['polo', 'Polo', 'text'], ['tipo', 'Tipo', 'text'], ['ambiente', 'Ambiente', 'text'], ['data', 'Data', 'date'], ['auditor', 'Auditor', 'text'], ['status', 'Status (Agendada / Realizada / Finalizada)', 'text']]],
    praticas: ['Aulas práticas', [['polo', 'Polo', 'text'], ['previstas', 'Previstas', 'number'], ['comprovadas', 'Comprovadas', 'number'], ['pendentes', 'Pendentes', 'number']]],
    laboratorios: ['Resultados dos laboratórios', [['polo', 'Polo', 'text'], ['laboratorio', 'Laboratório', 'text'], ['parecer', 'Parecer', 'text']]],
    contatos: ['Contatos', [['funcao', 'Função', 'text'], ['nome', 'Nome', 'text'], ['email', 'Email', 'email'], ['telefone', 'Telefone', 'text']]],
  };
  let version = 0, ready = false, blobUrl = null;
  const rows = {}, inputs = {};
  const contactOrigins = new WeakMap();
  function node(tag, text) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function message(text, error = false) {
    status.textContent = text;
    status.setAttribute('role', error ? 'alert' : 'status');
  }
  function invalidate() {
    version++;
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    blobUrl = null;
    download.removeAttribute('href');
    download.setAttribute('aria-disabled', 'true');
    download.tabIndex = -1;
    frame.removeAttribute('src');
    $('result-label').textContent = 'Nenhum HTML gerado';
    generate.disabled = !ready;
  }
  function input(key, label, type, value) {
    const element = node('input');
    element.type = type;
    element.value = value ?? '';
    element.setAttribute('aria-label', label);
    if (type === 'number') { element.min = '0'; element.step = key === 'nota' ? 'any' : '1'; }
    return element;
  }
  const warnings = node('p'); warnings.id = 'source-warnings'; warnings.setAttribute('role', 'note');
  const editor = node('fieldset'); editor.id = 'consolidado-editor'; editor.disabled = true;
  editor.append(node('legend', 'Dados do consolidado'));
  (document.querySelector('#step-editor') || form).append(warnings, editor);
  for (const [key, label, type] of scalars) {
    const control = input(key, label, type, ''); control.id = key;
    control.required = key === 'gestor' || key === 'ciclo';
    const caption = node('label', label); caption.htmlFor = key;
    inputs[key] = control; editor.append(caption, control);
  }
  editor.append(node('p', 'Campos vazios significam não informado. A agenda prioriza a data de realização; na ausência, usa a data agendada e identifica essa referência no status. Isso não comprova a data de realização. Ao revisar uma data manualmente, revise também seu status. Ao remover ou renomear um polo, linhas de dados que não pertençam à carteira serão omitidas da geração. Não há gravação nas bases.'));
  const bodies = {};
  for (const [section, [title, columns]] of Object.entries(sections)) {
    rows[section] = [];
    const heading = node('h2', title), table = node('table'), head = node('thead'), tr = node('tr');
    table.append(node('caption', title));
    for (const [, label] of columns) { const th = node('th', label); th.scope = 'col'; tr.append(th); }
    const actionHead = node('th', 'Ações'); actionHead.scope = 'col'; tr.append(actionHead);
    head.append(tr); bodies[section] = node('tbody'); table.append(head, bodies[section]);
    const scroll = node('div'); scroll.className = 'table-scroll'; scroll.tabIndex = 0; scroll.setAttribute('aria-label', title);
    const add = node('button', `Adicionar linha — ${title}`); add.type = 'button'; add.id = `add-${section}`;
    add.addEventListener('click', () => {
      addRow(section, {});
      if (section === 'polos') inputs.reprovados_sem_retorno.value = '';
      invalidate(); message('Linha adicionada. Revise os dados e o indicador da carteira antes de gerar.');
    });
    scroll.append(table); editor.append(heading, scroll, add);
  }
  function addRow(section, data) {
    const tr = node('tr'), controls = {};
    if (section === 'contatos') contactOrigins.set(controls, data.origem ?? null);
    for (const [key, label, type] of sections[section][1]) {
      const control = input(key, label, type, data[key]);
      control.dataset.section = section; control.dataset.field = key;
      const td = node('td'); td.append(control); tr.append(td); controls[key] = control;
    }
    const remove = node('button', 'Remover'); remove.type = 'button'; remove.dataset.remove = section;
    remove.setAttribute('aria-label', `Remover linha de ${sections[section][0]}`);
    remove.addEventListener('click', () => {
      if (section === 'polos') inputs.reprovados_sem_retorno.value = '';
      rows[section] = rows[section].filter(row => row !== controls); tr.remove(); invalidate();
      if (section === 'polos') window.CCAAContacts.sync(rows.polos.map(row => row.polo.value.trim()).filter(Boolean));
      message('Linha removida. Revise o indicador da carteira; polos fora da carteira serão omitidos.');
    });
    const actions = node('td'); actions.append(remove); tr.append(actions);
    bodies[section].append(tr); rows[section].push(controls);
  }
  function readValue(control) { return control.type === 'number' ? (control.value === '' ? null : Number(control.value)) : control.value; }
  function payload() {
    const draft = {};
    for (const [key, control] of Object.entries(inputs)) draft[key] = readValue(control);
    for (const section of Object.keys(sections)) draft[section] = rows[section].map(controls => {
      const row = Object.fromEntries(Object.entries(controls).map(([key, input]) => [key, readValue(input)]));
      if (section === 'contatos') row.origem = contactOrigins.get(controls);
      return row;
    });
    draft.polos = draft.polos.map(row => row.polo.trim()).filter(Boolean);
    for (const section of ['checklist', 'agenda', 'praticas', 'laboratorios']) draft[section] = draft[section].filter(row => draft.polos.includes(row.polo));
    draft.destinatarios = window.CCAAContacts.read(draft.polos);
    return draft;
  }
  async function loadDraft() {
    ready = false; invalidate(); editor.disabled = true; warnings.textContent = '';
    const current = version, id = record.value;
    if (!id) { message('Selecione um gestor ou o preenchimento manual.'); return; }
    message('Carregando dados da carteira…');
    try {
      const response = await fetch(`/api/draft/${flow}?${new URLSearchParams({id})}`, {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar o formulário');
      if (current !== version) return;
      for (const [key, control] of Object.entries(inputs)) control.value = data.draft[key] ?? '';
      for (const section of Object.keys(sections)) {
        bodies[section].replaceChildren(); rows[section] = [];
        for (const row of data.draft[section] || []) addRow(section, section === 'polos' ? {polo: row} : row);
      }
      window.CCAAContacts.mount(editor, data.draft, data.auditores);
      window.CCAAContacts.sync(data.draft.polos);
      warnings.textContent = [`Origem das bases: ${(data.source_cycles || []).join(', ') || 'não informada'}. Alterar o ciclo não atualiza a fonte.`, ...(data.warnings || [])].join('\n');
      ready = true; editor.disabled = false;
      window.CCAASteps?.show?.(2);
      message('Dados carregados. Revise a carteira e preencha as lacunas antes de gerar.');
    } catch (error) {
      if (current === version) message(error.message, true);
    } finally {
      if (current === version) generate.disabled = !ready;
    }
  }
  for (const type of ['input', 'change']) form.addEventListener(type, event => {
    if (event.target === record) {
      if (type === 'change') return loadDraft();
      ready = false;
    }
    if (event.target.dataset.section === 'polos') {
      inputs.reprovados_sem_retorno.value = '';
      window.CCAAContacts.sync(rows.polos.map(row => row.polo.value.trim()).filter(Boolean));
    }
    invalidate();
    message('Dados alterados. Gere novamente para atualizar a prévia e o download.');
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!ready || !form.reportValidity()) return;
    invalidate();
    const current = version, id = record.value, draft = payload(), label = draft.gestor;
    generate.disabled = true; message('Gerando HTML com os dados revisados…');
    try {
      const response = await fetch(`/api/render/${flow}`, {method: 'POST', cache: 'no-store', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, draft})});
      if (!response.ok) { const data = await response.json(); throw new Error(data.error || 'Não foi possível gerar o HTML'); }
      const html = await response.text();
      if (current !== version) return;
      const preview = response.headers.get('X-Preview-URL');
      if (!/^\/api\/preview\/[a-z0-9_-]+$/i.test(preview || '')) throw new Error('Resposta sem endereço seguro de prévia. Gere novamente.');
      frame.src = preview;
      blobUrl = URL.createObjectURL(new Blob([html], {type: 'text/html;charset=utf-8'}));
      download.href = blobUrl; download.download = `ccaa-${flow}-${id.replace(/[^a-z0-9_-]/gi, '_')}.html`;
      download.setAttribute('aria-disabled', 'false'); download.tabIndex = 0;
      $('result-label').textContent = label;
      message('HTML gerado. Confira a prévia ou baixe o arquivo. Nenhum email foi enviado.');
    } catch (error) {
      if (current === version) message(error.message, true);
    } finally {
      if (current === version) generate.disabled = !ready;
    }
  });
  $('record-label').textContent = 'Gestor / carteira';
  $('record-controls').disabled = false; $('date-control').hidden = true; $('reference-date').disabled = true;
  for (const link of document.querySelectorAll('[data-nav]')) if (link.dataset.nav === flow) link.setAttribute('aria-current', 'page');
  window.addEventListener('pagehide', () => { ready = false; invalidate(); });
  async function loadOptions() {
    const current = version;
    generate.disabled = true;
    try {
      const response = await fetch(`/api/options/${flow}`, {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar as bases');
      if (current !== version) return;
      record.replaceChildren(new Option('Selecione um gestor ou preenchimento manual', ''));
      for (const item of data.options) record.add(new Option(`${item.label} — ${item.polo_count} polo(s)`, item.id));
      record.disabled = !data.options.length;
      message('Selecione um gestor ou o preenchimento manual. Dados manuais não serão salvos nas bases.');
    } catch (error) {
      if (current === version) message(error.message, true);
    }
  }
  loadOptions();
}
