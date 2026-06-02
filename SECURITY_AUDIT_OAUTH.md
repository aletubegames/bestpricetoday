# 🔐 Auditoria de Segurança — Autenticação de Redes Sociais

**Projeto:** BestPriceToday  
**Data:** 2026-06-01  
**Escopo:** Autenticação OAuth para TikTok, YouTube, Instagram, Facebook  
**Realizado por:** Auditoria de Segurança Automatizada

---

## 📊 Resumo Executivo

| Severidade | Quantidade | Status |
|-----------|-----------|--------|
| 🔴 CRÍTICO | 4 | ⚠️ Requer ação imediata |
| 🟠 ALTO | 4 | ⚠️ Requer ação em curto prazo |
| 🟡 MÉDIO | 3 | ℹ️ Deve ser resolvido |
| 🟢 BAIXO | 0 | ✅ Sem achados |

**Risco Geral:** 🔴 CRÍTICO — Vulnerabilidades que expõem dados sensíveis e credenciais

---

## 🔴 Achados CRÍTICOS

### AUTH-001: Tokens OAuth armazenados em PLAINTEXT

**Severidade:** 🔴 CRÍTICO  
**Categoria:** Armazenamento de Tokens  
**Status:** ❌ Não corrigido

#### 📍 Localização
- `/backend/app/models/models.py` (linhas 287-336)
- Afeta: YouTubeAccount, InstagramAccount, FacebookAccount, TikTokAccount

#### 🐛 Problema
```python
class YouTubeAccount(Base):
    __tablename__ = "youtube_accounts"
    
    access_token     = Column(String, nullable=False)      # ← PLAINTEXT!
    refresh_token    = Column(String, nullable=True)       # ← PLAINTEXT!
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
```

Access tokens, refresh tokens são armazenados sem nenhuma criptografia no PostgreSQL.

#### ⚠️ Impacto
- **Gravidade:** MÁXIMA — qualquer acesso ao banco de dados expõe TODAS as contas conectadas
- **Janela de ataque:** Indefinida — tokens não expiram por falta de rotação
- **Compliance:** Violação GDPR, LGPD (dados pessoais sem proteção)

#### ✅ Remediação

**Passo 1:** Implementar criptografia com `cryptography.fernet`

```python
from cryptography.fernet import Fernet

class TokenCrypto:
    """Serviço de criptografia de tokens OAuth."""
    
    def __init__(self, key: str = settings.TOKEN_ENCRYPTION_KEY):
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, token: str) -> str:
        """Criptografa token com AES-256."""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """Descriptografa token."""
        return self.cipher.decrypt(encrypted.encode()).decode()
```

**Passo 2:** Criar migration para re-criptografar tokens

```python
# backend/alembic/versions/encrypt_oauth_tokens.py
from alembic import op
import sqlalchemy as sa
from cryptography.fernet import Fernet

def upgrade():
    """Criptografa todos os tokens existentes."""
    conn = op.get_bind()
    
    # YouTube
    result = conn.execute(sa.text("SELECT id, access_token, refresh_token FROM youtube_accounts"))
    for row in result:
        encrypted_access = TokenCrypto().encrypt(row[1])
        encrypted_refresh = TokenCrypto().encrypt(row[2]) if row[2] else None
        conn.execute(
            sa.text(
                "UPDATE youtube_accounts SET access_token = :at, refresh_token = :rt WHERE id = :id"
            ),
            {"at": encrypted_access, "rt": encrypted_refresh, "id": row[0]}
        )
    # Repetir para Instagram, Facebook, TikTok...
```

**Passo 3:** Usar modelo similar ao `MLToken` (que já implementa criptografia)

```python
# Verificar como MLToken implementa segurança
# backend/app/services/ml_token_service.py
```

**Passo 4:** Adicionar auditoria

