import json

from cryptography.fernet import Fernet


class UnknownKeyVersionError(Exception):
    pass


class TokenEncryptor:
    """Fernet-based credential encryptor with multi-key support for rotation.

    Two ways to construct:
    - Single key (legacy): ``TokenEncryptor(key_b64, key_id="v1")``.
    - Keyring (rotation):  ``TokenEncryptor(keyring={"v1": k1, "v2": k2}, active_key_id="v2")``.
      New writes use the active key; reads pick the cipher by stored ``key_id``.
    """

    def __init__(
        self,
        key_b64: str | None = None,
        key_id: str = "v1",
        *,
        keyring: dict[str, str] | None = None,
        active_key_id: str | None = None,
    ):
        if keyring is None:
            if key_b64 is None:
                raise ValueError("TokenEncryptor requires either key_b64 or keyring")
            keyring = {key_id: key_b64}
            active_key_id = key_id
        elif active_key_id is None:
            raise ValueError("active_key_id is required when constructing from a keyring")
        if active_key_id not in keyring:
            raise ValueError(f"active_key_id {active_key_id!r} not present in keyring")

        self._ciphers: dict[str, Fernet] = {
            kid: Fernet(k.encode()) for kid, k in keyring.items()
        }
        self._active_key_id = active_key_id

    @property
    def key_id(self) -> str:
        return self._active_key_id

    def encrypt(self, payload: dict) -> tuple[bytes, str]:
        plaintext = json.dumps(payload, separators=(",", ":")).encode()
        cipher = self._ciphers[self._active_key_id]
        return cipher.encrypt(plaintext), self._active_key_id

    def decrypt(self, ciphertext: bytes, key_id: str) -> dict:
        cipher = self._ciphers.get(key_id)
        if cipher is None:
            raise UnknownKeyVersionError(key_id)
        return json.loads(cipher.decrypt(ciphertext))
