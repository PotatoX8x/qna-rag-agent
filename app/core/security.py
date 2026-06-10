from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

_PWD_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(days=7)


def hash_password(password: str) -> str:
    return _PWD_CTX.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _PWD_CTX.verify(plain, hashed)


def create_access_token(user_id: str, email: str, secret: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + _TOKEN_TTL,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
