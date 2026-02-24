import os

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set minimal env vars so app.config.Settings can initialize."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("ENCRYPTION_KEY", key)

    # Clear the lru_cache so fresh settings are loaded
    from app.config import get_settings

    get_settings.cache_clear()


def test_encrypt_decrypt_roundtrip():
    from app.utils.crypto import decrypt, encrypt

    original = "my-secret-refresh-token"
    encrypted = encrypt(original)
    assert encrypted != original
    assert decrypt(encrypted) == original


def test_encrypt_produces_different_ciphertexts():
    from app.utils.crypto import encrypt

    a = encrypt("same-value")
    b = encrypt("same-value")
    # Fernet uses a random IV, so ciphertexts should differ
    assert a != b


def test_decrypt_invalid_raises():
    from cryptography.fernet import InvalidToken

    from app.utils.crypto import decrypt

    with pytest.raises(InvalidToken):
        decrypt("not-valid-ciphertext")
