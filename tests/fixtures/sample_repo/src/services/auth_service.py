"""Authentication service used by the login controller."""

from src.utils.crypto import hash_password, verify_password

USERS = {}


def register(username: str, password: str) -> None:
    USERS[username] = hash_password(password)


def authenticate(username: str, password: str) -> bool:
    digest = USERS.get(username)
    if not digest:
        return False
    return verify_password(password, digest)
