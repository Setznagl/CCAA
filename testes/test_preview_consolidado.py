import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
            return importlib.import_module('preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS')
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


    def sources(self, root):
        data = root / 'databases/09-11-26'
        data.mkdir(parents=True)
        sheet(data / 'auditoria-tabela-contatos.xlsx', ['Polo', 'Nome', 'E-mail', 'Perfil'], [
            ['A', 'Ana', 'shared@example.test', 'GESTOR PRINCIPAL'],
            ['A', 'Bia', 'shared@example.test', 'GESTOR PRINCIPAL'],
            ['B', 'Ana', 'ana@example.test', 'GESTOR PRINCIPAL'],
            ['Fora', 'Ana', 'ana@example.test', 'GESTOR PRINCIPAL'],
            ['A', 'Tutor', 'tutor@example.test', 'TUTOR']])
        sheet(data / 'auditoria-apps-prazo.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'], [
            ['A', 12, 3, 9], ['B', 10, 0, 10],
            ['Applied filters:\nsemestre_operacional is 262', None, None, None]])
        sheet(data / 'auditoria-polos-acompanhamento-262.xlsx', ['Polo', 'Rep. Sem Retorno'], [
            ['A', 2], ['B', 0], ['Filtros aplicados:\nsemestre_operacional_x é 262', None]])
        sheet(data / 'auditoria-timeline-262.xlsx', ['Polo', 'semestre_operacional_x', 'Laboratório',
            'Tipo auditoria', 'Auditor', 'Agendada', 'Data agendada', 'Realizada',
            'Data realização', 'Finalizada', 'Parecer Auditoria'], [
            ['A', 262, 'Lab', 'Regular', 'Auditora', 'Sim', '2026-11-12', 'Não', None, 'Não', 'Reprovado'],
            ['Applied filters:\nsemestre_operacional_x is 262', None, None, None, None, None, None, None, None, None, None]])
        return data

    def test_new_sources_preserve_people_roster_and_aggregated_practices(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.sources(root)
            records = self.adapter().load_consolidado(root)
        loaded = {r['label']: r for key, r in records.items() if key != 'manual'}
        self.assertEqual(set(loaded), {'Ana', 'Bia'})
        ana = loaded['Ana']
        self.assertEqual(ana['draft']['polos'], ['A', 'B'])
        self.assertEqual(ana['polo_count'], 2)
        self.assertEqual(ana['draft']['praticas'][0], {'polo': 'A', 'previstas': 12, 'comprovadas': 3, 'pendentes': 9})
        self.assertEqual(ana['draft']['reprovados_sem_retorno'], 2)
        self.assertEqual(ana['source_cycles'], ['262'])
        self.assertEqual(ana['draft']['agenda'][0]['status'], 'Agendada')
        self.assertEqual(ana['draft']['agenda'][0]['data'], '2026-11-12')
        self.assertEqual(ana['draft']['laboratorios'][0]['parecer'], 'Reprovado')
        self.assertEqual(ana['draft']['checklist'][0]['auditor'], '')
        self.assertIsNone(ana['draft']['checklist'][0]['nota'])
        self.assertTrue(any('amb' in w.lower() for w in ana['warnings']))
        self.assertEqual(loaded['Bia']['draft']['polos'], ['A'])

    def test_emails_export_is_distinct_atomic_regenerated_and_not_html_source(self):
        import os
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.sources(root)
            adapter = self.adapter()
            adapter.load_consolidado(root)
            output = data / 'emails.xlsx'
            self.assertTrue(output.is_file(), 'Planilha intermediária não foi gerada')
            def contents():
                wb = load_workbook(output)
                rows = list(wb.active.values)
                self.assertFalse(any(c.data_type == 'f' for row in wb.active for c in row))
                wb.close()
                return rows
            self.assertEqual(contents(), [('Polo', 'Email', 'Enviar'), ('A', 'shared@example.test', None), ('B', 'ana@example.test', None)])
            stamp = output.stat().st_mtime_ns
            adapter.load_consolidado(root)
            self.assertEqual(output.stat().st_mtime_ns, stamp)
            source = data / 'auditoria-tabela-contatos.xlsx'
            sheet(source, ['Polo', 'Nome', 'E-mail', 'Perfil'], [
                ['A', 'Ana', 'a@example.test', 'GESTOR PRINCIPAL'],
                ['A', 'Bia', 'b@example.test', 'GESTOR PRINCIPAL'],
                ['A', 'Bia', 'b@example.test', 'GESTOR PRINCIPAL']])
            os.utime(source, ns=(1, 1))
            adapter.load_consolidado(root)
            self.assertEqual(contents()[1], ('A', 'a@example.test;b@example.test', None))
            wb = load_workbook(output)
            wb.active['A2'] = 'ADULTERADO'
            wb.save(output)
            wb.close()
            loaded = adapter.load_consolidado(root)
            self.assertEqual(loaded['1']['draft']['polos'], ['A'])
            with patch.object(adapter.os, 'replace', side_effect=PermissionError('bloqueada')):
                os.utime(source, ns=(2, 2))
                loaded = adapter.load_consolidado(root)
            self.assertTrue(any('emails.xlsx' in w for w in loaded['1']['warnings']))
            self.assertEqual(contents()[1][0], 'ADULTERADO', 'Falha não deve destruir arquivo anterior')
            self.assertEqual(list(data.glob('.emails-*')), [])
            with patch.object(adapter.os, 'replace', side_effect=PermissionError('bloqueada')), patch.object(adapter.Path, 'unlink', side_effect=PermissionError('limpeza bloqueada')):
                try:
                    loaded = adapter.load_consolidado(root)
                except PermissionError:
                    self.fail('Falha na limpeza temporária não pode derrubar a prévia')
            self.assertTrue(any('emails.xlsx' in w for w in loaded['1']['warnings']))

    def test_unassigned_polo_is_identified_only_in_manual_review_warnings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.sources(root)
            sheet(data / 'auditoria-apps-prazo.xlsx',
                  ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'],
                  [['A', 12, 3, 9], ['Polo sem associação', 10, 0, 10]])
            records = self.adapter().load_consolidado(root)
        self.assertTrue(any('POLO SEM ASSOCIAÇÃO' in warning
                            for warning in records['manual']['warnings']))
        for key, record in records.items():
            if key != 'manual':
                self.assertFalse(any('POLO SEM ASSOCIAÇÃO' in warning
                                     for warning in record['warnings']))

    def test_missing_duplicate_and_invalid_counts_remain_manual(self):
        for value in (None, -1, 1.5, 'sem dado'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                data = self.sources(root)
                sheet(data / 'auditoria-apps-prazo.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'], [['A', value, 0, 1]])
                sheet(data / 'auditoria-polos-acompanhamento-262.xlsx', ['Polo', 'Rep. Sem Retorno'], [['A', 2], ['A', 2]])
                record = self.adapter().load_consolidado(root)['1']
                self.assertIsNone(record['draft']['praticas'][0]['previstas'])
                self.assertEqual(record['draft']['praticas'][0]['comprovadas'], 0)
                self.assertIsNone(record['draft']['reprovados_sem_retorno'])
                self.assertTrue(any('apps com ciclo não declarado' in w for w in record['warnings']))
                self.assertEqual(record['source_cycles'], ['262'])

    def test_no_filename_cycle_or_legacy_fallback_and_corrupt_source_is_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.sources(root)
            (data / 'auditoria-timeline-262.xlsx').write_bytes(b'corrompida')
            sheet(data / 'auditoria-apps-prazo.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'], [['A', 12, 3, 9]])
            sheet(data / 'auditoria-polos-acompanhamento-262.xlsx', ['Polo', 'Rep. Sem Retorno'], [['A', 0]])
            record = self.adapter().load_consolidado(root)['1']
            self.assertEqual(record['source_cycles'], [])
            self.assertEqual(record['draft']['ciclo'], '')
            self.assertEqual(record['draft']['reprovados_sem_retorno'], 0)
            self.assertTrue(any('inválida' in w for w in record['warnings']))
            (data / 'auditoria-tabela-contatos.xlsx').unlink()
            self.assertEqual(list(self.adapter().load_consolidado(root)), ['manual'])

    def test_export_blocks_excel_formula_prefixes_and_keeps_missing_contacts(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.sources(root)
            sheet(data / 'auditoria-apps-prazo.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'], [['+Polo', 1, 0, 1]])
            sheet(data / 'auditoria-tabela-contatos.xlsx', ['Polo', 'Nome', 'E-mail', 'Perfil'], [['+Polo', '+Nome', '+email@example.test', 'GESTOR PRINCIPAL']])
            self.adapter().load_consolidado(root)
            wb = load_workbook(data / 'emails.xlsx')
            rows = list(wb.active.values)
            self.assertIn(("'+Polo", "'+email@example.test", None), rows)
            self.assertIn(('A', None, None), rows)
            self.assertFalse(any(c.data_type == 'f' for row in wb.active for c in row))
            wb.close()

    def test_timeline_preserves_labs_dates_statuses_and_source_cycles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.sources(root)
            headers = ['Polo', 'semestre_operacional_x', 'Laboratório', 'Tipo auditoria', 'Auditor', 'Agendada', 'Data agendada', 'Realizada', 'Data realização', 'Finalizada', 'Parecer Auditoria']
            sheet(data / 'auditoria-timeline-262.xlsx', headers, [
                ['A', '26.1', 'Lab 1', 'Regular', 'X', 'Não', None, 'Não', None, 'Não', ''],
                ['A', 262, 'Lab 2', 'Regular', 'Y', 'Sim', '2026-11-11', 'Sim', '2026-11-12', 'Não', ''],
                ['A', 262, 'Lab 3', 'Regular', 'Z', 'Sim', None, 'Sim', '2026-11-13', 'Sim', 'Aprovado']])
            adapter = self.adapter()
            record = adapter.load_consolidado(root)['1']
            self.assertEqual(record['source_cycles'], ['261', '262'])
            self.assertEqual([r['status'] for r in record['draft']['agenda']], ['', 'Realizada', 'Finalizada'])
            self.assertEqual([r['data'] for r in record['draft']['agenda']], ['', '2026-11-12', '2026-11-13'])
            html = adapter.render_consolidado(record['draft'], SAMPLE, record['source_cycles'], record['warnings'])
            self.assertNotIn('NaT', html)
            self.assertIn('ciclos mistos', html)

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





if __name__ == '__main__':
    unittest.main()
