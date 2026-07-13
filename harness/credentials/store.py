import base64
import os
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialError(Exception):
    pass


class CredentialStore:
    """Stores API key encrypted at rest using Fernet."""

    SALT_FILE = ".salt"

    def __init__(self, store_path: Path = Path(".agent/credentials.enc")):
        self._store_path = Path(store_path)
        self._salt_path = self._store_path.parent / self.SALT_FILE

    def store(self, api_key: str, master_password: str):
        salt = os.urandom(16)
        fernet_key = self._derive_key(master_password, salt)
        fernet = Fernet(fernet_key)
        encrypted = fernet.encrypt(api_key.encode())
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_bytes(encrypted)
        self._salt_path.write_bytes(salt)

    def load(self, master_password: str) -> str:
        if not self._store_path.exists():
            raise CredentialError("No credentials stored")
        salt = self._salt_path.read_bytes()
        fernet_key = self._derive_key(master_password, salt)
        fernet = Fernet(fernet_key)
        try:
            decrypted = fernet.decrypt(self._store_path.read_bytes())
        except InvalidToken:
            raise CredentialError("Wrong master password or corrupted credential file")
        return decrypted.decode()

    def status(self) -> dict:
        if not self._store_path.exists():
            return {"configured": False}
        return {
            "configured": True,
            "created_at": datetime.fromtimestamp(
                self._store_path.stat().st_mtime
            ).isoformat(),
        }

    def clear(self):
        if self._store_path.exists():
            self._store_path.unlink()
        if self._salt_path.exists():
            self._salt_path.unlink()

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)
