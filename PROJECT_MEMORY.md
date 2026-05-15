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
| Frontend      | https://bestpricetoday.vercel.app (Next.js 14, Vercel)                    |
| Backend       | https://alessandro2090-bestpricetoday-api.hf.space (FastAPI, HuggingFace) |
| Banco         | Neon PostgreSQL (free tier) — string no `.env`                            |
| Cache         | Upstash Redis (free tier) — string no `.env`                              |
| Repo          | https://github.com/aletubegames/bestpricetoday                            |

---

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy async + Pydantic v2
- **Frontend:** Next.js 14 + TypeScript + inline styles (sem Tailwind classes)
- **Camada de integração:** `backend/app/integrations/` — clientes independentes por marketplace
- **Deploy backend:** workflow GitHub Actions sincroniza `backend/app/` → HF Space
- **Deploy frontend:** `vercel --prod --yes` (não auto-deploy — fazer manualmente)
- **Testes:** pytest + pytest-asyncio — 35+ testes passando

---

## Arquitetura do backend

```
backend/app/
├── main.py                          # FastAPI app + lifespan (cron de conversão)
├── api/v1/
│   ├── router.py
│   └── endpoints/
│       ├── search.py                # GET/POST /search + trending + debug/aliexpress
│       ├── alerts.py
│       ├── favorites.py
│       ├── products.py
│       ├── auth.py                  # OAuth ML + /auth/ml/status + /auth/ml/refresh
│       └── admin.py                 # Dashboard admin completo (requer X-Admin-Key header)
├── core/{config,cache,logging}.py   # logging tem SanitizingFilter (redacta tokens)
├── db/session.py
├── models/models.py                 # inclui ClickEvent, ConversionEvent, MLToken
├── schemas/schemas.py
├── integrations/
│   ├── base.py
│   ├── aliexpress/client.py         # AliExpressSigner TOP+GOP + AliExpressClient
│   ├── shopee/client.py             # ShopeeSigner + ShopeeClient (GraphQL)
│   └── conversion_tracker.py       # polling AliExpress + Lomadee orders
├── services/
│   ├── search.py
│   ├── ml_token_service.py          # ← NOVO: ML token store + auto-refresh
│   ├── ranking/engine.py
│   └── providers/
│       ├── aliexpress.py            # usa integrations/aliexpress
│       ├── shopee.py
│       ├── mercadolivre.py          # usa ml_token_service.get_token() do banco
│       ├── amazon.py
│       ├── lomadee.py
│       ├── kabum.py                 # implementado, não ativo
│       └── awin.py                  # implementado, não ativo
└── workers/
    ├── bestprice_bot.py             # Telegram bot
    └── conversion_cron.py           # polling horário de conversões
```

---

## Providers — estado real (2026-05-15)

| Provider      | Status prod | Detalhe |
|---------------|-------------|---------|
| **AliExpress**| ✅ Funciona | Retorna produtos com filtro relevância + fallback sem tracking_id se 402 |
| **Lomadee**   | ✅ Funciona | Source ID: `6ff2699e-ceaa-4fad-a58a-8b91f885485f` |
| **Mercado Livre** | ❌ 403 | App não aprovado no Programa de Afiliados ML. OAuth token ✅ salvo no banco. |
| **Shopee**    | ❌ Invalid Signature | Secret errado — precisa ser do portal affiliate.shopee.com.br |
| **Amazon**    | ⚠️ sem ACCESS_KEY | Associate tag: `aletubegames-20` configurado, falta ACCESS_KEY |
| KaBuM / Awin | ⏸️ pendente | Código pronto, sem credenciais |

---

## AliExpress — algoritmo de assinatura (CONFIRMADO E VALIDADO)

Protocolo TOP:
```
msg  = "".join(f"{k}{v}" for k, v in sorted(all_params.items()))
sign = HMAC-SHA256(key=app_secret, msg=msg).hexdigest().upper()
```
Protocolo GOP:
```
msg  = api_path + "".join(f"{k}{v}" for k, v in sorted(params.items()))
sign = HMAC-SHA256(key=app_secret, msg=msg).hexdigest().upper()
```

**Bug corrigido (2026-05-15):** ALIEXPRESS_TRACKING_ID inválido no HF → 402.
Fix: `search()` faz retry sem tracking_id quando recebe 402.

**Filtro de relevância:**
- `ACCESSORY_KEYWORDS`: capas, películas, mouse pads, bolsa manga — filtrados
- `_filter_relevant()`: numérico exato (4070 ≠ 4060), min 1 token texto em comum
- Fallback: produtos > R$50 quando filtro zera tudo

