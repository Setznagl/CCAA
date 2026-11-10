'use strict';
// Shared review of recipient data; kept outside the generated email HTML.
window.CCAAContacts = (() => {
  let rows = new Map(), auditors = [], root, known, gaps, selectedPolos = [];
  function node(tag, text) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function mount(parent, draft, choices) {
    root?.remove(); rows = new Map(); auditors = choices || [];
    root = node('fieldset'); root.id = 'recipient-review';
    root.append(node('legend', 'Destinatários e cópias — somente conferência, sem envio'));
    known = node('details');
    const summary = node('summary', 'Contatos preenchidos pela base');
    known.append(summary); root.append(known);
    gaps = node('div'); root.append(gaps);
    for (const source of draft.destinatarios || []) addRow(source);
    root.append(node('p', 'Contatos repetidos são exibidos uma vez. Lacunas são revisadas por polo; escolhas não são salvas nas bases. Emails múltiplos: separar por ponto e vírgula.'));
    root.addEventListener('change', () => sync(selectedPolos));
    parent.append(root);
  }
  function addRow(source) {
      const item = {source, controls: {}, section: node('fieldset')};
      item.section.dataset.recipientPolo = source.polo;
      item.section.append(node('legend', source.polo));
      let missing = false;
      for (const [field, label] of [['gestor', 'Gestor do polo'], ['email', 'Email do gestor'],
          ['negocios_nome', 'Gerente de negócios'], ['negocios_email', 'Email — negócios'],
          ['infra_nome', 'Consultor de infraestrutura'], ['infra_email', 'Email — infraestrutura']]) {
        const value = source[field] || '';
        if (!value) {
          missing = true;
          const control = node('input'); control.type = 'text'; control.value = '';
          control.maxLength = 1000; control.dataset.recipientField = field;
          control.required = field === 'gestor' || field === 'email';
          control.id = `recipient-${rows.size}-${field}`;
          const caption = node('label', label + (control.required ? ' — obrigatório' : ' — não informado; revise a cópia'));
          caption.htmlFor = control.id; item.section.append(caption, control);
          item.controls[field] = control;
        }
      }
      if (!source.academico_nome) {
        missing = true;
        const select = node('select'); select.required = true;
        select.id = `recipient-${rows.size}-academico`; select.dataset.recipientField = 'academico_nome';
        select.add(new Option('Escolha o auditor acadêmico deste polo', ''));
        for (const auditor of auditors) select.add(new Option(auditor.nome, auditor.nome));
        const caption = node('label', 'Auditor acadêmico — sem vínculo na base'); caption.htmlFor = select.id;
        item.section.append(caption, select); item.controls.academico_nome = select;
      }
      if (missing) gaps.append(item.section);
      rows.set(source.polo, item);
  }
  function sync(polos) {
    if (!root) return;
    for (const polo of new Set(polos)) if (!rows.has(polo)) addRow({polo});
    selectedPolos = [...new Set(polos)];
    const selected = new Set(polos);
    for (const [polo, item] of rows) {
      item.section.disabled = !selected.has(polo); item.section.hidden = !selected.has(polo);
    }
    known.replaceChildren(node('summary', 'Contatos preenchidos — polos selecionados'));
    const seen = new Set();
    for (const row of read(selectedPolos)) {
      for (const [label, name, email] of [['Gestor do polo', row.gestor, row.email],
          ['Gerente de negócios', row.negocios_nome, row.negocios_email],
          ['Infraestrutura', row.infra_nome, row.infra_email],
          ['Auditoria acadêmica', row.academico_nome, row.academico_email]]) {
        if (!name && !email) continue;
        const text = `${label}: ${name || 'Nome não informado'} — ${email || 'Email não informado'}`;
        if (!seen.has(text)) { known.append(node('p', text)); seen.add(text); }
      }
    }
  }
  function read(polos) {
    return [...new Set(polos)].map(polo => {
      const item = rows.get(polo);
      const value = item ? {...item.source} : {polo};
      if (item) for (const [field, input] of Object.entries(item.controls)) value[field] = input.value;
      value.academico_email = auditors.find(a => a.nome === value.academico_nome)?.email || '';
      return value;
    });
  }
  return {mount, sync, read};
})();
