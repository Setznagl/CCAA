import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from openpyxl import Workbook


def sheet(path, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Export'
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'fluxos/SITUACAO_REGULARIZACAO_DOS_POLOS/sample.html'


class ConsolidadoTests(unittest.TestCase):
    def adapter(self):
        try:
            return importlib.import_module('preview_consolidado')
        except ModuleNotFoundError:
            self.fail('Loader/renderer consolidado ainda não implementado')

    def test_manual_option_without_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            records = self.adapter().load_consolidado(Path(folder))
        self.assertEqual(list(records), ['manual'])
        record = records['manual']
        self.assertEqual(record['polo_count'], 0)
        self.assertEqual(record['draft']['polos'], [])
        self.assertEqual(record['draft']['gestor'], '')
        self.assertEqual(record['draft']['prazo_praticas'], '')
        self.assertIsNone(record['draft']['reprovados_sem_retorno'])
        self.assertEqual(record['source_cycles'], [])
        self.assertTrue(record['warnings'])

    def test_master_roster_four_sequences_labs_and_approval(self):
        adapter = self.adapter()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA'
            data.mkdir(parents=True)
            (data / 'Base de Polos - Master (1).xlsb').touch()
            headers = ['NOME UNIDADE SISTEMA', 'GESTOR DE POLO / DIRETOR UNIDADE',
                       'CANAL', 'STATUS DA UNIDADE/POLO']
            master = pd.DataFrame([
                ['POLO (999)A', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO'],
                [' polo (999)a  ', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO'],
                ['POLO SEM BASE', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO'],
                ['POLO EXCLUIDO', 'Gestora', 'PROPRIO', 'UNIDADE EM OPERACAO/CAPTACAO'],
                ['POLO FECHADO', 'Gestora', 'PARCEIRO', 'ENCERRADO'],
            ], columns=headers)
            for name in ('sequenciaa1', 'sequenciaa2', 'sequencia3', 'sequencia4'):
                sheet(data / (name + '.xlsx'), ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'],
                      [['POLO (999)A', 12, 3, 9], ['OUTRO (999)A', 100, 0, 100],
                       [None, None, None, None],
                       ['Filtros aplicados:\nsemestre_operacional é 261', None, None, None]])
            sheet(data / 'labs.xlsx', ['Polo', 'semestre_operacional_x', 'Laboratório',
                  'Tipo auditoria', 'Auditor', 'Agendada', 'Data agendada', 'Realizada',
                  'Data realização', 'Finalizada', 'Parecer Auditoria'], [
                      ['POLO (999)A', 261, 'Lab A', 'Regular', 'Auditora', 'Sim', '2026-05-22', 'Não', None, 'Não', 'Reprovado'],
                      ['POLO (999)A', 261, 'Lab B', 'Recorrente', 'Outro', 'Sim', '2026-05-20', 'Sim', '2026-05-21', 'Não', ''],
                      ['POLO (999)A', 261, 'Lab C', 'Regular', 'Outro', 'Sim', '2026-05-20', 'Sim', '2026-05-21', 'Sim', 'Aprovado'],
                  ])
            sheet(data / 'aprovacao.xlsx', ['Polo', 'Rep. Sem Retorno'], [['POLO (999)A', 7], ['POLO SEM BASE', 0]])
            original_read = pd.read_excel

            def guarded(path, **kwargs):
                if Path(path).suffix == '.xlsb':
                    self.assertEqual(kwargs['sheet_name'], 'BASE_DE_UNIDADES')
                    self.assertEqual(set(kwargs['usecols']), set(headers))
                    self.assertEqual(kwargs['engine'], 'pyxlsb')
                    return master
                self.assertNotEqual(Path(path).name, 'emails.xlsx')
                return original_read(path, **kwargs)

            with patch('pandas.read_excel', side_effect=guarded):
                records = adapter.load_consolidado(root)
        loaded = [v for k, v in records.items() if k != 'manual']
        self.assertEqual(len(loaded), 1, 'A carteira da Master ainda não foi carregada')
        record, = loaded
        draft = record['draft']
        self.assertEqual(record['label'], 'Gestora')
        self.assertEqual(record['polo_count'], 2)
        self.assertEqual(draft['praticas'], [{'polo': 'POLO (999)A', 'previstas': 48, 'comprovadas': 12, 'pendentes': 36}])
        self.assertEqual(draft['reprovados_sem_retorno'], 7)
        self.assertEqual([r['status'] for r in draft['agenda']], ['Agendada', 'Realizada', 'Finalizada'])
        self.assertEqual(draft['agenda'][1]['data'], '2026-05-21')
        self.assertEqual(draft['ciclo'], '261')
        self.assertEqual(record['source_cycles'], ['261'])
        self.assertEqual(len(draft['checklist']), 2)
        self.assertIsNone(draft['checklist'][0]['nota'])
        self.assertEqual(draft['checklist'][0]['auditor'], '')
        self.assertTrue(any('POLO SEM BASE' in w for w in record['warnings']))
        self.assertTrue(any('checklist' in w.lower() for w in record['warnings']))
        self.assertEqual(draft['prazo_auditorias'], '')

    def test_render_preserves_art_without_sample_data_and_escapes_text(self):
        adapter = self.adapter()
        draft = adapter.load_consolidado(ROOT / 'no-sources')['manual']['draft']
        draft.update(gestor='<img src=x onerror=alert(1)>', ciclo='262', polos=['Polo & Teste'])
        draft['agenda'] = [{'polo': 'Polo & Teste', 'tipo': 'Regular', 'ambiente': 'Lab',
                            'data': '2026-05-22', 'auditor': 'A < B', 'status': 'Agendada'}]
        self.assertTrue(hasattr(adapter, 'render_consolidado'), 'Renderer consolidado ainda não implementado')
        html = adapter.render_consolidado(draft, SAMPLE, source_cycles=['26.1'], warnings=['Fonte <antiga>'])
        self.assertIn('width="820"', html)
        self.assertIn('background:#F1EBF8;padding:18px 34px', html)
        for color in ('#6A2C91', '#5C3D9E', '#E0A458', '#D6246E'):
            self.assertIn(color, html)
        for secret in ('LUCAS BIGHETTI', 'MAUA/SP', 'SANTOS/SP', 'KAROLINE', 'MARIA.LIMA',
                       '99306-7364', '04/10', '06/10', '09/10/2026', '69,94', '5 laboratórios reprovados'):
            self.assertNotIn(secret, html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img', html)
        self.assertIn('Polo &amp; Teste', html)
        self.assertIn('Fonte &lt;antiga&gt;', html)
        self.assertIn('261', html)
        self.assertIn('26.2', html)
        self.assertIn('Não informado', html)
        self.assertIn('Agendada', html)
        self.assertNotIn('Não compareceu', html)
        self.assertEqual(draft['ciclo'], '262')

    def test_practice_totals_follow_rows_and_do_not_treat_missing_as_zero(self):
        adapter = self.adapter()
        rows = [{'polo': 'A', 'previstas': 10, 'comprovadas': 3, 'pendentes': 7},
                {'polo': 'B', 'previstas': 20, 'comprovadas': 5, 'pendentes': 15}]
        draft = {'gestor': 'Gestora', 'ciclo': '262', 'polos': ['A', 'B'], 'praticas': rows}
        html = adapter.render_consolidado(draft, SAMPLE)
        self.assertIn('TOTAL INFORMADO', html)
        total = html.split('TOTAL INFORMADO', 1)[1].split('</tr>', 1)[0]
        for field in ('previstas', 'comprovadas', 'pendentes'):
            self.assertIn('>' + str(sum(r[field] for r in rows)) + '</td>', total)
        expected_percent = f"{sum(r['comprovadas'] for r in rows) / sum(r['previstas'] for r in rows) * 100:.0f}%"
        self.assertIn(expected_percent, total)
        rows[1]['comprovadas'] = None
        html = adapter.render_consolidado(draft, SAMPLE)
        total = html.split('TOTAL INFORMADO', 1)[1].split('</tr>', 1)[0]
        self.assertIn('Não informado', total)
        self.assertNotIn('>0</td>', total)

    def test_rejects_invalid_manual_inputs_with_clear_value_errors(self):
        from copy import deepcopy
        adapter = self.adapter()
        valid = adapter.load_consolidado(ROOT / 'no-sources')['manual']['draft']
        valid.update(gestor='Gestora', ciclo='26.2', polos=['Polo'])
        invalid = [
            ('gestor', ''), ('gestor', 1), ('gestor', 'x' * 301), ('gestor', '\ud800'),
            ('ciclo', ''), ('ciclo', '263'), ('ciclo', 262), ('ciclo', '262.0'),
            ('polos', 'Polo'), ('polos', ['Polo', ' polo ']), ('polos', ['']),
            ('polos', ['x'] * 501), ('polos', [False]),
            ('agenda', {}), ('agenda', [False]), ('agenda', [{}] * 2001),
            ('agenda', [{'polo': 'Outro'}]), ('agenda', [{'polo': 'Polo', 'data': '2026-02-30'}]),
            ('agenda', [{'polo': 'Polo', 'data': '22/05/2026'}]),
            ('agenda', [{'polo': 'Polo', 'data': '20260522'}]),
            ('checklist', [{'polo': 'Polo', 'nota': float('nan')}]),
            ('checklist', [{'polo': 'Polo', 'nota': float('inf')}]),
            ('checklist', [{'polo': 'Polo', 'nota': -1}]),
            ('checklist', [{'polo': 'Polo', 'nota': '69,94'}]),
            ('praticas', [{'polo': 'Polo', 'previstas': 1.5}]),
            ('praticas', [{'polo': 'Polo', 'previstas': True}]),
            ('reprovados_sem_retorno', -1), ('reprovados_sem_retorno', 1e30),
            ('reprovados_sem_retorno', '1'), ('prazo_praticas', '04/10'),
            ('link_relatorio', 'javascript:alert(1)'), ('link_atendimento', '//evil.test'),
            ('link_relatorio', 'https://user:pass@host.test'),
            ('link_relatorio', 'https://host.test/\\evil'),
            ('link_relatorio', 'https://host.test/%0aevil'),
            ('link_relatorio', 'https://host.test:bad'),
            ('contatos', [{'email': 'a@b.test\r\nBcc:evil@bad.test'}]),
            ('contatos', [{'email': 'a@b.test?subject=evil'}]),
            ('contatos', [{'telefone': '\x00'}]), ('warnings', ['falso']),
            ('laboratorios', [{'polo': 'Polo', 'parecer': []}]),
            ('checklist', [{'polo': 'Polo', 'observacao': 'x' * 2001}]),
        ]
        for field, value in invalid:
            with self.subTest(field=field, value=repr(value)[:80]):
                draft = deepcopy(valid)
                draft[field] = value
                with self.assertRaises(ValueError) as error:
                    adapter.render_consolidado(draft, SAMPLE)
                self.assertTrue(str(error.exception))
        for draft in (None, [], 'x'):
            with self.assertRaises(ValueError):
                adapter.render_consolidado(draft, SAMPLE)

    def test_loader_handles_blank_lab_dates_and_partial_corrupt_sources(self):
        adapter = self.adapter()
        master = pd.DataFrame([['Polo', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO']],
                              columns=adapter.MASTER_COLUMNS)
        labs = pd.DataFrame([{'Polo': 'Polo', 'semestre_operacional_x': 261,
                              'Laboratório': 'Lab', 'Tipo auditoria': 'Regular', 'Auditor': '',
                              'Agendada': 'Não', 'Data agendada': pd.NaT, 'Realizada': 'Não',
                              'Data realização': pd.NaT, 'Finalizada': 'Não', 'Parecer Auditoria': ''}])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'fluxos/AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA'
            data.mkdir(parents=True)
            (data / 'Base de Polos - Master (1).xlsb').touch()

            def read(path, **kwargs):
                if Path(path).suffix == '.xlsb':
                    return master
                if Path(path).name == 'labs.xlsx':
                    return labs
                raise ValueError('Arquivo incompleto')

            with patch('pandas.read_excel', side_effect=read):
                records = adapter.load_consolidado(root)
        record = records['1']
        self.assertEqual(record['draft']['agenda'][0]['data'], '')
        self.assertEqual(record['draft']['agenda'][0]['status'], '')
        self.assertEqual(record['draft']['praticas'], [])
        self.assertIsNone(record['draft']['reprovados_sem_retorno'])
        html = adapter.render_consolidado(record['draft'], SAMPLE, record['source_cycles'], record['warnings'])
        self.assertNotIn('NaT', html)
        self.assertIn('Fonte sequenciaa1.xlsx ausente ou inválida', html)

    def test_invalid_source_counts_and_corrupt_workbook_become_manual_warnings(self):
        from zipfile import BadZipFile
        adapter = self.adapter()
        master = pd.DataFrame([['Polo', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO']],
                              columns=adapter.MASTER_COLUMNS)
        for value in (float('nan'), -1, 1.5, 'sem dado'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                data = root / 'fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA'
                data.mkdir(parents=True)
                (data / 'Base de Polos - Master (1).xlsb').touch()

                def read(path, **kwargs):
                    if Path(path).suffix == '.xlsb':
                        return master
                    if Path(path).name in adapter.SEQUENCES:
                        return pd.DataFrame([['Polo', value, 0, 0]], columns=['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'])
                    raise BadZipFile('Fonte corrompida')

                try:
                    with patch('pandas.read_excel', side_effect=read):
                        records = adapter.load_consolidado(root)
                except Exception as error:
                    self.fail(f'Fonte inválida deveria virar aviso, não {type(error).__name__}')
                record = records['1']
                self.assertEqual(record['draft']['praticas'], [])
                self.assertEqual(record['draft']['agenda'], [])
                self.assertIsNone(record['draft']['reprovados_sem_retorno'])
                self.assertTrue(any('inválida' in w for w in record['warnings']))

    def test_optional_blanks_safe_links_numeric_zero_and_local_template(self):
        adapter = self.adapter()
        draft = {'gestor': 'Gestora', 'ciclo': '261', 'polos': ['Polo'],
                 'link_relatorio': '', 'link_atendimento': 'https://example.test/?a=1&b=2',
                 'prazo_praticas': '2028-02-29',
                 'checklist': [{'polo': 'Polo', 'nota': 0}],
                 'praticas': [{'polo': 'Polo', 'previstas': 10, 'comprovadas': 0, 'pendentes': 10}],
                 'contatos': [{'funcao': 'Contato', 'nome': '<nome>', 'email': 'pessoa+teste#x%0a@example.test'}]}
        html = adapter.render_consolidado(draft, ROOT / 'missing-sample.html', ['261', '26.2'], [])
        self.assertNotIn('href="Não informado"', html)
        self.assertIn('href="mailto:pessoa%2Bteste%23x%250a@example.test"', html)
        self.assertIn('href="https://example.test/?a=1&amp;b=2"', html)
        self.assertIn('&lt;nome&gt;', html)
        self.assertIn('0%', html)
        self.assertIn('text-align:center;font-size:13px;font-weight:bold;color:#444444">0</td>', html)
        self.assertIn('2028-02-29', html)
        self.assertIn('ciclos mistos', html)
        self.assertIn('261, 262', html)
        self.assertNotIn('percentual', draft['praticas'][0])
        self.assertNotIn('agenda', draft)

    def test_no_academic_source_does_not_invent_cycle(self):
        adapter = self.adapter()
        master = pd.DataFrame([['Polo', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO']],
                              columns=adapter.MASTER_COLUMNS)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA'
            data.mkdir(parents=True)
            (data / 'Base de Polos - Master (1).xlsb').touch()

            def read(path, **kwargs):
                if Path(path).suffix == '.xlsb':
                    return master
                raise FileNotFoundError(path)

            with patch('pandas.read_excel', side_effect=read):
                record = adapter.load_consolidado(root)['1']
        self.assertEqual(record['source_cycles'], [])
        self.assertEqual(record['draft']['ciclo'], '')
        self.assertEqual(record['draft']['praticas'], [])

    def test_export_without_semester_does_not_assume_261(self):
        adapter = self.adapter()
        master = pd.DataFrame([['Polo', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO']],
                              columns=adapter.MASTER_COLUMNS)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA'
            data.mkdir(parents=True)
            (data / 'Base de Polos - Master (1).xlsb').touch()

            def read(path, **kwargs):
                if Path(path).suffix == '.xlsb':
                    return master
                if Path(path).name in adapter.SEQUENCES:
                    return pd.DataFrame([['Polo', 12, 0, 12]],
                                        columns=['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'])
                raise FileNotFoundError(path)

            with patch('pandas.read_excel', side_effect=read):
                record = adapter.load_consolidado(root)['1']
        self.assertEqual(record['source_cycles'], [])
        self.assertEqual(record['draft']['ciclo'], '')
        self.assertTrue(any('ciclo não declarado' in warning for warning in record['warnings']))
        self.assertEqual(record['draft']['praticas'][0]['previstas'], 48)

    def test_export_filter_metadata_carries_real_cycle(self):
        adapter = self.adapter()
        master = pd.DataFrame([['Polo', 'Gestora', 'PARCEIRO', 'UNIDADE EM OPERACAO/CAPTACAO']],
                              columns=adapter.MASTER_COLUMNS)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA'
            data.mkdir(parents=True)
            (data / 'Base de Polos - Master (1).xlsb').touch()

            def read(path, **kwargs):
                if Path(path).suffix == '.xlsb':
                    return master
                if Path(path).name in adapter.SEQUENCES:
                    return pd.DataFrame([['Polo', 12, 0, 12],
                                         ['Filtros aplicados:\nsemestre_operacional é 262', None, None, None]],
                                        columns=['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'])
                raise FileNotFoundError(path)

            with patch('pandas.read_excel', side_effect=read):
                record = adapter.load_consolidado(root)['1']
        self.assertEqual(record['source_cycles'], ['262'])
        self.assertEqual(record['draft']['ciclo'], '262')


if __name__ == '__main__':
    unittest.main()
