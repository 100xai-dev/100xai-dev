from cryptography.fernet import Fernet
import pytest

from app.services.encryption import TokenEncryptor, UnknownKeyVersionError


def test_token_encryptor_round_trips_credentials() -> None:
    encryptor = TokenEncryptor(Fernet.generate_key().decode(), key_id="v1")

    encrypted, key_id = encryptor.encrypt(
        {"username": "publisher", "application_password": "secret"}
    )

    assert key_id == "v1"
    assert encrypted != b'{"username":"publisher","application_password":"secret"}'
    assert encryptor.decrypt(encrypted, key_id) == {
        "username": "publisher",
        "application_password": "secret",
    }


def test_token_encryptor_rejects_unknown_key_version() -> None:
    encryptor = TokenEncryptor(Fernet.generate_key().decode(), key_id="v1")
    encrypted, _ = encryptor.encrypt({"secret": "value"})

    with pytest.raises(UnknownKeyVersionError):
        encryptor.decrypt(encrypted, "v0")

