import json

from cryptography.fernet import Fernet


class UnknownKeyVersionError(Exception):
    pass


class TokenEncryptor:
    def __init__(self, key_b64: str, key_id: str = "v1"):
        self.cipher = Fernet(key_b64.encode())
        self.key_id = key_id

    def encrypt(self, payload: dict) -> tuple[bytes, str]:
        plaintext = json.dumps(payload, separators=(",", ":")).encode()
        return self.cipher.encrypt(plaintext), self.key_id

    def decrypt(self, ciphertext: bytes, key_id: str) -> dict:
        if key_id != self.key_id:
            raise UnknownKeyVersionError(key_id)
        return json.loads(self.cipher.decrypt(ciphertext))

