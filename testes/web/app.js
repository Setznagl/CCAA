'use strict';
const flow = document.body.dataset.flow;
const form = document.querySelector('#form');
const record = document.querySelector('#record');
const referenceDate = document.querySelector('#reference-date');
const generate = document.querySelector('#generate');
const status = document.querySelector('#status');
const download = document.querySelector('#download');
const frame = document.querySelector('#preview');
const resultLabel = document.querySelector('#result-label');
let blobUrl = null;
let generation = 0;


function message(text, error = false) {
  status.setAttribute('role', error ? 'alert' : 'status');
  status.textContent = text;
}

function clearDownload() {
  if (blobUrl) URL.revokeObjectURL(blobUrl);
  blobUrl = null;
  download.removeAttribute('href');
  download.setAttribute('aria-disabled', 'true');
  download.tabIndex = -1;
}

function invalidate() {
  generation++;
  clearDownload();
  generate.disabled = false;
}

for (const link of document.querySelectorAll('[data-nav]')) {
  if (link.dataset.nav === flow) link.setAttribute('aria-current', 'page');
}
document.querySelector('#record-label').textContent = flow === 'mari' ? 'Gerente / grupo de destinatário' : 'Polo';
document.querySelector('#date-control').hidden = flow !== 'mari';

async function load() {
  try {
    const response = await fetch(`/api/options/${flow}`, {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar as bases');
    record.replaceChildren(new Option('Selecione um registro', ''));
    for (const item of data.options) {
      const count = flow === 'mari' ? ` — ${item.polo_count} polo(s)` : '';
      record.add(new Option(item.label + count, item.id));
    }
    referenceDate.value = data.today;
    record.disabled = !data.options.length;
    generate.disabled = !data.options.length;
    message(data.options.length ? `${data.options.length} registro(s) disponível(is). Selecione e gere uma prévia.` : 'Nenhum registro disponível nas bases.');
  } catch (error) {
    record.replaceChildren(new Option('Bases indisponíveis', ''));
    message(error.message, true);
  }
}

form.addEventListener('change', () => {
  invalidate();
  if (record.value) message('Seleção alterada. Gere o HTML para atualizar a prévia e o download.');
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  invalidate();
  const requestGeneration = generation;
  const id = record.value;
  const date = referenceDate.value;
  const label = record.selectedOptions[0].textContent;
  generate.disabled = true;
  message('Gerando HTML com os dados selecionados…');
  try {
    const parameters = new URLSearchParams({id, date});
    const response = await fetch(`/api/render/${flow}?${parameters}`, {cache: 'no-store'});
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Não foi possível gerar o HTML');
    }
    const html = await response.text();
    if (requestGeneration !== generation) return;
    frame.src = `/api/render/${flow}?${parameters}`;
    blobUrl = URL.createObjectURL(new Blob([html], {type: 'text/html;charset=utf-8'}));
    download.href = blobUrl;
    download.download = `ccaa-${flow}-${id.replace(/[^a-z0-9_-]/gi, '_')}.html`;
    download.setAttribute('aria-disabled', 'false');
    download.tabIndex = 0;
    resultLabel.textContent = label;
    message('HTML gerado. Confira a prévia ou baixe o arquivo. Nenhum email foi enviado.');
  } catch (error) {
    if (requestGeneration === generation) message(error.message, true);
  } finally {
    if (requestGeneration === generation) generate.disabled = false;
  }
});
window.addEventListener('pagehide', invalidate);
load();
