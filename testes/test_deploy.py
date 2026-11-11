"""Deployment file and launcher checks never operate a Docker daemon."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_requested_files_and_shell_syntax(self):
        for name in ('Dockerfile', 'docker-compose.yml', 'on.sh', '.dockerignore', '.env.example'):
            self.assertTrue((ROOT / name).is_file(), name)
        subprocess.run(['sh', '-n', str(ROOT / 'on.sh')], check=True)
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('USER ccaa', dockerfile)
        self.assertNotIn('COPY . .', dockerfile)
        self.assertNotIn('COPY databases', dockerfile)
        self.assertIn('/healthz', dockerfile)

    def test_launcher_matches_lira_sequence_and_preserves_credentials(self):
        self.assertTrue((ROOT / 'on.sh').is_file())
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'testes').mkdir()
            shutil.copyfile(ROOT / 'on.sh', folder / 'on.sh')
            shutil.copyfile(ROOT / 'testes/hosted.py', folder / 'testes/hosted.py')
            tools = folder / 'bin'
            tools.mkdir()
            docker = tools / 'docker'
            docker.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$DEPLOY_LOG"
case "$*" in
  *"config --format json") printf '%s\\n' '{"services":{"ccaa":{"user":"1000:1000"}}}' ;;
  "build -t ccaa:local .") test "${FAIL_BUILD:-0}" != 1 ;;
esac
''')
            sudo = tools / 'sudo'
            sudo.write_text('''#!/bin/sh
case "$1" in
  python3) exec "$@" ;;
  chown|chmod) exit 0 ;;
  *) exit 90 ;;
esac
''')
            docker.chmod(0o755)
            sudo.chmod(0o755)
            log = folder / 'calls.log'
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'], DEPLOY_LOG=str(log))
            subprocess.run(['sh', str(folder / 'on.sh')], env=env, check=True, capture_output=True)
            before = (folder / 'runtime/auth.json').read_bytes()
            subprocess.run(['sh', str(folder / 'on.sh')], env=env, check=True, capture_output=True)
            self.assertEqual((folder / 'runtime/auth.json').read_bytes(), before)
            calls = log.read_text().splitlines()
            self.assertLess(calls.index('compose -f docker-compose.yml stop ccaa'), calls.index('build -t ccaa:local .'))
            self.assertIn('compose -f docker-compose.yml up -d --no-build --pull never --force-recreate ccaa', calls)
            log.write_text('')
            result = subprocess.run(['sh', str(folder / 'on.sh')], env=dict(env, FAIL_BUILD='1'), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(' up ', log.read_text(), 'failed build must not recreate from an older image')
            self.assertEqual((folder / 'runtime/auth.json').read_bytes(), before)

    def test_real_compose_configuration_when_plugin_is_available(self):
        probe = subprocess.run(['docker', 'compose', 'version'], capture_output=True) if shutil.which('docker') else None
        if probe is None or probe.returncode:
            self.skipTest('Docker Compose plugin unavailable')
        with TemporaryDirectory() as temp:
            env_file = Path(temp) / 'example.env'
            env_file.write_text('COMPOSE_PROJECT_NAME=ccaa\nTRAEFIK_HOST=example.test\nCCAA_PORT=8876\nCCAA_UID=1000\nCCAA_GID=1000\n')
            env = {key: value for key, value in os.environ.items() if key not in {
                'COMPOSE_PROJECT_NAME', 'TRAEFIK_HOST', 'CCAA_PORT', 'CCAA_UID', 'CCAA_GID'}}
            result = subprocess.run(['docker', 'compose', '--env-file', str(env_file), '-f', str(ROOT / 'docker-compose.yml'),
                                     'config', '--format', 'json'], env=env, capture_output=True, text=True, check=True)
            service = json.loads(result.stdout)['services']['ccaa']
            self.assertEqual(service['network_mode'], 'host')
            self.assertNotIn('ports', service)
            self.assertEqual(service['user'], '1000:1000')
            self.assertEqual(service['environment']['CCAA_PUBLIC_URL'], 'https://ccaa.example.test')
            self.assertEqual(service['labels']['traefik.http.routers.ccaa.rule'], 'Host(`ccaa.example.test`)')
            self.assertEqual(service['labels']['traefik.http.services.ccaa.loadbalancer.server.port'], '8876')


if __name__ == '__main__':
    unittest.main()
