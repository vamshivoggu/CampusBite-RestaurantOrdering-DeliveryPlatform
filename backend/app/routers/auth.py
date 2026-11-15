from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Restaurant, User, UserRole
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import CurrentUser, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled")
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create an account. Restaurant owners also get their restaurant created."""
    email = payload.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        name=payload.name, email=email, password_hash=hash_password(payload.password),
        role=payload.role, phone=payload.phone, address=payload.address,
    )
    db.add(user)
    db.flush()
    if payload.role == UserRole.RESTAURANT_OWNER:
        db.add(Restaurant(
            owner_id=user.id, name=payload.restaurant_name.strip(), cuisine=payload.restaurant_cuisine,
            address=payload.restaurant_address, phone=payload.phone, is_open=True,
        ))
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Log in with email + password (JSON). Returns a JWT bearer token."""
    return _token_response(_authenticate(db, payload.email, payload.password))


@router.post("/token", include_in_schema=True, summary="OAuth2 password flow (used by Swagger 'Authorize')")
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = _authenticate(db, form.username, form.password)
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
