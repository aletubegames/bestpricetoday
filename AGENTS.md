# BestPriceToday — Regras do Projeto

## Banco de Dados (2026-09-29 — MIGRADO DO NEON PARA LOCAL)
- **Postgres 18 local no alaserver** (`127.0.0.1:5432`), DB `bestpricetoday`, role `bestpricetoday` (senha no `.env` DATABASE_URL e em `~/.pgpass`)
- Neon suspenso por quota excedida em 27/set — `.env` antigo salvo em `/home/alessandro/backend/.env.bak-neon-20260929` (URL Neon lá pra eventual import de dados históricos após reset de quota)
- **Alembic migrations são diffs, não schema completo** — `initial_schema` só faz drops. Em DB novo: NÃO rodar `alembic upgrade` (falha). O schema é criado por `init_db()` (create_all) no startup do backend; depois `alembic stamp head`
- Novo usuário sempre `is_admin=false` — promover admin via SQL: `UPDATE users SET is_admin=true WHERE email='...'`
- Tokens OAuth (ml_tokens, youtube_accounts, facebook_accounts, instagram_accounts, tiktok_accounts) ficaram no Neon — re-autenticados em 30/set (exceto TikTok)
- **ML OAuth redirect_uri**: o app ML (`2661096739949`) ainda tem `https://bestpricetoday.vercel.app/auth/callback` registrado no devportal (deploy morto, mas ML aceita e devolve o code na URL). `ML_REDIRECT_URI` no `.env` aponta pra essa URI — NÃO remover sem antes atualizar o cadastro no devportal ML pro alaserver. Auth ML exige conta principal (user_id=6727655)
- **Backup diário**: cron 4h `pg_dump` → `/home/alessandro/backups/bestpricetoday-YYYYMMDD.sql.gz` (retenção 14 dias)

## Deploy
- **SEMPRE que corrigir um arquivo, subir para o alaserver (192.168.15.45) imediatamente**
- SSH: `ssh alessandro@192.168.15.45` (só acessível via rede local, não 4G/5G)
- Backend: `/home/alessandro/backend/`
- Frontend: `/home/alessandro/frontend/`
- Reiniciar backend: `sudo systemctl restart bestprice-backend`
- Reiniciar frontend: `sudo systemctl restart bestprice-frontend`
- Rebuild frontend: `cd /home/alessandro/frontend && npx next build` depois reiniciar

## URLs
- **PUBLIC_SITE_URL**: `https://bestpricetoday.alaserver.com.br` (porta 443 padrão via Cloudflare Tunnel)
- **INTERNAL_API_URL**: `https://api.alaserver.com.br` (porta 443 padrão via Cloudflare Tunnel)
- Cloudflare Tunnel (cloudflared) faz proxy: edge Cloudflare → localhost:3000 (frontend) / localhost:8000 (API)
- Porta 8443 funciona como backup externo (nginx direto + port forwarding roteador). A porta 9443 era o backup antigo mas a Vivo bloqueia inbound desde 2026-08-05.
- /etc/hosts no servidor redireciona api/bestpricetoday → 127.0.0.1 (evita loop pelo Cloudflare)

## Nginx
- Porta 443: HTTPS (SSL) — rede local + Cloudflare Tunnel
- Porta 9443: HTTPS (SSL) — backup externo (port forwarding roteador)
- Porta 8443: HTTPS (SSL) — alternativa (port forwarding roteador)
- Porta 2053: HTTPS (SSL) — alternativa
- Porta 80: HTTP redirect para HTTPS
- **Erro 400 "plain HTTP request sent to HTTPS port"**: corrigir com `error_page 497`

## Cloudflare
- DNS gerenciado pelo Cloudflare (nameservers: leonidas.ns.cloudflare.com, tia.ns.cloudflare.com)
- Tunnel ID: 52eea050-68dc-4cf4-9c96-f114d501cc53
- Config: /etc/cloudflared/config.yml
- Serviço: `cloudflared` (systemd, habilitado no boot)
- SSL/TLS mode: Full
- Worker `bestpricetoday-facebook-proxy`: proxy do Facebook (não mexer)
- Worker `floral-dust-4710`: não usado (pode deletar)

## Serviços (systemd)
- `bestprice-backend` (uvicorn) — roda distributor loop, bot, alert_checker, conversion_cron, ml_refresh_cron
- `bestprice-frontend` (next-server)
- `cloudflared` — Cloudflare Tunnel (proxy porta 443)
- Serviços antigos user (bestprice-bot, channel-broadcaster, alert-checker) — DESABILITADOS

