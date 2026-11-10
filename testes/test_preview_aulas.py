import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import openpyxl

APPS = 'auditoria-apps-prazo.xlsx'
TIMELINE = 'auditoria-timeline-262.xlsx'
APPS_HEADERS = ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes',
                'Comprovação (%)', 'Dentro do prazo (%)', 'Validadas', 'Validação (%)']
TIMELINE_HEADERS = ['Polo', 'semestre_operacional_x', 'ID polo', 'Canal', 'ID cape',
                    'Cape', 'Laboratório', 'ID lab', 'Local', 'Tipo auditoria',
                    'Auditor', 'Agendada', 'Data agendada', 'Realizada',
                    'Data realização', 'Finalizada', 'Parecer Auditoria']
POLO = 'POLO FICTÍCIO/SP - I(101)A'


def manual(model):
    return {**model, 'prazo_praticas': '2026-05-31', 'prazo_auditoria': '2026-06-26'}


def sheet(path, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def timeline_row(polo=POLO, lab='Laboratório sintético', parecer='Reprovado'):
    return [polo, '262', 101, None, None, None, lab, 1,
            None, None, None, None, None, None, None, None, parecer]


class AulasPreviewTests(unittest.TestCase):
    def setUp(self):
        self.adapter = importlib.import_module('preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.data = Path(self.folder.name)

    def bases(self, apps=None, timeline=None):
        sheet(self.data / APPS, APPS_HEADERS,
              apps if apps is not None else [[POLO, 10, 4, 6]])
        sheet(self.data / TIMELINE, TIMELINE_HEADERS,
              timeline if timeline is not None else [timeline_row()])

    def test_manual_deadlines_are_required_and_never_loaded_as_defaults(self):
        self.bases()
        model = self.adapter.load_aulas(self.data)['101']
        with self.assertRaisesRegex(ValueError, 'prazo'):
            self.adapter.render_aulas(model)

    def test_review_requires_real_supplements_without_mutating_source(self):
        from copy import deepcopy
        self.bases(apps=[[POLO, 10, None, 6]], timeline=[])
        model = self.adapter.load_aulas(self.data)['101']
        original = deepcopy(model)
        draft = self.adapter.draft_aulas(model)
        self.assertEqual(draft['prazo_praticas'], '')
        self.assertEqual(draft['prazo_auditoria'], '')
        self.assertIsNone(draft['praticas']['comprovadas'])
        draft.update(prazo_praticas='2026-12-15', prazo_auditoria='2026-12-16', reviewed=True, labs_status='nao_aplicavel')
        for invalid in (None, float('nan'), True, -1, 1.5, '0', [], {}):
            draft['praticas']['comprovadas'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.adapter.review_aulas(draft, model)
        draft['praticas']['comprovadas'] = 0
        draft['labs_status'] = ''
        with self.assertRaisesRegex(ValueError, 'laboratórios'):
            self.adapter.review_aulas(draft, model)
        draft['labs_status'] = 'nao_aplicavel'
        reviewed = self.adapter.review_aulas(draft, model)
        self.assertEqual(reviewed['praticas']['comprovadas'], 0)
        self.assertEqual(model, original)
        html = self.adapter.render_aulas(reviewed)
        self.assertIn('15/12/2026', html)
        self.assertNotIn('31/05/2026', html)
        self.assertIn('não aplicável', html)
        draft['praticas_aplicaveis'] = False
        draft['praticas'] = None
        draft['prazo_praticas'] = ''
        draft['prazo_auditoria'] = ''
        html = self.adapter.render_aulas(self.adapter.review_aulas(draft, model))
        self.assertIn('Práticas: não aplicável', html)

    def test_generate_aggregated_practices_without_legacy_or_mail(self):
        self.bases()
        with patch('smtplib.SMTP', side_effect=AssertionError('Transporte proibido')):
            try:
                options = self.adapter.load_aulas(self.data)
            except FileNotFoundError as exc:
                self.fail(f'A prévia deve funcionar somente com as duas bases novas: {exc.filename}')
            self.assertEqual(list(options), ['101'])
            model = options['101']
            self.assertEqual(model['label'], POLO)
            self.assertEqual(model['polo_count'], 1)
            self.assertEqual(model.get('praticas'),
                             {'previstas': 10, 'comprovadas': 4, 'pendentes': 6})
            self.assertFalse(model.get('sequencias'))
            html = self.adapter.render_aulas(manual(model))
        self.assertIn('40%', html)
        self.assertIn('Laboratório sintético', html)
        self.assertIn('Reprovado', html)
        self.assertIn('ESCOPO', html)
        self.assertNotIn('>SEQ<', html)

    def test_export_footers_and_blank_separators_are_not_records(self):
        for footer in ('Applied filters:\nsemestre_operacional is 262',
                       'Filtros aplicados:\nsemestre_operacional é 262'):
            with self.subTest(footer=footer):
                self.bases(apps=[[POLO, 10, 4, 6], [], [footer]],
                           timeline=[timeline_row(), [], [footer]])
                try:
                    options = self.adapter.load_aulas(self.data)
                except (ValueError, TypeError) as exc:
                    self.fail(f'O leitor deve ignorar rodapés e separadores: {exc}')
                self.assertEqual(list(options), ['101'])
                self.assertEqual(len(options['101']['labs_lista']), 1)

    def test_missing_practices_stay_unknown_including_timeline_only_polo(self):
        other = 'POLO SINTÉTICO/RJ - I(202)A'
        self.bases(apps=[[POLO, 10, None, 6]],
                   timeline=[timeline_row(), timeline_row(polo=other)])
        try:
            options = self.adapter.load_aulas(self.data)
            html = self.adapter.render_aulas(manual(options['202']))
        except (ValueError, TypeError) as exc:
            self.fail(f'Ausência deve ser representada, não convertida em zero: {exc}')
        self.assertIsNone(options['101']['praticas']['comprovadas'])
        self.assertIsNone(options['202']['praticas'])
        self.assertIn('Não informado', html)
        self.assertNotIn('>0%<', html)
        self.assertNotIn('>0<', html)
        html_partial = self.adapter.render_aulas(manual(options['101']))
        self.assertIn('Não informado', html_partial)
        self.assertNotIn('>0%<', html_partial)

    def test_no_timeline_record_does_not_claim_no_audit(self):
        self.bases(timeline=[])
        model = self.adapter.load_aulas(self.data)['101']
        html = self.adapter.render_aulas(manual(model))
        self.assertIn('Sem registros na timeline', html)
        self.assertIn('não comprova ausência de auditoria', html)
        self.assertNotIn('Sem laboratórios registrados para esta unidade', html)
        self.assertNotIn('Não realizado', html)

    def test_workbook_strings_are_escaped_without_mutating_model(self):
        attack = '<img src=x onerror="alert(1)"> & \'texto\''
        name = f'{attack} - I(101)A'
        self.bases(apps=[[name, 10, 4, 6]],
                   timeline=[timeline_row(polo=name, lab=attack, parecer=attack)])
        model = self.adapter.load_aulas(self.data)['101']
        html = self.adapter.render_aulas(manual(model))
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; &#x27;texto&#x27;', html)
        self.assertEqual(model['nome'], name)
        self.assertEqual(self.adapter.render_aulas(manual(model)), html)

    def test_blank_laboratory_and_parecer_are_unknown_not_pending(self):
        self.bases(timeline=[timeline_row(lab=None, parecer=None)])
        model = self.adapter.load_aulas(self.data)['101']
        self.assertIsNone(model['labs_lista'][0]['nome'])
        self.assertIsNone(model['labs_lista'][0]['parecer'])
        html = self.adapter.render_aulas(manual(model))
        self.assertIn('Não informado', html)
        self.assertIn('Sem parecer', html)
        self.assertNotIn('1 pendente(s)', html)
        self.assertNotIn('>nan<', html)

    def test_aggregate_keeps_original_art_golden(self):
        self.bases(apps=[[POLO, 0, 0, 0]])
        html = self.adapter.render_aulas(manual(self.adapter.load_aulas(self.data)['101']))
        golden = Path(__file__).with_name('aulas_original_synthetic_golden.html').read_text(encoding='utf-8')
        # A fonte nova não discrimina sequências; só o cabeçalho semântico muda.
        self.assertEqual(html.replace('>ESCOPO<', '>SEQ<'), golden)

    def test_only_two_body_workbooks_are_read_and_no_transport_is_used(self):
        import pandas
        self.bases()
        original_read = pandas.read_excel
        reads = []

        def guarded_read(filename, **kwargs):
            self.assertIn(Path(filename).name, {APPS, TIMELINE})
            reads.append(Path(filename).name)
            return original_read(filename, **kwargs)

        for name in ('disparar_emails.py', 'emails.xlsx', 'Base de Polos - Master (1).xlsb'):
            (self.data / name).write_text('ARQUIVO PROIBIDO', encoding='utf-8')
        with patch('pandas.read_excel', side_effect=guarded_read), \
                patch('socket.create_connection', side_effect=AssertionError('Rede proibida')), \
                patch('smtplib.SMTP', side_effect=AssertionError('SMTP proibido')), \
                patch('smtplib.SMTP_SSL', side_effect=AssertionError('SMTP SSL proibido')), \
                patch('pathlib.Path.read_text', side_effect=AssertionError('Código legado proibido')):
            options = self.adapter.load_aulas(self.data)
            self.adapter.render_aulas(manual(options['101']))
        self.assertEqual(reads, [APPS, TIMELINE])

    def test_invalid_counts_are_rejected_not_truncated_or_negative(self):
        for invalid in (-1, 2.5, True, 'dez'):
            with self.subTest(value=invalid):
                self.bases(apps=[[POLO, 10, invalid, 6]])
                with self.assertRaisesRegex(ValueError, 'Contagem inválida'):
                    self.adapter.load_aulas(self.data)

    def test_required_headers_are_validated_even_for_empty_exports(self):
        for filename, headers in ((APPS, APPS_HEADERS), (TIMELINE, TIMELINE_HEADERS)):
            with self.subTest(filename=filename):
                self.bases()
                sheet(self.data / filename, headers[:1], [])
                with self.assertRaisesRegex(ValueError, 'Colunas ausentes'):
                    self.adapter.load_aulas(self.data)

    def test_duplicate_aggregates_are_rejected_instead_of_overwritten(self):
        self.bases(apps=[[POLO, 10, 4, 6], [POLO, 20, 8, 12]])
        with self.assertRaisesRegex(ValueError, 'Polo duplicado'):
            self.adapter.load_aulas(self.data)


if __name__ == '__main__':
    unittest.main()
