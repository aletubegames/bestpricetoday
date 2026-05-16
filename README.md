# BestPriceToday 🛍️

Comparador de preços em tempo real com links afiliados rastreados e dashboard de monetização.

## Arquitetura

```
BestPriceToday/
├── frontend/          # Next.js 14 (App Router) — Vercel
├── backend/           # FastAPI + PostgreSQL — HuggingFace Space
│   ├── app/
│   │   ├── api/v1/endpoints/   # search, admin, links, alerts, favorites, auth
│   │   ├── integrations/       # AliExpress, Shopee, ML OAuth, conversion_tracker
│   │   ├── services/providers/ # mercadolivre, aliexpress, shopee, amazon, lomadee, awin, kabum
│   │   ├── workers/            # alert_checker, bestprice_bot, channel_broadcaster, conversion_cron
│   │   ├── models/models.py    # SQLAlchemy ORM (PostgreSQL)
│   │   └── core/config.py      # Variáveis de ambiente (pydantic-settings)
│   └── hf_deploy/              # Espelho para HuggingFace Space (sync via sync_hf_deploy.sh)
└── shared/            # Tipos compartilhados
```

## Como Rodar Localmente

### Backend

```bash
cd backend
python -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edite com suas credenciais
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # edite NEXT_PUBLIC_API_URL
npm run dev
```

## Variáveis de Ambiente (Backend)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async URL |
| `ADMIN_MANAGER_KEY` | ✅ | Chave para endpoints /admin |
| `ALIEXPRESS_APP_KEY` | Recomendado | Busca + rastreio AliExpress |
| `ALIEXPRESS_APP_SECRET` | Recomendado | |
| `ALIEXPRESS_TRACKING_ID` | Recomendado | |
| `MERCADOLIVRE_APP_ID` | Recomendado | OAuth ML + busca |
| `MERCADOLIVRE_SECRET` | Recomendado | |
| `SHOPEE_APP_ID` | Opcional | Busca Shopee |
| `SHOPEE_SECRET` | Opcional | |
| `LOMADEE_API_KEY` | Opcional | Busca Lomadee |
| `TELEGRAM_BOT_TOKEN` | Opcional | Bot alertas |
| `TELEGRAM_CHANNEL_ID` | Opcional | Canal broadcast |
| `REDIS_URL` | Opcional | Cache (default: redis://localhost:6379) |

## Monetização

### Fluxo de Clique
1. Usuário clica em oferta → `OfferCard.tsx` chama `POST /api/v1/admin/clicks`
2. O click fica salvo em `click_events` com provider, título, preço e IP
3. Se usar `/r/{code}` (short link), o backend registra o clique e redireciona

### Tracking de Conversões
- **AliExpress:** API `aliexpress.affiliate.order.list.by.index` (poll horário)
- **Lomadee:** API `/v3/{sourceId}/report/commission` (poll horário)
- **Shopee:** GraphQL `conversionReport` (poll horário)
- **Mercado Livre:** Webhook HMAC + GET `/orders/{id}`

### Dashboard Admin
`GET /api/v1/admin/overview` (requer `X-Admin-Key`)

## Deploy

### Frontend (Vercel)
```bash
cd frontend && vercel --prod --yes
```

### Backend (HuggingFace Space)
```bash
cd backend && bash sync_hf_deploy.sh
cd hf_deploy && git add -A && git commit -m "deploy" && git push
```

## Testes

```bash
cd backend
PYTHONPATH=. .venv312/bin/pytest tests/test_integrity.py tests/test_api.py -v
```

## Endpoints Principais

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET/POST` | `/api/v1/search` | Busca multi-provider |
| `GET` | `/api/v1/search/trending` | Buscas em alta |
| `POST` | `/api/v1/admin/clicks` | Registra clique (sem auth) |
| `GET` | `/api/v1/admin/overview` | Dashboard monetização |
| `GET` | `/api/v1/r/{code}` | Redirect rastreado |
| `POST` | `/api/v1/links/create` | Cria short link |
| `GET/POST` | `/api/v1/alerts` | Alertas de preço |
| `GET/POST` | `/api/v1/favorites` | Favoritos |