```python
class YouTubeAccount(Base):
    __tablename__ = "youtube_accounts"
    
    # ... outras colunas ...
    access_token      = Column(String, nullable=False)
    is_encrypted      = Column(Boolean, default=False, index=True)  # Flag para auditoria
    encryption_version = Column(Integer, default=1)  # Para rotação de chave futura
```

**Timeline:** ⏱️ **MÁXIMA PRIORIDADE** — Implementar em 48 horas

---

### AUTH-009: Admin endpoints protegidos apenas por X-Admin-Key header

**Severidade:** 🔴 CRÍTICO  
**Categoria:** Autorização  
**Status:** ❌ Não corrigido

#### 📍 Localização
- Todos os endpoints de `/aletube/` dependem de `Depends(require_admin)`
- Implementação: `/backend/app/api/v1/endpoints/admin.py`

#### 🐛 Problema
```python
@router.post("/aletube/upload")
async def upload_video(
    file: UploadFile = File(...),
    _: str = Depends(require_admin),  # ← Apenas verifica header!
    db: AsyncSession = Depends(get_db),
):
    pass
```

A autenticação admin é feita apenas verificando o header `X-Admin-Key`:

```python
# require_admin = Depends(...) → verifica X-Admin-Key == ADMIN_MANAGER_KEY
```

#### ⚠️ Impacto
- Header estático = sem rotação, replay attacks
- Sem sessão = sem logout
- Sem 2FA para ações sensíveis (conectar conta do TikTok, publicar vídeo)
- Sem auditoria de ações

#### ✅ Remediação

**Passo 1:** Implementar autenticação por JWT

```python
# backend/app/core/security.py
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import HTTPException, status

class AdminAuthService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
    
    def create_access_token(self, admin_id: str, expires_delta: timedelta = None) -> dict:
        """Cria JWT access token (15 min)."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=15)
        
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {"admin_id": admin_id, "exp": expire, "type": "access"}
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return {"access_token": encoded_jwt, "token_type": "bearer", "expires_in": 900}
    
    def create_refresh_token(self, admin_id: str) -> str:
        """Cria JWT refresh token (7 dias)."""
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        to_encode = {"admin_id": admin_id, "exp": expire, "type": "refresh"}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_access_token(self, token: str) -> str:
        """Verifica e decodifica access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            return payload.get("admin_id")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
```

**Passo 2:** Criar endpoint de login

```python
# backend/app/api/v1/endpoints/admin.py
@router.post("/admin/login")
async def admin_login(
    username: str = Form(...),
    password: str = Form(...),
):
    """Admin login — verifica credenciais e retorna JWT."""
    # Verificar contra variável de ambiente ou banco de dados
    if username != settings.ADMIN_USERNAME or not verify_password(password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_data = admin_auth.create_access_token(username)
    refresh_token = admin_auth.create_refresh_token(username)
    
    # Armazenar refresh token em banco/Redis com TTL
    response = JSONResponse(content=token_data)
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=604800,  # 7 dias
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/admin"
    )
    return response
```

**Passo 3:** Atualizar endpoints para usar JWT

```python
@router.post("/aletube/upload")
async def upload_video(
    file: UploadFile = File(...),
    admin_id: str = Depends(verify_jwt_token),  # ← JWT, não header!
    db: AsyncSession = Depends(get_db),
):
    pass
```

**Passo 4:** Adicionar 2FA para ações sensíveis

```python
@router.get("/aletube/auth/youtube")
async def auth_youtube(
    admin_id: str = Depends(verify_jwt_token),
    totp_code: str = Query(...),  # Código TOTP do authenticator
):
    """OAuth YouTube — requer 2FA."""
    if not verify_totp(admin_id, totp_code):
        raise HTTPException(status_code=403, detail="Invalid 2FA code")
    
    # Continuar com OAuth...
```

**Passo 5:** CORS restritivo

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # ← Vazio: admin não usa CORS, usa sessão
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization"],
    expose_headers=["Content-Length"],
)

