# BestPriceToday 🛍️

Comparador de preços em tempo real com links afiliados rastreados, dashboard de monetização e geração de vídeos com IA.

[![Deploy](https://img.shields.io/badge/frontend-vercel-black)](https://bestpricetoday.vercel.app)
[![API](https://img.shields.io/badge/backend-huggingface-yellow)](https://alessandro2090-bestpricetoday-api.hf.space/docs)

---

## Arquitetura

```
BestPriceToday/
├── frontend/                    # Next.js 14 (App Router) — Vercel
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Busca principal
│       │   ├── admin/page.tsx   # Dashboard admin + gerador de vídeo
│       │   ├── alertas/page.tsx # Alertas de preço (owner_id)
│       │   └── r/[code]/        # Redirect rastreado
│       ├── components/offers/   # OfferCard com score IA + click tracking
│       ├── hooks/               # useSearch, useTrendingSearches
│       └── lib/api.ts           # ← Fonte única de API_BASE
│
├── backend/                     # FastAPI + PostgreSQL — HuggingFace Space
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── search.py        # Busca multi-provider + trending
│   │   │   ├── admin.py         # Dashboard, clicks, conversões, broadcast, vídeo
│   │   │   ├── links.py         # POST /links/create + GET /r/{code}
│   │   │   ├── alerts.py        # CRUD alertas (owner_id obrigatório)
│   │   │   ├── favorites.py     # CRUD favoritos (owner_id obrigatório)
│   │   │   └── auth.py          # OAuth Mercado Livre
│   │   ├── integrations/
│   │   │   ├── aliexpress/      # AliExpress TOP + GOP API
│   │   │   ├── shopee/          # Shopee GraphQL Affiliate API
│   │   │   └── conversion_tracker.py  # Poll orders AliExpress/Lomadee/Shopee/ML
│   │   ├── services/providers/  # aliexpress, shopee, mercadolivre, amazon, lomadee, awin, kabum
│   │   ├── workers/
│   │   │   ├── alert_checker.py      # Verifica alertas a cada 30min, notifica via Telegram
│   │   │   ├── bestprice_bot.py      # Telegram bot (/start /alertas /top /canal)
│   │   │   ├── channel_broadcaster.py # Broadcast automático com dedup 24h
│   │   │   └── conversion_cron.py    # Poll horário de conversões
│   │   ├── models/models.py     # SQLAlchemy ORM
│   │   └── core/config.py       # Variáveis de ambiente (pydantic-settings)
│   ├── hf_deploy/               # Espelho HuggingFace (sync via sync_hf_deploy.sh)
│   ├── tests/
│   │   ├── test_integrity.py    # 16 testes estruturais (sem endpoint fake, ownership, etc.)
│   │   └── test_api.py          # 8 testes funcionais
│   └── scripts/
│       └── migration_owner_id.py # Migration owner_id (já aplicada em produção)
└── .github/workflows/
    └── deploy-hf.yml            # CI/CD: push em backend/ → deploy automático no HF Space
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

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async (ex: Neon) |
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

Acesso: `https://bestpricetoday.vercel.app/admin`
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

### Gerador de Vídeo — Formatos
| Formato | Quando usar (sugerido automaticamente) |
|---|---|
| 💥 Oferta Choque | Desconto ≥ 10% |
| 🎙️ Viral TikTok | Produto com ≥ 5 cliques recentes |
| 🏆 Top 3 | Categorias com múltiplas opções (fone, notebook…) |
| ⚔️ VS Comparativo | Marcas conhecidas (Samsung, iPhone, RTX…) |
| 🔔 Alerta de Preço | Desconto 5–20% |
| ⏳ Última Chance | Preço < R$100 |
| 🎥 WAN2.1 Cinemático | Produtos premium (≥ R$1.500) |

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

## Broadcaster Telegram

- Roda a cada hora (3 ofertas das 9h–23h, 1 fora do horário)
- **Sem repetição:** deduplicação por URL nas últimas 24h
- **Variedade:** sorteia categorias diferentes (smartphones, games, casa, audio…)
- **Seleção ponderada:** score da oferta influencia mas não é determinístico
- Disparo manual: `POST /api/v1/admin/broadcast/telegram?n=3`

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
- `hf_deploy` sincronizado com canônico

---

## Deploy

### Frontend (Vercel)
```bash
cd frontend && vercel --prod --yes
```

### Backend (HuggingFace Space)
Push para `master` em qualquer arquivo de `backend/` dispara o GitHub Action `deploy-hf.yml` automaticamente.

Para deploy manual:
```bash
cd backend && bash sync_hf_deploy.sh
```

### HF Deploy separado
```bash
cd backend/hf_deploy
git add -A && git commit -m "deploy: <desc>" && git push origin main
```

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
