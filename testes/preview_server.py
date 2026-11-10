"""Local, read-only HTML preview server. No mail transport is loaded."""
import argparse
from collections import OrderedDict
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit
import uuid
from gerencial import key as directory_key, load_directory, recipients, review_recipients, support_contacts

FLOW_PAGES = {
    '/mari': ('mari', 'Agenda Semanal de Auditorias', 'AGENDA_SEMANAL_AUDITORIAS',
              'Agenda e contatos de databases/09-11-26. Revise todas as datas/laboratórios e complete GO, email e grupo econômico antes de gerar. Não há filtro automático de semana; não executa VBA ou Excel.'),
    '/aulas-praticas': ('aulas-praticas', 'Agenda de Regularização da Auditoria Acadêmica', 'AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA',
                      'Lê aulas previstas e comprovadas apenas de databases/09-11-26 e mantém o layout do email. Este teste não lê destinatários nem carrega funções de envio.'),
    '/fast-track-infra-2026': ('fast-track-infra-2026', 'Agenda Fast Track Infra 2026', 'AGENDA_FAST_TRACK_INFRA_2026',
                             'Modelo fixo baseado no exemplo_email.pdf. Sem campos ou leitura das planilhas. Prazo 31/08 preservado do exemplo de 2026; não é um prazo atualizado.'),
    '/auditoria-situacao-polos': ('auditoria-situacao-polos', 'Agenda de Auditoria e Situação de Regularização dos Polos',
                                'AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS',
                                'Reutiliza as bases locais e permite completar ou revisar os dados antes de gerar. 262 e 26.2 são o mesmo semestre; o semestre das fontes continua identificado na prévia.'),
}
HTML_POLICY = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; sandbox"
PAGE_POLICY = "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'self'"


def source_file(root, folder, legacy, filename):
    """Accept the renamed flow and preserved pre-pull sources."""
    paths = [Path(root) / 'fluxos' / name / filename for name in (folder, legacy)]
    return next((path for path in paths if path.is_file()), paths[0])


