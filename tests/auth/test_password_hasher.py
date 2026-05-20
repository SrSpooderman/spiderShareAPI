import pytest

from app.modules.auth.application.password_hasher import PasswordHasher


@pytest.mark.unit
def test_password_hasher_verifies_original_password() -> None:
    password_hasher = PasswordHasher()

    password_hash = password_hasher.hash_password("secret")

    assert password_hasher.verify_password("secret", password_hash) is True


@pytest.mark.unit
def test_password_hasher_rejects_wrong_password() -> None:
    password_hasher = PasswordHasher()

    password_hash = password_hasher.hash_password("secret")

    assert password_hasher.verify_password("wrong", password_hash) is False


@pytest.mark.unit
def test_password_hasher_uses_salt() -> None:
    password_hasher = PasswordHasher()

    first_hash = password_hasher.hash_password("secret")
    second_hash = password_hasher.hash_password("secret")

    assert first_hash != second_hash
