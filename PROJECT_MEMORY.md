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
- **Camada de integração:** `backend/app/integrations/` — clientes independentes por marketplace
- **Deploy backend:** assets de deploy em `backend/deploy/` + workflow sincroniza `backend/app/` para o Space HF
- **Deploy frontend:** Vercel (auto-deploy no push)
- **Testes:** pytest + pytest-asyncio (backend) — 40 testes, todos passando

---

## Arquitetura do backend (atualizada)

```
backend/app/
├── main.py
├── api/v1/
│   ├── router.py
│   └── endpoints/{search,alerts,favorites,products,auth}.py
├── core/{config,cache,logging}.py
├── db/session.py
├── models/models.py
├── schemas/schemas.py
├── integrations/                    ← NOVO (2026-05-15)
│   ├── base.py                      # MarketplaceClient ABC + ProductResult + CouponResult
│   ├── aliexpress/client.py         # AliExpressSigner (TOP+GOP) + AliExpressClient
│   └── shopee/client.py             # ShopeeSigner + ShopeeClient (GraphQL)
├── services/
│   ├── search.py                    # orquestrador paralelo
│   ├── ranking/engine.py
│   └── providers/
│       ├── base.py
│       ├── aliexpress.py            # usa integrations/aliexpress
│       ├── shopee.py                # usa integrations/shopee
│       ├── mercadolivre.py
│       ├── amazon.py
│       ├── lomadee.py
│       ├── kabum.py                 # implementado, não integrado
│       └── awin.py                  # implementado, não integrado
└── workers/bestprice_bot.py         # Telegram bot
```

---

## Providers — estado real (2026-05-15)

| Provider      | Código | Orquestrador | Credenciais | Resultado em prod |
|---------------|--------|-------------|-------------|-------------------|
| **AliExpress**| ✅ refatorado | ✅ ativo | ✅ APP_KEY+SECRET ok | ✅ Funciona — retorna produtos (com filtro de relevância) |
| **Lomadee**   | ✅      | ✅ ativo | ✅ API_KEY ok | ✅ Funciona — retorna produtos |
| MercadoLivre  | ✅      | ✅ ativo | ⚠️ sem acesso à busca | ❌ 403 permanente em `/sites/MLB/search` — app não aprovado no programa de afiliados ML |
| Shopee        | ✅ refatorado | ✅ ativo | ⚠️ veja seção abaixo | ❌ 10020 Invalid Signature |
| Amazon        | ✅      | ✅ ativo | ❌ sem ACCESS_KEY | `not_configured` |
| KaBuM         | ✅      | ❌ comentado | sem token | pendente |
| Awin          | ✅      | ❌ comentado | sem token | pendente |

---

## Afiliados cadastrados

| Loja           | Status  | ID / Detalhe                              |
|----------------|---------|-------------------------------------------|
| Mercado Livre  | ✅ ativo | APP_ID: 2661096739949809                  |
| Amazon         | ✅ ativo | Associate tag: `aletubegames-20`          |
| Shopee         | ✅ ativo | APP_ID: 18308041054                       |
| AliExpress     | ✅ ativo | API aprovada + Advanced API liberada      |
| Lomadee        | ✅ ativo | Source ID: 6ff2699e-ceaa-4fad-...         |

---

## AliExpress — algoritmo de assinatura (CONFIRMADO E VALIDADO)

Protocolo TOP (Business APIs, método com ponto):
```
msg  = "".join(f"{k}{v}" for k, v in sorted(all_params.items()))
sign = HMAC-SHA256(key=app_secret, msg=msg).hexdigest().upper()
# app_secret é APENAS a chave do HMAC — não entra na string
# method (ex: aliexpress.affiliate.product.query) é parâmetro normal
```

Protocolo GOP (System APIs, path com barra):
```
msg  = api_path + "".join(f"{k}{v}" for k, v in sorted(params.items()))
sign = HMAC-SHA256(key=app_secret, msg=msg).hexdigest().upper()
# api_path é prefixado (ex: /auth/token/create)
# 'method' NÃO é parâmetro nos GOP
```

Vetores de teste oficiais (app_secret='helloworld') — AMBOS PASSANDO:
- TOP → `F7F7926B67316C9D1E8E15F7E66940ED3059B1638C497D77973F30046EFB5BBB` ✅
- GOP → `35607762342831B6A417A0DED84B79C05FEFBF116969C48AD6DC00279A9F4D81` ✅

