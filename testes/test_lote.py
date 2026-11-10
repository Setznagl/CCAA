"""Batch preparation stays local and cannot load an email transport."""
from contextlib import closing
import http.client
from io import BytesIO
import json
from pathlib import Path
import threading
import unittest
import zipfile

from openpyxl import Workbook, load_workbook
from preview_server import make_server


class BatchHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(Path(__file__).resolve().parents[1], 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        with closing(http.client.HTTPConnection('127.0.0.1', self.server.server_port)) as connection:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def test_batch_entry_only_on_fast_track(self):
        status, _, body = self.request('GET', '/fast-track-infra-2026')
        self.assertEqual(status, 200)
        self.assertIn(b'DIsparo em lote', body)
        self.assertLess(body.index(b'id="download"'), body.index(b'id="batch-open"'))
        for route in ('/mari', '/aulas-praticas', '/auditoria-situacao-polos'):
            status, _, body = self.request('GET', route)
            self.assertEqual(status, 200)
            self.assertNotIn(b'id="batch-open"', body)

    def test_spreadsheet_template_and_import_preserve_unselected_rows(self):
        import base64
        status, _, data = self.request('GET', '/api/lote/modelo.xlsx')
        self.assertEqual(status, 200)
        book = load_workbook(BytesIO(data))
        sheet = book['DESTINATARIOS']
        self.assertEqual(list(next(sheet.values)), ['Enviar', 'Polo', 'Para', 'CC', 'CCO', 'Assunto'])
        self.assertFalse(any(row[0] for row in list(sheet.values)[1:]))
        sheet.append(['SIM', 'Polo QA', 'qa@example.test', '', '', 'Assunto específico'])
        sheet.append(['', 'Polo a revisar', 'inválido', '', '', ''])
        output = BytesIO()
        book.save(output)
        status, _, data = self.request('POST', '/api/lote/importar', json.dumps({
            'xlsx': base64.b64encode(output.getvalue()).decode('ascii')}), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200, data)
        rows = json.loads(data)['rows']
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]['selecionado'])
        self.assertFalse(rows[1]['selecionado'])
        self.assertEqual(rows[1]['para'], 'inválido')

    def payload(self):
        return {'html': '<!doctype html><html><meta charset="utf-8"><body>Comunicado aprovado — QA</body></html>',
                'aprovado': True, 'remetente': '', 'assunto': 'Assunto padrão', 'rows': [
                    {'selecionado': True, 'polo': 'Polo A', 'para': 'qa@example.test',
                     'cc': 'copia@example.test', 'cco': '', 'assunto': ''},
                    {'selecionado': False, 'polo': 'Não incluir', 'para': 'inválido',
                     'cc': '', 'cco': '', 'assunto': ''}]}

    def post_json(self, path, payload):
        return self.request('POST', path, json.dumps(payload), {'Content-Type': 'application/json'})

    def test_package_is_explicit_and_preview_preserves_html(self):
        payload = self.payload()
        status, headers, data = self.post_json('/api/lote/preview', payload)
        self.assertEqual(status, 200, data)
        self.assertEqual(data.decode('utf-8'), payload['html'])
        self.assertEqual(self.request('GET', headers['X-Preview-URL'])[2], data)
        status, headers, data = self.post_json('/api/lote/pacote', payload)
        self.assertEqual(status, 200, data)
        self.assertEqual(headers['Content-Type'], 'application/zip')
        with zipfile.ZipFile(BytesIO(data)) as archive:
            self.assertEqual(set(archive.namelist()), {'lote.json', 'mensagem.html', 'executar.ps1', 'abrir.cmd', 'LEIA-ME.txt'})
            self.assertEqual(archive.read('mensagem.html').decode('utf-8'), payload['html'])
            manifest = json.loads(archive.read('lote.json'))
            self.assertEqual(len(manifest['rows']), 1)
            self.assertEqual(manifest['rows'][0]['assunto'], 'Assunto padrão')
            self.assertNotIn('polo', manifest['rows'][0], 'only required routing travels')
        _, _, second = self.post_json('/api/lote/pacote', payload)
        with zipfile.ZipFile(BytesIO(second)) as archive:
            self.assertEqual(json.loads(archive.read('lote.json'))['batch_id'], manifest['batch_id'])

    def test_unapproved_empty_invalid_duplicate_batches_are_rejected(self):
        for change in ({'aprovado': False}, {'rows': []}, {'html': ''}, {'remetente': 'bad'}, {'rows': 'bad'}):
            with self.subTest(change=change):
                status, _, _ = self.post_json('/api/lote/pacote', dict(self.payload(), **change))
                self.assertEqual(status, 400)
        payload = self.payload()
        payload['rows'][0]['para'] = 'qa@example.test\r\nBcc: leak@example.test'
        self.assertEqual(self.post_json('/api/lote/pacote', payload)[0], 400)
        payload = self.payload()
        payload['rows'].append(dict(payload['rows'][0]))
        self.assertEqual(self.post_json('/api/lote/pacote', payload)[0], 400)
        for address in ('qa@domain..test', 'qa@-domain.test', '.qa@domain.test', 'qa..test@domain.test'):
            payload = self.payload()
            payload['rows'][0]['para'] = address
            with self.subTest(address=address):
                self.assertEqual(self.post_json('/api/lote/pacote', payload)[0], 400)

    def test_import_rejects_formulas_malformed_files_and_limits(self):
        import base64
        for encoded in ('not-base64', base64.b64encode(b'not a workbook').decode('ascii')):
            self.assertEqual(self.post_json('/api/lote/importar', {'xlsx': encoded})[0], 400)
        book = Workbook()
        sheet = book.active
        sheet.title = 'DESTINATARIOS'
        sheet.append(['Enviar', 'Polo', 'Para', 'CC', 'CCO', 'Assunto'])
        sheet.append(['SIM', 'QA', '=1+1', '', '', ''])
        output = BytesIO()
        book.save(output)
        self.assertEqual(self.post_json('/api/lote/importar', {'xlsx': base64.b64encode(output.getvalue()).decode('ascii')})[0], 400)
        sheet['A502'] = 'SIM'
        output = BytesIO()
        book.save(output)
        self.assertEqual(self.post_json('/api/lote/importar', {'xlsx': base64.b64encode(output.getvalue()).decode('ascii')})[0], 400)

    def test_reordering_identical_lot_preserves_the_bridge_fingerprint(self):
        payload = self.payload()
        payload['rows'][1].update(selecionado=True, para='second@example.test')
        _, _, first = self.post_json('/api/lote/pacote', payload)
        payload['rows'].reverse()
        _, _, second = self.post_json('/api/lote/pacote', payload)
        with zipfile.ZipFile(BytesIO(first)) as before, zipfile.ZipFile(BytesIO(second)) as after:
            self.assertEqual(json.loads(before.read('lote.json'))['batch_id'], json.loads(after.read('lote.json'))['batch_id'])
            self.assertEqual(before.read('lote.json'), after.read('lote.json'), 'same batch ID must retain exact state fingerprint')

    def test_batch_rejects_cross_origin_bad_content_type_and_oversize_headers(self):
        self.assertEqual(self.request('POST', '/api/lote/pacote', '{}',
                                     {'Content-Type': 'application/json', 'Origin': 'https://example.test'})[0], 403)
        self.assertEqual(self.request('POST', '/api/lote/pacote', '{}', {'Content-Type': 'text/plain'})[0], 415)
        with closing(http.client.HTTPConnection('127.0.0.1', self.server.server_port)) as connection:
            connection.putrequest('POST', '/api/lote/pacote')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader('Content-Length', str(4 * 1024 * 1024 + 1))
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            response.read()


if __name__ == '__main__':
    unittest.main()
