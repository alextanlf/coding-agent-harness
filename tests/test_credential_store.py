import pytest
from pathlib import Path
from harness.credentials.store import CredentialStore, CredentialError


@pytest.fixture
def store(tmp_path):
    return CredentialStore(store_path=tmp_path / "credentials.enc")


def test_store_and_load(store):
    key = "sk-test123456789"
    store.store(key, master_password="mypassword")
    loaded = store.load("mypassword")
    assert loaded == key


def test_wrong_password_raises(store):
    store.store("sk-test", master_password="correct")
    with pytest.raises(CredentialError):
        store.load("wrong")


def test_status_when_not_configured(store):
    status = store.status()
    assert status["configured"] is False


def test_status_when_configured(store):
    store.store("sk-test", master_password="pass")
    status = store.status()
    assert status["configured"] is True
    assert "sk-test" not in str(status)


def test_status_never_returns_key(store):
    store.store("sk-supersecretkey", master_password="pass")
    status = store.status()
    status_str = str(status)
    assert "sk-supersecretkey" not in status_str


def test_clear(store):
    store.store("sk-test", master_password="pass")
    assert store.status()["configured"] is True
    store.clear()
    assert store.status()["configured"] is False


def test_load_when_not_configured_raises(store):
    with pytest.raises(CredentialError):
        store.load("any")


def test_encrypted_file_not_plaintext(store):
    key = "sk-mysecretapikey123"
    store.store(key, master_password="pass")
    raw = store._store_path.read_bytes()
    assert key.encode() not in raw
