from datetime import datetime, timedelta, timezone
import os, jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlmodel import Session, select
from .database import get_session
from .models import User

SECRET_KEY = os.getenv("SECRET_KEY", "finance-tracker-local-secret")
ALGORITHM = "HS256"
TOKEN_MINUTES = 240
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def authenticate(email: str, password: str, session: Session) -> User | None:
    user = session.exec(select(User).where(User.email == email.lower().strip())).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

def create_token(user: User) -> str:
    return jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)},
        SECRET_KEY, algorithm=ALGORITHM
    )

def decode_user(token: str, session: Session) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return session.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None

def current_web_user(request: Request, session: Session) -> User | None:
    token = request.cookies.get("session_token")
    return decode_user(token, session) if token else None

def current_api_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token requerido")
    user = decode_user(credentials.credentials, session)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o vencido")
    return user
