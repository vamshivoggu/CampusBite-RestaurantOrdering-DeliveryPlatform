"""Password hashing (bcrypt), JWT handling and role-based access dependencies."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Restaurant, User, UserRole

# tokenUrl powers the "Authorize" button in Swagger UI (/docs)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    auto_error=False,
    description=(
        "Log in with your **email address** in the `username` field (e.g. `customer@campusbite.dev` / "
        "`Password@123`). Leave `client_id` and `client_secret` empty."
    ),
)


def _pw_bytes(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes; truncate explicitly so long inputs never error.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(token: Annotated[str | None, Depends(oauth2_scheme)], db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again",
                            headers={"WWW-Authenticate": "Bearer"})
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_roles(*roles: UserRole):
    """Dependency factory: allow only users whose role is in `roles`."""

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user

    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]
CustomerUser = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]
OwnerUser = Annotated[User, Depends(require_roles(UserRole.RESTAURANT_OWNER))]
DeliveryUser = Annotated[User, Depends(require_roles(UserRole.DELIVERY_PARTNER))]


def get_owner_restaurant(owner: OwnerUser, db: Session = Depends(get_db)) -> Restaurant:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.owner_id == owner.id).order_by(Restaurant.id))
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No restaurant is linked to this owner account")
    return restaurant


OwnerRestaurant = Annotated[Restaurant, Depends(get_owner_restaurant)]
