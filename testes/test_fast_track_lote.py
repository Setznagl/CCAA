"""Fast Track batch tests use synthetic contacts, never production downloads."""
from contextlib import closing
from io import BytesIO
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
import zipfile

from openpyxl import Workbook
from preview_server import make_server


def batch_fixture(root):
    data = root / 'databases/09-11-26'
    data.mkdir(parents=True)
    book = Workbook()
    book.active.title = 'Export'
    book.active.append(['NOME UNIDADE SISTEMA', 'GESTOR DE POLO / DIRETOR UNIDADE',
                        'EMAIL GESTOR PRISMA / EMAIL DIRETOR DE UNIDADE', 'GER. COM. / GER. NEG.',
                        'CONSULTOR DE INFRA', 'AUDITOR ACADEMICO', 'GRUPO ECONOMICO'])
    for polo, auditor in [('Polo A', 'Acadêmico'), ('Polo B', '')]:
        book.active.append([polo, 'Gestor', 'gestor@example.test', 'Negócios', 'Infra', auditor, 'Grupo'])
    auditors = book.create_sheet('AUDITORES')
    auditors.append(['NOME', 'EMAIL'])
    auditors.append(['Acadêmico', 'academico@example.test'])
    book.save(data / 'auditoria-base-gerencial.xlsx')
    book = Workbook()
    book.active.title = 'Export'
    book.active.append(['Nome', 'E-mail'])
    book.active.append(['Negócios', 'negocios@example.test'])
    book.active.append(['Infra', 'infra@example.test'])
    book.save(data / 'auditoria-base-gerencial-contatos.xlsx')
    source = root / 'databases/acompamento'
    source.mkdir(parents=True)
    book = Workbook()
    book.active.title = 'AÇÕES_ENFERMAGEM_PRESENCIAL_202'
    book.active.append(['NOME UNIDADE SISTEMA (time infra)', 'FONE E E-MAIL DO GESTOR DO POLO',
                        'Status Lab. Multidisciplinar', 'Status Laboratório de Enfermagem'])
    for polo, first, second in [('Polo A', 'Reprovado', 'Aprovado'), ('Polo B', None, 'Reprovado'),
                                ('Polo A', 'Reprovado', None), ('Polo aprovado', 'Aprovado', 'Aprovado'),
                                ('Polo sem status', None, None), ('Polo sem cadastro', 'Reprovado', None)]:
        book.active.append([polo, 'temporario@example.test', first, second])
    book.active.append(['Applied filters: exemplo', '', 'Reprovado'])
    book.create_sheet('Comments').append(['Não interpretar comentários como polos'])
    book.save(source / 'polos-irregulares-fasttrack.xlsx')
    template = root / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html'
    template.parent.mkdir(parents=True)
    template.write_bytes(b'\xef\xbb\xbf<!doctype html>\r\n<html><body>Prazo 31/08</body></html>')


class FastTrackBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        batch_fixture(self.root)
        self.server = make_server(self.root, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, payload=None):
        with closing(http.client.HTTPConnection('127.0.0.1', self.server.server_port)) as connection:
            connection.request('GET' if payload is None else 'POST', path,
                               body=None if payload is None else json.dumps(payload),
                               headers={} if payload is None else {'Content-Type': 'application/json'})
            response = connection.getresponse()
            return response.status, response.read()

    def test_package_requires_academic_per_selected_polo_and_keeps_fixed_bytes(self):
        status, body = self.request('/api/lote/fast-track')
        self.assertEqual(status, 200, body)
        data = json.loads(body)
        payload = dict(data, aprovado=True, assunto='Fast Track QA', remetente='')
        for row in payload['rows'][:2]:
            row['selecionado'] = True
        path = '/api/lote/fast-track/pacote'
        self.assertEqual(self.request(path, payload)[0], 400, 'missing academic blocks export')
        payload['rows'][1]['academico_nome'] = 'Acadêmico'
        status, body = self.request(path, payload)
        self.assertEqual(status, 200, body)
        with zipfile.ZipFile(BytesIO(body)) as archive:
            self.assertEqual(archive.read('mensagem.html'), data['html'].encode())
            original_manifest = archive.read('lote.json')
            manifest = json.loads(archive.read('lote.json'))
            self.assertEqual(len(manifest['rows']), 2, 'same contacts still produce one message per polo')
            self.assertEqual(len({r['id'] for r in manifest['rows']}), 2)
            for row in manifest['rows']:
                self.assertEqual(set(row['cc'].split(';')), {'infra@example.test', 'negocios@example.test', 'academico@example.test'})
                self.assertEqual(set(row), {'id', 'para', 'cc', 'cco', 'assunto'})
        payload['rows'].reverse()
        status, reordered = self.request(path, payload)
        self.assertEqual(status, 200, reordered)
        with zipfile.ZipFile(BytesIO(reordered)) as archive:
            self.assertEqual(archive.read('lote.json'), original_manifest)
        payload['rows'].reverse()
        payload['html'] = '<body>alterado</body>'
        self.assertEqual(self.request(path, payload)[0], 400, 'cannot replace approved fixed template')
        payload['html'] = data['html']
        payload['rows'][1]['polo'] = 'Polo aprovado'
        self.assertEqual(self.request(path, payload)[0], 400, 'cannot include polo outside failed source')
        payload['rows'][1]['polo'] = 'Polo A'
        self.assertEqual(self.request(path, payload)[0], 400, 'cannot repeat a polo')
        payload['rows'][1]['polo'] = 'Polo B'
        payload['rows'][1]['academico_nome'] = 'Não cadastrado'
        self.assertEqual(self.request(path, payload)[0], 400, 'academic must belong to registry')
        payload['rows'][1]['selecionado'] = False
        self.assertEqual(self.request(path, payload)[0], 200, 'deselected missing role does not block')
        _, refreshed = self.request('/api/lote/fast-track')
        self.assertEqual(json.loads(refreshed)['rows'][1]['academico_nome'], '', 'manual choice is not persisted')

    def test_bad_source_schema_and_formulas_fail_without_falling_back(self):
        from openpyxl import load_workbook

        source = self.root / 'databases/acompamento/polos-irregulares-fasttrack.xlsx'
        book = load_workbook(source)
        book.active['C2'] = '=1+1'
        book.save(source)
        self.assertEqual(self.request('/api/lote/fast-track')[0], 503)
        book.active['C2'] = 'Reprovado'
        book.active['A1'] = 'Cabeçalho inesperado'
        book.save(source)
        self.assertEqual(self.request('/api/lote/fast-track')[0], 503)

    def test_load_failed_polos_uses_directory_not_temporary_contacts(self):
        status, body = self.request('/api/lote/fast-track')
        self.assertEqual(status, 200, body)
        data = json.loads(body)
        self.assertEqual([r['polo'] for r in data['rows']], ['Polo A', 'Polo B', 'Polo sem cadastro'])
        self.assertTrue(all(r['selecionado'] is False for r in data['rows']))
        self.assertEqual(data['rows'][0]['para'], 'gestor@example.test')
        self.assertEqual(set(data['rows'][0]['cc'].split(';')), {'infra@example.test', 'negocios@example.test'})
        self.assertEqual(data['rows'][0]['academico_nome'], 'Acadêmico')
        self.assertEqual(data['rows'][1]['academico_nome'], '')
        self.assertEqual(data['rows'][2]['para'], '')
        self.assertNotIn('temporario@example.test', body.decode())
        self.assertEqual(data['html'].encode(), (self.root / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html').read_bytes())


if __name__ == '__main__':
    unittest.main()