Endpoints implementados em `integrations/aliexpress/client.py`:
- `search()` → `aliexpress.affiliate.product.query` (TOP)
- `get_hot_products()` → `aliexpress.affiliate.hotproduct.query` (TOP)
- `get_product_detail()` → `aliexpress.affiliate.product.detail.get` (TOP)
- `get_affiliate_link()` → `aliexpress.affiliate.link.generate` (TOP) + fallback deep link
- `get_coupons()` → `aliexpress.affiliate.promotion.flash.get` (TOP)

---

## Shopee — problema de autenticação (INVESTIGADO 2026-05-15)

**Status:** API ativa no portal, APP_ID=18308041054, SECRET presente no `.env`.

**Problema:** endpoint retorna `error [10020]: Invalid Signature`.

**O que foi confirmado via testes:**
- Formato do header está correto: `SHA256 Credential={APP_ID},Timestamp={ts},Signature={sig}`
- Timestamp deve ser em **segundos** (milissegundos retorna "Request Expired")
- APP_ID é válido (formato diferente retorna "Invalid Credential" vs "Invalid Signature")
- Algoritmo testado sem sucesso: HMAC(secret, appid+ts), SHA256(appid+ts+secret),
  HMAC(appid, secret+ts), com path, com body hash, com milissegundos, uppercase, lowercase, etc.

**Hipótese mais provável:**
O `SHOPEE_SECRET` no `.env` é o segredo do painel **Open Platform** (API de vendedores),
não o segredo da **Affiliate API** (painel de afiliados). São portais diferentes:
- Vendedor: https://open.shopee.com (partner_key para operações de loja)
- Afiliado:  https://affiliate.shopee.com.br (secret específico para GraphQL afiliado)

**Ação necessária:**
Logar em https://affiliate.shopee.com.br → My Tools → Open API → copiar o
**App Secret** específico do portal de afiliados e atualizar `SHOPEE_SECRET` no `.env`.

O código de autenticação (`integrations/shopee/client.py`) está correto —
o problema é a credencial errada, não o algoritmo.

---

## Mercado Livre — diagnóstico completo (2026-05-15)

**`/sites/MLB/search` está permanentemente bloqueado para apps não aprovados.**

Não é problema de token expirado. É uma mudança de política do ML (aconteceu ~2024/2025).
Todos os apps de terceiros recebem 403 `forbidden` nesse endpoint,
independente de token, user-agent ou parâmetros.

Confirmado programaticamente (2026-05-15):
- `client_credentials` ainda funciona e gera token válido para o app
- Token gerado: `APP_USR-2661096739949809-...` (user_id=6727655, nickname=ALESSANDRO SOUZA45)
- Com esse token, `/users/me` e `/sites/MLB/categories` funcionam
- `/sites/MLB/search` → 403 com qualquer combinação de parâmetros/headers

**O que ainda funciona com client_credentials:**
- `GET /users/me` — info da conta
- `GET /sites/MLB/categories` — lista de categorias
- `GET /users/{id}/items/search` — itens do próprio vendedor

**O que está bloqueado (403):**
- `GET /sites/MLB/search?q=...` — busca pública de produtos
- `GET /items/{id}` — detalhe de produto por ID

**Como desbloquear:**
O Mercado Livre tem um **Programa de Afiliados** separado:
https://www.mercadolivre.com.br/ajuda/programa-afiliados  
Apps aprovados no programa recebem acesso ao endpoint de busca.
O app atual (`APP_ID=2661096739949809`) ainda não tem essa aprovação.

**Ação necessária:**
1. Solicitar aprovação do app no **Programa de Parceiros/Afiliados** do ML
2. Enquanto não aprovado: depender de AliExpress + Shopee + Lomadee para os resultados
3. O provider ML pode ser desativado no orquestrador até a aprovação para não poluir o status com erros

**Não existe workaround técnico** — a API está restrita por política, não por configuração.

---

## Testes (2026-05-15)

**40/40 passando** — `pytest backend/tests/ -v`

Cobertura:
- `test_api.py` — 7 testes: health, search validação, alertas, cache
- `test_integrations.py` — 28 testes: signer TOP+GOP com vetores oficiais, parsing, filtros, Shopee, ProductResult
- `test_providers.py` — 2 testes: filtro de acessórios AliExpress, Lomadee parsing
- `test_ranking.py` — 3 testes: ranking, fake discount detection

---

## Busca ao vivo — resultado real (2026-05-15)

**`iphone 16 pro`**: AliExpress retorna 3 ofertas (películas — filtro precisa de "protetor" na lista)
**`rtx 4070`**: Lomadee retorna 1 PC Gamer com RTX 4070 por R$10.966