---

## Mercado Livre — token e OAuth

**OAuth implementado e funcional:**
- Callback: `GET /api/v1/auth/ml/callback?code=...`
- Salva tokens no banco (`ml_tokens` table) via `ml_token_service.py`
- Auto-refresh: 10min antes de expirar, salva NOVO par (refresh_token é single-use)
- Status: `GET /api/v1/auth/ml/status` — mostra estado sem expor valores
- Renovação manual: `POST /api/v1/auth/ml/refresh`

**Para gerar novo OAuth:**
```
https://auth.mercadolivre.com.br/authorization?response_type=code
  &client_id=2661096739949809
  &redirect_uri=https://bestpricetoday.vercel.app/auth/callback
```
Logar com conta principal (user_id=6727655) — não colaborador.

**Busca bloqueada (403):**
`/sites/MLB/search` bloqueado para apps não aprovados no Programa de Afiliados.
Não é problema de token — é política da plataforma. Precisa aprovar o app.

---

## Shopee — diagnóstico

APP_ID=18308041054, SECRET presente mas **errado**.
O `SHOPEE_SECRET` no `.env` é do portal Open Platform (vendedores).
A Affiliate API precisa do secret de: https://affiliate.shopee.com.br → My Tools → Open API
O código está correto — problema é credencial errada.

---

## Admin Dashboard (`/admin`)

**Acesso:** `https://bestpricetoday.vercel.app/admin`
**Auth:** header `X-Admin-Key: ADMIN_MANAGER_KEY` (configurar no HF Space secrets)

**Endpoints backend (`/api/v1/admin/`):**
- `POST /clicks` — registra clique (sem auth — chamado automaticamente)
- `GET /overview` — métricas + cliques por provider
- `GET /analytics` — série temporal por dia
- `GET /marketplaces` — performance por marketplace
- `GET /traffic` — fontes de tráfego
- `GET /conversions` — lista paginada
- `POST /conversions/poll` — força polling AliExpress + Lomadee
- `POST /webhooks/mercadolivre` — recebe notificações ML
- `GET /integrations/status` — status real de todas as plataformas
- `GET /products/top` — top produtos por cliques
- `GET /report` — relatório completo

**Webhook ML para registrar no portal:**
```
POST https://alessandro2090-bestpricetoday-api.hf.space/api/v1/admin/webhooks/mercadolivre
```

**Features do dashboard:**
- Filtros: plataforma + período (hoje/7d/30d)
- KPI cards, funil conversão, gráfico temporal, tabela comparativa
- Status integrações (tempo real via API)
- Export CSV
- Top 10 produtos expandíveis

---

## Segurança implementada (2026-05-15)

- `SanitizingFilter` no logger — redacta `Bearer xxx`, `access_token=xxx`, tokens `APP-`
- OAuth callback não exibe tokens em HTML (estava como textarea — CORRIGIDO)
- `admin_key` vai em header `X-Admin-Key`, não em query string
- Security headers em todas as respostas: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, etc.
- Tokens ML nunca logados — só `[token redacted]`
- `ml_tokens` no banco com `expires_at` — sem tokens em `.env` em produção

---

## Frontend — features implementadas

**OfferCard premium:**
- Logo SVG de cada marketplace (inline, sem deps externas)
- Score IA: anel SVG circular animado + label "Ótimo/Bom/Fraco"
- Mini sparkline de tendência de preço (7 pontos)
- Badges dinâmicos (máx 3): 🔥 Quente, ⭐ Melhor Preço, ↓ Queda, ⚠️ Inflado, 🚚 Frete, 💰 Cashback, 🏷️ Cupom
- Hover: glow neon + translateY(-2px)
- Botão ⊕ para comparar (máx 3)

**Comparador lado a lado:**
- Barra flutuante no rodapé com selecionados
- Modal com destaque ✓ MENOR PREÇO

**Provider status pills:**
- Só mostra providers com `returned_count > 0`
- Shopee/ML/Amazon/erros ficam invisíveis ao usuário quando sem resultado

**Click tracking:** POST `/admin/clicks` fire-and-forget em cada "Ver oferta"
**UTM:** `utm_source=bestpricetoday&utm_medium=affiliate&utm_content={provider}`
**Skeleton:** shimmer animado estilo Netflix

**Footer:** Termos de Uso | Política de Privacidade | Contato | Admin

