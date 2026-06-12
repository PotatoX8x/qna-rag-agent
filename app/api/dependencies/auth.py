from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db
from app.container import ServiceContainer
from app.core.security import decode_access_token
from app.db.orm.user import User

_bearer = HTTPBearer()


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate the request and return the active ``User`` row.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        Bearer token extracted from the ``Authorization`` header by FastAPI.
    db : AsyncSession
        Database session injected by ``get_db``.

    Returns
    -------
    User
        The authenticated, active user.

    Raises
    ------
    HTTPException
        401 when the token is invalid, expired, or the user no longer exists.
    """
    secret = ServiceContainer.get_instance().config["auth"]["jwt_secret"]
    try:
        payload = decode_access_token(credentials.credentials, secret)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user
