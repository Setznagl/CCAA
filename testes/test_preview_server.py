import importlib
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class PreviewServerTests(unittest.TestCase):
    def test_four_test_pages_follow_current_flow_names(self):
        try:
            server_module = importlib.import_module('preview_server')
        except ModuleNotFoundError:
            self.fail('O servidor das duas páginas de teste ainda não existe')
        server = server_module.make_server(ROOT, port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            names = {
                '/mari': 'Agenda Semanal de Auditorias',
                '/aulas-praticas': 'Agenda de Regularização da Auditoria Acadêmica',
                '/fast-track-infra-2026': 'Agenda Fast Track Infra 2026',
                '/auditoria-situacao-polos': 'Agenda de Auditoria e Situação de Regularização dos Polos',
            }
            for route, heading in names.items():
                with self.subTest(route=route):
                    with urlopen(base + route, timeout=10) as response:
                        html = response.read().decode()
                        self.assertEqual(response.status, 200)
                        self.assertIn('<title>CCAA — ' + heading + '</title>', html)
                        self.assertIn('<h1 id="page-title">' + heading + '</h1>', html)
                        for label in names.values():
                            self.assertIn('>' + label + '</a>', html)
                        if route == '/aulas-praticas':
                            self.assertIn('<code>AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA</code>', html)
                        self.assertIn('id="generate"', html)
                        self.assertIn('id="preview"', html)
                        self.assertIn('sandbox', html)
                        self.assertIn('id="download"', html)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_aulas_api_and_download_match_original_renderer(self):
        import preview_server
        from preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA import load_aulas, render_aulas
        server = preview_server.make_server(ROOT, port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            import json
            with urlopen(base + '/api/options/aulas-praticas', timeout=30) as response:
                data = json.load(response)
            self.assertTrue(any(x['id'] == '11815820' for x in data['options']))
            self.assertTrue(all(set(x) == {'id', 'label', 'polo_count'} for x in data['options']))
            from preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA import draft_aulas, review_aulas
            route = '/api/render/aulas-praticas?id=11815820&date=2026-09-11'
            with self.assertRaises(HTTPError) as refused:
                urlopen(base + route, timeout=30)
            self.assertEqual(refused.exception.code, 405)
            refused.exception.close()
            model = load_aulas(ROOT / 'databases/09-11-26')['11815820']
            draft = draft_aulas(model)
            draft.update(prazo_praticas='2026-12-15', prazo_auditoria='2026-12-16', reviewed=True)
            if not draft['labs_lista']:
                draft['labs_status'] = 'nao_aplicavel'
            for lab in draft['labs_lista']:
                lab['nome'] = lab['nome'] or 'Laboratório de teste'
                lab['parecer'] = lab['parecer'] or 'Parecer de teste'
            request = Request(base + '/api/render/aulas-praticas', data=json.dumps({'id': '11815820', 'draft': draft}).encode(), headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=30) as response:
                html = response.read()
                snapshot = response.headers['X-Preview-URL']
                self.assertIn('sandbox', response.headers['Content-Security-Policy'])
            expected = render_aulas(review_aulas(draft, model)).encode()
            self.assertEqual(html, expected)
            with urlopen(base + snapshot + '?download=1', timeout=30) as response:
                self.assertEqual(response.read(), html)
                self.assertIn('attachment;', response.headers['Content-Disposition'])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_source_files_transports_and_cross_site_requests_are_not_exposed(self):
        import preview_server
        server = preview_server.make_server(ROOT, port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            cases = [
                (Request(base + '/fluxos/AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA/emails.xlsx'), 404),
                (Request(base + '/api/send', method='POST', data=b''), 405),
                (Request(base + '/api/options/aulas-praticas', headers={'Host': 'evil.invalid'}), 403),
                (Request(base + '/mari', headers={'Sec-Fetch-Site': 'cross-site'}), 403),
                (Request(base + '/api/options/unknown'), 404),
            ]
            for request, expected in cases:
                with self.subTest(url=request.full_url):
                    with self.assertRaises(HTTPError) as error:
                        urlopen(request, timeout=10)
                    self.assertEqual(error.exception.code, expected)
                    error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
