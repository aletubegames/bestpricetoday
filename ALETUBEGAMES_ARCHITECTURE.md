# 🎥 Aletubegames — App de Distribuição de Conteúdo

## 📌 O Aletubegames em Uma Frase

**Aplicação separada que monitora uma pasta local, gera metadados com IA, publica vídeos no YouTube e Telegram usando infraestrutura compartilhada do BestPrice, e deleta após sucesso.**

---

## 🏢 Relação com BestPrice

- **BestPrice:** Comparador de preços com integração a 7+ marketplaces
- **Aletubegames:** App de distribuição de vídeos para redes sociais
- **Compartilham:** YouTube API, Telegram Bot, Database (Neon), Redis (Upstash), Deploy (HF Space)
- **São independentes:** Codebases separadas, repos separados, versioning separado

---

## 🏗️ Estrutura do Projeto

```
Aletubegames/
├── backend/                           # FastAPI (roda localmente no PC)
│   ├── app/
│   │   ├── main.py                   # FastAPI + lifespan (watchdog + workers)
│   │   ├── api/v1/
│   │   │   ├── router.py
│   │   │   └── endpoints/
│   │   │       ├── videos.py         # GET /videos, POST /videos/process
│   │   │       ├── posts.py          # CRUD posts, POST /posts/{id}/publish
│   │   │       └── status.py         # GET /status/{post_id}
│   │   ├── core/
│   │   │   ├── config.py             # Settings (reutiliza env do BestPrice)
│   │   │   ├── logging.py
│   │   │   └── cache.py
│   │   ├── db/
│   │   │   ├── session.py            # Mesma Neon do BestPrice
│   │   │   └── migrations/           # Nova tabela: aletubegames_posts
│   │   ├── models/
│   │   │   └── models.py             # ⭐ NOVO: Video, Post, PublishedPost
│   │   ├── schemas/
│   │   │   └── schemas.py            # ⭐ NOVO: VideoCreate, PostUpdate, PublishRequest
│   │   ├── integrations/
│   │   │   ├── youtube/
│   │   │   │   └── client.py         # ✅ Import/Reutiliza do BestPrice
│   │   │   ├── telegram/
│   │   │   │   └── client.py         # ✅ Import/Reutiliza do BestPrice
│   │   │   └── ai/
│   │   │       └── claude_service.py # ⭐ NOVO: Gera título/desc/tags
│   │   ├── workers/
│   │   │   ├── watcher.py            # ⭐ NOVO: Monitora ./uploads/postar
│   │   │   └── publisher.py          # ⭐ NOVO: Publica em paralelo (YT + TG)
│   │   └── utils/
│   │       └── file_handler.py       # ⭐ NOVO: Validar/copiar/deletar vídeos
│   ├── requirements.txt               # watchdog, google-auth-oauthlib, telethon, anthropic
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/                          # Next.js (Vercel)
│   ├── src/app/
│   │   ├── page.tsx                  # Dashboard: lista vídeos pendentes
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── videos/
│   │       ├── page.tsx              # Galeriam listagem
│   │       └── [id]/
│   │           └── page.tsx          # Editor: título, desc, tags, publish
│   ├── src/components/
│   │   ├── VideoPreview.tsx
│   │   ├── MetadataForm.tsx
│   │   └── PublishModal.tsx
│   ├── src/hooks/
│   │   └── useVideos.ts              # Fetch videos do backend
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
│
├── uploads/
│   └── postar/                       # 📁 Pasta que você coloca .mp4
│
├── docker-compose.yml                # Postgres (dev) + Redis (dev)
├── .env.example                      # Reutiliza credenciais do BestPrice
├── Makefile
├── README.md
└── .gitignore
```

---

## 🔄 Fluxo Operacional

### **1️⃣ Você coloca vídeo na pasta**

```
✋ Você: Salva video.mp4 em ./uploads/postar/
↓
🔍 Watchdog detecta novo arquivo
↓
📝 Backend insere em DB: status = "PENDENTE"
↓
📱 Frontend atualiza dashboard (websocket opcional)
```

