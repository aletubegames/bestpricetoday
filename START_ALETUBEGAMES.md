# 🚀 Como Iniciar AleTubeGames Localmente

## Status Atual
- Backend: ❌ Não rodando
- Frontend: ❌ Não rodando
- PostgreSQL: ❓ Verificar
- Redis: ❓ Verificar

## Pré-requisitos Instalados
✅ Node.js e npm (frontend)
✅ Python 3.9+ (backend)
✅ PostgreSQL (Neon)
✅ Redis (Upstash)
✅ Credenciais OAuth configuradas

## Passo 1: Iniciar Backend FastAPI

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday/backend

# Ativar virtualenv
source /home/alessandro/bin/Git_Repo/BestPriceToday/venv/bin/activate

# Instalar dependências (se necessário)
pip install -r requirements.txt

# Rodar servidor
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Esperado:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Teste:**
```bash
curl http://localhost:8000/docs
# Deve abrir Swagger UI
```

---

## Passo 2: Iniciar Frontend Next.js

**Em outro terminal:**

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday/frontend

# Instalar dependências (se necessário)
npm install

# Rodar servidor
npm run dev
```

**Esperado:**
```
> next dev
  ▲ Next.js 15.x.x
  - ready started server on 0.0.0.0:3000
```

**Teste:**
```bash
# Em seu navegador
http://localhost:3000
```

---

## Passo 3: Conectar Contas de Rede Social

### A. YouTube

1. Acesse: `http://localhost:3000/aletube`
2. Clique em **"Conectar YouTube"** (ou botão equivalente)
3. Será redirecionado para `http://localhost:8000/aletube/auth/youtube`
4. Autorize o acesso em: `https://accounts.google.com/...`
5. Google redireciona para: `http://localhost:3000/aletube/callback/youtube?code=XXX&state=YYY`
6. Backend salva credentials em `youtube_accounts`
7. Volta para AleTubeGames com ✅ YouTube conectado

**Verificar:**
```bash
# Terminal - verificar se account foi criada
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/aletube/accounts
```

### B. Instagram/Facebook

1. Clique em **"Conectar Instagram"** (ou "Conectar Facebook")
2. Será redirecionado para `http://localhost:8000/aletube/auth/facebook`
3. Autorize em: `https://www.facebook.com/login.php?...`
4. Facebook redireciona para callback
5. Backend salva em `instagram_accounts` + `facebook_accounts`

### C. TikTok

1. Clique em **"Conectar TikTok"**
2. Será redirecionado para `http://localhost:8000/aletube/auth/tiktok`
3. Autorize em: `https://www.tiktok.com/v2/oauth/authorize?...`
4. TikTok redireciona para callback
5. Backend salva em `tiktok_accounts` com `account_type="admin"`

---

## Passo 4: Testar Publicação de Vídeo

### Upload

```bash
curl -X POST "http://localhost:8000/aletube/upload" \
  -F "file=@seu_video.mp4" \
  -F "title=Meu Vídeo de Teste" \
  -F "description=Teste do AleTubeGames" \
  -F "platforms=youtube&platforms=instagram&platforms=facebook&platforms=tiktok" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Resposta:
{
  "video_id": "uuid...",
  "filename": "seu_video.mp4",
  "status": "uploaded"
}
```

### Publicar

```bash
curl -X POST "http://localhost:8000/aletube/publish" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "video_id": "uuid...",
    "platforms": ["youtube", "instagram", "facebook", "tiktok"],
    "metadata": {
      "youtube": {
        "title": "Meu Vídeo",
        "description": "Descrição aqui"
      }
    }
  }'

# Resposta:
{
  "video_id": "uuid...",
  "status": "published",
  "platforms": {
    "youtube": {"status": "ok", "video_id": "dQw4w9WgXcQ"},
    "instagram": {"status": "ok", "media_id": "..."},
    "facebook": {"status": "ok", "post_id": "..."},
    "tiktok": {"status": "ok", "short_link": "..."}
  }
}
```

### Verificar Status

```bash
curl "http://localhost:8000/aletube/videos" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Deve mostrar:
{
  "total": 1,
  "videos": [{
    "id": "uuid...",
    "filename": "seu_video.mp4",
    "status": "published",  # ✅ Não mais "failed"!
    "youtube_video_id": "dQw4w9WgXcQ",
    "instagram_media_id": "...",
    "facebook_post_id": "...",
    "tiktok_video_id": "..."
  }]
}
```

