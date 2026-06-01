import re

import bcrypt

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def validate_password_strength(password: str) -> None:
    """Raise ValueError if password doesn't meet strength requirements."""
    if not _PASSWORD_RE.match(password):
        raise ValueError(
            "Password must be at least 8 characters and contain uppercase, "
            "lowercase, a digit, and a special character."
        )