---

## TikTok Developer Portal

**Status:** App em review (`This version of BestPriceToday is in review`)

**Arquivos de verificação em `frontend/public/`:**
- `tiktokXjVhFhEDGo79Czy1rcORT0chwwzKFGeN.txt` → `/`
- `terms/tiktokVrNQ8yzd58acU8Fnwh6GvIUr5tFXjHCZ.txt` → `/terms/`
- `privacy/tiktoknM3Ajz7U5iXok5D3vus1iKIT4JQEzbhl.txt` → `/privacy/`

**Scopes solicitados:** `video.upload`, `user.info.basic`
**Produtos:** Login Kit + Content Posting API v2

**publisher.py** em `/home/alessandro/wan2/publisher.py`:
- `upload_tiktok()` implementado (Content Posting API v2)
- `tiktok_token.json` existe mas `access_token` vazio — preencher após aprovação

---

## Pipeline Wan2.1

- **Modelo:** `/home/alessandro/wan2/models/Wan2.1-T2V-14B-Diffusers/` (75GB)
- **Pipeline:** `/home/alessandro/wan2/video_engine.py`
- **Publisher:** `/home/alessandro/wan2/publisher.py` (Telegram ✅, YouTube ✅, TikTok ⏳)
- **GPU:** RTX 4090 24GB (bfloat16 + cpu offload)
- **Status:** modelo baixado, pipeline completo, **pendente teste real de geração**

---

## Conversão — loop clique→venda

**Rastreamento de cliques:** ✅ Funciona — `click_events` table via POST /admin/clicks
**Polling de orders:** ✅ Implementado em `conversion_tracker.py`
- AliExpress: `aliexpress.affiliate.order.list.by.index` a cada 1h
- Lomadee: `/report/commission` a cada 1h
- ML: webhook (registrar URL no portal ML)
**Deduplicação:** `external_order_id` — mesma order nunca duplica

---

## Pendências prioritárias

### Alta prioridade
1. **Shopee** → pegar App Secret de https://affiliate.shopee.com.br → My Tools → Open API
2. **ML Programa de Afiliados** → solicitar aprovação para desbloquear `/sites/MLB/search`
3. **ADMIN_MANAGER_KEY** → configurar nos secrets do HF Space
4. **Webhook ML** → registrar URL no ML Developer Portal → Notificações

### Média prioridade
5. **Favorite.user_id** → nullable=True + migration Alembic real
6. **alertas/page.tsx** → não carrega alertas do banco (sem useEffect de fetch)
7. **og-image.png / manifest.json / apple-touch-icon** → não existem em `public/`
8. **Migrations Alembic** → `versions/` vazio, schema via `create_all()` apenas
9. **Wan2.1** → testar pipeline completo com 1 produto real

### Baixa prioridade
10. `calculate_score()` em `engine.py` — código morto (nunca chamada)
11. `CuponomiaProvider` — implementado, não integrado
12. `datetime.utcnow` deprecated no Python 3.12 — warnings nos testes
13. Rate limiting — declarado mas não implementado
14. `docker-compose.yml` + Makefile — referenciam `telegram_bot` (correto: `bestprice_bot`)

---

## Variáveis de ambiente

### `backend/.env` (local) e HF Space secrets (produção)
```
DATABASE_URL               # Neon PostgreSQL
REDIS_URL                  # Upstash Redis
MERCADOLIVRE_APP_ID=2661096739949809
MERCADOLIVRE_SECRET
MERCADOLIVRE_ACCESS_TOKEN  # obsoleto — tokens agora no banco (ml_tokens)
MERCADOLIVRE_REFRESH_TOKEN # obsoleto — tokens agora no banco (ml_tokens)
AMAZON_PARTNER_TAG=aletubegames-20
LOMADEE_API_KEY
LOMADEE_SOURCE_ID=6ff2699e-ceaa-4fad-a58a-8b91f885485f
ALIEXPRESS_APP_KEY
ALIEXPRESS_APP_SECRET
ALIEXPRESS_TRACKING_ID     # ⚠️ inválido no HF → código faz fallback sem tracking
SHOPEE_APP_ID=18308041054
SHOPEE_SECRET              # ⚠️ errado — precisa ser do portal afiliado
TELEGRAM_BOT_TOKEN
ADMIN_MANAGER_KEY          # ⚠️ configurar no HF Space secrets
```

---

_Atualizado: 2026-05-15 (11h05 BRT)_