### **2️⃣ Dashboard mostra vídeo pendente**

```
🖥️  Você abre Aletubegames no navegador
↓
📋 Lista: "video.mp4 - PENDENTE"
↓
👆 Você clica "Gerar Metadados"
```

### **3️⃣ IA gera título + descrição + tags**

```
🤖 Claude API processa:
   📝 Título: "GAMEPLAY ÉPICO - Eliminação FINAL [1080p 60fps]"
   📝 Descrição: "Assista a essa jogada INSANA!\n\n▶️ Inscreva-se: [link]\n..."
   🏷️  Tags: ["gameplay", "games", "épico", "twitch", ...]
↓
✏️  Você revisa e ajusta se necessário
↓
💾 Clica "CONFIRMAR"
```

### **4️⃣ Publica em YouTube + Telegram em paralelo**

```
🎬 Backend inicia upload:

┌─ YouTube ──────────────┐
│ • OAuth2 do Google     │
│ • resumable_upload     │
│ • Retorna: video_id    │
│ • Link: youtu.be/...   │
└────────────────────────┘
         ║
         ╠════════════╗
         ║            ║
         ↓            ↓
    Status OK?   Status OK?
         │            │
         ✅            ✅
         
┌─ Telegram ─────────────┐
│ • Telethon (vídeo)     │
│ • Com legenda + link   │
│ • Retorna: message_id  │
└────────────────────────┘
```

### **5️⃣ Limpeza automática**

```python
if youtube_status == 200 AND telegram_status == 200:
    ✅ Sucesso!
    os.remove("./uploads/postar/video.mp4")  # Deleta arquivo
    db.update(status="PUBLICADO", youtube_id="...", telegram_msg_id="...")
else:
    ❌ Erro em uma das plataformas
    db.update(status="ERRO_PUBLICAÇÃO", error_log="...")
    # Arquivo permanece intacto para retry
```

---

## � Compartilhamento de Infraestrutura

### Reutiliza 100% do BestPrice

| Recurso | BestPrice | Aletubegames | Detalhes |
|---------|-----------|--------------|----------|
| **YouTube API** | ✅ Usa | ✅ Usa | Mesma Google OAuth2, mesma credencial `credentials.json` |
| **Telegram Bot** | ✅ Usa | ✅ Usa | Mesmo `TELEGRAM_BOT_TOKEN`, mesmo canal destino |
| **Database (Neon)** | ✅ `neondb` | ✅ `neondb` | Nova tabela: `aletubegames_posts` (mesma DB) |
| **Redis (Upstash)** | ✅ Fila | ✅ Fila | Mesma `REDIS_URL`, namespace separado |
| **Deploy (HF Space)** | ✅ Space | ✅ Space | Novo endpoint `/aletubegames/*` no mesmo Space |
| **Google Auth Flow** | ✅ OAuth2 | ✅ OAuth2 | Reutiliza refresh token armazenado |

### Cópia de Código

```python
# Em Aletubegames, você importa do BestPrice:

from bestprice_integrations.youtube import YouTubeUploader      # ✅ Reutilizar
from bestprice_integrations.telegram import TelegramSender      # ✅ Reutilizar

# E implementa apenas:

from aletubegames.integrations.ai import ClaudeMetadataGenerator  # ⭐ NOVO
from aletubegames.workers import VideoWatcher                      # ⭐ NOVO
from aletubegames.models import Post, PublishedPost               # ⭐ NOVO
```

### Variáveis de Ambiente (reutiliza do BestPrice)

```bash
# .env.example (Aletubegames)

# Compartilhadas com BestPrice
TELEGRAM_BOT_TOKEN=8553563290:AAE...
GOOGLE_OAUTH_CREDENTIALS={"type": "service_account", ...}
GOOGLE_REFRESH_TOKEN=1//0...
DATABASE_URL=postgresql+asyncpg://...  # Mesma Neon
REDIS_URL=rediss://default:...         # Mesma Upstash

# Novas para Aletubegames
ANTHROPIC_API_KEY=sk-ant-...           # Claude API
VIDEOS_WATCH_PATH=./uploads/postar     # Pasta local
TELEGRAM_CHANNEL_ID=-100123456789      # Seu canal destino
```