---

## Passo 5: Verificar em Dashboard

Se tudo funcionou:

1. Acesse `http://localhost:3000/aletube`
2. Você verá:
   ```
   ✅ YouTube conectado
   ✅ Instagram conectado
   ✅ Facebook conectado
   ✅ TikTok conectado
   ```
3. Seu vídeo aparecerá na tabela com:
   - Status: **published** (não mais failed)
   - Plataformas: YouTube, Instagram, Facebook, TikTok
   - Links para cada vídeo

---

## Troubleshooting

### Backend não inicia

```bash
# Erro 1: Port 8000 em uso
lsof -i :8000
kill -9 PID

# Erro 2: Dependências faltando
pip install -r requirements.txt --upgrade

# Erro 3: Banco de dados não acessível
# Verificar DATABASE_URL em backend/.env
psql $DATABASE_URL -c "SELECT 1"
```

### Frontend não conecta com backend

```bash
# Verificar se backend está rodando
curl http://localhost:8000/docs

# Verificar CORS em backend
# backend/app/main.py deve ter:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### OAuth redireciona para HTTPS (erro em localhost)

```bash
# Temporário: desabilitar verificação SSL em dev
export NODE_TLS_REJECT_UNAUTHORIZED=0

# Melhor: use ngrok para HTTPS local
ngrok http 3000
# Use URL do ngrok em OAuth redirect_uri
```

### Nenhuma conta aparece em /aletube/accounts

```bash
# Verificar se tabelas foram criadas
psql $DATABASE_URL -c "\\dt" | grep -i account

# Se vazio, executar migrações
cd backend
alembic upgrade head

# Se ainda vazio, criar contas manualmente
python -c "
from app.db.session import engine, Base
Base.metadata.create_all(bind=engine)
"
```

---

## Estrutura de Diretórios

```
BestPriceToday/
├── backend/                          # FastAPI
│   ├── app/
│   │   ├── main.py                   # App principal
│   │   ├── core/config.py            # Credenciais OAuth
│   │   ├── integrations/
│   │   │   ├── youtube.py            # YouTubeClient
│   │   │   ├── instagram.py          # InstagramFacebookClient
│   │   │   └── tiktok.py             # TikTokClient
│   │   ├── api/v1/endpoints/
│   │   │   └── aletube.py            # Endpoints /aletube/*
│   │   ├── models/models.py          # BD: YouTubeAccount, InstagramAccount, etc.
│   │   └── db/session.py             # SQLAlchemy setup
│   ├── .env                          # Credenciais (gitignore)
│   └── requirements.txt
│
└── frontend/                         # Next.js
    ├── src/
    │   ├── app/
    │   │   ├── aletube/
    │   │   │   ├── page.tsx           # Dashboard AleTubeGames
    │   │   │   └── callback/
    │   │   │       ├── youtube/page.tsx
    │   │   │       ├── instagram/page.tsx
    │   │   │       └── tiktok/page.tsx
    │   │   └── layout.tsx
    │   └── components/
    └── .env.local
```

---

## Credenciais Necessárias (já configuradas?)

Verificar em `backend/.env`:

```bash
# YouTube
YOUTUBE_CLIENT_ID=369034326111-...apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-...

# Instagram/Facebook
INSTAGRAM_APP_ID=xxx
INSTAGRAM_APP_SECRET=xxx
FACEBOOK_REDIRECT_URI=http://localhost:3000/aletube/callback/facebook

# TikTok
TIKTOK_CLIENT_KEY=awllka8qo05dhkri
TIKTOK_CLIENT_SECRET=MjJUon...

# Database & Redis
DATABASE_URL=postgresql+asyncpg://user:pass@host/db?ssl=require
REDIS_URL=rediss://...
```

---

## Próximos Passos

1. ✅ Inicie backend: `python -m uvicorn app.main:app --reload`
2. ✅ Inicie frontend: `npm run dev`
3. ✅ Acesse http://localhost:3000/aletube
4. ✅ Conecte YouTube, Instagram, Facebook, TikTok
5. ✅ Faça upload de vídeo
6. ✅ Clique "Publicar"
7. ✅ Veja status mudar para **published** (não failed)
8. ✅ Vídeo deve aparecer nas plataformas em ~5-60 min

---

**Status:** 🔴 Blocked (stack não rodando)  
**Ação:** Iniciar backend + frontend conforme instruções acima  
**ETA:** 10 min para conexão OAuth funcionar
