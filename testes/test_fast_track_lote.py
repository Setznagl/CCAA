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
                        'Status Lab. Multidisciplinar', 'Status Laboratório de Enfermagem',
                        'Data Checklist de Laboratório'])
    for polo, first, second, date in [('Polo A', 'Reprovado', 'Reprovado', '01/11/2026'),
                                     ('Polo B', None, None, None), ('Polo B', None, None, '  '),
                                     ('Polo aprovado', 'Aprovado', 'Aprovado', '02/11/2026'),
                                     ('Polo reprovado com data', 'Reprovado', None, '03/11/2026')]:
        book.active.append([polo, 'temporario@example.test', first, second, date])
    book.active.append(['Applied filters: exemplo'])
    book.create_sheet('Comments').append(['Não interpretar comentários como polos'])
    book.save(source / 'polos-irregulares-fasttrack.xlsx')
    book = Workbook()
    book.active.title = 'Planilha1'
    book.active.append([None, 'UNIDADE', 'GESTOR', 'DATA CL'])
    for polo, date in [('Polo A', None), ('Polo B', '   '), ('Polo sem cadastro', None),
                       ('Polo infraestrutura com data', '04/11/2026')]:
        book.active.append([None, polo, 'Não usar esse contato', date])
    book.active.append([None, 'Filtros aplicados: exemplo'])
    book.create_sheet('Planilha2').append([None, 'Não interpretar lista auxiliar como polos'])
    book.save(source / 'auditoria-infraestrutura-fasttrack.xlsx')
    template = root / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html'
    template.parent.mkdir(parents=True)
    template.write_bytes(b'\xef\xbb\xbf<!doctype html>\r\n<html><body>Prazo 20/11/2026</body></html>')


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
            self.assertEqual({row['assunto'] for row in manifest['rows']},
                             {row['assunto'] for row in payload['rows'][:2]})
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
        payload['rows'][0]['assunto'] = ''
        status, fallback = self.request(path, dict(payload, html=data['html']))
        self.assertEqual(status, 200, fallback)
        with zipfile.ZipFile(BytesIO(fallback)) as archive:
            self.assertEqual(archive.read('lote.json'), original_manifest, 'blank subject falls back to per-polo pattern, not global subject')
        self.assertEqual(self.request(path, payload)[0], 400, 'cannot replace approved fixed template')
        payload['html'] = data['html']
        payload['rows'][1]['polo'] = ''
        self.assertEqual(self.request(path, payload)[0], 400, 'empty polo name is invalid')
        payload['rows'][1]['polo'] = 'Polo A'
        self.assertEqual(self.request(path, payload)[0], 400, 'cannot repeat a polo')
        payload['rows'][1]['polo'] = 'Polo B'
        payload['rows'][1]['academico_nome'] = 'Não cadastrado'
        self.assertEqual(self.request(path, payload)[0], 400, 'academic must belong to registry')
        payload['rows'][1]['selecionado'] = False
        self.assertEqual(self.request(path, payload)[0], 200, 'deselected missing role does not block')
        _, refreshed = self.request('/api/lote/fast-track')
        self.assertEqual(json.loads(refreshed)['rows'][1]['academico_nome'], '', 'manual choice is not persisted')

    def test_manual_add_edit_delete_exports_reviewed_rows_without_changing_sources(self):
        import hashlib

        sources = list(self.root.rglob('*.xlsx'))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        _, body = self.request('/api/lote/fast-track')
        data = json.loads(body)
        edited = dict(data['rows'][0], polo='Polo corrigido', selecionado=True, assunto='',
                      para='corrigido@example.test')
        added = dict(edited, polo='Novo polo', para='novo@example.test')
        payload = dict(data, rows=[edited, added], aprovado=True, remetente='', assunto='Ignorar padrão global')
        status, body = self.request('/api/lote/fast-track/pacote', payload)
        self.assertEqual(status, 200, body)
        with zipfile.ZipFile(BytesIO(body)) as archive:
            manifest = json.loads(archive.read('lote.json'))
            self.assertEqual({r['para'] for r in manifest['rows']}, {'corrigido@example.test', 'novo@example.test'})
            self.assertEqual({r['assunto'] for r in manifest['rows']},
                             {data['rows'][0]['assunto'].replace('Polo A', name) for name in ('Polo corrigido', 'Novo polo')})
            self.assertEqual(archive.read('mensagem.html'), data['html'].encode())
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, before)
        _, refreshed = self.request('/api/lote/fast-track')
        self.assertEqual(json.loads(refreshed)['rows'], data['rows'])
        for invalid in ('', '   ', '\nPolo', 'x' * 256, '🔥'):
            with self.subTest(polo=invalid):
                added['polo'] = invalid
                self.assertEqual(self.request('/api/lote/fast-track/pacote', payload)[0], 400)
        added['polo'] = '  PÓLO   corrigido '
        self.assertEqual(self.request('/api/lote/fast-track/pacote', payload)[0], 400, 'normalized duplicate')

    def test_bad_source_schema_and_formulas_fail_without_falling_back(self):
        from openpyxl import load_workbook

        source = self.root / 'databases/acompamento/polos-irregulares-fasttrack.xlsx'
        book = load_workbook(source)
        book.active['E2'] = '=1+1'
        book.save(source)
        self.assertEqual(self.request('/api/lote/fast-track')[0], 503)
        book.active['E2'] = '01/11/2026'
        book.active['A1'] = 'Cabeçalho inesperado'
        book.save(source)
        self.assertEqual(self.request('/api/lote/fast-track')[0], 503)

    def test_load_missing_checklists_unites_independent_sources_without_temporary_contacts(self):
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
        self.assertEqual(data['rows'][0]['pendencias'], ['Checklist de infraestrutura'])
        self.assertEqual(data['rows'][1]['pendencias'], ['Checklist de laboratório', 'Checklist de infraestrutura'])
        for row in data['rows']:
            self.assertEqual(row['assunto'], '[ PREENCHIMENTO OBRIGATÓRIO - CL INSUMOS e CL REVENUE SHARE] Novo prazo máximo para preenchimento - ' + row['polo'])
        self.assertNotIn('temporario@example.test', body.decode())
        self.assertEqual(data['html'].encode(), (self.root / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html').read_bytes())


    def test_unknown_source_label_stays_manual_and_can_be_exported_after_review(self):
        _, body = self.request('/api/lote/fast-track')
        data = json.loads(body)
        row = data['rows'][2]
        self.assertEqual(row['para'], '')
        self.assertEqual(row['cc'], '')
        self.assertEqual(row['academico_nome'], '')
        row.update(selecionado=True, para='manual@example.test', cc='copia@example.test', academico_nome='Acadêmico')
        status, body = self.request('/api/lote/fast-track/pacote', dict(data, aprovado=True, remetente='', assunto=''))
        self.assertEqual(status, 200, body)
        with zipfile.ZipFile(BytesIO(body)) as archive:
            manifest = json.loads(archive.read('lote.json'))
            self.assertEqual(len(manifest['rows']), 1)
            self.assertEqual(manifest['rows'][0]['para'], 'manual@example.test')
            self.assertEqual(manifest['rows'][0]['assunto'], row['assunto'])
        _, refreshed = self.request('/api/lote/fast-track')
        self.assertEqual(json.loads(refreshed)['rows'][2]['para'], '')

    def test_infrastructure_uses_named_sheet_regardless_of_sheet_order(self):
        from openpyxl import load_workbook

        status, original = self.request('/api/lote/fast-track')
        self.assertEqual(status, 200, original)
        path = self.root / 'databases/acompamento/auditoria-infraestrutura-fasttrack.xlsx'
        book = load_workbook(path)
        auxiliary = book['Planilha2']
        auxiliary.delete_rows(1, auxiliary.max_row)
        auxiliary.append([None, 'UNIDADE', 'GESTOR', 'DATA CL'])
        auxiliary.append([None, 'Polo auxiliar que não participa', '', None])
        book.move_sheet('Planilha2', offset=-1)
        book.save(path)
        status, reordered = self.request('/api/lote/fast-track')
        self.assertEqual(status, 200, reordered)
        self.assertEqual(json.loads(reordered)['rows'], json.loads(original)['rows'])
        book['Planilha1'].title = 'Outra aba'
        book.save(path)
        self.assertEqual(self.request('/api/lote/fast-track')[0], 503, 'missing named sheet must not fall back to auxiliary data')

    def test_new_source_errors_formulas_and_missing_file_are_not_blank_or_fallback(self):
        from openpyxl import load_workbook

        path = self.root / 'databases/acompamento/auditoria-infraestrutura-fasttrack.xlsx'
        book = load_workbook(path)
        for invalid in ('=1+1', '#N/A'):
            book.active['D2'] = invalid
            book.save(path)
            self.assertEqual(self.request('/api/lote/fast-track')[0], 503)
        book.active['D2'] = 0
        book.save(path)
        status, body = self.request('/api/lote/fast-track')
        self.assertEqual(status, 200, body)
        self.assertNotIn('Polo A', [r['polo'] for r in json.loads(body)['rows']], 'zero is not a missing date')
        path.unlink()
        self.assertEqual(self.request('/api/lote/fast-track')[0], 503, 'missing second source must not silently export first only')


if __name__ == '__main__':
    unittest.main()
