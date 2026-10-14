"""Authenticated encryption for the local TimeTree session file."""
from pathlib import Path


def decrypt_session(cipher_path, key_path):
    from cryptography.fernet import Fernet, InvalidToken
    try:
        key = Path(key_path).read_bytes().strip()
        token = Fernet(key).decrypt(Path(cipher_path).read_bytes().strip()).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeError):
        raise ValueError('TimeTree-Secret kann nicht entschlüsselt werden: Schlüssel oder Datei ungültig.') from None
    if not token or any(character.isspace() for character in token) or ';' in token:
        raise ValueError('Entschlüsseltes TimeTree-Secret enthält keinen gültigen Cookie-Wert.')
    return token
