# BestPriceToday 🛍️

Comparador de preços em tempo real com links afiliados rastreados, dashboard de monetização e geração de vídeos com IA.

[![Deploy](https://img.shields.io/badge/frontend-alaserver-blue)](https://bestpricetoday.alaserver.com.br)
[![API](https://img.shields.io/badge/backend-alaserver-green)](https://api.alaserver.com.br/health)

---

## Arquitetura

```
BestPriceToday/
├── frontend/                    # Next.js 14 (App Router) — Alaserver
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Busca principal
│       │   ├── admin/page.tsx   # Dashboard admin + gerador de vídeo
│       │   ├── alertas/page.tsx # Alertas de preço (owner_id)
│       │   ├── afiliados/page.tsx # Dashboard de afiliados (6 providers)
│       │   ├── cupons/page.tsx  # Grid de produtos com cupom ML
│       │   ├── oferta/[code]/   # Página de oferta profissional
│       │   └── r/[code]/        # Redirect rastreado
│       ├── components/
│       │   ├── layout/Header.tsx   # Header compartilhado (Lucide icons, responsive)
│       │   ├── layout/Section.tsx   # Wrapper de seção reutilizável
│       │   └── offers/          # OfferCard com score IA + click tracking
│       ├── hooks/               # useSearch, useTrendingSearches
│       └── lib/api.ts           # ← Fonte única de API_BASE
│
├── backend/                     # FastAPI + uvicorn — alaserver (Cloudflare Tunnel)
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── search.py        # Busca multi-provider + trending
│   │   │   ├── admin.py         # Dashboard, clicks, conversões, broadcast, vídeo
│   │   │   ├── links.py         # POST /links/create + GET /r/{code}
│   │   │   ├── alerts.py        # CRUD alertas (owner_id obrigatório)
│   │   │   ├── favorites.py     # CRUD favoritos (owner_id obrigatório)
│   │   │   ├── affiliate.py     # Seed de produtos afiliados ML
│   │   │   └── auth.py          # OAuth Mercado Livre
│   │   ├── integrations/
│   │   │   ├── aliexpress/      # AliExpress TOP + GOP API
│   │   │   ├── shopee/          # Shopee GraphQL Affiliate API
│   │   │   ├── youtube.py       # Publicação de Shorts no YouTube
│   │   │   └── conversion_tracker.py  # Poll orders AliExpress/Lomadee/Shopee/ML
│   │   ├── services/providers/  # aliexpress, shopee, mercadolivre, amazon, lomadee, awin, kabum
│   │   ├── workers/
│   │   │   ├── distributor.py          # Orquestrador central (4x/dia: 12h, 15h, 19h, 21h)
│   │   │   ├── coupon_distributor.py   # Cupons ML (2x/dia: 12h, 19h) + vídeo XTTS
│   │   │   ├── ml_coupon_scraper.py    # Scraper de cupons do Portal do Afiliado ML
│   │   │   ├── bestprice_bot.py        # Telegram bot (/start /alertas /top /canal)
│   │   │   ├── alert_checker.py        # Verifica alertas a cada 30min, notifica via Telegram
│   │   │   ├── conversion_cron.py      # Poll horário de conversões
│   │   │   ├── ml_refresh_cron.py      # Renova token ML a cada 15-25min
│   │   │   └── channel_broadcaster.py  # DEPRECATED (substituído por distributor.py)
│   │   ├── models/models.py     # SQLAlchemy ORM
│   │   └── core/config.py       # Variáveis de ambiente (pydantic-settings)
│   ├── DEPRECATED/               # Espelho DEPRECATED (DEPRECATED - conta bloqueada)
│   ├── tests/
│   │   ├── test_integrity.py    # 16 testes estruturais
│   │   └── test_api.py          # 8 testes funcionais
│   └── scripts/
│       └── migration_owner_id.py # Migration owner_id (já aplicada em produção)
└── .github/workflows/
    └── deploy-hf.yml            # CI/CD: DEPRECATED (Hugging Face conta bloqueada)
```

---

## Como Rodar Localmente

### Backend

```bash
cd backend
python -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edite com suas credenciais
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
# crie .env.local com:
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Tecnologias

- **Backend:** Python 3.14 + FastAPI + SQLAlchemy async + Pydantic v2 + PostgreSQL (Neon)
- **Frontend:** Next.js 14 (App Router) + React 18 + TypeScript + CSS Modules + Tailwind CSS + Lucide icons + Framer Motion
- **Deploy:** Alaserver (192.168.100.30) + Cloudflare Tunnel
- **Cache:** Redis (Upstash / localhost)
- **Vídeo:** ffmpeg + XTTS v2 (voz clonada)

---

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async (ex: Neon) em produção; SQLite fallback local |
| `ADMIN_MANAGER_KEY` | ✅ | Chave para endpoints `/admin` |
| `ALIEXPRESS_APP_KEY` | Recomendado | Busca + rastreio AliExpress |
| `ALIEXPRESS_APP_SECRET` | Recomendado | |
| `ALIEXPRESS_TRACKING_ID` | Recomendado | |
| `MERCADOLIVRE_APP_ID` | Recomendado | OAuth ML + busca |
| `MERCADOLIVRE_SECRET` | Recomendado | |
| `SHOPEE_APP_ID` | Opcional | Busca Shopee |
| `SHOPEE_SECRET` | Opcional | Do portal affiliate.shopee.com.br |
| `LOMADEE_API_KEY` | Opcional | |
| `LOMADEE_SOURCE_ID` | Opcional | |
| `AMAZON_PARTNER_TAG` | Opcional | Associate tag |
| `TELEGRAM_BOT_TOKEN` | Opcional | Bot de alertas e busca |
| `TELEGRAM_CHANNEL_ID` | Opcional | Canal broadcast (ex: `@BestPriceTodayBR`) |
| `REDIS_URL` | Opcional | Cache busca (default: redis://localhost) |
| `INTERNAL_API_URL` | Opcional | URL interna para alert_checker buscar preços |
| `ALERT_CHECK_INTERVAL` | Opcional | Intervalo do checker em segundos (default: 1800) |

---

## Monetização

### Fluxo completo
```
Busca → Ranking IA → OfferCard
  → trackClick() → POST /admin/clicks (analytics)
  → href affiliate_url + UTM
  → compra no marketplace
  → conversão registrada via webhook / poll horário
  → comissão real no dashboard admin
```

### Short links rastreados (`/r/{code}`)
```
POST /api/v1/links/create  →  { code, url: /r/{code} }
Usuário clica /r/{code}    →  registra ClickEvent + redirect 302
```

### Tracking de Conversões
| Plataforma | Método |
|---|---|
| AliExpress | Poll `aliexpress.affiliate.order.list.by.index` (horário) |
| Lomadee | Poll `/v3/{sourceId}/report/commission` (horário) |
| Shopee | Poll GraphQL `conversionReport` (horário) |
| Mercado Livre | Webhook HMAC-SHA256 + GET `/orders/{id}` |

---

## Dashboard Admin

Acesso: `https://bestpricetoday.alaserver.com.br/admin`
Auth: header `X-Admin-Key: <ADMIN_MANAGER_KEY>`

### Funcionalidades
- **KPIs:** cliques, conversões, receita, comissão, CTR, R$/clique
- **Gráficos:** série temporal por dia, receita por plataforma
- **Marketplace:** tabela comparativa ordenável
- **Integrações:** status real (ML token, AliExpress, Shopee…)
- **📣 Marketing Automático:**
  - Canal Telegram: broadcast manual de 3 ofertas diversificadas
  - **🎥 Gerador de Vídeo IA:** seleciona produto do Top 10, escolhe formato com sugestão inteligente, define plataformas (Telegram/YouTube/TikTok), acompanha log em tempo real
- **Top 10 produtos** clicados com drill-down
- **Cliques e Conversões** recentes paginados
- **Export CSV**

### Gerador de Vídeo — Formatos e Narração
| Formato | Quando usar (sugerido automaticamente) |
|---|---|
| 💥 Oferta Choque | Desconto ≥ 10% |
| 🎙️ Viral TikTok | Produto com ≥ 5 cliques recentes |
| 🏆 Top 3 | Categorias com múltiplas opções (fone, notebook…) |
| ⚔️ VS Comparativo | Marcas conhecidas (Samsung, iPhone, RTX…) |
| 🔔 Alerta de Preço | Desconto 5–20% |
| ⏳ Última Chance | Preço < R$100 |
| 🎥 WAN2.1 Cinemático | Produtos premium (≥ R$1.500) |

**Narração:** XTTS v2 (voz clonada ElevenLabs — locutor "matheus")
- Roteiro estruturado com aberturas aleatórias
- Frase de utilidade extraída do título do produto
- Preços por extenso (ex: "doze mil e quinhentos reais")
- Expansão de marcas/unidades para TTS (ex: "Samsung Galaxy S24" em vez de "S24")

---

## Alertas de Preço

```
Usuário cria alerta (query + target_price + owner_id)
  → owner_id = localStorage["bpt_anon_id"] (browser)
  → owner_id = str(telegram_user_id) (bot)
alert_checker.py roda a cada 30min:
  → busca preço atual via /search
  → se preço ≤ target: notifica via Telegram (se owner_id numérico)
  → marca triggered_at, desativa alerta
```

**API — owner_id obrigatório em todos os endpoints:**
```
POST /api/v1/alerts          body: { query, target_price, owner_id }
GET  /api/v1/alerts          ?owner_id=...
DELETE /api/v1/alerts/{id}   ?owner_id=...  (valida ownership)
```

---

## Distributor (Orquestrador Central)

Roda continuamente dentro do `bestprice-backend`, postando ofertas em horários estratégicos:
- **12h:** 2 ofertas (pico almoço)
- **15h:** 1 oferta (tarde)
- **19h:** 2 ofertas (pico noite)
- **21h:** 1 oferta (noite — pico de compra online)

Canais: Telegram, Facebook, Instagram, YouTube (simultâneos)
- Janela de tolerância: 2 horas
- Deduplicação: 48h (não repete mesma URL)
- YouTube roda em background (`asyncio.create_task`)
- Filtros: preço ≥ R$100, desconto ≥ 20%, comissão estimada ≥ R$8

## Coupon Distributor (Separado)

Sistema independente que posta cupons Mercado Livre 2x/dia:
- **12h e 19h** (mesmos horários do distributor)
- Canais: Telegram, Facebook, Instagram, YouTube
- YouTube: imagem do produto + overlay de preço/cupom + narração XTTS v2 (voz clonada ElevenLabs)
- Produtos: top clicados/convertidos do catálogo, combinados com cupons ML ativos
- Cupom = rastreio permanente (não expira em 48h como cookie do link)
- Cupons vencidos são DELETADOS

---

## Testes

```bash
cd backend
PYTHONPATH=. .venv312/bin/pytest tests/ -v
# 24/24 passando
```

### test_integrity.py (16 testes)
- Sem endpoint `/conversions/test` no código nem nas rotas
- Sem `commission_rate`/`commission_value` hardcoded em produção
- `conversion_tracker.py` usa dados reais das plataformas
- Ownership: todos endpoints retornam 422 sem `owner_id`
- Frontend: nenhum fallback de URL fora de `lib/api.ts`
- `DEPRECATED` sincronizado com canônico

---

## Deploy

### Infraestrutura

- **Servidor:** `alaserver` (`192.168.100.30`, rede local)
- **Proxy:** Cloudflare Tunnel (`cloudflared`) na porta 443
- **Backup:** nginx nas portas 9443/8443/2053 (port forwarding roteador)

### Serviços systemd

```bash
sudo systemctl restart bestprice-backend    # FastAPI + workers (porta 8000)
sudo systemctl restart bestprice-frontend   # Next.js (porta 3000)
sudo systemctl restart cloudflared          # Cloudflare Tunnel
sudo systemctl reload nginx                 # Reverse proxy
```

### Video API local (GPU — usada pelo admin de vídeo)
```bash
# Iniciar manualmente
cd ~/wan2 && python video_api.py   # porta 8765

# Instalar como serviço permanente
sudo cp ~/wan2/bestprice-video-api.service /etc/systemd/system/
sudo systemctl enable --now bestprice-video-api

# Verificar
curl http://localhost:8765/health
```

### Frontend (Alaserver)
```bash
ssh alessandro@192.168.100.30
cd /home/alessandro/frontend
npx next build
sudo systemctl restart bestprice-frontend
```

### Backend (Alaserver)
```bash
ssh alessandro@192.168.100.30
cd /home/alessandro/backend
sudo systemctl restart bestprice-backend
```

> **Nota:** Hugging Face deployment foi descontinuado (conta bloqueada). Não usar `deploy-hf.yml` nem `sync_DEPRECATED.sh`.

---

## Endpoints Principais

| Método | Path | Auth | Descrição |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `GET` | `/api/v1/search` | — | Busca multi-provider |
| `GET` | `/api/v1/search/trending` | — | Buscas em alta |
| `POST` | `/api/v1/admin/clicks` | — | Registra clique |
| `GET` | `/api/v1/admin/overview` | Admin | Dashboard KPIs |
| `POST` | `/api/v1/admin/broadcast/telegram` | Admin | Broadcast manual |
| `POST` | `/api/v1/admin/video/publish` | Admin | Gerar e publicar vídeo |
| `GET` | `/api/v1/admin/video/status/{job_id}` | Admin | Status do job de vídeo |
| `GET` | `/api/v1/r/{code}` | — | Redirect rastreado |
| `POST` | `/api/v1/links/create` | — | Cria short link |
| `GET/POST` | `/api/v1/alerts` | — | Alertas (owner_id obrigatório) |
| `DELETE` | `/api/v1/alerts/{id}` | — | Remove alerta (valida owner) |
| `GET/POST` | `/api/v1/favorites` | — | Favoritos (owner_id obrigatório) |
| `GET` | `/api/v1/auth/ml/status` | — | Status token ML |
| `POST` | `/api/v1/auth/ml/refresh` | — | Renova token ML |