# Para endpoints admin, adicionar middleware extra:
# - Verificar Referer = bestpricetoday.vercel.app/admin
# - Verificar Origin = bestpricetoday.vercel.app
# - Rate limit por IP
```

**Timeline:** ⏱️ **MÁXIMA PRIORIDADE** — Implementar em 72 horas

---

### AUTH-010: Secrets potencialmente expostos em repositório

**Severidade:** 🔴 CRÍTICO  
**Categoria:** Secrets Management  
**Status:** ⚠️ Verificar

#### 📍 Localização
- `.env` files
- GitHub Actions secrets
- HuggingFace Space environment variables

#### 🐛 Problema
Se há valores reais de `TIKTOK_CLIENT_SECRET`, `YOUTUBE_CLIENT_SECRET`, etc. em git history, todos os secrets estão comprometidos.

#### ✅ Remediação

**Verificar git history:**

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

# Procurar por padrões de secrets
git log -p --all | grep -iE 'secret|token|key|api' | head -50

# Usar ferramentas especializadas
pip install truffleHog
truffleHog filesystem . --json > secrets_found.json

# Se encontrar: fazer IMMEDIATE REVOCATION
# 1. Todos os TIKTOK_CLIENT_SECRET precisa ser rotacionado no TikTok Developer Portal
# 2. Todos os YOUTUBE_CLIENT_SECRET no Google Cloud Console
# 3. INSTAGRAM_APP_SECRET, ADMIN_MANAGER_KEY na variável de ambiente
```

**Configurar proteção:**

```bash
# Adicionar ao .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo ".env.*.local" >> .gitignore

# Commit com message de correção
git add .gitignore
git commit -m "security: add .env to gitignore"

# Configurar pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Previne commit de secrets
if git diff --cached | grep -iE 'secret|api_key|token' | grep -v '.example'; then
    echo "❌ ERROR: Detected potential secrets in staged files"
    echo "Do not commit credentials. Use .env.example instead."
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

**Timeline:** ⏱️ **IMEDIATO** — Verificar AGORA

---

### AUTH-012: Client secrets são enviados via POST sem proteção adicional

**Severidade:** 🔴 CRÍTICO  
**Categoria:** OAuth Credentials  
**Status:** ❌ Não corrigido

#### 📍 Localização
- `/backend/app/integrations/tiktok.py` (linha 70)
- `/backend/app/integrations/instagram.py` (linha 44)
- `/backend/app/integrations/youtube.py` (linha 42)

#### 🐛 Problema
```python
# tiktok.py linha 66-75
async def get_access_token(self, code: str) -> Dict[str, Any]:
    url = f"{self.base_url}/oauth/token/"
    data = {
        "client_key":    self.client_key,      # ← Em plaintext na memória
        "client_secret": self.client_secret,   # ← EXPOSIÇÃO!
        "code":          code,
        "grant_type":    "authorization_code",
        "redirect_uri":  self.redirect_uri,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)  # ← Via HTTPS, mas é necessário
```

O `client_secret` é enviado em texto plano na requisição POST. Embora HTTPS criptografe em trânsito, qualquer downgrade attack, MITM com certificado falso, ou proxy mal configurado expõe o secret.

#### ⚠️ Impacto
- OAuth token hijacking
- Publicação não autorizada em contas
- Comprometimento de todas as contas conectadas

#### ✅ Remediação

**Passo 1:** Forçar HTTPS globalmente

```python
# backend/app/main.py
from starlette.middleware.https import HTTPSMiddleware

# Produção
if not settings.DEBUG:
    app.add_middleware(HTTPSMiddleware, redirect=True)
```

**Passo 2:** Adicionar HSTS header

```python
# backend/app/main.py
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Força HTTPS por 1 ano
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Previne clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Previne MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # CSP: apenas scripts do nosso domínio
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    
    return response