Problemas identificados:
- `ACCESSORY_KEYWORDS` do AliExpress não cobre "protetor de tela", "cobertura" → passa acessórios
- ML retorna 401 (token expirado, era 403 antes)

---

## O que está quebrado / pendente HOJE

### Alta prioridade
1. **Shopee Invalid Signature** → pegar o App Secret correto do portal de afiliados (não Open Platform)
2. **Mercado Livre 401** → renovar access_token (expirou); implementar refresh automático com REFRESH_TOKEN
3. **AliExpress filtra mal** → adicionar ao `ACCESSORY_KEYWORDS`: "protetor", "protetor de tela", "cobertura", "vidro temperado", "tempered", "glass"
4. **Favorite.user_id nullable=False** → endpoint `/favorites` quebra; precisa de migration
5. **`docker-compose.yml` + Makefile** → `dev-bot` e serviço `telegram_bot` referenciam módulo inexistente (`telegram_bot` vs `bestprice_bot`)

### Média prioridade
6. **Sem rate limiting** — `RATE_LIMIT_PER_MINUTE=30` declarado mas não implementado
7. **OAuth callback expõe tokens em HTML** — `auth/ml/callback` retorna access_token em textarea
8. **alertas/page.tsx** não carrega alertas existentes do banco (sem useEffect de fetch)
9. **og-image.png / manifest.json / apple-touch-icon** — referenciados no metadata mas não existem em `public/`
10. **`migrations/versions/` vazio** — Alembic nunca gerou migrations reais; todo schema via `create_all()`

### Baixa prioridade
11. `calculate_score()` em `engine.py` — código morto com lógica errada (nunca chamada)
12. `CuponomiaProvider` — implementado, não integrado em lugar nenhum
13. `datetime.utcnow` deprecated no Python 3.12 — warnings nos testes
14. `next-pwa@5.6.0` incompatível com Next.js 14 App Router

---

## Pipeline de vídeo automático (Wan2.1)

- **Modelo:** Wan2.1-T2V-14B (75GB, text-to-video)
- **Localização:** `/home/alessandro/wan2/models/Wan2.1-T2V-14B-Diffusers/`
- **Venv:** `/home/alessandro/wan2/venv/`
- **Pipeline:** `/home/alessandro/wan2/pipeline.py`
- **Fluxo:** busca oferta na API → gera prompt → Wan2.1 gera vídeo → edge-tts narra → ffmpeg combina → posta no Telegram
- **GPU:** RTX 4090 24GB (bfloat16 + cpu offload)
- **Saída:** `/home/alessandro/wan2/videos/`
- **Status:** modelo baixado, pipeline escrito, pendente teste de geração real

---

## Próximos passos prioritários

1. **Shopee** → pegar App Secret correto do portal afiliado e testar
2. **ML token** → renovar `MERCADOLIVRE_ACCESS_TOKEN` ou implementar refresh automático
3. **AliExpress keywords** → adicionar "protetor", "cobertura", "tempered", "vidro"
4. **Favorite bug** → `nullable=True` + migration Alembic
5. **docker-compose/Makefile** → corrigir nome do módulo do bot
6. **Wan2.1** → testar pipeline completo com 1 produto real

---

## Variáveis de ambiente (.env)

- `DATABASE_URL` — Neon PostgreSQL
- `REDIS_URL` — Upstash Redis
- `MERCADOLIVRE_APP_ID=2661096739949809` / `MERCADOLIVRE_SECRET` / `MERCADOLIVRE_ACCESS_TOKEN` (⚠️ expirado)
- `AMAZON_PARTNER_TAG=aletubegames-20` (sem ACCESS_KEY ainda)
- `LOMADEE_API_KEY` / `LOMADEE_SOURCE_ID=6ff2699e-ceaa-4fad-a58a-8b91f885485f`
- `ALIEXPRESS_APP_KEY` / `ALIEXPRESS_APP_SECRET` / `ALIEXPRESS_TRACKING_ID`
- `SHOPEE_APP_ID=18308041054` / `SHOPEE_SECRET` (⚠️ provavelmente credencial errada — ver seção Shopee)
- `TELEGRAM_BOT_TOKEN`

## Fonte da verdade dos `.env`

- **Backend local / Docker:** `backend/.env`
- **Frontend local:** `frontend/.env.local`
- **Hugging Face Space:** secrets/variables do Space HF (não `hf_deploy/.env`)

---

_Atualizado: 2026-05-15_
