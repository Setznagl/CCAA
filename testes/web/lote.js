'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const form = $('batch-form'), status = $('status'), roster = $('batch-rows');
  const preview = $('batch-preview'), build = $('batch-build'), approved = $('batch-approved');
  let html = '', rows = [], revision = 0, htmlVersion = 0, sheetVersion = 0;
  let busy = false;
  function message(text, error = false) {
    status.textContent = text;
    status.setAttribute('role', error ? 'alert' : 'status');
  }
  function refresh() {
    const count = rows.filter(row => row.selecionado).length;
    $('batch-count').textContent = `${count} mensagem(ns) selecionada(s) de ${rows.length} linha(s).`;
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
  function drawRows() {
    roster.replaceChildren();
    rows.forEach((row, index) => {
      const fieldset = document.createElement('fieldset');
      fieldset.dataset.row = index;
      const legend = document.createElement('legend');
      legend.textContent = `Linha ${index + 1}${row.polo ? ' — ' + row.polo : ''}`;
      fieldset.append(legend);
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
        label.htmlFor = input.id; label.textContent = title;
        input.addEventListener('input', () => { row[key] = input.value; });
        group.append(label, input); fields.append(group);
      }
      selection.addEventListener('input', () => {
        row.selecionado = selection.checked;
        fields.querySelector('[data-field=para]').required = row.selecionado;
        refresh();
      });
      fieldset.append(fields); roster.append(fieldset);
    });
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
  $('batch-html').addEventListener('change', async () => {
    const version = ++htmlVersion;
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
    if (!form.reportValidity() || busy) return;
    const version = revision;
    const payload = {html, rows, remetente: $('batch-sender').value, assunto: $('batch-subject').value, aprovado: approved.checked};
    busy = true; refresh(); message('Preparando o pacote local. Nenhum email será enviado pelo site.');
    try {
      const response = await post('/api/lote/pacote', payload);
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
