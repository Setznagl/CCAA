"""Flow identifiers are also the importable preview module names."""
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
FLOW_APIS = {
    'AGENDA_SEMANAL_AUDITORIAS': ('load_mari', 'render_mari'),
    'AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA': ('load_aulas', 'render_aulas'),
    'AGENDA_FAST_TRACK_INFRA_2026': ('render_fast_track',),
    'AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS': ('load_consolidado', 'render_consolidado'),
}


class PreviewModuleNamesTests(unittest.TestCase):
    def test_every_flow_has_an_importable_preview_with_its_exact_name(self):
        for flow, names in FLOW_APIS.items():
            module_name = 'preview_' + flow
            with self.subTest(flow=flow):
                self.assertTrue((HERE / (module_name + '.py')).is_file(), module_name)
                module = importlib.import_module(module_name)
                for name in names:
                    self.assertTrue(callable(getattr(module, name)), name)

    def test_fast_track_module_preserves_static_bytes_without_reading_bases(self):
        module_path = HERE / 'preview_AGENDA_FAST_TRACK_INFRA_2026.py'
        self.assertTrue(module_path.is_file(), 'Falta o módulo Fast Track com o nome padronizado')
        module = importlib.import_module(module_path.stem)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy = root / 'fluxos/FAST_TRACK_INFRA_2026/modelo_email.html'
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b'<!doctype html>legado\r\n')
            modern = root / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html'
            with patch('pandas.read_excel', side_effect=AssertionError('Sem bases')):
                self.assertEqual(module.render_fast_track(root), legacy.read_bytes())
                modern.parent.mkdir(parents=True)
                body = '<!doctype html><p>Prévia estática — 31/08</p>\r\n'.encode('utf-8')
                modern.write_bytes(body)
                self.assertEqual(module.render_fast_track(root), body)
                self.assertEqual(modern.read_bytes(), body)


if __name__ == '__main__':
    unittest.main()
