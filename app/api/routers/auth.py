from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db
from app.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.container import ServiceContainer
from app.core.security import create_access_token, hash_password, verify_password
from app.db.orm.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Register a new user and return an access token.

    Parameters
    ----------
    body : RegisterRequest
        Email and plaintext password.
    db : AsyncSession
        Injected database session.

    Returns
    -------
    TokenResponse
        JWT access token for the newly created user.

    Raises
    ------
    HTTPException
        409 when the email is already registered.
    """
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    secret = ServiceContainer.get_instance().config["auth"]["jwt_secret"]
    return TokenResponse(access_token=create_access_token(str(user.id), user.email, secret))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate an existing user and return an access token.

    Parameters
    ----------
    body : LoginRequest
        Email and plaintext password.
    db : AsyncSession
        Injected database session.

    Returns
    -------
    TokenResponse
        JWT access token.

    Raises
    ------
    HTTPException
        401 when credentials are invalid, 403 when the account is disabled.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    secret = ServiceContainer.get_instance().config["auth"]["jwt_secret"]
    return TokenResponse(access_token=create_access_token(str(user.id), user.email, secret))
