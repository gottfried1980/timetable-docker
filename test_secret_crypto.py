import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from secret_crypto import decrypt_session
import timetree_sync as sync

prepare = runpy.run_path(str(Path(__file__).parent / 'prepare-secret.py'))['prepare']


class SecretTests(unittest.TestCase):
    def test_encryption_key_reuse_and_reject_tampering(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root = Path(folder)
            cipher, key = root / 'secrets/session.enc', root / 'keys/session.key'
            prepare('fake-private-session', cipher, key)
            self.assertNotIn(b'fake-private-session', cipher.read_bytes())
            self.assertEqual(decrypt_session(cipher,key),'fake-private-session')
            original_key=key.read_bytes()
            prepare('renewed-session',cipher,key)
            self.assertEqual(key.read_bytes(),original_key)
            self.assertEqual(decrypt_session(cipher,key),'renewed-session')
            wrong=root / 'wrong.key'; wrong.write_bytes(Fernet.generate_key())
            with self.assertRaises(ValueError): decrypt_session(cipher,wrong)
            cipher.write_bytes(cipher.read_bytes()[:20] + b'broken')
            with self.assertRaises(ValueError): decrypt_session(cipher,key)

    def test_sync_reads_encrypted_secret_without_windows(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder); cipher=root/'secrets/session.enc'; key=root/'keys/session.key'
            prepare('fake-session',cipher,key)
            with patch.dict(os.environ, {'TIMETREE_SESSION_FILE':str(cipher),'TIMETREE_KEY_FILE':str(key)}), \
                    patch('sys.argv',['sync','sync','--live','--dry-run','--calendar','demo-calendar']), \
                    patch.object(sync,'live_state',return_value=[]), \
                    patch.object(sync,'read_credentials',side_effect=AssertionError('Windows read')), \
                    patch.object(sync,'fetch_events',return_value=[]) as fetch, patch('builtins.print'):
                self.assertEqual(sync.main(),0)
                self.assertEqual(fetch.call_args.args[3],'fake-session')


if __name__ == '__main__': unittest.main()