## Scrapers (NAO sao orfaos — manter rodando)
- `ml_scraper` — roda via cron 9h05 diario (`run_ml_scraper.sh`), usa Playwright/Chromium. Percorre 26 categorias do portal de afiliados — pode durar horas.
- `amazon_scraper` — roda via cron 3h diario (`run_amazon_scraper.sh`)
- `ml_coupon_scraper` — coleta cupons de afiliado ML via Portal do Afiliado (Playwright + cookies manuais), cron **23h diario** (à noite, evita colidir com ml_scraper das 9h que pode durar horas). Compartilha `.ml_chrome_profile.lock` com keeper/scraper/login — espera até `PROFILE_LOCK_WAIT_S` (600s) em vez de pular (bug histórico ago-out/2026: keeper `*/30` disparava no mesmo segundo das 23h, segurava o lock ~3s no HTTP keepalive e o scraper pulava TODA rodada — tabela `coupons` zerou). **ATENÇÃO (out/2026): ML encerrou a geração manual de códigos** — `/afiliados/coupons` redireciona para `/afiliados/hub` e a seção sumiu do portal (probe confirmou 0 refs a "cupom" no hub/campanhas). Novo modelo ML: cupom do vendedor embutido no link de afiliado (sem código). Scraper vai coletar 0 até ser reescrito pro novo fluxo — avaliar desativar o cron ou migrar `/cupons` do site.
- `ml_coupon_scraper --cleanup-only` — deleta cupons vencidos, cron 2h diario
- `ml_session_keeper` — mantém sessão ML viva renovando cookies, cron **a cada 30min** com `DISPLAY=:99 --headless=false` (janela real no Xvfb — fingerprint headless é detectável). Tri-estado no HTTP: `alive`/`expired`/`network_error`. Erro de rede (DNS/internet caiu) NÃO abre browser, NÃO marca expired, NÃO alerta (backoff curto 30min). Sessão expirada confirmada NÃO reabre browser se `EXPIRED_FILE` já existe (evita padrão de bot 288x/dia). Sucesso do browser só com prova real (≥1 página do portal carrega de verdade — URL contém `mercadolivre` e não é `about:blank`/`chrome-error://`); se nenhuma carregar, NÃO salva storage_state/cookies (evita snapshot degradado que mata a sessão). Guarda na injeção: só injeta storage_state se for mais novo que o cookie DB do perfil. Backoff de bot 2h após browser falhar. Pool de UAs Chrome 138+ com rotação aleatória. HTTP keepalive não reescreve cookies (evita corrupção). Retoma ciclo normal automaticamente quando login manual novo reescreve cookies/storage_state mais novo que `EXPIRED_FILE`.
- Processos Chromium/Playwright sao do ml_scraper / ml_coupon_scraper — NAO matar
- Se ml_scraper travar (rodando >24h), pode reiniciar com `cd /home/alessandro/backend && setsid bash run_ml_scraper.sh < /dev/null > /dev/null 2>&1 &`

## Sessão ML Afiliados (login + renovação)
- Login manual via VNC (porta 5900): `cd /home/alessandro/backend && DISPLAY=:99 venv/bin/python -m app.workers.ml_scraper --login`
- ML usa reCAPTCHA Enterprise v2 (desafio de imagem) — bloqueia login programático
- `ml_session_keeper` roda a cada 30min e renova cookies automaticamente enquanto sessão for válida
- **Tri-estado HTTP**: `alive` (200 sem login) / `expired` (redirect jms/login) / `network_error` (DNS/timeout — não confundir com sessão morta)
- **Backoff de bot 2h** após browser falhar (não abre browser 288x/dia — era detectado como bot)
- **Backoff de rede 30min** após erro de DNS/internet (não é sessão morta — não abre browser, não alerta)
- **Parar browser quando expired**: se `EXPIRED_FILE` existe, keeper não reabre browser (só HTTP check + alerta Telegram a cada 6h). Retoma quando login manual novo faz cookies/storage_state mais novos que `EXPIRED_FILE`.
- **Sucesso do browser só com prova real**: ≥1 página do portal carrega (URL contém `mercadolivre`, não é `about:blank`/`chrome-error://`). Se nenhuma carregar (rede), NÃO salva storage_state/cookies (snapshot degradado mata a sessão).
- **Guarda na injeção de cookies**: só injeta storage_state se for mais novo que o cookie DB do perfil (`Default/Cookies`).
- **Dedup de alertas**: `ml_scraper` e `ml_coupon_scraper` suprimem alerta "LOGIN FALHOU"/"Cookies expirados" se `EXPIRED_FILE` é recente (<12h) — keeper já alertou pelo mesmo incidente.
- Pool de User-Agents Chrome 138+ com rotação aleatória (UA fixo/desatualizado era detectado)
- HTTP keepalive não reescreve cookies (evita corrupção de sessão)
- Quando sessão expira (~7-30 dias), só login manual via VNC renova
- Timestamp da última renovação OK: `.ml_session_last_ok`
- Backoff após falha de bot: `.ml_session_browser_backoff` (2h)
- Backoff após erro de rede: `.ml_session_network_backoff` (30min)
- Cookies: `.ml_cookies.json` + storage state: `.ml_storage_state.json`
- Chromium de login manual (tem `--login` ou `login_profile` nos args) NÃO é morto pelo session_keeper

## Token OAuth ML (API — roda no alaserver 192.168.15.45)
- Tokens na tabela `ml_tokens` (Neon), NÃO no `.env`
- **NÃO confundir** com sessão de afiliados (cookies Playwright / VNC / `ml_session_keeper`)
- **Bug histórico (11 semanas):** cron logava "renovado com sucesso" sem chamar a API
  (get_token devolvia token antigo entre 30–60min). Logs: 186 falsos vs 63 reais.
- **Fix:** só `force_refresh()` + `asyncio.Lock` (refresh single-use).
  Sucesso só se expiry pular (~360min). Nunca logar sucesso com 44/59min.
- Cron 15min: health live `/users/me` → se 401/403 ou <60min → force_refresh real
- Se falhar de verdade: Telegram alert (cooldown 6h) + arquivo `.ml_oauth_alert_sent`
- Reauth: `https://api.alaserver.com.br/api/v1/auth/ml/authorize`
- Endpoints: `GET /auth/ml/status`, `POST /auth/ml/refresh`, `GET /admin/integrations/status`

## Deduplicação e stats (2026-09-13)
- `ml_scraper.save_single_product`: dedup por `ml_code` (MLB/MLBU) — meli.la muda a cada coleta, dedup por affiliate_url NUNCA funciona
- `POST /admin/clicks`: exige X-Admin-Key (era aberto)
- Stats do admin (`overview`, `marketplaces`, `traffic`, `analytics`, `conversions/summary`) filtram UAs de bot via `_real_clicks_cond()` — distributor_* no `source` pode ser clique real de usuário, NÃO filtrar por source
- ML earnings no admin vêm de `affiliate_metrics_snapshots` (overview.ml_metrics) — ML não tem API de ordens, Amazon também não
- Backup pré-dedup: tabela `affiliate_products_bak_20260913` no Neon

## Cupons ML (modelo novo — desde 05/out/2026)
- **Modelo antigo MORTO**: ML descontinuou cupom de afiliado com código gerável (ALETUBE*). `/afiliados/coupons` redireciona pro hub — os seletores `#coupons-tabs-tab-*` não existem mais.
- **Fonte nova**: página de cupons do consumidor `https://www.mercadolivre.com.br/cupons` (~2200 cupons). Lista completa em `/cupons/filter?all=true&page=N` (30/página, ~74 páginas). Requer sessão logada (mesmos cookies do keeper).
- **Scraper é HTTP puro** (httpx + `.ml_cookies.json`, SEM Chromium/perfil — não usa `.ml_chrome_profile.lock`). Dados no `<script id="__NORDIC_RENDERING_CTX__">` (`_n.ctx.r={...}`, parse com `raw_decode` após o primeiro `{`).
- Estrutura: `appProps.pageProps.filteredCouponsData.coupons` (UI) + `tracking.view.eventData.coupons_list` (dados limpos: item_ids, collectors, discount_value, expiration_date ISO, pagination.total).
- `coupon_code` sintético: `MLC-{campaignId}` (não existe código digitável — cupom é ativado na conta via botão "Aplicar", que o scraper NUNCA clica).
- `product_url`: ACTIVE → `action.value`; INACTIVE → reconstruído `lista.mercadolivre.com.br/_CustId_{collectors[0]}?coupon_campaign_id={id}`; fallback = primeiro item.
- `status.id`: ACTIVE/INACTIVE é por conta (ativado na nossa conta), NÃO validade — todos são `is_active=True` no banco.
- Produtos amostra: `item_ids` (MLB) + `items[]` (imagem/título); preço enriquecido via `api.mercadolibre.com/items?ids=` (20/batch, token OAuth da tabela ml_tokens) quando token disponível.
- "Conferir"/lista de produtos cai em CAPTCHA wall quando acessado por bot — extração nunca navega pra lá, só guarda a URL (funciona pra usuário real).
- Cookies em `.ml_cookies.json` — login manual via VNC (reCAPTCHA bloqueia login programático)
- Cupons vencidos: DELETAR (não só desativar)
- Cupons que SOMEM da listagem sem vencer: `deactivate_missing_ml_coupons` desativa (is_active=False) — só roda após coleta COMPLETA (flag `completed` do scrape; coleta parcial não desativa nada)
- Unique constraint `(provider, coupon_code)` na tabela coupons (index `uq_coupons_provider_code`) — upsert filtra provider e purga duplicatas históricas
- `/api/v1/affiliate/coupons/products` deduplica por `ml_code`/`product_url` (mesmo produto em vários cupons = 1 card no site); `/coupons/stores` conta distinct
- Enriquecimento `/items` do ML: app atual retorna 403 por item → desligado automaticamente (`cache["__disabled__"]`); `is_available` só vira False com status explícito != "active" (campo ausente NÃO marca indisponível)
- `conditions` guarda só condições reais — "Sem compra mínima"/"Sem limite" são ausência de condição e não entram no texto
- Frontend: `/cupons` — grid com filtros; cupom MLC-* mostra "ative na sua conta" (sem código pra copiar), CTA "Ver na loja"
- Parser BR: "." = milhar, "," = decimal (R$1.670 = 1670, R$630,33 = 630.33)

## Distributor
- Posta às 12h e 19h (janela de 2h de tolerância)
- Canais: telegram, facebook, instagram, youtube
- YouTube roda em background (asyncio.create_task) para não travar o loop
- Links sempre sem porta (https://bestpricetoday.alaserver.com.br/r/{code})

## Frontend

### Design system
- Cores principais definidas em `globals.css` via tokens CSS:
  - `--bg: #eeeef8` — fundo da página
  - `--s1: #ffffff` — superfície primária
  - `--s2: #f5f7ff` — superfície secundária
  - `--s3: #eef0ff` — superfície terciária
  - `--s4: #e4e8ff` — superfície quaternária
  - `--txt: #1a1a2e` — texto principal
  - `--muted: rgba(26,26,46,0.70)` — texto secundário
  - `--muted2: rgba(26,26,46,0.60)` — texto terciário
  - `--bd: #e0e0f0` — bordas
  - `--bdhov: rgba(100,80,255,0.25)` — borda hover
  - `--acc: #7c3aed` — roxo primário
  - `--acc2: #8b7cf8` — roxo secundário
  - `--grn: #00b894` — verde
  - `--org: #f97316` — laranja
  - `--ylw: #f59e0b` — amarelo
  - `--red: #e74c3c` — vermelho
- Logo: imagem `/logo-header.png` + texto "BestPrice" em `#820AD1` (Nubank blue) e "Today" em `#FF6200` (Itaú orange)

### Header
- Componente compartilhado em `src/components/layout/Header.tsx`
- Ícones via `lucide-react` (não emojis)
- Página atual destacada com gradiente roxo
- Área de clique dos botões: `8px 14px` mínimo
- Menu hambúrguer abaixo de 480px; ícones-only entre 480px e 680px
- Padding otimizado abaixo de 520px

### Responsividade
- Mobile-first com CSS Modules e container queries
- Grid de produtos varia por página: 6 colunas em `/produto/[query]` (>=1400px), 6 colunas em `/afiliados` (>=1600px), 5 colunas na classe global `.grid-products` (>=1800px)
- Páginas com muitos inline styles ainda precisam de refatoração futura (`admin`, `aletubegames`, `alertas`, `dashboard`, `perfil`) — baixa prioridade

### Build
- `npx next build` (gera estáticos e server)
- Após deploy: `sudo systemctl restart bestprice-frontend`
- Para enviar apenas arquivos alterados, usar `rsync` por pasta; nunca passar dois paths locais para um path remoto (pode apagar arquivos do servidor)

### Alterações recentes (2026-07-01)
- Logo padronizado no header, footer, login e registro
- Grid de produtos responsivo (varia por página: 6 colunas em `/produto/[query]` >=1400px, 6 colunas em `/afiliados` >=1600px, 5 colunas na classe global `.grid-products` >=1800px)
- Auditados e removidos CSS classes não usadas em várias páginas
- Header refatorado: ícones Lucide, estado ativo, botões maiores, padding otimizado abaixo de 520px
- Página `/cupons` alinhada à paleta do site
- Corrigidas quebras de responsividade em `/alertas`, `/privacy`, `/terms`, `/deletion-status`, `/dashboard`, `/perfil`, `/categoria/[cat]`, `/marca/[marca]`
- Dependências não usadas removidas do `package.json`
- `coupon_distributor.py` corrigido: timezone UTC, AsyncClient para imagens, cleanup de tmpdir, frases de utilidade ampliadas com fallback por substantivo, vídeo de teste validado
