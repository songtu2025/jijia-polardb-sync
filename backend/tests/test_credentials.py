import pytest
from cryptography.fernet import Fernet

from backend.app.core.credentials import CredentialCipher
from backend.app.core.errors import ApiError


def test_credential_cipher_round_trip_and_missing_key() -> None:
    cipher = CredentialCipher(Fernet.generate_key().decode("ascii"))
    encrypted = cipher.encrypt("secret-app-key")

    assert encrypted != "secret-app-key"
    assert cipher.decrypt(encrypted) == "secret-app-key"

    with pytest.raises(ApiError) as error:
        CredentialCipher("")
    assert error.value.code == "CREDENTIAL_KEY_MISSING"
