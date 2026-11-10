"""HTTP review contract with disposable new-source XLSX fixtures."""
import copy
from contextlib import closing
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_server import make_server
from test_mari_new_sources import sources


class MariApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        sources(self.temp.name)
        self.server = make_server(self.temp.name, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()

    def request(self, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request('POST' if body is not None else 'GET', path,
                           json.dumps(body) if body is not None else None,
                           headers or ({'Content-Type': 'application/json'} if body is not None else {}))
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_reviewed_post_snapshot_is_exact_and_get_cannot_bypass_review(self):
        originals = {p: p.read_bytes() for p in Path(self.temp.name).rglob('*.xlsx')}
        status, _, body = self.request('/api/options/mari')
        self.assertEqual(status, 200, body)
        options = json.loads(body)['options']
        identity = next(o['id'] for o in options if o['label'] == 'GO Válido')
        status, _, body = self.request('/api/draft/mari?id=' + identity)
        self.assertEqual(status, 200, body)
        data = json.loads(body)
        self.assertEqual(data['source_cycles'], ['262'])
        self.assertTrue(data['warnings'])
        draft = data['draft']
        payload = {'id': identity, 'draft': draft, 'date': '2026-11-01'}
        self.assertEqual(self.request('/api/render/mari?id=' + identity)[0], 405)
        self.assertEqual(self.request('/api/render/mari?id=' + identity + '&download=1')[0], 405)
        self.assertEqual(self.request('/api/render/mari', payload)[0], 400)
        draft.update(reviewed=True, label='GO <Revisado>', email='go@example.org')
        for row in draft['rows']: row['grupo'] = 'G <Manual>'
        payload['source_cycles'] = ['999']; payload['warnings'] = ['inventado']
        status, headers, html = self.request('/api/render/mari', payload)
        self.assertEqual(status, 200, html)
        self.assertIn(b'GO &lt;Revisado&gt;', html)
        self.assertNotIn(b'go@example.org', html)
        self.assertNotIn(b'inventado', html)
        preview = headers['X-Preview-URL']
        self.assertRegex(preview, r'^/api/preview/[a-f0-9]{32}$')
        self.assertEqual(self.request(preview)[2], html)
        status, headers, downloaded = self.request(preview + '?download=1')
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, html)
        self.assertIn('attachment;', headers['Content-Disposition'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        draft['label'] = 'Mudou'
        self.assertEqual(self.request(preview)[2], html)
        self.assertEqual(self.request('/api/draft/mari?id=' + identity)[2], body)
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)

    def test_page_loads_dedicated_review_script_and_identifies_module(self):
        status, _, page = self.request('/mari')
        self.assertEqual(status, 200)
        self.assertIn(b'<script src="/mari.js" defer></script>', page)
        self.assertIn(b'preview_AGENDA_SEMANAL_AUDITORIAS.py', page)
        self.assertEqual(self.request('/mari.js')[0], 200)

    def test_invalid_forms_and_local_security_are_rejected(self):
        self.assertEqual(self.request('/api/render/mari', {'id':'1','draft':{}}, {'Content-Type':'text/plain'})[0], 415)
        self.assertEqual(self.request('/api/render/mari', {}, {'Content-Type':'application/json', 'Origin':'https://evil.example'})[0], 403)
        for bad in [[], {}, {'id':'missing','draft':{}}, {'id':None,'draft':{}}]:
            self.assertIn(self.request('/api/render/mari', bad)[0], (400, 404))
        self.assertEqual(self.request('/api/preview/not-found')[0], 404)
        # The server rejects oversized headers before reading the body; sending
        # a full MiB races its connection close and can break the test client.
        with closing(http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)) as connection:
            connection.putrequest('POST', '/api/render/mari')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader('Content-Length', str(1024 * 1024 + 1))
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            self.assertIn('limite', json.loads(response.read())['error'])


if __name__ == '__main__': unittest.main()
