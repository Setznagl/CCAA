"""Exercise the real command-line server without loading operational data."""
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen


SERVER = Path(__file__).with_name('preview_server.py')


class ServerStartupTests(unittest.TestCase):
    def test_one_announced_address_serves_every_page(self):
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, str(SERVER), '--port', str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 8
            while True:
                try:
                    with urlopen(f'http://127.0.0.1:{port}/mari', timeout=0.3) as response:
                        self.assertEqual(response.status, 200)
                    break
                except (URLError, TimeoutError):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        self.fail('O servidor não ficou disponível na porta solicitada')
                    time.sleep(0.03)
            for path in ('/aulas-praticas', '/fast-track-infra-2026', '/auditoria-situacao-polos'):
                with urlopen(f'http://127.0.0.1:{port}{path}', timeout=2) as response:
                    self.assertEqual(response.status, 200)
        finally:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
        addresses = [line for line in stdout.splitlines() if line.startswith('CCAA: http://')]
        self.assertEqual(len(addresses), 1, stdout)
        self.assertEqual(addresses[0], f'CCAA: http://127.0.0.1:{port}/')
        self.assertEqual(stderr, '')

    def test_occupied_port_fails_without_starting_on_another_port(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            result = subprocess.run(
                [sys.executable, str(SERVER), '--port', str(port)],
                capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'A porta {port} já está em uso', result.stderr)
        self.assertNotIn('CCAA: http://', result.stdout)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
