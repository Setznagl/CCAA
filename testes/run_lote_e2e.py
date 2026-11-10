"""Run the batch browser test against a test-owned ephemeral server."""
import os
from pathlib import Path
import subprocess
import tempfile
import threading

from openpyxl import Workbook
from preview_server import make_server
from test_fast_track_lote import batch_fixture

root = Path(__file__).resolve().parents[1]
server = make_server(root, 0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with tempfile.TemporaryDirectory(prefix='ccaa-lote-e2e-') as scratch:
        book = Workbook()
        sheet = book.active
        sheet.title = 'DESTINATARIOS'
        sheet.append(['Enviar', 'Polo', 'Para', 'CC', 'CCO', 'Assunto'])
        sheet.append(['SIM', 'Polo QA', 'qa@example.test', '', '', ''])
        sheet.append(['', 'Polo não selecionado', 'inválido', '', '', ''])
        fixture = Path(scratch) / 'destinatarios.xlsx'
        book.save(fixture)
        env = dict(os.environ, CCAA_TEST_URL=f'http://127.0.0.1:{server.server_port}',
                   CCAA_LOTE_XLSX=str(fixture))
        env.setdefault('CCAA_EVIDENCE', str(Path(tempfile.gettempdir()) / 'ccaa-lote-evidence'))
        subprocess.run(['node', str(root / 'testes/test_lote_e2e.mjs')], env=env, check=True, timeout=120)
        fixture_root = Path(scratch) / 'fast-track'
        batch_fixture(fixture_root)
        mapped_server = make_server(fixture_root, 0)
        mapped_thread = threading.Thread(target=mapped_server.serve_forever, daemon=True)
        mapped_thread.start()
        try:
            env['CCAA_TEST_URL'] = f'http://127.0.0.1:{mapped_server.server_port}'
            subprocess.run(['node', str(root / 'testes/test_fast_track_lote_e2e.mjs')], env=env, check=True, timeout=120)
        finally:
            mapped_server.shutdown()
            mapped_server.server_close()
            mapped_thread.join()
finally:
    server.shutdown()
    server.server_close()
    thread.join()
