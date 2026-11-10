"""HTTP regressions for modern flow names and editable preview snapshots."""
import json
from html import escape
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from preview_server import make_server


class NewPreviewServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = make_server(self.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        self.temp.cleanup()

    def request(self, path, payload=None, headers=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(self.base + path, data=data, headers=headers or ({'Content-Type': 'application/json'} if data is not None else {}))
        try:
            response = urlopen(request, timeout=15)
        except HTTPError as exc:
            response = exc
        with response:
            return response.code, dict(response.headers), response.read()

    def test_modern_fast_track_folder_is_served_without_databases(self):
        folder = self.root / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026'
        folder.mkdir(parents=True)
        expected = '<!doctype html><html><body>Modelo fixo</body></html>'
        (folder / 'modelo_email.html').write_text(expected)
        with patch('pandas.read_excel', side_effect=AssertionError('Não ler bases')):
            status, headers, body = self.request('/api/render/fast-track-infra-2026')
        self.assertEqual(status, 200, body.decode())
        self.assertEqual(body.decode(), expected)
        self.assertIn('sandbox', headers['Content-Security-Policy'])

    def backend(self):
        draft = {'gestor': 'Gestor de teste', 'ciclo': '261', 'polos': ['Polo de teste']}
        record = {'label': 'Gestor de teste', 'polo_count': 1, 'draft': draft,
                  'warnings': ['Fonte 261'], 'source_cycles': ['261']}

        def render(draft, sample_path, source_cycles=(), warnings=()):
            return '<html><body style="margin:0">' + escape(draft['gestor']) + ':' + ','.join(source_cycles) + '</body></html>'

        return SimpleNamespace(load_consolidado=lambda root: {'gestor': record}, render_consolidado=render)

    def test_draft_and_post_return_an_isolated_exact_snapshot(self):
        with patch.dict('sys.modules', {'preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS': self.backend()}):
            status, _, raw = self.request('/api/options/auditoria-situacao-polos')
            self.assertEqual(status, 200, raw.decode())
            self.assertEqual(json.loads(raw)['options'][0]['id'], 'gestor')
            status, _, raw = self.request('/api/draft/auditoria-situacao-polos?id=gestor')
            self.assertEqual(status, 200)
            model = json.loads(raw)
            self.assertEqual(model['source_cycles'], ['261'])
            self.assertEqual(model['warnings'], ['Fonte 261'])
            model['draft']['gestor'] = 'Manual <não é HTML>'
            model['draft']['ciclo'] = '262'
            status, headers, html = self.request('/api/render/auditoria-situacao-polos', {'id': 'gestor', 'draft': model['draft']})
            self.assertEqual(status, 200, html.decode())
            self.assertIn('Manual &lt;não é HTML&gt;:261', html.decode())
            url = headers['X-Preview-URL']
            self.assertTrue(url.startswith('/api/preview/'))
            status, frame_headers, snapshot = self.request(url)
            self.assertEqual(status, 200)
            self.assertEqual(snapshot, html)
            self.assertIn('sandbox', frame_headers['Content-Security-Policy'])
            status, download_headers, downloaded = self.request(url + '?download=1')
            self.assertEqual(status, 200)
            self.assertEqual(downloaded, html)
            self.assertIn('attachment;', download_headers['Content-Disposition'])
            self.assertNotIn('Manual', url)

    def test_removed_polo_does_not_leak_through_source_warnings(self):
        backend = self.backend()
        records = backend.load_consolidado(self.root)
        records['gestor']['warnings'] = ['Polo de teste: práticas ausentes', 'Fonte real 261']
        backend.load_consolidado = lambda root: records
        backend.render_consolidado = Mock(return_value='<html><body>Prévia</body></html>')
        with patch.dict('sys.modules', {'preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS': backend}):
            status, _, _ = self.request('/api/render/auditoria-situacao-polos',
                                       {'id': 'gestor', 'draft': {'gestor': 'Manual', 'polos': ['Polo mantido']}})
        self.assertEqual(status, 200)
        self.assertEqual(backend.render_consolidado.call_args.kwargs['warnings'], ['Fonte real 261'])

    def test_post_rejects_foreign_origins_invalid_payloads_and_oversize(self):
        route = '/api/render/auditoria-situacao-polos'
        cases = [
            ({'id': 'gestor', 'draft': {}}, {'Content-Type': 'application/json', 'Host': 'evil.invalid'}, 403),
            ({'id': 'gestor', 'draft': {}}, {'Content-Type': 'application/json', 'Origin': 'https://evil.invalid'}, 403),
            ({'id': 'gestor', 'draft': {}}, {'Content-Type': 'application/json', 'Sec-Fetch-Site': 'cross-site'}, 403),
            ({'id': 'gestor', 'draft': {}}, {'Content-Type': 'text/plain'}, 415),
            ({'id': 'gestor', 'draft': {}}, {'Content-Type': 'application/json', 'Content-Length': str(1024 * 1024 + 1)}, 413),
            ([], None, 400),
            ({'id': 'gestor', 'draft': []}, None, 400),
            ({'id': 5, 'draft': {}}, None, 400),
            ({'id': 'desconhecido', 'draft': {}}, None, 404),
        ]
        with patch.dict('sys.modules', {'preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS': self.backend()}):
            for payload, headers, expected in cases:
                with self.subTest(payload=payload, expected=expected):
                    status, _, _ = self.request(route, payload, headers)
                    self.assertEqual(status, expected)
            request = Request(self.base + route, data=b'{', headers={'Content-Type': 'application/json'})
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=10)
            self.assertEqual(error.exception.code, 400)
            error.exception.close()

    def test_snapshots_are_bounded_and_render_does_not_mutate_loaded_data(self):
        with patch.dict('sys.modules', {'preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS': self.backend()}):
            urls = []
            for number in range(17):
                status, headers, _ = self.request('/api/render/auditoria-situacao-polos',
                                                  {'id': 'gestor', 'draft': {'gestor': f'Manual {number}'}})
                self.assertEqual(status, 200)
                urls.append(headers['X-Preview-URL'])
            self.assertEqual(len(set(urls)), 17)
            self.assertEqual(self.request(urls[0])[0], 404)
            self.assertEqual(self.request(urls[-1])[0], 200)
            status, _, raw = self.request('/api/draft/auditoria-situacao-polos?id=gestor')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['draft']['gestor'], 'Gestor de teste')
            self.assertEqual(self.request('/api/render/auditoria-situacao-polos?id=gestor')[0], 405)


if __name__ == '__main__':
    unittest.main()
