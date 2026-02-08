import pytest
from app.core.encryption import encrypt_value, decrypt_value
from app.core.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_encrypt_decrypt_roundtrip():
    plaintext = "my-secret-password"
    encrypted = encrypt_value(plaintext)
    assert encrypted != plaintext
    assert decrypt_value(encrypted) == plaintext


def test_password_hash_and_verify():
    password = "testpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_create_and_decode():
    token = create_access_token(user_id=42)
    payload = decode_access_token(token)
    assert payload["sub"] == 42
