import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import create_user, get_user_by_username
from app.models import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()

SECRET_KEY = os.getenv("JWT_SECRET", "batch-image-studio-secret-key-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        username: str = payload["username"]
        return {"id": user_id, "username": username}
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")


@router.post("/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    if len(req.username.strip()) < 2:
        raise HTTPException(status_code=400, detail="사용자명은 2자 이상이어야 합니다")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="비밀번호는 4자 이상이어야 합니다")

    if get_user_by_username(req.username.strip()):
        raise HTTPException(status_code=409, detail="이미 사용 중인 사용자명입니다")

    user = create_user(req.username.strip(), hash_password(req.password))
    token = create_access_token(user["id"], user["username"])
    return TokenResponse(access_token=token, user_id=user["id"], username=user["username"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = get_user_by_username(req.username.strip())
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="사용자명 또는 비밀번호가 올바르지 않습니다")

    token = create_access_token(user["id"], user["username"])
    return TokenResponse(access_token=token, user_id=user["id"], username=user["username"])


@router.get("/auth/me")
async def me(current_user=Depends(get_current_user)):
    return current_user
