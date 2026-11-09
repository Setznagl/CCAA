import ast
import hashlib
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'rev/DisparoAulasPraticas/disparar_emails.py'


def sheet(path, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


class AulasPreviewTests(unittest.TestCase):
    def test_generate_from_workbooks_without_mail(self):
        try:
            adapter = importlib.import_module('preview_aulas')
        except ModuleNotFoundError:
            self.fail('O adaptador isolado de prévia de aulas ainda não existe')
        before = hashlib.sha256(SOURCE.read_bytes()).digest()
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            (data / 'disparar_emails.py').write_bytes(SOURCE.read_bytes())
            sheet(data / 'sequenciaa1.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'],
                  [['POLO TESTE/SP - I(101)A', 10, 4, 6]])
            sheet(data / 'labs.xlsx', ['Polo', 'Laboratório', 'Parecer Auditoria'],
                  [['POLO TESTE/SP - I(101)A', 'Laboratório de teste', 'Reprovado']])
            with patch('smtplib.SMTP', side_effect=AssertionError('Transporte proibido')):
                options = adapter.load_aulas(data)
                self.assertEqual(list(options), ['101'])
                self.assertEqual(options['101']['label'], 'POLO TESTE/SP - I(101)A')
                html = adapter.render_aulas(options['101'])
            self.assertIn('<!DOCTYPE html>', html)
            self.assertIn('POLO TESTE/SP - I(101)A', html)
            self.assertIn('Laboratório de teste', html)
            self.assertIn('Reprovado', html)
            self.assertIn('40%', html)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).digest(), before)

    def test_preview_does_not_read_recipient_files(self):
        import preview_aulas as adapter
        import pandas
        original_read = pandas.read_excel
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            (data / 'disparar_emails.py').write_bytes(SOURCE.read_bytes())
            sheet(data / 'sequenciaa1.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'],
                  [['POLO TESTE/SP - I(101)A', 10, 4, 6]])
            (data / 'emails.xlsx').write_bytes(b'not-part-of-body-preview')
            (data / 'Base de Polos - Master (1).xlsb').write_bytes(b'not-part-of-body-preview')

            def guarded_read(filename, **kwargs):
                if Path(filename).name in {'emails.xlsx', 'Base de Polos - Master (1).xlsb'}:
                    raise AssertionError('A prévia do corpo não deve resolver destinatários')
                return original_read(filename, **kwargs)

            with patch('pandas.read_excel', side_effect=guarded_read):
                options = adapter.load_aulas(data)
            self.assertIn('101', options)


if __name__ == '__main__':
    unittest.main()
