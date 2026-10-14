"""Encrypt a TimeTree session; optionally migrate and remove its plaintext file."""
import argparse
import getpass
import os
from pathlib import Path
import tempfile


def prepare(token, output, key_path):
    from cryptography.fernet import Fernet
    from secret_crypto import decrypt_session
    output, key_path = Path(output).resolve(), Path(key_path).resolve()
    if output.parent == key_path.parent or output == key_path:
        raise ValueError('Schlüssel und verschlüsseltes Secret in getrennten Ordnern speichern.')
    if not token or any(character.isspace() for character in token) or ';' in token:
        raise ValueError('Ungültiger Cookie-Wert.')
    key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if key_path.exists():
        key = key_path.read_bytes().strip()
        Fernet(key)
    else:
        key = Fernet.generate_key()
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as file:
            file.write(key + b'\n')
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    cipher = Fernet(key).encrypt(token.encode('utf-8'))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(cipher + b'\n')
        if decrypt_session(temporary, key_path) != token:
            raise ValueError('Überprüfung der Verschlüsselung fehlgeschlagen.')
        if os.name != 'nt':
            temporary.chmod(0o600)
            key_path.chmod(0o600)
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description='TimeTree-Secret verschlüsselt speichern.')
    parser.add_argument('--key-file', type=Path, required=True, help='Separater Pfad für den Schlüssel')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'secrets/timetree_session.enc')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--migrate', type=Path, help='Klartextdatei verschlüsseln und nach Prüfung entfernen')
    source.add_argument('--from-windows', action='store_true', help='Windows-Sitzung direkt verschlüsselt exportieren')
    args = parser.parse_args()
    try:
        if args.migrate:
            if args.migrate.resolve() in (args.key_file.resolve(), args.output.resolve()):
                raise ValueError('Quelldatei muss von Schlüssel und Zieldatei verschieden sein.')
            token = args.migrate.read_text(encoding='utf-8-sig').strip()
        elif args.from_windows:
            from timetree_sync import read_credentials, SESSION_SECRET
            _, token = read_credentials(SESSION_SECRET)
        else:
            token = getpass.getpass('TimeTree _session_id (nur Wert, verdeckt): ').strip()
        prepare(token, args.output, args.key_file)
        if args.migrate:
            args.migrate.unlink()
        print('Secret verschlüsselt und Entschlüsselung geprüft. Schlüssel separat schützen.')
        if args.migrate:
            print('Die alte Klartextdatei wurde entfernt. Vorhandene Backups werden nicht verändert.')
    except ImportError:
        raise SystemExit('Modul fehlt: python -m pip install -r requirements-sync.txt') from None
    except (OSError, ValueError, RuntimeError):
        raise SystemExit('Einrichtung fehlgeschlagen. Dateirechte, Cookie und Schlüssel prüfen; keine Werte ausgegeben.') from None


if __name__ == '__main__':
    main()
