"""
auth.py — Autenticação de usuários (email + senha) + ML OAuth

Rotas:
  POST /auth/register     — cria conta
  POST /auth/login        — retorna JWT
  GET  /auth/me           — dados do usuário logado
  GET  /auth/ml/callback  — OAuth ML
  POST /auth/ml/refresh   — renova token ML
  GET  /auth/ml/status    — status token ML
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import uuid
from datetime import timedelta

from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.models.models import User
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from datetime import datetime, timezone

router = APIRouter()
security = HTTPBearer(auto_error=False)
import bcrypt as _bcrypt

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30
REDIRECT_URI = "https://bestpricetoday.vercel.app/auth/callback"
ML_SCOPES = "read_catalog catalog_suggestions item_competition"


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8")[:72], _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode())
    except Exception:
        return False


def create_jwt(user_id: str, is_admin: bool = False) -> str:
    payload = {
        "sub": user_id,
        "admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token não fornecido.")
    payload = decode_jwt(credentials.credentials)
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo.")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador.")
    return user


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str | None
    email: str | None
    is_admin: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Rotas de usuário ──────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=TokenOut, status_code=201)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    try:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

        user = User(
            id=uuid.uuid4(),
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        await db.flush()

        token = create_jwt(str(user.id), is_admin=False)
        return TokenOut(
            access_token=token,
            user=UserOut(id=str(user.id), name=user.name, email=user.email, is_admin=False),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {type(e).__name__}: {str(e)[:200]}")


@router.post("/auth/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada.")

    token = create_jwt(str(user.id), is_admin=user.is_admin)
    return TokenOut(
        access_token=token,
        user=UserOut(id=str(user.id), name=user.name, email=user.email, is_admin=user.is_admin),
    )


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=str(user.id), name=user.name, email=user.email, is_admin=user.is_admin)


# ── ML OAuth (mantido) ────────────────────────────────────────────────────────

async def _do_token_refresh(refresh_token: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.mercadolibre.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.MERCADOLIVRE_APP_ID,
                    "client_secret": settings.MERCADOLIVRE_SECRET,
                    "refresh_token": refresh_token,
                },
            )
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        logger.error(f"ML token refresh error: {e}")
        return None


async def get_valid_ml_token() -> str | None:
    token = settings.MERCADOLIVRE_ACCESS_TOKEN
    if token:
        return token
    refresh = settings.MERCADOLIVRE_REFRESH_TOKEN
    if not refresh:
        return None
    data = await _do_token_refresh(refresh)
    if data:
        logger.info("ML token refreshed successfully [token value redacted]")
        return data.get("access_token")
    return None


@router.get("/auth/ml/authorize")
async def ml_authorize():
    """Gera a URL de autorização ML. Acesse no browser."""
    from urllib.parse import urlencode
    params = urlencode({
        "response_type": "code",
        "client_id": settings.MERCADOLIVRE_APP_ID,
        "redirect_uri": REDIRECT_URI,
    })
    url = f"https://auth.mercadolivre.com.br/authorization?{params}"
    return HTMLResponse(f"""
    <html><head><style>
      body{{font-family:system-ui;background:#07070f;color:#e2e8f0;padding:2rem}}
      a{{color:#7c6aff;font-size:1.1rem}}
      .box{{background:#111;border:1px solid #7c6aff;border-radius:12px;padding:1.5rem;max-width:600px}}
      code{{background:#1e293b;padding:4px 8px;border-radius:4px;font-size:0.85rem;word-break:break-all}}
    </style></head><body>
    <div class="box">
      <h2>🔐 Autorizar Mercado Livre</h2>
      <p>Redirect URI: <code>{REDIRECT_URI}</code></p>
      <p><a href="{url}" target="_blank">👉 Clique aqui para autorizar</a></p>
      <p style="font-size:0.8rem;color:#64748b">Após autorizar, você será redirecionado de volta e o token será salvo automaticamente.</p>
    </div></body></html>
    """)


@router.get("/auth/ml/callback")
async def ml_oauth_callback(code: str = None, error: str = None, db: AsyncSession = Depends(get_db)):
    if error or not code:
        return HTMLResponse("<h2>❌ Erro de autenticação</h2>", status_code=400)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.MERCADOLIVRE_APP_ID,
                "client_secret": settings.MERCADOLIVRE_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
        )

    if resp.status_code != 200:
        error_body = resp.text[:500]
        logger.error(f"ML OAuth token exchange failed: HTTP {resp.status_code} — {error_body}")
        return HTMLResponse(f"<h2>❌ Erro ao obter token ML</h2><pre>{resp.status_code}: {error_body}</pre>", status_code=400)

    data = resp.json()
    logger.info(f"ML OAuth success — user_id={data.get('user_id')} [tokens redacted]")

    try:
        from app.services.ml_token_service import save_from_oauth
        await save_from_oauth(db, data)
    except Exception as e:
        logger.error(f"Failed to save ML tokens: {type(e).__name__}")

    return HTMLResponse("""
    <html><head><style>
      body{font-family:system-ui;background:#07070f;color:#0f0;padding:2rem}
      .box{background:#111;border:1px solid #00e5a0;border-radius:12px;padding:1.5rem;max-width:500px}
    </style></head><body>
    <div class="box">
      <h2>✅ Autenticação ML concluída</h2>
      <p>Tokens registrados com sucesso.</p>
    </div></body></html>
    """)


@router.post("/auth/ml/refresh")
async def ml_refresh_token(db: AsyncSession = Depends(get_db)):
    from app.services.ml_token_service import get_token, get_token_status
    token = await get_token(db)
    status = await get_token_status(db)
    return {"ok": bool(token), "status": status}


@router.get("/auth/ml/status")
async def ml_token_status(db: AsyncSession = Depends(get_db)):
    from app.services.ml_token_service import get_token_status
    return await get_token_status(db)
