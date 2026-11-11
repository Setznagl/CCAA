"""Hosted access uses disposable credentials; local defaults stay unchanged."""
import base64
from contextlib import closing
import hashlib
import http.client
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from preview_server import make_server


class HostedTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.auth = Path(self.temp.name) / 'auth.json'
        self.password = 'QA-disposable-password-not-a-real-credential'
        salt = bytes.fromhex('11' * 16)
        self.auth.write_text(json.dumps({'version': 1, 'user': 'qa-admin', 'salt': salt.hex(),
            'hash': hashlib.scrypt(self.password.encode(), salt=salt, n=16384, r=8, p=1).hex()}))
        self.auth.chmod(0o600)
        self.origin = 'https://ccaa.example.test'
        with patch.dict(os.environ, CCAA_PUBLIC_URL=self.origin, CCAA_AUTH_FILE=str(self.auth), CCAA_HOST='127.0.0.1'):
            self.server = make_server(Path(__file__).resolve().parents[1], 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path='/', *, credentials=None, method='GET', headers=None, body=None):
        fields = {'Host': 'ccaa.example.test'}
        if credentials:
            fields['Authorization'] = 'Basic ' + base64.b64encode(credentials.encode()).decode()
        fields.update(headers or {})
        with closing(http.client.HTTPConnection('127.0.0.1', self.server.server_port)) as connection:
            connection.request(method, path, body=body, headers=fields)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def test_all_content_requires_login(self):
        for path in ('/', '/mari', '/app.js', '/api/lote/fast-track', '/api/lote/modelo.xlsx', '/healthz'):
            with self.subTest(path=path):
                status, headers, _ = self.request(path)
                self.assertEqual(status, 401)
                self.assertIn('Basic realm="CCAA"', headers['WWW-Authenticate'])
                self.assertEqual(headers['Cache-Control'], 'no-store')
        valid = 'qa-admin:' + self.password
        self.assertEqual(self.request('/fast-track-infra-2026/lote', credentials=valid)[0], 200)
        self.assertEqual(self.request('/app.js', credentials=valid)[0], 200)
        self.assertEqual(self.request('/', credentials='other:' + self.password)[0], 401)
        self.assertEqual(self.request('/', credentials='qa-admin:wrong')[0], 401)

    def test_exact_authority_origin_and_safe_navigation(self):
        valid = 'qa-admin:' + self.password
        self.assertEqual(self.request(credentials=valid, headers={'Host': 'evil.example.test'})[0], 403)
        self.assertEqual(self.request(credentials=valid, headers={'Origin': 'https://evil.example.test'})[0], 403)
        self.assertEqual(self.request(credentials=valid, headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request('/fast-track-infra-2026', credentials=valid,
            headers={'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'})[0], 200)
        fields = {'Content-Type': 'application/json'}
        self.assertEqual(self.request('/api/lote/preview', method='POST', credentials=valid, headers=fields,
                                     body=json.dumps({'html': '<p>QA</p>'}))[0], 403)
        fields['Origin'] = self.origin
        self.assertEqual(self.request('/api/lote/preview', method='POST', credentials=valid, headers=fields,
                                     body=json.dumps({'html': '<p>QA</p>'}))[0], 200)
        self.assertEqual(self.request('/app.js', headers={'X-Forwarded-For': '127.0.0.1'})[0], 401)

    def test_health_is_anonymous_only_with_local_authority(self):
        status, _, body = self.request('/healthz', headers={'Host': f'127.0.0.1:{self.server.server_port}'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'status': 'ok'})
        self.assertEqual(self.request('/mari', headers={'Host': f'127.0.0.1:{self.server.server_port}'})[0], 403)

    def test_valid_browser_assets_do_not_fail_under_parallel_loading(self):
        from concurrent.futures import ThreadPoolExecutor

        valid = 'qa-admin:' + self.password
        self.assertEqual(self.request('/app.js', credentials=valid)[0], 200)
        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(lambda _: self.request('/app.js', credentials=valid)[0], range(24)))
        self.assertEqual(statuses, [200] * 24)

    def test_credential_initialization_is_private_and_does_not_rotate_on_restart(self):
        folder = Path(self.temp.name) / 'runtime'
        command = [sys.executable, str(Path(__file__).with_name('hosted.py')), '--init-auth', str(folder)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((folder / 'auth.json').is_file())
        config = (folder / 'auth.json').read_bytes()
        login = (folder / 'acesso.txt').read_bytes()
        password = login.decode().splitlines()[1].split(': ', 1)[1]
        self.assertNotIn(password.encode(), config)
        self.assertNotIn(password, result.stdout)
        self.assertEqual((folder / 'auth.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((folder / 'acesso.txt').stat().st_mode & 0o777, 0o600)
        self.assertEqual((folder.stat().st_mode & 0o777), 0o700)
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual((folder / 'auth.json').read_bytes(), config)
        self.assertEqual((folder / 'acesso.txt').read_bytes(), login)

    def test_invalid_hosted_configuration_fails_closed(self):
        for url in ('http://ccaa.example.test', 'https://ccaa..example.test', 'https://-ccaa.example.test',
                    'https://ccaa.example.test:8443', 'https://user@ccaa.example.test', 'https://ccaa.example.test/path'):
            with self.subTest(url=url), patch.dict(os.environ, CCAA_PUBLIC_URL=url, CCAA_AUTH_FILE=str(self.auth)):
                with self.assertRaises(ValueError):
                    make_server(Path(self.temp.name), 0)
        with patch.dict(os.environ, CCAA_PUBLIC_URL='', CCAA_AUTH_FILE='', CCAA_HOST='0.0.0.0'):
            with self.assertRaises(ValueError):
                make_server(Path(self.temp.name), 0)


if __name__ == '__main__':
    unittest.main()
