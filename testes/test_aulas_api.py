import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from preview_server import make_server
from test_preview_aulas import APPS, TIMELINE, APPS_HEADERS, TIMELINE_HEADERS, POLO, sheet


class AulasManualAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        folder = root / 'databases/09-11-26'
        folder.mkdir(parents=True)
        sheet(folder / APPS, APPS_HEADERS, [[POLO, 10, None, 6]])
        sheet(folder / TIMELINE, TIMELINE_HEADERS, [])
        self.server = make_server(root, 0)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.close)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=5)

    def request(self, path, payload=None, headers=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base + path, data=data, headers=headers or ({'Content-Type': 'application/json'} if data else {}))
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read(), response.headers
        except HTTPError as exc:
            with exc:
                return exc.code, exc.read(), exc.headers

    def test_missing_fields_block_post_and_get_bypass_without_mutating_cached_source(self):
        path = '/api/draft/aulas-praticas?id=101'
        status, body, _ = self.request(path)
        self.assertEqual(status, 200)
        source = json.loads(body)
        draft = source['draft']
        self.assertEqual(draft['prazo_praticas'], '')
        self.assertEqual(draft['prazo_auditoria'], '')
        self.assertIsNone(draft['praticas']['comprovadas'])
        self.assertEqual(draft['labs_status'], '')
        render = '/api/render/aulas-praticas'
        self.assertEqual(self.request(render + '?id=101')[0], 405)
        payload = {'id': '101', 'draft': copy.deepcopy(draft)}
        self.assertEqual(self.request(render, payload)[0], 400)
        edited = payload['draft']
        edited.update(reviewed=True, prazo_praticas='2026-12-15', prazo_auditoria='2026-12-16', labs_status='informado')
        edited['praticas']['comprovadas'] = 0
        edited['labs_lista'] = [{'nome': '<script>Laboratório manual</script>', 'parecer': 'Aprovado'}]
        edited['nome'] = 'NOME INJETADO'
        payload['source_cycles'] = ['999']
        status, html, headers = self.request(render, payload)
        self.assertEqual(status, 200, html)
        self.assertIn(b'15/12/2026', html)
        self.assertNotIn(b'31/05/2026', html)
        self.assertIn(b'&lt;script&gt;Laborat', html)
        self.assertNotIn(b'NOME INJETADO', html)
        token = headers['X-Preview-URL']
        self.assertRegex(token, r'^/api/preview/[a-f0-9]+$')
        self.assertEqual(self.request(token)[1], html)
        status, downloaded, download_headers = self.request(token + '?download=1')
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, html)
        self.assertIn('attachment;', download_headers['Content-Disposition'])
        self.assertEqual(download_headers['Cache-Control'], 'no-store')
        self.assertIn('sandbox', download_headers['Content-Security-Policy'])
        self.assertEqual(json.loads(self.request(path)[1]), source)
        for value in (None, True, -1, 1.5, float('nan'), '0', {}, []):
            with self.subTest(value=value):
                edited['praticas']['comprovadas'] = value
                self.assertEqual(self.request(render, payload)[0], 400)
        self.assertEqual(self.request(render, payload, {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request(render, {'id': '101', 'draft': {}, 'padding': 'x' * (1024 * 1024)})[0], 413)


if __name__ == '__main__':
    unittest.main()
