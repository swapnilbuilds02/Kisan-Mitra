"""Shared, memory-hard password handling for all account roles."""

import base64
import hashlib
import hmac
import secrets

_N = 2**14
_R = 8
_P = 1


def validate_password(password: str) -> None:
    if not isinstance(password, str) or not 12 <= len(password) <= 1024 or len(password.encode('utf-8')) > 2048:
        raise ValueError('Password must contain 12 to 1024 characters')
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError('Password must contain a letter and a digit')


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return 'scrypt$16384$8$1$' + base64.b64encode(salt).decode('ascii') + '$' + base64.b64encode(digest).decode('ascii')


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        if not isinstance(password, str) or len(password.encode('utf-8')) > 2048:
            return False
        if encoded is None:
            hashlib.scrypt(password.encode('utf-8'), salt=b'KisanMitraDummy!', n=_N, r=_R, p=_P, dklen=32)
            return False
        if not isinstance(encoded, str):
            return False
        scheme, n, r, p, salt_text, digest_text = encoded.split('$')
        if (scheme, n, r, p) != ('scrypt', '16384', '8', '1'):
            return False
        salt = base64.b64decode(salt_text, validate=True)
        expected = base64.b64decode(digest_text, validate=True)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=_N, r=_R, p=_P, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False
