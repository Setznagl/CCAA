"""Restricted hosted access; never imports an email transport."""
import base64
import binascii
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import urlsplit


class HostedAccess:
    def __init__(self, public_url, auth_file):
        parsed = urlsplit(public_url)
        hostname = parsed.hostname or ''
        if (parsed.scheme != 'https' or parsed.netloc.lower() != hostname
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment
                or not 1 <= len(hostname) <= 253
                or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                       for label in hostname.split('.'))):
            raise ValueError('CCAA_PUBLIC_URL deve ser https://dominio, sem porta, caminho ou credenciais')
        self.origin = 'https://' + hostname
        self.authority = hostname
        path = Path(auth_file)
        try:
            if path.stat().st_size > 4096 or path.stat().st_mode & 0o077:
                raise ValueError('Arquivo de autenticação deve ser restrito ao usuário (modo600)')
            config = json.loads(path.read_text(encoding='utf-8'))
            if (set(config) != {'version', 'user', 'salt', 'hash'} or config['version'] != 1
                    or not isinstance(config['user'], str) or not 1 <= len(config['user']) <= 128
                    or ':' in config['user'] or any(ord(c) < 33 for c in config['user'])
                    or not re.fullmatch(r'[0-9a-f]{32}', config['salt'])
                    or not re.fullmatch(r'[0-9a-f]{128}', config['hash'])):
                raise ValueError('Configuração de autenticação inválida')
            self.user = hashlib.sha256(config['user'].encode()).digest()
            self.salt = bytes.fromhex(config['salt'])
            self.expected = bytes.fromhex(config['hash'])
        except (OSError, ValueError, TypeError, KeyError):
            raise ValueError('Configure CCAA_AUTH_FILE com o arquivo válido e restrito criado pelo on.sh') from None
        self.hash_slots = threading.BoundedSemaphore(4)
        self.accepted_header = None

    def authorize(self, request):
        headers = request.headers
        host = headers.get('Host', '').lower()
        local = {f'127.0.0.1:{request.server.server_port}', f'localhost:{request.server.server_port}'}
        if (request.command == 'GET' and request.path == '/healthz'
                and request.client_address[0] in {'127.0.0.1', '::1'} and host in local
                and len(headers.get_all('Host', [])) == 1 and not headers.get('Origin')
                and headers.get('Sec-Fetch-Site') != 'cross-site'):
            return True
        origin = headers.get('Origin')
        external_navigation = (request.command == 'GET' and headers.get('Sec-Fetch-Mode') == 'navigate'
                               and headers.get('Sec-Fetch-Dest') == 'document')
        if (len(headers.get_all('Host', [])) != 1 or host not in {self.authority, self.authority + ':443'}
                or len(headers.get_all('Origin', [])) > 1
                or (origin and origin != self.origin)
                or (request.command not in {'GET', 'HEAD'} and origin != self.origin)
                or (headers.get('Sec-Fetch-Site') == 'cross-site' and not external_navigation)):
            request.close_connection = True
            request.json_reply(403, {'error': 'Origem ou domínio não autorizado'})
            return False
        value = headers.get('Authorization', '')
        single_header = len(headers.get_all('Authorization', [])) == 1 and len(value) <= 2048
        fingerprint = hashlib.sha256(value.encode()).digest() if single_header else None
        if self.accepted_header is not None and fingerprint is not None and hmac.compare_digest(fingerprint, self.accepted_header):
            return True
        if not self.hash_slots.acquire(blocking=False):
            request.close_connection = True
            request.reply(503, 'Autenticação ocupada; tente novamente.', headers={'Retry-After': '1'})
            return False
        valid = False
        try:
            if single_header and value[:6].lower() == 'basic ':
                decoded = base64.b64decode(value[6:], validate=True).decode('utf-8')
                user, separator, password = decoded.partition(':')
                if separator and len(user) <= 128 and 1 <= len(password) <= 512:
                    derived = hashlib.scrypt(password.encode(), salt=self.salt, n=16384, r=8, p=1)
                    valid_user = hmac.compare_digest(hashlib.sha256(user.encode()).digest(), self.user)
                    valid = hmac.compare_digest(derived, self.expected) and valid_user
        except (ValueError, binascii.Error, UnicodeDecodeError):
            pass
        finally:
            self.hash_slots.release()
        if valid:
            self.accepted_header = fingerprint
            return True
        request.close_connection = True
        request.reply(401, 'Autenticação necessária.', headers={'WWW-Authenticate': 'Basic realm="CCAA", charset="UTF-8"'})
        return False


def init_auth(folder):
    folder = Path(folder)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.chmod(0o700)
    auth, login = folder / 'auth.json', folder / 'acesso.txt'
    if auth.exists():
        HostedAccess('https://ccaa.invalid', auth)
        return False
    if login.exists():
        raise ValueError('acesso.txt existe sem auth.json; confira os arquivos antes de inicializar')
    password, salt = secrets.token_urlsafe(32), secrets.token_bytes(16)
    config = {'version': 1, 'user': 'admin', 'salt': salt.hex(),
              'hash': hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()}
    # Exclusive creation preserves existing credentials on repeated deploys.
    for path, content in ((login, f'Usuário: admin\nSenha: {password}\n'),
                          (auth, json.dumps(config))):
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as stream:
            stream.write(content)
    return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Inicializa uma credencial local sem sobrescrever a existente')
    parser.add_argument('--init-auth', required=True, metavar='PASTA')
    args = parser.parse_args()
    init_auth(args.init_auth)
    print('Credenciais preservadas em ' + str(Path(args.init_auth) / 'acesso.txt') + '; conteúdo não exibido.')
