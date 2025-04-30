# todo/routers/auth.py
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from ..database import SessionLocal
from ..models import Users

# ──────────────────────────────────────────────────────────────────────────────
# Router setup
# ──────────────────────────────────────────────────────────────────────────────
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Template directory (always resolves to todo/templates)
# ──────────────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

# ──────────────────────────────────────────────────────────────────────────────
# Security constants and utilities
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY = "197b2c37c391bed93fe80344fe73b806947a65e36206e05a1a23c2fa12702fe3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# ──────────────────────────────────────────────────────────────────────────────
# Database dependency
# ──────────────────────────────────────────────────────────────────────────────


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDependency = Annotated[Session, Depends(get_db)]


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────────────────────────────────────
class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str
    phone_number: str


class Token(BaseModel):
    access_token: str
    token_type: str


# ──────────────────────────────────────────────────────────────────────────────
# Page routes
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/login-page")
def render_login_page(request: Request):
    """Render the login page template."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request},
    )


@router.get("/register-page")
def render_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


# ──────────────────────────────────────────────────────────────────────────────
# Authentication helpers
# ──────────────────────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str, db: Session):
    """Verify username & password, return user model or False."""
    user = db.query(Users).filter(Users.username == username).first()
    if not user or not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta):
    """Create a new JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
):
    """Decode JWT, validate, and return current user info."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return {"username": username, "id": user_id, "user_role": user_role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


# ──────────────────────────────────────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    db: DbDependency,
    req: CreateUserRequest,
):
    """Create a new user."""
    user = Users(
        username=req.username,
        email=req.email,
        first_name=req.first_name,
        last_name=req.last_name,
        role=req.role,
        hashed_password=bcrypt_context.hash(req.password),
        is_active=True,
        phone_number=req.phone_number,
    )
    db.add(user)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency,
):
    """Authenticate user and return token."""
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token: Annotated[str, Depends(oauth2_scheme)],
):
    """Refresh an existing valid token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("id")
        user_role = payload.get("role")
        if username is None or user_id is None:
            raise JWTError
        new_token = create_access_token(
            data={"sub": username, "id": user_id, "role": user_role},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": new_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
        )