---

## 🎯 Resumo das Vantagens

✅ **Código seco:** Reutiliza 100% da integração YouTube + Telegram  
✅ **Uma DB:** Mesma Neon, nova tabela separada  
✅ **Escalabilidade:** Depois adiciona TikTok, Instagram sem impactar BestPrice  
✅ **Independência:** Deploy, versionamento, manutenção completamente separados  
✅ **Segurança:** Cada app tem seu próprio ciclo de vida, tokens isolados por serviço  

---

## 📦 Stack Técnico

| Camada | Tecnologia | Reutiliza? |
|--------|-----------|-----------|
| **Backend API** | FastAPI 0.104+ | ✅ Padrão BestPrice |
| **Database** | PostgreSQL (Neon) | ✅ Mesma instância |
| **Cache/Fila** | Redis (Upstash) | ✅ Mesma instância |
| **File Watcher** | Watchdog 3.0+ | ⭐ NOVO |
| **YouTube Upload** | google-auth-oauthlib | ✅ BestPrice |
| **Telegram (vídeos)** | Telethon 1.31+ | ⭐ NOVO |
| **IA Metadados** | Anthropic Claude API | ⭐ NOVO |
| **Frontend** | Next.js 14, TypeScript | ✅ Padrão |
| **Deploy Backend** | HuggingFace Space | ✅ Mesmo Space |
| **Deploy Frontend** | Vercel | ⭐ Novo projeto Vercel |

---

## 🚀 Plano de Implementação

### **Fase 1: Setup (30 min)**
- [ ] Criar novo repo: `github.com/aletubegames/aletubegames`
- [ ] Copiar estrutura do BestPrice
- [ ] Configurar `docker-compose.yml` local
- [ ] Setup `.env.example` com variáveis compartilhadas

### **Fase 2: Models + Database (1h)**
- [ ] Criar migrations: tabela `aletubegames_posts`
- [ ] Models: `Video`, `Post`, `PublishedPost`
- [ ] Schemas: `VideoCreate`, `PostUpdate`, `PublishRequest`

### **Fase 3: Workers (1.5h)**
- [ ] `workers/watcher.py` - Monitorar `./uploads/postar` com watchdog
- [ ] `workers/publisher.py` - Upload YouTube + Telegram em paralelo
- [ ] `utils/file_handler.py` - Validar, copiar, deletar vídeos

### **Fase 4: Integração IA (1h)**
- [ ] `integrations/ai/claude_service.py` - Gerar metadados
- [ ] Prompt engineering para título/desc/tags otimizados

### **Fase 5: API Endpoints (1h)**
- [ ] `GET /videos` - Listar vídeos pendentes
- [ ] `POST /videos/process` - Inserir novo vídeo
- [ ] `GET /posts/{id}` - Detalhes do post
- [ ] `POST /posts/{id}/publish` - Publicar em YouTube + Telegram
- [ ] `GET /status/{id}` - Status da publicação

### **Fase 6: Frontend (2h)**
- [ ] Dashboard com listagem de vídeos
- [ ] Editor de metadados
- [ ] Modal de publicação
- [ ] Status updates em tempo real

### **Fase 7: Deploy (1h)**
- [ ] Push para HF Space (novo endpoint)
- [ ] Deploy frontend para Vercel
- [ ] Testar fluxo completo

---

## 🔒 Segurança & Boas Práticas

- ✅ Validar extensão de arquivo (apenas `.mp4`)
- ✅ Limitar tamanho máximo (ex: 4GB)
- ✅ Usar `asyncio.gather()` para uploads paralelos
- ✅ Retry automático com backoff exponencial
- ✅ Logs estruturados para debugging
- ✅ Webhook de notificação ao usuário (opcional)
- ✅ Cleanup de arquivos com `.replace()` em vez de `.remove()` para segurança

---

## ✅ Próximas Ações

**Confirma para começar a implementação?** 🎬
