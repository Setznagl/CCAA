"""Local, read-only HTML preview server. No mail transport is loaded."""
import argparse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit

FLOW_PAGES = {
    '/mari': ('mari', 'Auditoria Mari', 'AGENDA_SEMANAL_AUDITORIAS',
              'Reprodução isolada do HTML de Mari; não executa VBA ou Excel.'),
    '/aulas-praticas': ('aulas-praticas', 'Aulas práticas', 'REGULARIZACAO_AUDITORIA_ACADEMICA',
                      'Reutiliza as funções de dados e HTML do Python atual. Este teste do corpo não lê destinatários nem carrega funções de envio.'),
}
HTML_POLICY = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; sandbox"
PAGE_POLICY = "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'self'"


def make_server(root, port=8876):
    root = Path(root).resolve()
    web = Path(__file__).resolve().parent / 'web'
    cache = {}
    lock = threading.Lock()

    def models(flow):
        with lock:
            if flow not in cache:
                if flow == 'mari':
                    from preview_mari import load_mari
                    cache[flow] = load_mari(root / 'fluxos/AGENDA_SEMANAL_AUDITORIAS')
                elif flow == 'aulas-praticas':
                    from preview_aulas import load_aulas
                    cache[flow] = load_aulas(root / 'fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA')
                else:
                    raise ValueError('Frente desconhecida')
            return cache[flow]

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body=b'', kind='text/plain; charset=utf-8', policy=PAGE_POLICY, download=None):
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
            self.end_headers()
            self.wfile.write(body)

        def json_reply(self, status, data):
            self.reply(status, json.dumps(data, ensure_ascii=False), 'application/json; charset=utf-8')

        def do_GET(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.json_reply(403, {'error': 'Acesso permitido apenas pelo endereço local deste teste'})
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
            if path in FLOW_PAGES:
                flow, heading, folder, note = FLOW_PAGES[path]
                body = (web / 'page.html').read_text(encoding='utf-8')
                for key, value in {'FLOW': flow, 'HEADING': heading, 'FOLDER': folder, 'NOTE': note}.items():
                    body = body.replace('__' + key + '__', value)
                self.reply(200, body, 'text/html; charset=utf-8')
                return
            if path in {'/app.js', '/app.css'}:
                kind = 'text/javascript' if path.endswith('.js') else 'text/css'
                self.reply(200, (web / path[1:]).read_bytes(), kind + '; charset=utf-8')
                return
            try:
                pieces = path.strip('/').split('/')
                if len(pieces) != 3 or pieces[0] != 'api' or pieces[1] not in {'options', 'render'}:
                    self.json_reply(404, {'error': 'Página não encontrada'})
                    return
                action, flow = pieces[1:]
                if flow not in {'mari', 'aulas-praticas'}:
                    self.json_reply(404, {'error': 'Frente não encontrada'})
                    return
                records = models(flow)
                if action == 'options':
                    self.json_reply(200, {'today': date.today().isoformat(), 'options': [
                        {'id': key, 'label': item['label'], 'polo_count': item['polo_count']}
                        for key, item in records.items()
                    ]})
                    return
                args = parse_qs(target.query, max_num_fields=4)
                identity = args.get('id', [''])[0]
                if len(identity) > 100 or identity not in records:
                    self.json_reply(404, {'error': 'Selecione um registro disponível nas bases'})
                    return
                today = date.fromisoformat(args.get('date', [date.today().isoformat()])[0])
                if flow == 'mari':
                    from preview_mari import render_mari
                    html = render_mari(records[identity], today)
                else:
                    from preview_aulas import render_aulas
                    html = render_aulas(records[identity])
                filename = f'ccaa-{flow}-{today.isoformat()}.html' if args.get('download') == ['1'] else None
                self.reply(200, html, 'text/html; charset=utf-8', HTML_POLICY, filename)
            except ValueError as exc:
                self.json_reply(400, {'error': str(exc)})
            except Exception as exc:
                self.json_reply(503, {'error': 'Não foi possível ler as bases ou gerar o HTML: ' + str(exc)})

        def do_POST(self):
            self.json_reply(405, {'error': 'Este ambiente só permite leitura e geração de HTML'})

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8876)
    args = parser.parse_args()
    server = make_server(Path(__file__).resolve().parents[1], args.port)
    print(f'CCAA: http://127.0.0.1:{server.server_port}/mari', flush=True)
    print(f'CCAA: http://127.0.0.1:{server.server_port}/aulas-praticas', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