```

**Passo 3:** Backend-to-backend token exchange (alternativa mais segura)

```python
# Ao invés de enviar client_secret do frontend, usar backend para trocar
# Frontend faz POST /api/v1/oauth/code para backend
# Backend faz POST para provedor com client_secret
# Backend retorna apenas access_token (sem secret)
```

**Passo 4:** Rate limiting na troca de tokens

```python
# backend/app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/oauth/token")
@limiter.limit("5/minute")  # Máximo 5 tentativas por minuto por IP
async def exchange_oauth_code(code: str):
    pass
```

**Timeline:** ⏱️ **MÁXIMA PRIORIDADE** — Implementar em 48 horas

---

## 🟠 Achados ALTO

### AUTH-003: State parameter não é validado após OAuth callback

**Severidade:** 🟠 ALTO  
**Categoria:** CSRF Protection  
**Status:** ❌ Não corrigido

#### 📍 Localização
- `/backend/app/api/v1/endpoints/aletube.py` (linha 272-326)
- Endpoints: `GET /aletube/auth/youtube`, `GET /aletube/callback/youtube`, etc.

#### 🐛 Problema
```python
# Estado é gerado:
@router.get("/auth/youtube")
async def auth_youtube(_: str = Depends(require_admin)):
    state = _sec.token_hex(16)  # ← Gerado
    auth_url = youtube_client.get_auth_url(state)
    return {"auth_url": auth_url, "state": state}

# Mas NÃO é validado no callback:
@router.get("/callback/youtube")
async def callback_youtube(
    code:  str,
    state: str,  # ← Aceita qualquer valor!
    _:     str = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
):
    # Nenhuma verificação de state vs. state_original
    token_data = await youtube_client.get_access_token(code)
```

#### ⚠️ Impacto
- **CSRF Attack:** Atacante pode iniciar OAuth fluxo, ganhar token, depois injetar esse token no seu browser
- **Token hijacking:** Se o estado não é validado, qualquer código é aceito

#### ✅ Remediação

**Passo 1:** Armazenar state em Redis

```python
# backend/app/api/v1/endpoints/aletube.py
import redis.asyncio as redis
from app.core.cache import get_redis

@router.get("/auth/youtube")
async def auth_youtube(
    _: str = Depends(require_admin),
    redis_client: redis.Redis = Depends(get_redis)
):
    import secrets
    state = secrets.token_hex(16)
    
    # Armazenar state em Redis com TTL 10 minutos
    await redis_client.setex(
        f"oauth_state:{state}",
        600,  # 10 minutos
        "admin_youtube"
    )
    
    auth_url = youtube_client.get_auth_url(state)
    return {"auth_url": auth_url}
