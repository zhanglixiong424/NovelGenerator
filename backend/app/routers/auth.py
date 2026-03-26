from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, hash_password, verify_password, create_access_token
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, SetupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/setup", response_model=TokenResponse)
async def setup_admin(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    """First-time setup: create admin account. Only works when no users exist."""
    result = await db.execute(select(func.count(User.id)))
    count = result.scalar()
    if count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin already exists")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(_: User = Depends(get_current_user)):
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )
