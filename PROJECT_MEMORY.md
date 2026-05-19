# PROJECT_MEMORY.md — BestPriceToday

> Arquivo de referência rápida. Se você perdeu o contexto, comece aqui.

---

## Atualizações recentes (2026-05-18)

### 1) Integração TikTok

- **Backend:**
  - `backend/app/integrations/tiktok.py` — `TikTokClient`: OAuth2, troca de token, publicação via `PULL_FROM_URL`
  - `backend/app/api/v1/endpoints/tiktok.py` — endpoints: `GET /tiktok/auth`, `GET /tiktok/callback`, `POST /tiktok/publish`
  - `backend/app/api/v1/router.py` — rota `/tiktok` registrada
  - `backend/app/core/config.py` — `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- **Frontend:**
  - `frontend/src/components/TikTokPublisher.tsx` — modal IA: gera título/descrição/hashtags + botão publicar
  - `frontend/src/app/produto/[query]/ProductSearchClient.tsx` — botão TikTok em cada oferta
- **Verificação de domínio:** 7 arquivos `.txt` em `public/` + 2 em `public/privacy/` e `public/terms/` — todos 200 OK no Vercel
- **Credenciais HF Space:** `TIKTOK_CLIENT_KEY=awllka8qo05dhkri` + `TIKTOK_CLIENT_SECRET` configurados
- **Status:** `GET /tiktok/auth` funcionando, aguardando aprovação do app pelo TikTok
- **Redirect URI:** `https://bestpricetoday.vercel.app/api/v1/tiktok/callback`

### 2) Correções de bugs críticos (2026-05-17/18)

- `auto_share_to_channel()` — TypeError silenciado corrigido (`bestprice_bot.py`)
- `ConversionEvent.created_at` → `converted_at` (`admin.py:600`)
- `docker-compose.yml` + `Makefile` — `telegram_bot` → `bestprice_bot`
- `datetime.utcnow()` → `datetime.now(timezone.utc)` em 7 arquivos + testes
- `DateTime` → `DateTime(timezone=True)` em todos os models — corrige 500 no POST /alerts
- `calculate_score()` removida (código morto)
- `SECRET_KEY` e `ADMIN_MANAGER_KEY` regeneradas com valores seguros
- `INTERNAL_API_URL` adicionada ao `.env` (alert_checker usava localhost no HF)

### 3) Alembic migrations

- `backend/alembic/` inicializado com `env.py` async
- Migration inicial gerada: `bef783622397_initial_schema.py`
- Comando: `cd backend && PYTHONPATH=. alembic upgrade head`

### 4) Assets frontend

- `frontend/public/og-image.png` (1200×630) criado
- `frontend/public/apple-touch-icon.png` (180×180) criado
- `frontend/public/manifest.json` criado (PWA)
- `frontend/next.config.mjs` — `protocol: "https"` adicionado nos `remotePatterns`

### 5) sync_hf_deploy.sh expandido

- Agora sincroniza: endpoints, providers, core, models, services, ranking
- Antes sincronizava apenas `alerts.py`, `favorites.py`, `schemas.py`

### 6) Situação atual (2026-05-18 01h30 BRT)

- `health` ✅ | `search` ✅ | `POST /alerts` ✅ | Shopee ✅ | AliExpress ✅ (tracking pendente restart HF)
- Admin dashboard ✅ (ADMIN_MANAGER_KEY corrigida no HF)
- Bot Telegram ✅ `@BestPriceToday_bot`
- TikTok ⏳ aguardando aprovação do app
- 59/59 testes passando

---

## Atualizações recentes (2026-05-17)

### 1) Video API + ngrok (incidente 404 resolvido)

- Erro observado no admin: `Video API retornou 404: <!DOCTYPE html> ...`
- Causa raiz confirmada:
  - `http://localhost:8765/health` estava OK (API local online)
  - túnel público retornava página HTML do ngrok com `ERR_NGROK_3200` (endpoint offline)
- Ação aplicada:
  - criado serviço user-level: `~/.config/systemd/user/bestprice-ngrok.service`
  - serviço habilitado com `systemctl --user enable --now bestprice-ngrok.service`
  - validação: `https://sacrament-subduing-confined.ngrok-free.dev/health` retornando `{"ok": true}`
- Observação operacional:
  - para manter serviço user-level ativo mesmo sem login após reboot: `sudo loginctl enable-linger alessandro`

### 2) Fonte única de segredos (`backend/.env`)

- Decisão: `backend/.env` é a fonte da verdade para segredos.
- Ajustes:
  - `wan2/publisher.py` passou a carregar variáveis do arquivo `backend/.env`
  - `.env` local em `~/wan2` removido
  - variáveis adicionadas em `backend/.env` sem remover existentes:
    - `TELEGRAM_CHANNEL_ID`
    - `VIDEO_API_KEY`

### 3) Organização de artefatos de vídeo

- Cada execução agora cria diretório próprio em `~/wan2/videos` com padrão:
  - `YYYYMMDD_HHMMSS_<formato>/`
- Arquivos por execução (não limpa automaticamente):
  - áudio, base, imagem de produto, vídeo final
- Pipeline híbrido grava estágios em subpasta:
  - `stages/` com S1/S2/S3 + áudio

### 4) Prompts e narração (qualidade de campanha)

- Implementado normalizador de fala PT-BR no `content_strategy.py`:
  - regras para siglas/unidades técnicas (Wi-Fi, USB-C, GB, TB, mAh, Hz etc.)
- Templates de narração por canal:
  - `telegram`, `youtube`, `tiktok`, `multi`
- Idioma de prompts T2V/I2V:
  - padronização EN-only para estabilidade visual
  - modo determinístico com variação criativa controlada

### 5) Anti-repetição entre dias (scheduler)

- Problema identificado: repetição de vídeos em dias distintos por reinício de sequência + catálogo fixo.
- Correções aplicadas em `~/wan2/scheduler.py`:
  - histórico persistente (`historico`) de postagens
  - bloqueio de repetição por 72h para produto e título similar
  - rotação determinística diária da lista de produtos (seed por data)
  - fallback para produto alternativo quando oferta similar recente é detectada
- Correção complementar em `content_strategy.py`:
  - bucket criativo alterado para diário (mantém consistência no dia e varia entre dias)

### 6) Situação atual

- `video_api.py` local: online
- ngrok público: online com auto start user-level
- sintaxe Python validada nos arquivos alterados durante os ajustes do dia

---

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
- **Testes:** pytest + pytest-asyncio — **24 testes passando** (test_integrity.py:16 + test_api.py:8)

---

## Arquitetura do backend

```
backend/app/
├── main.py                          # FastAPI app + lifespan (workers: conversion cron, broadcaster, bot, alert checker)
├── api/v1/
│   ├── router.py
│   └── endpoints/
│       ├── search.py                # GET/POST /search + trending
│       ├── alerts.py                # CRUD alertas — owner_id obrigatório
│       ├── favorites.py             # CRUD favoritos — owner_id obrigatório
│       ├── products.py
│       ├── links.py                 # POST /links/create + GET /r/{code} (tracked redirect)
│       ├── auth.py                  # OAuth ML + /auth/ml/status + /auth/ml/refresh
│       └── admin.py                 # Dashboard admin completo (requer X-Admin-Key header)
├── core/{config,cache,logging}.py
├── db/session.py
├── models/models.py                 # ClickEvent, ConversionEvent, MLToken, ShortLink, PriceAlert, Favorite
├── schemas/schemas.py               # AlertCreate/FavoriteCreate exigem owner_id obrigatório
├── integrations/
│   ├── aliexpress/client.py
│   ├── shopee/client.py
│   └── conversion_tracker.py       # polling AliExpress + Lomadee + Shopee, sem valores hardcoded
├── services/
│   ├── search.py
│   ├── ml_token_service.py
│   ├── ranking/engine.py
│   └── providers/{aliexpress,shopee,mercadolivre,amazon,lomadee,kabum,awin}.py
└── workers/
    ├── bestprice_bot.py             # Telegram bot — /alertas funcional (sem "Em breve")
    ├── channel_broadcaster.py
    ├── conversion_cron.py           # polling horário de conversões
    └── alert_checker.py            # ← NOVO: verifica alertas a cada 30min, envia Telegram se preço caiu

backend/hf_deploy/                   # Deploy target HuggingFace Space (standalone)
├── app/api/v1/endpoints/alerts.py   # ← sincronizado via sync_hf_deploy.sh
├── app/api/v1/endpoints/favorites.py
├── app/schemas/schemas.py
└── ...                              # NÃO inclui admin.py nem links.py

backend/sync_hf_deploy.sh            # ← NOVO: copia alerts.py, favorites.py, schemas.py → hf_deploy
backend/scripts/migration_owner_id.py # ← NOVO: migration owner_id aplicada em produção
backend/tests/test_integrity.py      # ← NOVO: 16 testes estruturais
```

---

## Modelo de identidade — owner_id (BREAKING CHANGE 2026-05-16)

Alertas e favoritos usam `owner_id` obrigatório em vez de `telegram_id` opcional.

| Contexto         | Valor de owner_id                             |
|------------------|-----------------------------------------------|
| Browser          | `localStorage["bpt_anon_id"]` (gerado uma vez) |
| Telegram bot     | `str(update.effective_user.id)`               |

**Migration aplicada em produção:**
- Coluna `owner_id VARCHAR NOT NULL` adicionada em `alertas` e `favoritos`
- Dados migrados: `owner_id = telegram_id` onde existia, senão `migrated_{uuid}`
- `user_id` nas duas tabelas agora é nullable
- Índice criado: `ix_alertas_owner_id`, `ix_favoritos_owner_id`

**API — todos os endpoints exigem owner_id:**
- `GET /alerts?owner_id=...` — obrigatório (Query param)
- `DELETE /alerts/{id}?owner_id=...` — valida ownership antes de desativar
- `POST /alerts` body: `{query, target_price, owner_id}` — 422 sem owner_id ou com vazio
- Idem para /favorites

---

## Monetização — fluxo completo

```
Busca → Ranking → OfferCard → trackClick() → POST /admin/clicks
                            ↓
                     Link afiliado com UTM
                     (ou /r/{code} para links de vídeo)
                            ↓
                    302 → Site do marketplace
                            ↓
               Conversão registrada via:
               • Webhook ML (registrar URL no portal)
               • Polling horário AliExpress + Lomadee + Shopee
               → tabela conversion_events
               → dashboard admin mostra receita/comissão real
```

**Short links** (`/r/{code}`):
- Criado por `POST /api/v1/links/create` (sem auth — chamado pelo pipeline Wan2.1)
- Redirect registra ClickEvent antes do 302
- Estatísticas: `short_links.clicks` + `last_clicked_at`

---

## Providers — estado real (2026-05-16)

| Provider       | Status prod | Detalhe |
|----------------|-------------|----------|
| **AliExpress** | ✅ Funciona | Retry sem tracking_id quando 402 |
| **Lomadee**    | ✅ Funciona | Source ID: `6ff2699e-ceaa-4fad-a58a-8b91f885485f` |
| **Mercado Livre** | ❌ 403  | App não aprovado no Programa de Afiliados. OAuth ✅ no banco. |
| **Shopee**     | ❌ Invalid Signature | Secret errado — precisa do portal affiliate.shopee.com.br |
| **Amazon**     | ⚠️ sem ACCESS_KEY | Associate tag: `aletubegames-20` configurado |
| KaBuM / Awin   | ⏸️ pendente | Código pronto, sem credenciais |

---

## Admin Dashboard (`/admin`)

**Acesso:** `https://bestpricetoday.vercel.app/admin`
**Auth:** header `X-Admin-Key: ADMIN_MANAGER_KEY`
**Layout:** responsivo — funciona em mobile e desktop

**Endpoints backend (`/api/v1/admin/`):**
- `POST /clicks` — registra clique (sem auth)
- `GET /overview` — métricas gerais
- `GET /analytics` — série temporal
- `GET /marketplaces` — performance por marketplace
- `GET /traffic` — fontes de tráfego
- `GET /conversions` — lista paginada
- `POST /conversions/poll` — força polling afiliados
- `POST /webhooks/mercadolivre` — webhook ML
- `GET /integrations/status` — status real das plataformas
- `GET /products/top` — top produtos
- `GET /report` — relatório completo
- `POST /broadcast/telegram` — posta ofertas no canal

---

## Testes (`backend/tests/`)

```bash
cd backend
PYTHONPATH=. .venv312/bin/pytest tests/ -v
# 24/24 passando (2026-05-16)
```

**test_integrity.py** (16 testes estruturais):
1. Sem endpoint `/conversions/test` no código nem nas rotas registradas
2. Sem `commission_rate`/`commission_value` hardcoded em arquivos de produção
3. `conversion_tracker.py` usa dados reais (sem flat rate, sem `DEFAULT_COMMISSION`)
4. Ownership: todos endpoints de alerts/favorites retornam 422 sem `owner_id`
5. Frontend: nenhum arquivo fora de `lib/api.ts` declara fallback de URL
6. `hf_deploy` sincronizado com canônico (falha se `sync_hf_deploy.sh` não rodou)

**test_api.py** (8 testes):
- Health, validação de busca, mock de providers, schema de alertas, cache hit

---

## Frontend — centralizção da API URL

**Fonte única:** `frontend/src/lib/api.ts`
```typescript
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://alessandro2090-bestpricetoday-api.hf.space";
```

Todos os arquivos importam `{ API_BASE }` dali. Nenhum fallback inline ou `localhost` restante.

---

## Alertas de preço — fluxo completo

1. Usuário acessa `/alertas`, `bpt_anon_id` gerado e persistido em `localStorage`
2. `POST /api/v1/alerts` com `{query, target_price, owner_id: bpt_anon_id}`
3. `alert_checker.py` roda a cada 30min, busca alertas ativos sem `triggered_at`
4. Para cada alerta: busca preço atual via `/api/v1/search`
5. Se `preço_atual ≤ target_price`:
   - `owner_id` numérico → envia mensagem Telegram
   - `owner_id` bpt_anon → marca como processado (web push futuro)
   - `triggered_at = now`, `is_active = False`
6. Telegram bot `/alertas` mostra link do site + ID do usuário para vincular

---

## Pipeline Wan2.1

- **Modelo:** `/home/alessandro/wan2/models/Wan2.1-T2V-14B-Diffusers/` (75GB)
- **Publisher:** `/home/alessandro/wan2/publisher.py` — corrigido (sem duplicatas, TinyURL, link clicável)
- **GPU:** RTX 4090 24GB
- **Fluxo:** gera vídeo → encurta link → publica Telegram ✅ YouTube ✅ TikTok ⏳
- **YouTube links:** encurtados via TinyURL API para garantir clicabilidade na descrição

### Wan2.1 — Prompt Correto (2026-05-19)

**NÃO usar:** `masterpiece quality` (piora resultado — gera lixo e mutação)

**Usar:**
```
High-end product commercial video of the exact object from the reference image.
The object remains identical to the reference image.
No deformation.
No additional objects.
Clean background.
Slow cinematic orbital camera movement.
Professional studio lighting.
Soft reflections.
Realistic shadows.
Product centered.
Commercial advertising style.
Ultra detailed.
Stable geometry.
```

### Wan2.1 — Parâmetros Corretos
- **cfg:** 4-6 (CFG alto = mais lixo, mais mutação, mais frame ruim)
- **steps:** 20-30
- **motion_strength:** baixo

### O Segredo Real da Qualidade: A Imagem Inicial
A maioria usa print lixo, fundo ruim, JPEG comprimido. O correto:
1. PNG limpo
2. Fundo removido, produto centralizado
3. Sombra fake já pronta
4. **Upscale 4x ANTES do Wan2.1**

**Fluxo de pré-processamento:**
```
Produto real → Remove background → Upscale 4x → Sharpen leve → Wan2.1 motion → FFmpeg overlay
```

### Hack de Geração — Nunca Gerar Vídeo Longo
- Gerar apenas 3-5 segundos de IA (máximo)
- IA longa: destrói consistência, explode VRAM, gera mutação
- Expandir tudo no FFmpeg: slow motion, frame interpolation, camera shake, zoom digital, particles, light sweep

### TTS — Preferência de Qualidade
- **Fish Speech:** melhor naturalidade, mais emoção → **usar para escala**
- **GPT-SoVITS:** melhor clone de voz, mais pesado → usar para personagem/locutor fixo
- **Edge-TTS:** NÃO usar para produção (não serve para canal)
- Ordem: Fish Speech > Edge-TTS

### FFmpeg — O Que Torna Profissional
Não é o vídeo da IA — é o pós-processamento:
- sound design, glow, particles, motion blur, typography, transitions, SFX

Elementos FFmpeg que faltam implementar:
- easing, blur, vignette, glow, sharpen, grain cinematográfico

**Exemplo de filtro profissional:**
```bash
ffmpeg -i video.mp4 -i overlay.png -filter_complex "
[0:v]eq=contrast=1.08:saturation=1.15,
unsharp=5:5:1.0,
vignette=PI/5,
fps=60[v0];

[v0][1:v]overlay=0:0,
drawtext=text='R$ 99,90':
fontfile=/fonts/Montserrat-Bold.ttf:
fontsize=120:
fontcolor=yellow:
x=(w-text_w)/2:
y=1550
"
-c:v libx264 -crf 18 final.mp4
```

### Pipeline Completo AleTubeGames
```
Imagem Produto
→ Background Removal
→ Upscale
→ Template Visual
→ Wan2.1 I2V
→ Fish Speech
→ FFmpeg Motion Graphics
→ Auto Subtitle
→ Auto Upload
```

> **Insight principal:** A parte inteligente do sistema NÃO é a IA — é o pipeline, a consistência, a automação, a identidade visual fixa e a velocidade. Isso é o que diferencia produto profissional de demo de IA.

---

## Pendências prioritárias

### Alta prioridade
1. **Shopee secret** → pegar de https://affiliate.shopee.com.br → My Tools → Open API
2. **ML Programa de Afiliados** → solicitar aprovação para desbloquear `/sites/MLB/search`
3. **ADMIN_MANAGER_KEY** → configurar nos secrets do HF Space
4. **Webhook ML** → registrar URL no portal ML Developer → Notificações

### Média prioridade
5. **Migration Alembic real** → `versions/` vazio; schema via `create_all()` apenas
6. **og-image.png / manifest.json / apple-touch-icon** → ausentes em `public/`
7. **Wan2.1** → testar pipeline completo com 1 produto real
8. **Web push para alertas anônimos** → `bpt_anon_id` sem canal de entrega ainda

### Baixa prioridade
9. `calculate_score()` em `engine.py` — código morto
10. `CuponomiaProvider` — implementado, não integrado
11. `datetime.utcnow` deprecated → warnings nos testes (Python 3.12)
12. `docker-compose.yml` + Makefile — referenciam `telegram_bot` (correto: `bestprice_bot`)

---

## Variáveis de ambiente

### `backend/.env` (local) e HF Space secrets (produção)
```
DATABASE_URL               # Neon PostgreSQL
REDIS_URL                  # Upstash Redis
MERCADOLIVRE_APP_ID=2661096739949809
MERCADOLIVRE_SECRET
AMAZON_PARTNER_TAG=aletubegames-20
LOMADEE_API_KEY
LOMADEE_SOURCE_ID=6ff2699e-ceaa-4fad-a58a-8b91f885485f
ALIEXPRESS_APP_KEY
ALIEXPRESS_APP_SECRET
ALIEXPRESS_TRACKING_ID     # ⚠️ inválido no HF → fallback sem tracking
SHOPEE_APP_ID=18308041054
SHOPEE_SECRET              # ⚠️ errado — precisa do portal afiliado
TELEGRAM_BOT_TOKEN
ADMIN_MANAGER_KEY          # ⚠️ configurar no HF Space secrets
INTERNAL_API_URL           # URL interna para alert_checker.py buscar preços (default: localhost:8000)
ALERT_CHECK_INTERVAL       # Intervalo do alert_checker em segundos (default: 1800)
```

---

## Admin — Gerador de Vídeo IA (2026-05-16)

### Endpoint backend
- `POST /api/v1/admin/video/publish` — dispara `traffic_machine.py` como subprocess não-bloqueante
  - Body: `{ query, plataformas: ["telegram","youtube","tiktok"], formato }`
  - Retorna `{ job_id, pid, log }` imediatamente
- `GET /api/v1/admin/video/status/{job_id}` — retorna tail do log + flag `done`

### UI no admin (`VideoPublisher` component)
1. **Passo 1 — Produto:** botão Auto ou Top 10 cliques (carregados do dashboard)
2. **Passo 2 — Formato:** sugestão inteligente ao selecionar produto
   - Desconto ≥ 30% → Oferta Choque (TOP)
   - Preço ≥ R$1.500 → WAN2.1 Cinemático
   - ≥ 20 cliques → Viral TikTok
   - Marca conhecida → VS Comparativo
   - Categoria ampla → Top 3
   - Preço < R$100 → Última Chance
   - O formato TOP é selecionado automaticamente; mostra motivo da sugestão
3. **Passo 3 — Plataformas:** toggle Telegram / YouTube / TikTok
4. **Log em tempo real:** poll a cada 3s, mostra tail do stdout do processo

