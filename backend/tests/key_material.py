"""Ephemeral RSA test keys. No private key is written to disk."""

from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.app.auth import TokenService


@lru_cache(maxsize=2)
def key_pair(label="test-v1"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return private, public


def token_service(label="test-v1"):
    private, public = key_pair(label)
    return TokenService(private, {label: public}, label)