def make_server(root, port=8876):
    root = Path(root).resolve()
    web = Path(__file__).resolve().parent / 'web'
    cache = {}
    snapshots = OrderedDict()
    lock = threading.Lock()

    def models(flow):
        with lock:
            if flow not in cache:
                if '_directory' not in cache:
                    cache['_directory'] = load_directory(root / 'databases/09-11-26')
                if flow == 'mari':
                    from preview_AGENDA_SEMANAL_AUDITORIAS import load_mari
                    cache[flow] = load_mari(root, cache['_directory'])
                elif flow == 'aulas-praticas':
                    from preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA import load_aulas
                    cache[flow] = load_aulas(root / 'databases/09-11-26')
                elif flow == 'auditoria-situacao-polos':
                    from preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS import load_consolidado
                    cache[flow] = load_consolidado(root)
                else:
                    raise ValueError('Frente desconhecida')
            return cache[flow]

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body=b'', kind='text/plain; charset=utf-8', policy=PAGE_POLICY, download=None, headers=None):
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', policy)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            if download:
                self.send_header('Content-Disposition', f'attachment; filename="{download}"')
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def json_reply(self, status, data):
            self.reply(status, json.dumps(data, ensure_ascii=False), 'application/json; charset=utf-8')

        def local_request(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origin = self.headers.get('Origin')
            if (self.headers.get('Host') not in allowed
                    or self.headers.get('Sec-Fetch-Site') == 'cross-site'
                    or (origin and origin not in {'http://' + host for host in allowed})):
                self.json_reply(403, {'error': 'Acesso permitido apenas pelo endereço local deste teste'})
                return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            target = urlsplit(self.path)
            path = target.path
            if path == '/':
                self.send_response(302)
                self.send_header('Location', '/mari')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if path == '/favicon.ico':
                self.reply(204)
                return
            if path == '/api/lote/modelo.xlsx':
                from lote import spreadsheet_template
                self.reply(200, spreadsheet_template(),
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           download='destinatarios-fast-track.xlsx')
                return
            if path == '/api/lote/fast-track':
                from lote import fast_track_batch
                try:
                    self.json_reply(200, fast_track_batch(root))
                except Exception:
                    self.json_reply(503, {'error': 'Não foi possível carregar os reprovados. Confira a base Fast Track, a gerencial e os cadastros de contatos.'})
                return
            if path == '/fast-track-infra-2026/lote':
                self.reply(200, (web / 'lote.html').read_bytes(), 'text/html; charset=utf-8')
                return
            if path in FLOW_PAGES:
                flow, heading, folder, note = FLOW_PAGES[path]
                static = flow == 'fast-track-infra-2026'
                body = (web / 'page.html').read_text(encoding='utf-8')
                for key, value in {'FLOW': flow, 'HEADING': heading, 'FOLDER': folder, 'NOTE': note,
                                   'BATCH_BUTTON': ('<a id="batch-open" class="download" href="/fast-track-infra-2026/lote">DIsparo em lote</a>' if static else ''),
                                   'RECORD_STATE': 'hidden disabled' if static else '',
                                   'GENERATE_STATE': '' if static else 'disabled',
                                   'INITIAL_STATUS': 'Modelo estático pronto para gerar.' if static else 'Lendo as bases recebidas…',
                                   'EXTRA_SCRIPT': ('<script src="/consolidado.js" defer></script>' if flow == 'auditoria-situacao-polos'
                                                    else '<script src="/mari.js" defer></script>' if flow == 'mari'
                                                    else '<script src="/aulas.js" defer></script>' if flow == 'aulas-praticas' else '')}.items():
                    body = body.replace('__' + key + '__', value)
                self.reply(200, body, 'text/html; charset=utf-8')
                return
            if path.startswith('/fonts/') and path.endswith('.woff2'):
                target = web / 'fonts' / Path(path).name
                if target.is_file() and target.parent == (web / 'fonts'):
                    self.reply(200, target.read_bytes(), 'font/woff2')
                else:
                    self.reply(404)
                return
            if path in {'/app.js', '/app.css', '/steps.js', '/contacts.js', '/consolidado.js', '/mari.js', '/aulas.js',
                        '/lote.js', '/lote.css'}:
                kind = 'text/javascript' if path.endswith('.js') else 'text/css'
                self.reply(200, (web / path[1:]).read_bytes(), kind + '; charset=utf-8')
                return
            try:
                pieces = path.strip('/').split('/')
                if len(pieces) == 3 and pieces[:2] == ['api', 'preview']:
                    with lock:
                        snapshot = snapshots.get(pieces[2])
                    if snapshot is None:
                        self.json_reply(404, {'error': 'Prévia expirada ou inexistente. Gere o HTML novamente.'})
                        return
                    html, filename = snapshot
                    args = parse_qs(target.query, max_num_fields=4)
                    self.reply(200, html, 'text/html; charset=utf-8', HTML_POLICY,
                               filename if args.get('download') == ['1'] else None)
                    return
                if len(pieces) != 3 or pieces[0] != 'api' or pieces[1] not in {'options', 'render', 'draft'}:
                    self.json_reply(404, {'error': 'Página não encontrada'})
                    return
                action, flow = pieces[1:]
                if flow not in {page[0] for page in FLOW_PAGES.values()}:
                    self.json_reply(404, {'error': 'Frente não encontrada'})
                    return
                if flow == 'fast-track-infra-2026':
                    if action != 'render':
                        self.json_reply(404, {'error': 'Este modelo estático não usa seleção de registros'})
                        return
                    args = parse_qs(target.query, max_num_fields=4)
                    from preview_AGENDA_FAST_TRACK_INFRA_2026 import render_fast_track
                    html = render_fast_track(root)
                    filename = 'ccaa-fast-track-infra-2026.html' if args.get('download') == ['1'] else None
                    self.reply(200, html, 'text/html; charset=utf-8', HTML_POLICY, filename)
                    return
                records = models(flow)
                if action == 'options':
                    options = []
                    labels = [item['label'] for item in records.values()]
                    for identity, item in records.items():
                        label = item['label']
                        if labels.count(label) > 1:
                            draft = item['draft']
                            polos = draft.get('polos') or [r['polo'] for r in draft.get('rows', [])]
                            email = cache['_directory']['polos'].get(directory_key(polos[0]), {}).get('email', '') if polos else ''
                            label += ' — ' + (email or 'email pendente')
                        options.append({'id': identity, 'label': label, 'polo_count': item['polo_count']})
                    self.json_reply(200, {'today': date.today().isoformat(), 'options': options})
                    return
                args = parse_qs(target.query, max_num_fields=4)
                identity = args.get('id', [''])[0]
                if len(identity) > 100 or identity not in records:
                    self.json_reply(404, {'error': 'Selecione um registro disponível nas bases'})
                    return
                if action == 'draft':
                    if flow == 'aulas-praticas':
                        from preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA import draft_aulas
                        draft = draft_aulas(records[identity])
                        draft['destinatarios'] = recipients([records[identity]['nome']], cache['_directory'])
                        self.json_reply(200, {'draft': draft, 'auditores': cache['_directory']['auditores'],
                                             'warnings': ['Sem linhas na timeline não comprova ausência de auditoria. As fontes não certificam prazos vigentes.']})
                        return
                    if flow not in {'auditoria-situacao-polos', 'mari'}:
                        self.json_reply(404, {'error': 'Esta frente não possui formulário complementar'})
                        return
                    record = records[identity]
                    draft = dict(record['draft'])
                    if flow == 'auditoria-situacao-polos':
                        draft['destinatarios'] = recipients(draft['polos'], cache['_directory'])
                        draft['contatos'] = [dict(contact, origem=index) for index, contact in enumerate(draft['contatos'])]
                    self.json_reply(200, {'draft': draft, 'warnings': record['warnings'],
                                         'source_cycles': record['source_cycles'], 'auditores': cache['_directory']['auditores']})
                    return
                if flow in {'auditoria-situacao-polos', 'mari', 'aulas-praticas'}:
                    self.json_reply(405, {'error': 'Use o formulário para gerar esta prévia com POST'})
                    return

            except ValueError as exc:
                self.json_reply(400, {'error': str(exc)})
            except Exception as exc:
                self.json_reply(503, {'error': 'Não foi possível ler as bases ou gerar o HTML: ' + str(exc)})

        def do_POST(self):
            if not self.local_request():
                return
            path = urlsplit(self.path).path
            if path in {'/api/lote/importar', '/api/lote/preview', '/api/lote/pacote', '/api/lote/fast-track/pacote'}:
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    self.json_reply(415, {'error': 'Envie os campos como JSON'})
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 4 * 1024 * 1024:
                        self.json_reply(413, {'error': 'Lote excede 4 MiB ou está vazio'})
                        return
                    payload = json.loads(self.rfile.read(length).decode('utf-8'))
                    if not isinstance(payload, dict):
                        raise ValueError('Formulário inválido')
                    from lote import approved_html, build_package, import_spreadsheet
                    if path == '/api/lote/importar':
                        self.json_reply(200, {'rows': import_spreadsheet(payload.get('xlsx'))})
                    elif path == '/api/lote/fast-track/pacote':
                        from lote import build_fast_track_package
                        self.reply(200, build_fast_track_package(root, payload), 'application/zip', download='ccaa-fast-track-lote.zip')
                    elif path == '/api/lote/pacote':
                        self.reply(200, build_package(payload), 'application/zip', download='ccaa-fast-track-lote.zip')
                    else:
                        html = approved_html(payload)
                        token = uuid.uuid4().hex
                        with lock:
                            snapshots[token] = (html, 'ccaa-fast-track-aprovado.html')
                            while len(snapshots) > 16:
                                snapshots.popitem(last=False)
                        self.reply(200, html, 'text/html; charset=utf-8', HTML_POLICY,
                                   headers={'X-Preview-URL': '/api/preview/' + token})
                except (ValueError, UnicodeDecodeError) as exc:
                    self.json_reply(400, {'error': str(exc)})
                except Exception:
                    self.json_reply(400, {'error': 'Não foi possível preparar o lote. Confira os arquivos e tente novamente.'})
                return
            if path not in {'/api/render/auditoria-situacao-polos', '/api/render/mari', '/api/render/aulas-praticas'}:
                self.json_reply(405, {'error': 'Este ambiente só permite leitura e geração de HTML'})
                return
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                self.json_reply(415, {'error': 'Envie os campos como JSON'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0:
                    raise ValueError('Formulário vazio')
                if length > 1024 * 1024:
                    self.json_reply(413, {'error': 'Formulário excede o limite de 1 MiB'})
                    return
                payload = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(payload, dict) or not isinstance(payload.get('id'), str) or not isinstance(payload.get('draft'), dict):
                    raise ValueError('Selecione um gestor e preencha um formulário válido')
                flow = path.rsplit('/', 1)[1]
                records = models(flow)
                identity = payload['id']
                if len(identity) > 100 or identity not in records:
                    self.json_reply(404, {'error': 'Selecione um gestor disponível ou o preenchimento manual'})
                    return
                record = records[identity]
                draft = dict(payload['draft'])
                submitted_contacts = draft.pop('destinatarios', None)
                if flow == 'aulas-praticas':
                    from preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA import review_aulas, render_aulas
                    reviewed = review_aulas(draft, record)
                    selected = [record['nome']]
                    html = render_aulas(reviewed)
                elif flow == 'mari':
                    from preview_AGENDA_SEMANAL_AUDITORIAS import review_mari, render_mari
                    reference = payload.get('date')
                    if not isinstance(reference, str) or len(reference) != 10:
                        raise ValueError('Informe a data de referência dos avisos')
                    today = date.fromisoformat(reference)
                    reviewed = review_mari(draft, record)
                    selected = list(dict.fromkeys(row['polo'] for row in reviewed['rows']))
                    html = render_mari(reviewed, today).replace('GERENTE OPERACIONAL', 'GESTOR DO POLO')
                else:
                    selected = draft.get('polos', [])
                    if not isinstance(selected, list) or any(not isinstance(polo, str) for polo in selected):
                        raise ValueError('polos: informe uma lista de nomes de polos')
                    removed = set(record['draft']['polos']) - set(selected)
                    warnings = [warning for warning in record['warnings']
                                if not any(warning.startswith(polo + ':') for polo in removed)]
                    from preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS import render_consolidado
                    reviewed_contacts = review_recipients(submitted_contacts, selected, cache['_directory'])
                    original_contacts = record['draft']['contatos']
                    entered_contacts = draft.get('contatos', [])
                    if not isinstance(entered_contacts, list):
                        raise ValueError('Contatos: informe uma lista de contatos')
                    current_contacts = support_contacts(reviewed_contacts)
                    source_contacts = support_contacts(recipients(selected, cache['_directory']))
                    draft['contatos'] = []
                    for entry in entered_contacts:
                        if not isinstance(entry, dict):
                            raise ValueError('Contato inválido')
                        contact = dict(entry)
                        origin = contact.pop('origem', None)
                        if origin is not None:
                            if type(origin) is not int or not 0 <= origin < len(original_contacts):
                                raise ValueError('Origem do contato inválida')
                            if original_contacts[origin] not in source_contacts:
                                continue
                        elif contact in original_contacts and contact not in source_contacts:
                            continue
                        draft['contatos'].append(contact)
                    draft['contatos'].extend(c for c in current_contacts
                                             if c not in original_contacts and c not in draft['contatos'])
                    sample = source_file(root, 'AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS',
                                         'SITUACAO_REGULARIZACAO_DOS_POLOS', 'sample.html')
                    html = render_consolidado(draft, sample,
                                              source_cycles=record['source_cycles'], warnings=warnings)
                if flow != 'auditoria-situacao-polos':
                    review_recipients(submitted_contacts, selected, cache['_directory'])
                token = uuid.uuid4().hex
                filename = f'ccaa-{flow}.html'
                with lock:
                    snapshots[token] = (html, filename)
                    while len(snapshots) > 16:
                        snapshots.popitem(last=False)
                self.reply(200, html, 'text/html; charset=utf-8', HTML_POLICY,
                           headers={'X-Preview-URL': '/api/preview/' + token})
            except (ValueError, UnicodeDecodeError) as exc:
                self.json_reply(400, {'error': str(exc)})
            except Exception as exc:
                self.json_reply(503, {'error': 'Não foi possível ler as bases ou gerar o HTML: ' + str(exc)})

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8876)
    args = parser.parse_args()
    try:
        server = make_server(Path(__file__).resolve().parents[1], args.port)
    except OSError as exc:
        raise SystemExit(
            f'A porta {args.port} já está em uso (provavelmente um servidor anterior ainda ativo).\n'
            f'Encerre o processo antigo antes de subir outro; uma única porta atende todos os templates.\n'
            f'Detalhe: {exc}')
    print(f'CCAA: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
