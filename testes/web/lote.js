'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const form = $('batch-form'), status = $('status'), roster = $('batch-rows');
  const preview = $('batch-preview'), build = $('batch-build'), approved = $('batch-approved');
  let html = '', rows = [], revision = 0, htmlVersion = 0, sheetVersion = 0;
  let busy = false;
  let fixedBatch = false, auditors = [];
  function message(text, error = false) {
    status.textContent = text;
    status.setAttribute('role', error ? 'alert' : 'status');
  }
  function refresh() {
    const count = rows.filter(row => row.selecionado).length;
    const pending = fixedBatch ? rows.filter(row => row.selecionado && (!row.para.trim() || !row.academico_nome)).length : 0;
    $('batch-count').textContent = `${count} mensagem(ns) selecionada(s) de ${rows.length} linha(s).${pending ? ` ${pending} polo(s) selecionado(s) com gestor ou acadêmico pendente.` : ''}`;
    $('batch-selection').hidden = !rows.length;
    $('batch-subject').disabled = fixedBatch;
    build.disabled = busy || !html || !count;
    $('batch-preview-button').disabled = !html;
  }
  function invalidate() {
    revision++;
    approved.checked = false;
    busy = false;
    refresh();
  }
  form.addEventListener('input', event => {
    if (event.target !== approved || !approved.checked) invalidate();
  });
  function filterRows() {
    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const search = normalize($('batch-search').value.trim());
    for (const fieldset of roster.children) {
      const row = rows[Number(fieldset.dataset.row)];
      fieldset.hidden = !normalize(`${row.polo} ${row.gestor || ''}`).includes(search);
    }
  }
  $('batch-search').addEventListener('input', filterRows);
  $('batch-select-visible').addEventListener('click', () => {
    for (const fieldset of roster.children) {
      if (!fieldset.hidden) rows[Number(fieldset.dataset.row)].selecionado = true;
    }
    invalidate(); drawRows();
  });
  $('batch-clear-selection').addEventListener('click', () => {
    rows.forEach(row => { row.selecionado = false; });
    invalidate(); drawRows();
  });
  function drawRows() {
    roster.replaceChildren();
    rows.forEach((row, index) => {
      const fieldset = document.createElement('fieldset');
      fieldset.dataset.row = index;
      const legend = document.createElement('legend');
      legend.textContent = `Linha ${index + 1}${row.polo ? ' — ' + row.polo : ''}`;
      fieldset.append(legend);
      if (fixedBatch) {
        const source = document.createElement('p'); source.className = 'hint';
        source.textContent = row.gestor ? `Gestor na gerencial: ${row.gestor}` : 'Gestor não localizado: complete Para manualmente.';
        fieldset.append(source);
        const reason = document.createElement('p'); reason.className = 'hint';
        reason.textContent = `Pendência: ${row.pendencias.join(' e ')}.`;
        fieldset.append(reason);
      }
      const selection = document.createElement('input');
      selection.type = 'checkbox'; selection.checked = row.selecionado; selection.dataset.field = 'selecionado';
      const selectedLabel = document.createElement('label'); selectedLabel.className = 'batch-check';
      selectedLabel.append(selection, document.createTextNode('Incluir esta mensagem'));
      fieldset.append(selectedLabel);
      const fields = document.createElement('div'); fields.className = 'batch-fields';
      for (const [key, title] of [['para', 'Para'], ['cc', 'CC'], ['cco', 'CCO'], ['assunto', 'Assunto da linha (opcional)']]) {
        const group = document.createElement('div'), label = document.createElement('label'), input = document.createElement('input');
        input.id = `batch-${index}-${key}`; input.dataset.field = key; input.value = row[key];
        input.type = 'text'; input.maxLength = key === 'assunto' ? 255 : 2000;
        input.required = key === 'para' && row.selecionado;
        label.htmlFor = input.id; label.textContent = fixedBatch && key === 'cc' ? 'CC — negócios e infraestrutura (editável)' : title;
        if (fixedBatch && key === 'assunto') label.textContent = 'Assunto do polo (preenchido automaticamente, revisável)';
        input.addEventListener('input', () => { row[key] = input.value; });
        group.append(label, input); fields.append(group);
      }
      if (fixedBatch) {
        const group = document.createElement('div'), label = document.createElement('label'), select = document.createElement('select');
        select.id = `batch-${index}-academic`; select.dataset.field = 'academico_nome';
        label.htmlFor = select.id; label.textContent = 'Acadêmico em CC — obrigatório para incluir o polo';
        select.append(new Option('Escolha um acadêmico cadastrado', ''));
        auditors.forEach(auditor => select.append(new Option(`${auditor.nome} — ${auditor.email}`, auditor.nome)));
        select.value = row.academico_nome; select.required = row.selecionado;
        const email = document.createElement('p'); email.className = 'hint';
        const showAcademic = () => { email.textContent = auditors.find(auditor => auditor.nome === select.value)?.email || 'Escolha manual necessária para incluir este polo.'; };
        showAcademic();
        select.addEventListener('input', () => { row.academico_nome = select.value; showAcademic(); refresh(); });
        group.append(label, select, email); fields.append(group);
      }
      selection.addEventListener('input', () => {
        row.selecionado = selection.checked;
        fields.querySelector('[data-field=para]').required = row.selecionado;
        if (fixedBatch) fields.querySelector('[data-field=academico_nome]').required = row.selecionado;
        refresh();
      });
      fieldset.append(fields); roster.append(fieldset);
    });
    filterRows();
    refresh();
  }
  async function post(path, data) {
    const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Não foi possível preparar o lote');
    }
    return response;
  }
  async function fileBytes(input) {
    const file = input.files[0];
    if (!file || file.size > 1024 * 1024) throw new Error('Escolha um arquivo de até 1 MiB');
    return new Uint8Array(await file.arrayBuffer());
  }
  $('batch-load-fast-track').addEventListener('click', async () => {
    const sheet = ++sheetVersion, content = ++htmlVersion;
    fixedBatch = true; html = ''; rows = []; auditors = [];
    preview.removeAttribute('src'); $('batch-search').value = '';
    invalidate(); drawRows(); message('Cruzando os polos com checklist pendente com os cadastros de contato…');
    try {
      const response = await fetch('/api/lote/fast-track');
      const data = await response.json();
      if (sheet !== sheetVersion || content !== htmlVersion) return;
      if (!response.ok) throw new Error(data.error || 'Não foi possível carregar as pendências');
      html = data.html; rows = data.rows; auditors = data.auditores;
      invalidate(); drawRows();
      message('Pendências carregadas, sem seleção automática. Revise contatos e assuntos por polo, complete o acadêmico quando faltar e confira o comunicado com prazo de 20/11/2026.');
    } catch (error) {
      if (sheet === sheetVersion && content === htmlVersion) message(error.message, true);
    }
  });
  $('batch-html').addEventListener('change', async () => {
    const version = ++htmlVersion;
    if (fixedBatch) { rows = []; fixedBatch = false; drawRows(); }
    html = ''; preview.removeAttribute('src'); invalidate();
    try {
      const bytes = await fileBytes($('batch-html'));
      const content = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
      if (!content.trim() || content.includes('\0')) throw new Error('HTML vazio ou inválido');
      if (version !== htmlVersion) return;
      html = content;
      invalidate();
      message('HTML carregado. Confira a prévia, os prazos e a renderização no Outlook antes do envio.');
      refresh();
    } catch (error) { if (version === htmlVersion) message(error.message, true); }
  });
  $('batch-xlsx').addEventListener('change', async () => {
    const version = ++sheetVersion;
    fixedBatch = false;
    rows = []; drawRows(); invalidate();
    try {
      const bytes = await fileBytes($('batch-xlsx'));
      let binary = '';
      for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
      const data = await (await post('/api/lote/importar', {xlsx: btoa(binary)})).json();
      if (version !== sheetVersion) return;
      rows = data.rows; invalidate(); drawRows();
      message('Planilha importada. Revise a seleção, Para, CC, CCO e assuntos.');
    } catch (error) { if (version === sheetVersion) message(error.message, true); }
  });
  $('batch-preview-button').addEventListener('click', async () => {
    const version = revision;
    try {
      const response = await post('/api/lote/preview', {html});
      if (version !== revision) return;
      preview.src = response.headers.get('X-Preview-URL');
      message('Prévia do HTML carregado pronta. Recursos externos estão bloqueados nesta conferência.');
    } catch (error) { if (version === revision) message(error.message, true); }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (roster.querySelector(':invalid')) { $('batch-search').value = ''; filterRows(); }
    if (!form.reportValidity() || busy) return;
    const version = revision;
    const payload = {html, rows, remetente: $('batch-sender').value, assunto: $('batch-subject').value, aprovado: approved.checked};
    busy = true; refresh(); message('Preparando o pacote local. Nenhum email será enviado pelo site.');
    try {
      const response = await post(fixedBatch ? '/api/lote/fast-track/pacote' : '/api/lote/pacote', payload);
      const blob = await response.blob();
      if (version !== revision) return;
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = 'ccaa-fast-track-lote.zip'; link.hidden = true;
      document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      message('Pacote baixado. Extraia no Windows e abra abrir.cmd; rascunhos são o padrão. Nenhum email foi enviado pelo site.');
    } catch (error) { if (version === revision) message(error.message, true); }
    finally { if (version === revision) { busy = false; refresh(); } }
  });
  window.addEventListener('pagehide', () => { revision++; htmlVersion++; sheetVersion++; });
  refresh();
})();
