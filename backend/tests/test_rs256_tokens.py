"""RS256 contract tests with RSA keys generated only in memory."""

from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import jwt
import pytest

from backend.app.auth import AUDIENCE, ISSUER, AuthenticationError, TokenService
from backend.tests.key_material import key_pair


def signed(private, kid, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid4()), "sid": str(uuid4()), "jti": str(uuid4()),
        "typ": "access", "iat": now, "nbf": now,
        "exp": now + timedelta(minutes=15), "iss": ISSUER, "aud": AUDIENCE,
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": kid})


def test_valid_rs256_and_required_claims():
    private, public = key_pair("test-v1")
    tokens = TokenService(private, {"test-v1": public}, "test-v1")
    user, session = uuid4(), uuid4()
    value = tokens.issue_access(user, session)
    assert jwt.get_unverified_header(value)["kid"] == "test-v1"
    assert tokens.decode_access(value).user_id == user
    assert tokens.decode_access(value).session_id == session


@pytest.mark.parametrize("overrides", [
    {"iss": "https://wrong.example"},
    {"aud": "wrong-audience"},
    {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
    {"typ": "refresh"},
])
def test_wrong_issuer_audience_expiry_or_type_rejected(overrides):
    private, public = key_pair("test-v1")
    tokens = TokenService(private, {"test-v1": public}, "test-v1")
    with pytest.raises(AuthenticationError):
        tokens.decode_access(signed(private, "test-v1", **overrides))


def test_unknown_kid_wrong_signature_and_algorithm_confusion_rejected():
    private, public = key_pair("test-v1")
    other_private, _ = key_pair("test-v2")
    tokens = TokenService(private, {"test-v1": public}, "test-v1")
    for value in (
        signed(private, "unknown"),
        signed(other_private, "test-v1"),
        jwt.encode({"sub": str(uuid4())}, "attacker-controlled-key-long-enough-for-test", algorithm="HS256", headers={"kid": "test-v1"}),
        jwt.encode({"sub": str(uuid4())}, key="", algorithm="none", headers={"kid": "test-v1"}),
    ):
        with pytest.raises(AuthenticationError):
            tokens.decode_access(value)


def test_public_key_overlap_supports_rotation_without_accepting_removed_key():
    old_private, old_public = key_pair("test-v1")
    new_private, new_public = key_pair("test-v2")
    old_token = signed(old_private, "test-v1")
    overlap = TokenService(new_private, {"test-v1": old_public, "test-v2": new_public}, "test-v2")
    assert overlap.decode_access(old_token).user_id
    assert jwt.get_unverified_header(overlap.issue_access(uuid4(), uuid4()))["kid"] == "test-v2"
    retired = TokenService(new_private, {"test-v2": new_public}, "test-v2")
    with pytest.raises(AuthenticationError):
        retired.decode_access(old_token)


def test_invalid_key_config_fails_closed(monkeypatch):
    old_private, old_public = key_pair("test-v1")
    _, other_public = key_pair("test-v2")
    with pytest.raises(ValueError):
        TokenService(old_private, {"test-v1": other_public}, "test-v1")
    for name in ("JWT_PRIVATE_KEY_PEM", "JWT_PUBLIC_KEYS_JSON", "JWT_ACTIVE_KID"):
        monkeypatch.delenv(name, raising=False)
    assert TokenService.from_environment() is None
    monkeypatch.setenv("JWT_PRIVATE_KEY_PEM", old_private)
    monkeypatch.setenv("JWT_PUBLIC_KEYS_JSON", '{"test-v1": "not a key"}')
    monkeypatch.setenv("JWT_ACTIVE_KID", "test-v1")
    assert TokenService.from_environment() is None


def test_environment_keyring_loads_without_files(monkeypatch):
    private, public = key_pair("test-v1")
    monkeypatch.setenv("JWT_PRIVATE_KEY_PEM", private)
    monkeypatch.setenv("JWT_PUBLIC_KEYS_JSON", json.dumps({"test-v1": public}))
    monkeypatch.setenv("JWT_ACTIVE_KID", "test-v1")
    loaded = TokenService.from_environment()
    assert loaded is not None
    assert loaded.decode_access(loaded.issue_access(uuid4(), uuid4())).user_id