```

**Passo 2:** Validar state no callback

```python
@router.get("/callback/youtube")
async def callback_youtube(
    code:  str,
    state: str,
    _:     str = Depends(require_admin),
    db:    AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    # ✅ VALIDAR STATE
    stored_state = await redis_client.get(f"oauth_state:{state}")
    if not stored_state:
        raise HTTPException(status_code=403, detail="Invalid or expired state parameter")
    
    # Remover state para evitar replay
    await redis_client.delete(f"oauth_state:{state}")
    
    # Agora processar code com segurança
    token_data = await youtube_client.get_access_token(code)
```

**Passo 3:** Usar PKCE (Authorization Code + Proof Key for Exchange)

```python
# RFC 7636 — mais seguro, especialmente em mobile/SPAs
import base64
import secrets

def generate_pkce_pair():
    """Gera code_verifier e code_challenge para PKCE."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    return code_verifier, code_challenge

@router.get("/auth/youtube")
async def auth_youtube(
    _: str = Depends(require_admin),
    redis_client: redis.Redis = Depends(get_redis)
):
    state = secrets.token_hex(16)
    code_verifier, code_challenge = generate_pkce_pair()
    
    # Armazenar ambos em Redis
    await redis_client.setex(
        f"oauth_session:{state}",
        600,
        json.dumps({"code_verifier": code_verifier})
    )
    
    # Google suporta PKCE nativo
    auth_url = f"{youtube_client.base_url}/auth/authorize?code_challenge={code_challenge}&code_challenge_method=S256&state={state}&..."
    return {"auth_url": auth_url}
```

**Timeline:** ⏱️ Implementar em 1 semana

---

### AUTH-006: Refresh tokens não são renovados proativamente

**Severidade:** 🟠 ALTO  
**Categoria:** Token Management  
**Status:** ❌ Não corrigido

#### 📍 Localização
- `/backend/app/models/models.py` (token_expires_at)
- `/backend/app/api/v1/endpoints/aletube.py` (linha 301)

#### 🐛 Problema
```python
# Token é armazenado com expiration:
expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

# Mas nenhum worker renova proativamente
# Sistema espera token expirar para descobrir que está inválido
```

#### ✅ Remediação

**Passo 1:** Criar worker de renovação

```python
# backend/app/workers/oauth_token_refresh.py
import asyncio
from datetime import datetime, timezone, timedelta

async def refresh_expiring_tokens():
    """Worker que roda a cada hora para renovar tokens próximos de expirar."""
    db = await get_db_session()
    redis_client = await get_redis()
    
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=1)  # Renovar 24h antes
    
    # YouTube
    youtube_accounts = (await db.execute(
        select(YouTubeAccount).where(
            YouTubeAccount.token_expires_at < threshold,
            YouTubeAccount.is_active == True
        )
    )).scalars()
    
    for account in youtube_accounts:
        try:
            new_token_data = await youtube_client.refresh_token(account.refresh_token)
            account.access_token = new_token_data["access_token"]
            account.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=new_token_data.get("expires_in", 3600)
            )
            await db.commit()
            
            # Log sucesso
            logger.info(f"✅ Renovado YouTube token para {account.channel_id}")
            
        except Exception as e:
            logger.error(f"❌ Falha ao renovar YouTube token: {str(e)}")
            # Enviar alerta para admin
            await redis_client.lpush("token_renewal_alerts", json.dumps({
                "platform": "youtube",
                "account_id": str(account.id),
                "error": str(e),
                "timestamp": now.isoformat()
            }))
```

**Passo 2:** Registrar worker no lifespan

```python
# backend/app/main.py
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    token_refresh_task = asyncio.create_task(refresh_tokens_periodically())
    yield
    # Shutdown
    token_refresh_task.cancel()

async def refresh_tokens_periodically():
    """Task que roda a cada hora."""
    while True:
        try:
            await refresh_expiring_tokens()
        except Exception as e:
            logger.error(f"Erro no worker de renovação: {e}")
        
        await asyncio.sleep(3600)  # 1 hora

app = FastAPI(lifespan=lifespan)
```

**Passo 3:** Wrapper para métodos que usam token

```python
# backend/app/integrations/youtube.py
async def _ensure_valid_token(account: YouTubeAccount):
    """Verifica se token está válido, renova se necessário."""
    now = datetime.now(timezone.utc)
    
    if account.token_expires_at and account.token_expires_at < now:
        # Token expirou, renovar
        try:
            new_data = await youtube_client.refresh_token(account.refresh_token)
            account.access_token = new_data["access_token"]
            account.token_expires_at = now + timedelta(seconds=new_data.get("expires_in", 3600))
            await db.commit()
        except Exception as e:
            raise HTTPException(status_code=403, detail="Could not refresh authentication token")

@youtube_client.upload_video
async def upload_video(account: YouTubeAccount, ...):
    await _ensure_valid_token(account)  # ← Verificar antes de usar
    # ... rest of upload logic
```

**Timeline:** ⏱️ Implementar em 1 semana

---

### AUTH-011: Sem validação de origem de OAuth callback

**Severidade:** 🟠 ALTO  
**Categoria:** Session Management  
**Status:** ❌ Não corrigido

#### 📍 Localização
- `/backend/app/api/v1/endpoints/aletube.py` (linha 282-326)

#### 🐛 Problema
Callback não valida se a requisição vem de uma origem legítima:

```python
@router.get("/callback/youtube")
async def callback_youtube(
    code:  str,
    state: str,
    ...
):
    # Nenhuma validação de:
    # - Referer header
    # - Origin header
    # - User-Agent
    # - IP
```

#### ✅ Remediação

```python
@router.get("/callback/youtube")
async def callback_youtube(
    code:  str,
    state: str,
    request: Request,
    ...
):
    # ✅ Validar Referer
    referer = request.headers.get("referer", "")
    if not referer.startswith("https://bestpricetoday.vercel.app/aletube"):
        logger.warning(f"Suspicious referer: {referer}")
        raise HTTPException(status_code=403, detail="Invalid origin")
    
    # ✅ Validar Origin
    origin = request.headers.get("origin", "")
    if origin != "https://bestpricetoday.vercel.app":
        logger.warning(f"Suspicious origin: {origin}")
        raise HTTPException(status_code=403, detail="Invalid origin")
    
    # ✅ Validar state (já implementado acima)
    stored_state = await redis_client.get(f"oauth_state:{state}")
    if not stored_state:
        raise HTTPException(status_code=403, detail="Invalid state")
    
    # ✅ Rate limit por IP
    client_ip = request.client.host
    rate_key = f"oauth_callback:{client_ip}"
    attempt_count = await redis_client.incr(rate_key)
    if attempt_count == 1:
        await redis_client.expire(rate_key, 3600)  # 1 hora
    if attempt_count > 10:  # Máximo 10 tentativas por hora por IP
        logger.warning(f"Rate limit exceeded for IP {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests")
    
    # Continuar...
```

**Timeline:** ⏱️ Implementar em 3 dias

---

## 🟡 Achados MÉDIO

### AUTH-002: Redirect URIs hardcoded no código fonte

**Severidade:** 🟡 MÉDIO  
**Status:** ❌ Não corrigido

#### 🐛 Problema
```python
# config.py
TIKTOK_REDIRECT_URI: str = "https://bestpricetoday.vercel.app/tiktok/callback"
YOUTUBE_REDIRECT_URI: str = "https://bestpricetoday.vercel.app/aletube/callback/youtube"
FACEBOOK_REDIRECT_URI: str = "https://bestpricetoday.vercel.app/aletube/callback/facebook"
```

#### ✅ Remediação
- Mover para `.env` apenas
- Adicionar validação de whitelist antes de processar callback
- Documentar todos os URIs esperados

---

### AUTH-004: Erros de OAuth expõem detalhes da API

**Severidade:** 🟡 MÉDIO  
**Status:** ❌ Não corrigido

#### 🐛 Problema
```python
raise HTTPException(status_code=400, detail=f"Erro OAuth YouTube: {str(e)}")
```

#### ✅ Remediação
```python
# Log completo no servidor
logger.error(f"OAuth error for YouTube: {str(e)}", exc_info=True)

# Retornar mensagem genérica ao cliente
raise HTTPException(
    status_code=400,
    detail="Authentication failed. Please try again or contact support."
)
```

---

### AUTH-005: Escopos OAuth excessivamente amplos

**Severidade:** 🟡 MÉDIO  
**Status:** ⚠️ Verificar

#### 🐛 Problema
- Instagram: `instagram_manage_insights` não é usado (pode ser removido)
- YouTube: `youtube.readonly` + `userinfo.profile` — verificar necessidade

#### ✅ Remediação
- Auditar cada escopo: "Por que é necessário?"
- Documentar em comentário
- Implementar scope seletivo: usuário escolhe quais permissões conceder

---

### AUTH-007: Tokens podem ser logados acidentalmente

**Severidade:** 🟡 MÉDIO  
**Status:** ❌ Não corrigido

#### ✅ Remediação
```python
# Implementar sanitizador de logs
def sanitize_for_logging(data: dict) -> dict:
    """Remove tokens e secrets antes de logar."""
    sensitive_keys = ["access_token", "refresh_token", "client_secret", "api_key"]
    return {
        k: f"{v[:10]}...(redacted)" if k in sensitive_keys else v
        for k, v in data.items()
    }

# Usar sempre
logger.info(f"Token data: {sanitize_for_logging(token_data)}")
```

---

### AUTH-008: Tokens não são revogados ao desconectar

**Severidade:** 🟡 MÉDIO  
**Status:** ❌ Não corrigido

#### ✅ Remediação
```python
@router.delete("/accounts/{platform}")
async def disconnect_account(platform: str, ...):
    """Desconectar conta — revoga token no provedor."""
    
    if platform == "youtube":
        account = (await db.execute(select(YouTubeAccount)...)).scalar()
        
        # ✅ Revogar no Google
        try:
            await revoke_youtube_token(account.access_token)
        except Exception as e:
            logger.error(f"Failed to revoke YouTube token: {e}")
        
        # Depois, deletar do banco
        await db.delete(account)
        await db.commit()
    
    # Repetir para Instagram, Facebook, TikTok...
```

---

## 📋 Checklist de Remediação

### 🔴 CRÍTICO (Implementar em 7 dias)

- [ ] **AUTH-001:** Criptografar tokens OAuth com AES-256
- [ ] **AUTH-009:** Implementar JWT + 2FA para admin
- [ ] **AUTH-010:** Verificar e revogar secrets expostos em git
- [ ] **AUTH-012:** Forçar HTTPS + HSTS headers

### 🟠 ALTO (Implementar em 14 dias)

- [ ] **AUTH-003:** State parameter + PKCE
- [ ] **AUTH-006:** Worker de renovação de tokens
- [ ] **AUTH-011:** Validação de origem + rate limiting

### 🟡 MÉDIO (Implementar em 30 dias)

- [ ] **AUTH-002:** Redirect URIs em .env
- [ ] **AUTH-004:** Sanitização de erros
- [ ] **AUTH-005:** Audit de escopos OAuth
- [ ] **AUTH-007:** Log sanitization
- [ ] **AUTH-008:** Revogação de tokens

---

## 🚀 Implementação Recomendada

### Fase 1: Imediato (hoje)
1. Verificar git history para secrets expostos
2. Se encontrado, rotacionar TODOS os secrets
3. Configurar `.gitignore` corretamente

### Fase 2: Curto Prazo (1 semana)
1. Implementar criptografia de tokens
2. Implementar JWT + login admin
3. HTTPS + HSTS forcing

### Fase 3: Médio Prazo (2 semanas)
1. State + PKCE
2. Token renewal worker
3. Origin validation

### Fase 4: Longo Prazo (1 mês)
1. Limpar scopes excessivos
2. Log sanitization
3. Token revocation flow

---

## 📞 Recursos Úteis

### Documentação OAuth
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OWASP OAuth 2.0](https://owasp.org/www-community/attacks/oauth-2-0-bearer-token-abuse)

### Python Security
- `cryptography.fernet` — Criptografia simétrica
- `python-jose` — JWT
- `slowapi` — Rate limiting

### Tools
- `truffleHog` — Detectar secrets em git
- `bandit` — Análise estática Python
- `sqlmap` — Testar SQL injection

---

## 🔗 Próximas Etapas

1. **Revisão:** Apresentar achados a stakeholders
2. **Priorização:** Confirmar timeline de remediação
3. **Desenvolvimento:** Criar PRs para cada finding
4. **Testes:** Teste de penetração após remediação
5. **Auditoria:** Re-auditoria em 30 dias

---

**Auditoria concluída:** 2026-06-01  
**Status:** ✅ Achados documentados e priorizados  
**Próxima revisão:** 2026-07-01
