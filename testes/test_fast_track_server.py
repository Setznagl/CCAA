import threading
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from preview_server import make_server


class FastTrackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        folder = root / 'fluxos/FAST_TRACK_INFRA_2026'
        folder.mkdir(parents=True)
        self.html = '<!doctype html><html lang="pt-BR"><body style="margin:0">Modelo estático de teste</body></html>'
        (folder / 'modelo_email.html').write_text(self.html, encoding='utf-8')
        self.server = make_server(root, port=0)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=5)
        self.temp.cleanup()

    def test_page_is_in_navigation_and_has_no_required_user_input(self):
        for route in ('/mari', '/aulas-praticas', '/fast-track-infra-2026'):
            with urlopen(self.base + route) as response:
                body = response.read().decode()
            self.assertIn('href="/fast-track-infra-2026"', body)
        self.assertIn('Fast Track Infra 2026', body)
        self.assertIn('id="record-controls" hidden disabled', body)
        self.assertNotIn('id="generate" type="submit" disabled', body)
        self.assertIn('id="preview"', body)
        self.assertIn('id="download"', body)
        self.assertNotIn('__RECORD_STATE__', body)

    def test_render_and_download_are_exact_static_html_without_spreadsheet_reads(self):
        with patch('pandas.read_excel', side_effect=AssertionError('Não ler bases')), patch('openpyxl.load_workbook', side_effect=AssertionError('Não ler bases')):
            with urlopen(self.base + '/api/render/fast-track-infra-2026') as response:
                self.assertEqual(response.read(), self.html.encode())
                self.assertIn('sandbox', response.headers['Content-Security-Policy'])
            with urlopen(self.base + '/api/render/fast-track-infra-2026?download=1') as response:
                self.assertEqual(response.read(), self.html.encode())
                self.assertIn('attachment;', response.headers['Content-Disposition'])
                self.assertIn('fast-track-infra-2026', response.headers['Content-Disposition'])
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + '/api/options/fast-track-infra-2026')
        self.assertEqual(error.exception.code, 404)
        error.exception.close()


if __name__ == '__main__':
    unittest.main()
