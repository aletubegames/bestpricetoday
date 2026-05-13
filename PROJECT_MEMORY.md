# PROJECT_MEMORY.md — BestPriceToday

> Arquivo de referência rápida. Se você perdeu o contexto, comece aqui.

---

## O que é

Comparador de preços com monetização 100% via afiliados.
O usuário busca, vê os melhores preços rankeados, clica no link de afiliado e você ganha comissão.
**Nenhuma cobrança ao usuário. Custo zero até R$40k/mês de receita.**

---

## Infraestrutura

| Serviço       | URL / Detalhe                                                              |
|---------------|----------------------------------------------------------------------------|
| Frontend      | https://bestpricetoday.vercel.app (Next.js, Vercel free)                  |
| Backend       | https://alessandro2090-bestpricetoday-api.hf.space (FastAPI, HuggingFace) |
| Banco         | Neon PostgreSQL (free tier) — string no `.env`                            |
| Cache         | Upstash Redis (free tier) — string no `.env`                              |
| Repo          | https://github.com/aletubegames/bestpricetoday                            |

---

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy async + Pydantic v2
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS
- **Deploy backend:** Dockerfile em `backend/hf_deploy/`
- **Deploy frontend:** Vercel (auto-deploy no push)
- **Testes:** pytest + pytest-asyncio (backend)

---

## Afiliados cadastrados

| Loja           | Status  | ID / Detalhe                          |
|----------------|---------|---------------------------------------|
| Mercado Livre  | ✅ ativo | APP_ID: 2661096739949809              |
| Amazon         | ✅ ativo | Associate tag: `aletubegames-20`      |
| Shopee         | ✅ ativo | App ID/Secret pendente                |
| AliExpress     | ✅ ativo | Open Platform separada (bestpricetoday) |
| Lomadee        | ✅ ativo | Source ID cadastrado, API key no suporte |

---

## Providers — estado real

| Provider      | Código | Integrado ao orquestrador | Credenciais |
|---------------|--------|--------------------------|-------------|
| MercadoLivre  | ✅      | ✅                        | ⚠️ /products/search bloqueado para apps novos (403) |
| Amazon        | ✅      | ✅                        | ❌ ACCESS_KEY/SECRET vazios (PA-API requer histórico de vendas) |
| Shopee        | ✅      | ✅                        | ❌ APP_ID/SECRET vazios |
| AliExpress    | ✅      | ✅                        | ❌ APP_KEY/SECRET vazios |
| Lomadee       | ✅      | ✅                        | ⚠️ SOURCE_ID ok, x-api-key pendente no suporte |
| KaBuM         | ✅      | ❌ comentado em search.py | sem credenciais |
| Awin          | ✅      | ❌ comentado em search.py | sem credenciais |

---

## Arquitetura do backend

```
backend/app/
├── main.py                  # FastAPI app + lifespan
├── api/v1/
│   ├── router.py            # inclui search + alerts
│   └── endpoints/
│       ├── search.py        # GET /search
│       └── alerts.py        # POST/GET/DELETE /alerts
├── core/
│   ├── config.py            # Settings (pydantic-settings)
│   ├── cache.py             # Redis via Upstash
│   └── logging.py
├── db/session.py            # async engine + Base + get_db
├── models/models.py         # ORM: User, Search, Product, Offer,
│                            #   PriceAlert, Favorite, PriceHistory,
│                            #   AffiliateClick, Analytics, Coupon
├── schemas/schemas.py       # Pydantic: OfferSchema, SearchResponse,
│                            #   AlertCreate, AlertResponse, ClickTrack
├── services/
│   ├── search.py            # Orquestrador paralelo de providers
│   ├── ranking/engine.py    # Score 0-100 (preço, frete, desconto, trust)
│   └── providers/
│       ├── base.py
│       ├── mercadolivre.py
│       ├── amazon.py
│       ├── shopee.py
│       ├── aliexpress.py
│       ├── lomadee.py
│       ├── kabum.py         # implementado, não integrado
│       └── awin.py          # implementado, não integrado
└── workers/
    ├── telegram_bot.py      # bot de alertas via Telegram
    └── bestprice_bot.py
```

---

## O que está quebrado / incompleto HOJE

### 1. Alertas — conflito user_id nulo vs obrigatório
- `alerts.py:17` → `user_id=None` (auth pendente)
- `models.py:130` → `nullable=False` (banco rejeita)
- **Decisão necessária:** auth real (Clerk/JWT) OU alertas anônimos com `nullable=True`
- **Solução rápida adotada:** tornar `nullable=True` no modelo + aceitar `telegram_id` opcional no payload

### 2. Frontend anuncia mais do que o backend entrega
- `page.tsx:47` → "7 lojas ao vivo"
- `page.tsx:97` → "Mercado Livre, Amazon, Shopee e mais"
- Providers reais ativos com credenciais: 0 (todos bloqueados por API)
- **Ação:** atualizar copy do frontend OU ativar providers com dados reais

### 3. Endpoints faltantes no router
- Modelos prontos no banco: `Favorite`, `PriceHistory`, `Analytics`, `AffiliateClick`
- Endpoints inexistentes: `/favorites`, `/products/{id}/history`, `/clicks`, `/analytics`
- Páginas do frontend existem mas estão vazias: `dashboard/`, `favorites/`, `alerts/`

### 4. Testes insuficientes
- Só health + validação de query
- Falta: busca com mock de provider, CRUD alertas, cache hit/miss, ranking determinístico

### 5. Ambiente local desalinhado
- `requirements.txt` declara pytest mas não está instalado no venv ativo
- **Fix:** `pip install -r requirements.txt` no venv correto

---

## Pipeline de vídeo automático (Wan2.1)

- **Modelo:** Wan2.1-T2V-14B (75GB, text-to-video)
- **Localização:** `/home/alessandro/wan2/models/Wan2.1-T2V-14B-Diffusers/`
- **Venv:** `/home/alessandro/wan2/venv/`
- **Pipeline:** `/home/alessandro/wan2/pipeline.py`
- **Fluxo:** busca oferta na API → gera prompt → Wan2.1 gera vídeo → edge-tts narra → ffmpeg combina → posta no Telegram
- **GPU:** RTX 4090 24GB (bfloat16 + cpu offload)
- **Saída:** `/home/alessandro/wan2/videos/`
- **Dependências:** `diffusers 0.33+`, `imageio`, `edge-tts`, `torch` (no venv wan2)
- **Status:** modelo baixado, pipeline escrito, pendente teste de geração real

---

## Próximos passos prioritários

1. **Corrigir alertas** → `nullable=True` em `PriceAlert.user_id` + aceitar `telegram_id` no payload
2. **Corrigir frontend** → ajustar copy para refletir providers reais disponíveis
3. **Adicionar endpoints** → `/favorites`, `/products/{id}/history`, `/clicks`
4. **Fechar ambiente dev** → instalar pytest no venv do backend
5. **Testar pipeline Wan2.1** → rodar `pipeline.py` com 1 produto, checar geração de vídeo
6. **Desbloquear providers** → aguardar/solicitar credenciais Shopee, AliExpress, Lomadee

---

## Variáveis de ambiente importantes (ver `.env`)

- `DATABASE_URL` — Neon PostgreSQL
- `REDIS_URL` — Upstash
- `MERCADOLIVRE_APP_ID` / `MERCADOLIVRE_SECRET`
- `AMAZON_PARTNER_TAG=aletubegames-20` (sem access key ainda)
- `LOMADEE_SOURCE_ID` (sem API key ainda)
- `TELEGRAM_BOT_TOKEN`

---

_Atualizado: 2026-05-13_
