from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

_PWD_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(days=7)


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Parameters
    ----------
    password : str
        Plaintext password supplied by the user.

    Returns
    -------
    str
        bcrypt hash suitable for storage.
    """
    return _PWD_CTX.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash.

    Parameters
    ----------
    plain : str
        Plaintext password to verify.
    hashed : str
        Previously hashed value from the database.

    Returns
    -------
    bool
        ``True`` if the password matches, ``False`` otherwise.
    """
    return _PWD_CTX.verify(plain, hashed)


def create_access_token(user_id: str, email: str, secret: str) -> str:
    """Create a signed JWT for the given user.

    Parameters
    ----------
    user_id : str
        UUID of the user (stored as ``sub`` claim).
    email : str
        User email (informational claim, not used for auth).
    secret : str
        HMAC secret from ``JWT_SECRET`` env var.

    Returns
    -------
    str
        Signed JWT string with a 7-day expiry.
    """
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + _TOKEN_TTL,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    """Decode and verify a JWT, returning its payload.

    Parameters
    ----------
    token : str
        Raw JWT string from the ``Authorization`` header.
    secret : str
        HMAC secret used to verify the signature.

    Returns
    -------
    dict
        Decoded claims including ``sub`` and ``email``.

    Raises
    ------
    ValueError
        When the token is invalid, expired, or the signature does not match.
    """
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
