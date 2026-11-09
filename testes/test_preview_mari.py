"""Compatibility checks against the untouched, saved cp1252 preview."""
import importlib.util
from datetime import date, datetime
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'rev' / 'Disparo Auditoria Mari'
MODULE = Path(__file__).with_name('preview_mari.py')


def renderer():
    if not MODULE.exists():
        return None
    spec = importlib.util.spec_from_file_location('preview_mari', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def golden_body():
    saved = (SOURCE / 'previews' / 'adiel_martins_cogna_com_br.html').read_text(encoding='cp1252')
    # Only transport metadata/comment and file encoding differ from HTMLBody.
    return saved[saved.index('<html>'):].strip().replace('charset="windows-1252"', 'charset="UTF-8"')


class MariTests(unittest.TestCase):
    def test_cached_workbook_grouping_matches_saved_body(self):
        module = renderer()
        self.assertTrue(callable(getattr(module, 'load_mari', None)), 'cached Mari loader not implemented')
        models = module.load_mari(SOURCE)
        self.assertEqual(len(models), 14)
        self.assertEqual(sum(m['polo_count'] for m in models.values()), 36)
        self.assertEqual(list(models), list(module.load_mari(SOURCE)))
        model = next(m for m in models.values() if m['label'] == 'ADIEL MARTINS')
        self.assertEqual(module.render_mari(model, date(2026, 9, 11)), golden_body())
        self.assertNotIn('@', module.render_mari(model, date(2026, 9, 11)))

    def test_brazilian_text_date_uses_same_valid_date_branch(self):
        model = {'label': '', 'polo_count': 1, 'rows': [
            {'polo': 'P&D <Sul>', 'grupo': '', 'date': '11/09/2026'},
        ]}
        html = renderer().render_mari(model, date(2026, 9, 11))
        self.assertIn('sexta-feira', html)
        self.assertIn('Gerente Operacional', html)
        self.assertIn('P&amp;D &lt;Sul&gt;', html)
        self.assertIn('>polo</span>', html)
        self.assertNotIn('>polos</span>', html)

    def test_missing_invalid_dates_and_row_order_remain_unchanged(self):
        model = {'label': '  Nome & <GO>  ', 'polo_count': 2, 'rows': [
            {'polo': 'Mesmo polo', 'grupo': ' ', 'date': None},
            {'polo': 'Mesmo polo', 'grupo': 'A&B', 'date': '<pendente>'},
        ]}
        html = renderer().render_mari(model, date(2026, 9, 11))
        self.assertIn('>A definir</span>', html)
        self.assertIn('>A marcar</td>', html)
        self.assertIn('border-left:3px solid #B26A00', html)
        self.assertIn('background:#FAF8FD;padding:11px', html)
        self.assertIn('&lt;pendente&gt;</td>', html)
        self.assertIn('>-</td>', html)
        self.assertIn('Nome &amp; &lt;GO&gt;', html)
        self.assertEqual(html.count('>Mesmo polo</td>'), 2)
        self.assertIn('line-height:1.1">2</span>', html)
        self.assertLess(html.index('>A marcar</td>'), html.index('&lt;pendente&gt;</td>'))

    def test_today_controls_past_highlight_not_saved_preheader(self):
        model = {'label': 'GO', 'polo_count': 1, 'rows': [
            {'polo': 'Polo', 'grupo': '3', 'date': datetime(2026, 9, 11, 9)},
        ]}
        module = renderer()
        before = module.render_mari(model, date(2026, 9, 11))
        after = module.render_mari(model, date(2026, 9, 12))
        self.assertNotIn('data já passou', before)
        self.assertIn('data já passou', after)
        self.assertIn('Próxima: sexta-feira, 11/09.', after)
        self.assertIn('>11/09/2026</span>', after)

    def test_full_saved_preview_markup(self):
        module = renderer()
        self.assertIsNotNone(module, 'isolated Mari renderer not implemented')
        model = {'label': 'ADIEL MARTINS', 'polo_count': 2, 'rows': [
            {'polo': 'PORANGATU/GO - I(22483)AC', 'grupo': '3', 'date': datetime(2026, 9, 8, 9)},
            {'polo': 'RUBIATABA/GO - I(5605)U', 'grupo': '5', 'date': datetime(2026, 9, 11, 9)},
        ]}
        self.assertEqual(module.render_mari(model, date(2026, 9, 11)), golden_body())


if __name__ == '__main__':
    unittest.main()
