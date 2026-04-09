"""
JWT authentication: register, login, /me, password change.

Passwords hashed with bcrypt via passlib.
Tokens are HS256 JWTs signed with JWT_SECRET, valid for JWT_EXPIRE_HOURS.

Role model:
  is_admin=1  — can trigger scrapes, run alignment, manage all profiles
  is_admin=0  — can create projects, generate drafts, manage own profiles/capabilities
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS, ALLOW_REGISTRATION
from backend.database import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_user_by_email(email: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def _get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def _create_user(email: str, hashed_password: str, is_admin: bool = False) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, hashed_password, is_admin) VALUES (?, ?, ?)",
            (email.lower(), hashed_password, 1 if is_admin else 0),
        )
        conn.commit()
        return cur.lastrowid


def _update_password(user_id: int, hashed_password: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET hashed_password = ? WHERE id = ?",
            (hashed_password, user_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _make_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict | None:
    """
    Dependency: returns the user dict if a valid Bearer token is present,
    otherwise returns None (routes decide whether to enforce auth).
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        return None
    return _get_user_by_id(user_id)


def require_user(user: dict | None = Depends(get_current_user)) -> dict:
    """Dependency: raises 401 if no valid token."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    """Dependency: raises 403 if the authenticated user is not an admin."""
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def make_require_own_profile_or_admin(profile_id_param: str = "profile_id"):
    """
    Factory that returns a dependency enforcing:
      - Admin users may pass any profile_id (or None for a full run)
      - Non-admin users must pass a profile_id that they own
    Usage:
        Depends(make_require_own_profile_or_admin())
    Returns the resolved user dict.
    """
    from fastapi import Query as _Query
    from backend.db.crud import get_all_profiles as _get_profiles

    def _dep(profile_id: int | None = None, user: dict = Depends(require_user)) -> dict:
        if user.get("is_admin"):
            return user
        if profile_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non-admin users must specify a profile_id.",
            )
        owned = [p["id"] for p in _get_profiles(user_id=user["id"])]
        if profile_id not in owned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own that profile.",
            )
        return user

    return _dep


# Singleton dependency for /align/run
require_own_profile_or_admin = make_require_own_profile_or_admin()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False


@router.post("/register", status_code=201, response_model=TokenResponse)
def register(body: RegisterRequest):
    if not ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently closed. Contact your administrator.",
        )
    email = body.email.strip().lower()
    if not email or not body.password:
        raise HTTPException(status_code=422, detail="email and password required")
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    if _get_user_by_email(email):
        raise HTTPException(status_code=409, detail="email already registered")

    hashed = _pwd.hash(body.password)
    user_id = _create_user(email, hashed)

    # Claim any un-owned, non-shared profiles (runs once for the first registered user)
    with get_connection() as conn:
        conn.execute(
            "UPDATE profiles SET user_id = ? WHERE user_id IS NULL AND shared = 0",
            (user_id,),
        )
        conn.commit()

    user = _get_user_by_id(user_id)
    return {"access_token": _make_token(user_id), "is_admin": bool(user["is_admin"])}


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = _get_user_by_email(form.username)
    if not user or not _pwd.verify(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": _make_token(user["id"]), "is_admin": bool(user["is_admin"])}


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "is_admin": bool(user["is_admin"]),
        "created_at": user["created_at"],
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.patch("/password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(require_user)):
    if not _pwd.verify(body.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=422, detail="New password must differ from current password")
    _update_password(user["id"], _pwd.hash(body.new_password))
    return {"message": "Password updated successfully"}