### `traffic_machine.py` atualizado
- Aceita `redes` no dict `decisao` (vindo do admin)
- Default anterior `["telegram", "youtube"]` mantido quando não especificado

---

## Broadcaster Telegram (2026-05-16)

### Problema corrigido
- Sempre enviava as mesmas ofertas porque não havia memória do que já foi postado
- `fetch_best_offer` sempre retornava top-1 do cache Redis

### Soleição
- **Deduplicado:** hash MD5 do `affiliate_url` salvo em `/tmp/broadcaster_dedup.json` por 24h
- **10 categorias** (smartphones, games, casa, audio, tv_video, tablets, cameras, periferico, wearables, informatica)
- **Sorteia N categorias diferentes** por rodada
- **Seleção ponderada por score** dentro de cada categoria — não deterministic

---

_Atualizado: 2026-05-16 (03h00 BRT)_

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

## Video API local (2026-05-16)

### Problema
O admin estava chamando `/admin/video/publish` no HF Space, que tentava rodar `traffic_machine.py` em `/root/wan2` (inexistente). O Wan2.1 e a GPU só existem na máquina local.

### Solução: `~/wan2/video_api.py`
Servidor FastAPI leve (porta 8765) que roda **localmente** e expõe:
- `POST /video/publish` — dispara `traffic_machine.py` como subprocess
- `GET /video/status/{job_id}` — retorna tail do log
- `GET /health` — verifica se está online

```bash
# Iniciar manualmente
cd ~/wan2 && python video_api.py

# Instalar como serviço systemd (persistência)
sudo cp ~/wan2/bestprice-video-api.service /etc/systemd/system/
sudo systemctl enable --now bestprice-video-api
```

### Fluxo admin → vídeo
```
Admin (browser)
  1. Tenta POST http://localhost:8765/video/publish (direto na máquina local)
  2. Se offline, fallback via HF Space que usa VIDEO_API_URL do .env
Video API local executa traffic_machine.py com os parâmetros
Admin faz poll GET /video/status/{job_id} a cada 3s, mostra log em tempo real
Admin mostra ✅ / ❌ online/offline da API local
```

### Variáveis de ambiente adicionadas
```
VIDEO_API_URL = http://localhost:8765   # URL da Video API (usada pelo HF Space como proxy)
VIDEO_API_KEY =                         # chave opcional (vazio = aceita tudo localmente)
VIDEO_API_PORT = 8765                   # porta da Video API
```

### publisher.py — bug corrigido
- `max(0, orig - preco)` falhava com `NoneType - float` quando a API retornava `original_price: null`
- Corrigido: todos os campos numéricos usam `float(offer.get(...) or 0)`

### Serviço de timer (scheduler existente)
- `bestprice-video.timer` roda a cada 2h24min via systemd (✅ ativo)
- Status: `active (waiting)` — próxima execução em ~15min após cada ciclo
- Log em `~/wan2/scheduler.log`

---

## Correções traffic_machine.py + torchvision (2026-05-16 noite)

### Bug 1 — `TypeError: register_post() got an unexpected keyword argument 'topic'`
- `traffic_machine.py` chamava `register_post(topic=..., format_name=..., score=...)` mas a assinatura em `content_strategy.py` é `register_post(titulo: str, formato: str)`
- **Fix em `~/wan2/traffic_machine.py`:** corrigido para `register_post(titulo=offer.get("titulo", ...), formato=format_name)`

### Bug 2 — `Could not import module 'UMT5EncoderModel'` (WAN2.1 falhava)
- **Causa raiz:** incompatibilidade `torch 2.12.0+cu130` + `torchvision 0.20.1+cu121` (cu121 é para torch ~2.5)
- `torchvision::nms` falhava no registro, cascateando e quebrando import do transformers/UMT5
- **Fix:** `pip install torchvision>=0.24.0 --index-url https://download.pytorch.org/whl/cu130` → instalado `0.27.0+cu130`
- WAN2.1 e UMT5EncoderModel carregam normalmente após fix

### Status wan2 repo
- `~/wan2` é local sem remote git
- Alterações em `traffic_machine.py`, `hybrid_pipeline.py`, `video_engine_v3.py` não versionadas remotamente

---

_Atualizado: 2026-05-16 (21h50 BRT)_
