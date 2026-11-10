"""Mari sources and mandatory review; fixtures contain no operational contacts."""
import sys
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, date
from openpyxl import Workbook
sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview_AGENDA_SEMANAL_AUDITORIAS as mari


def sources(root):
    folder = Path(root) / 'databases/09-11-26'
    folder.mkdir(parents=True)
    for name, rows in {
        'auditoria-timeline-262.xlsx': [
            ['Polo', 'semestre_operacional_x', 'Laboratório', 'Data agendada'],
            ['Polo A', '262', 'Lab 1', datetime(2026, 11, 1, 9)],
            ['Polo A', '262', 'Lab 2', datetime(2026, 11, 3, 10)],
            ['Polo B', '262', 'Lab 3', None],
            ['Polo C', '262', 'Lab 4', datetime(2026, 11, 4)],
            ['Polo D', '262', 'Lab 5', datetime(2026, 11, 5)],
            [], ['Applied filters:\nsemestre_operacional_x is 262']],
        'auditoria-tabela-contatos.xlsx': [
            ['Polo', 'Gerente Operacional', 'E-mail'],
            ['Polo A', 'GO Válido', 'gestor-polo@example.org'],
            ['Polo A', 'GO Válido', 'outro-polo@example.org'],
            ['Polo B', 'TBD - Pessoa', 'polo-b@example.org'],
            ['Polo C', 'GO Um', 'polo-c@example.org'],
            ['Polo C', 'GO Dois', 'outro-c@example.org'],
            ['Polo D', 'GO Válido', 'polo-d@example.org'],
            [], ['Filtros aplicados:\nPolo não está em branco']],
    }.items():
        workbook = Workbook(); sheet = workbook.active
        for row in rows: sheet.append(row)
        workbook.save(folder / name); workbook.close()


class SourcesTests(unittest.TestCase):
    def test_new_sources_keep_every_lab_and_unknown_managers_accessible(self):
        with tempfile.TemporaryDirectory() as root:
            sources(root)
            try:
                models = mari.load_mari(Path(root))
            except FileNotFoundError:
                self.fail('Mari must read only the new XLSX sources, not require the legacy XLSM')
            self.assertEqual(list(models), list(mari.load_mari(Path(root))))
            self.assertEqual(sum(m['polo_count'] for m in models.values()), 4)
            known = next(m for m in models.values() if m['label'] == 'GO Válido')
            self.assertEqual(known['polo_count'], 2)
            self.assertEqual(len(known['draft']['rows']), 3)
            self.assertEqual(known['draft']['email'], '')
            self.assertEqual(known['draft']['rows'][0]['grupo'], '')
            self.assertEqual(known['draft']['rows'][0]['date'], '2026-11-01T09:00')
            self.assertEqual(known['source_cycles'], ['262'])
            unknown = next(m for m in models.values() if m['draft']['label'] == '')
            self.assertEqual({r['polo'] for r in unknown['draft']['rows']}, {'Polo B', 'Polo C'})
            self.assertEqual(len(unknown['warnings']) > 0, True)
            self.assertTrue(all('gestor-polo@' not in str(m) for m in models.values()))

    def test_review_requires_supplements_and_preserves_selected_source_identity(self):
        import copy
        self.assertTrue(callable(getattr(mari, 'review_mari', None)), 'review validator is required before rendering')
        with tempfile.TemporaryDirectory() as root:
            sources(root)
            record = next(m for m in mari.load_mari(Path(root)).values() if m['label'] == 'GO Válido')
            draft = copy.deepcopy(record['draft'])
            with self.assertRaises(ValueError): mari.review_mari(draft, record)
            draft.update(label='GO & <Revisado>', email='go@example.org', reviewed=True)
            for row in draft['rows']: row['grupo'] = 'G & <Um>'
            model = mari.review_mari(draft, record)
            self.assertEqual(model['polo_count'], 2)
            self.assertEqual(len(model['rows']), 3)
            html = mari.render_mari(model, date(2026, 11, 1))
            self.assertIn('GO &amp; &lt;Revisado&gt;', html)
            self.assertIn('G &amp; &lt;Um&gt;', html)
            self.assertIn('Lab 2', html)
            self.assertIn('10:00', html)
            self.assertIn('line-height:1.1">2</span>', html)
            for field, bad in [('label', 'TBD - Fulano'), ('email', 'polo@example.org\r\nBcc: x@y.org'), ('reviewed', False), ('rows', []), ('rows', [None]), ('label', 'a' * 301)]:
                changed = copy.deepcopy(draft); changed[field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    mari.review_mari(changed, record)
            for field, bad in [('id', 'inventado'), ('date', ''), ('date', '2026-02-30T10:00'), ('grupo', ''), ('grupo', 'TBD'), ('selected', 'false'), ('polo', '<inventado>')]:
                changed = copy.deepcopy(draft); changed['rows'][0][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    mari.review_mari(changed, record)
            changed = copy.deepcopy(draft)
            for row in changed['rows']: row['grupo'] = 'TBD'
            with self.assertRaises(ValueError): mari.review_mari(changed, record)
            changed = copy.deepcopy(draft); changed['rows'][1]['grupo'] = 'outro'
            with self.assertRaises(ValueError): mari.review_mari(changed, record)
            draft['rows'][1]['selected'] = False
            draft['rows'][1]['date'] = ''
            selected = mari.review_mari(draft, record)
            self.assertEqual(len(selected['rows']), 2)
            self.assertEqual(selected['polo_count'], 2)


if __name__ == '__main__': unittest.main()
