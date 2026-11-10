"""Portable smoke checks; behavioral checks run via tests.ps1 and pwsh."""
from pathlib import Path
import unittest

ROOT = Path(__file__).parent

class Contract(unittest.TestCase):
    def test_launcher_uses_policy_and_explains_failure(self):
        launcher = (ROOT / 'abrir.cmd').read_text(encoding='utf-8')
        self.assertIn('powershell.exe -NoProfile -File "%~dp0executar.ps1"', launcher)
        self.assertNotIn('bypass', launcher.lower())
        self.assertIn('pause', launcher)
        self.assertIn('procure o suporte de TI', launcher)

    def test_bridge_exists_and_preserves_security_boundaries(self):
        self.assertTrue((ROOT / 'executar.ps1').is_file(), 'Missing runnable Outlook bridge')
        raw = (ROOT / 'executar.ps1').read_bytes()
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'), 'Windows PowerShell 5.1 requires BOM for Portuguese')
        script = raw.decode('utf-8-sig')
        for forbidden in ('SyncObjects', 'SendAndReceive', 'PropertyAccessor', 'Invoke-Expression'):
            self.assertNotIn(forbidden, script)
        self.assertIn('SendUsingAccount', script)
        self.assertIn('GetItemFromID', script)
        self.assertIn('FileShare]::None', script)
        self.assertIn('File]::Replace', script)

if __name__ == '__main__':
    unittest.main()
