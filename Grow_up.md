# Grow_up.md — Plano Realista para Romper a Bolha

> **Único KPI:** R$ de comissão **confirmada** entrando no bolso.
> **Base:** alaserver (192.168.15.45) + Cloudflare Tunnel. Nada de ngrok/Vercel
> como infra principal. Nada de projeção irreal — só o caminho escalável com o
> arsenal que já existe.

---

## 📊 Resumo executivo (atualizado 2026-07-01)

### ✅ Implementado (Fase 0, 1, 2 e 3.2 — SEO em escala)
| Área | Status | Detalhe |
|---|---|---|
| URLs consistentes | ✅ | `PUBLIC_SITE_URL` + `INTERNAL_API_URL` centralizados, ngrok removido, Cloudflare Tunnel ativo |
| Links Telegram | ✅ | Short links `/r/{code}` → 302 redirect funcionando (sem :9443) |
| Métricas ML | ✅ | Scraping diário do portal de afiliados → `affiliate_metrics_snapshots` |
| SSR SEO | ✅ | `/produto/[query]` server-rendered com JSON-LD `Product` + `AggregateOffer` |
| Sitemap honesto | ✅ | **95 URLs** com conteúdo real (4 estáticas + 10 categorias + 81 produtos) |
| Categorias | ✅ | 10 hubs `/categoria/[cat]` com SSR + JSON-LD `CollectionPage` |
| Analytics | ✅ | GA4 (`G-D2J769S99H`) + Microsoft Clarity (`xd51oaxppe`) ativos |
| Distribuição | ✅ | Orquestrador `distributor.py` 4x/dia (12h, 15h, 19h, 21h) em 4 canais (Telegram + Facebook + Instagram + YouTube) |
| Cupons ML | ✅ | `coupon_distributor.py` 2x/dia (12h, 19h) + vídeo XTTS para YouTube |
| IA legendas | ✅ | OpenRouter com fallback gracioso (postagem nunca falha) |
| Dashboard | ✅ | `/admin/distribute/stats` tracking por canal/post |
| Header compartilhado | ✅ | `src/components/layout/Header.tsx` com Lucide icons, logo padronizado e responsividade completa |
| Filtro de relevância | ✅ | Remove acessórios (capas, cases, joysticks, gift cards) de buscas de produtos principais |
| Filtro Lomadee | ✅ | Remove resultados irrelevantes (ex: Dorflex para "iphone") |
| **Amazon scraper** | ✅ | **1.066 produtos ativos** via Playwright + **cron 3am diário** (atualiza preços/estoque) |
| **Provider Amazon 3 modos** | ✅ | PA-API → scraper local → fallback search link (sempre rastreia comissão) |
| **Ranking com relevância** | ✅ | Boost por match do título + round-robin de providers (diversidade) |
| **Dashboard Afiliados** | ✅ | `/afiliados` com 5 providers (ML + Amazon + Shopee + AliExpress + Lomadee), grid 6 colunas, paginação múltiplos de 24 |
| **Histórico de Preços** | ✅ | Tabela `affiliate_price_history` + scrapers salvam snapshot diário (1 por dia/produto) + gráfico SVG no dashboard + página pública `/produto` e `/oferta` + disclaimer sobre período monitorado |
| **Lomadee DeepLink** | ✅ | Fallback Custom → deeplink manual com sourceId (não usa BrandPage que leva à homepage) |
| **Bing Webmaster** | ✅ | Site verificado + sitemap enviado |

### Catálogo atual
- **Amazon:** 1.066 produtos ativos (scraper via Playwright, 64 queries)
- **Mercado Livre:** 1.466 produtos ativos (scraper portal afiliados)
- **AliExpress:** 50 hot products (API ao vivo)
- **Shopee:** 48 hot products (API ao vivo, listType=2 Top performance)
- **Lomadee:** ~24 produtos (API ao vivo, catálogo sem search)
- **Queries válidas:** 81 (≥3 ofertas com preço real)

### ⬜ Pendente (ações do usuário)
| Item | Ação |
|---|---|
| **GATE: compra teste** | Comprar R$ 15-30 via link afiliado → aguardar 24-48h → scrape métricas |
| **Google Search Console** | Adicionar `https://bestpricetoday.alaserver.com.br` + enviar sitemap |
| **Redirect URIs** | Atualizar YouTube, Facebook, TikTok, Mercado Livre nos consoles de desenvolvedor (sem :9443) |
| ~~Criar App Meta novo~~ | ✅ FEITO — app Business `1555866299595457` (casos de uso: Pages + Instagram) |
| ~~Criar Página FB + IG Business~~ | ✅ FEITO — 3 páginas conectadas: Bestpricetoday + Achados Shoppee + Achados Shopee |
| ~~OAuth Facebook~~ | ✅ FEITO — 3 páginas + 1 Instagram (@aletubegames) salvos no banco, post de teste OK |
| ~~OAuth TikTok/YouTube~~ | ✅ YouTube FEITO — postando Shorts automaticamente. TikTok pendente |
| ~~Bing Webmaster~~ | ✅ FEITO — verificado via XML, sitemap enviado |

### 📈 Métricas atuais
- **Posts no Telegram:** 31 (cliques: 6)
- **Posts no Facebook:** 7 em 3 páginas (cliques: 7) — Bestpricetoday + Achados Shoppee + Achados Shopee
- **Posts no Instagram:** 6 (@aletubegames, cliques: 1)
- **Posts no YouTube:** 6 (cliques: 1)
- **Páginas indexáveis:** 95 (sitemap) — 4 estáticas + 10 categorias + 81 produtos
- **Queries com produtos:** 81 (airfryers + iPhones + Galaxy + notebooks + TVs + PS5 + etc)
- **Catálogo total:** 2.532 produtos ativos (1.466 ML + 1.066 Amazon) + AliExpress/Shopee/Lomadee ao vivo
- **Dashboard afiliados:** 5 providers funcionando (ML 1466, Amazon 1066, Shopee 48, Lomadee 24, AliExpress 50)
- **Frequência de postagem:**
  - Distributor principal: 4x/dia (12h, 15h, 19h, 21h) em 4 canais
  - Coupon distributor: 2x/dia (12h, 19h) em 4 canais
  - Total: até 6 janelas/dia combinando ofertas + cupons

---

## Realidade verificada em 2026-07-01 (atualizada pós-implementação)

### O que está NO AR (verificado por curl + SSH)
- ✅ **Frontend HTTPS** `https://bestpricetoday.alaserver.com.br/` —
  HTTP 200, título "BestPriceToday — Menor Preço do Brasil", ISR ativo.
  Serviço `bestprice-frontend.service` active running (next-server v14.2.3).
  Cloudflare Tunnel (porta 443 padrão) + nginx backup na porta 9443.
- ✅ **API HTTPS** `https://api.alaserver.com.br/` — nginx + uvicorn,
  `/health` 200. Serviço `bestprice-backend.service` active running.
  Cloudflare Tunnel (porta 443 padrão) + nginx backup na porta 9443.
- ✅ Backend na máquina alaserver (`192.168.15.45:8000`), DB Neon, Redis Upstash.
- ✅ nginx com vhosts: `bestprice-frontend-ssl` (:443+:9443+:8443+:2053),
  `bestprice-api-ssl` (:443+:9443+:8443+:2053), `bestprice-redirect` (:80→HTTPS).
  Cert Let's Encrypt `alaserver.com.br` válido. `error_page 497` redireciona
  HTTP→HTTPS na porta 9443 (resolve erro 400 no 4G/5G).
- ✅ **Cloudflare Tunnel ativo** — `cloudflared` service (systemd, enabled no boot).
  Tunnel ID: `52eea050-68dc-4cf4-9c96-f114d501cc53`.
  DNS gerenciado pelo Cloudflare (nameservers: leonidas + tia.ns.cloudflare.com).
  SSL/TLS mode: Full. Universal SSL ativo (Google Trust Services).
  Worker `bestpricetoday-facebook-proxy` intacto (não mexer).
- ✅ **ngrok removido** — todos os workers agora usam `https://api.alaserver.com.br` (sem porta).
- ✅ 3 serviços systemd: `bestprice-frontend.service`, `bestprice-backend.service`, `cloudflared.service`.
- ✅ Arsenal completo: OAuth ML, Shopee, AliExpress, TikTok, YouTube, Facebook,
  Instagram, Telegram + OpenRouter LLM + GPU vídeo local (via ngrok — só vídeo).
- ✅ **GA4 ativo** (ID: `G-D2J769S99H`) — tráfego e conversões rastreados.
- ✅ **Microsoft Clarity ativo** (ID: `xd51oaxppe`) — heatmaps + session replay.
- ✅ **SSR ativo** em `/produto/[query]` — Google vê preços sem JS (ISR 30min).
- ✅ **Sitemap com 95 URLs** (4 estáticas + 10 categorias + 81 produtos com ofertas reais).
- ✅ **10 páginas de categoria** (`/categoria/[cat]`) com SSR + JSON-LD.
- ✅ **Amazon scraper ativo** (1.084 produtos: iPhones, Galaxy, notebooks, TVs, PS5, etc).
- ✅ **Cron diário 3am** — scraper Amazon atualiza preços e remove produtos fora de estoque.
- ⚠️ **Páginas de marca** (`/marca/[slug]`) existem mas têm 0 ofertas — removidas do sitemap.
- ✅ **Distributor automático** postando em 4 canais 4x/dia (12h, 15h, 19h, 21h).
- ✅ **Coupon distributor** postando cupons ML em 4 canais 2x/dia (12h, 19h) com vídeo XTTS para YouTube.
- ✅ **3 páginas Facebook** ativas: Bestpricetoday + Achados Shoppee + Achados Shopee.
- ✅ **Header compartilhado** com Lucide icons, logo padronizado e responsividade mobile-first (CSS Modules).
- ✅ **Instagram @aletubegames** ativo (Business account vinculada).
- ✅ **Scraping de métricas ML** rodando diariamente (portal de afiliados).

### ⏰ Crons ativos no servidor
| Horário | Script | O que faz |
|---------|--------|-----------|
| **3am** | `run_amazon_scraper.sh` | Desativa produtos Amazon antigos, roda scraper (64 queries), reativa encontrados |
| **4am** | `run_ml_scraper.sh` | Scraper portal afiliados ML + métricas |

> **Nota:** `conversion_cron` e `ml_refresh_cron` foram removidos do crontab
> (2026-06-28) — ambos rodam como background tasks no `bestprice-backend.service`
> (main.py). Os cron jobs não tinham `__main__` e nunca executaram nada (logs 0 bytes).
- ✅ **Filtro de acessórios** ativo no ranking (remove capas/cases de buscas de produtos).
- ✅ **Filtro de relevância Lomadee** ativo (remove resultados sem token principal).

### O que estava QUEBRADO e FOI CORRIGIDO

> **NOTA (2026-06-29):** Todas as URLs migraram de `:9443` para porta 443 padrão
> via Cloudflare Tunnel. As referências a `:9443` no histórico abaixo são registros
> da época — a porta 9443 continua como backup mas a URL oficial é sem porta.

1. ~~**Nada escuta na porta 443.**~~ → **CORRIGIDO (2026-06-28)**: Nextcloud
   removido. Nginx agora escuta em 443 (rede local) e 9443 (externo).
   Operadora bloqueia 80/443 inbound, então 9443 é a porta oficial.
2. ~~**Links do Telegram quebrados.**~~ → **CORRIGIDO**: `PUBLIC_SITE_URL`
   centralizado em `config.py`, todas as URLs hardcoded substituídas em
   12+ arquivos (backend + frontend). Short links gerados com `:9443`.
3. ~~**Workers Telegram → ngrok.**~~ → **CORRIGIDO**: `INTERNAL_API_URL`
   trocado de ngrok para `https://api.alaserver.com.br:9443` em todos os
   workers. Zero dependência de ngrok.
4. ~~**Loop de conversão ML invisível.**~~ → **CORRIGIDO via scraping**:
   `scrape_metrics_summary()` no `ml_scraper.py` coleta métricas do portal
   de afiliados ML diariamente. Tabela `affiliate_metrics_snapshots` no banco.
5. ~~**SEO inexistente em escala.**~~ → **CORRIGIDO**: SSR em `/produto/[query]`
   com JSON-LD `Product` + `AggregateOffer`. Sitemap com **95 URLs com conteúdo
   real** (antes 314, tentou 5.046 mas 99.7% estariam vazias). 10 páginas de
   categoria com JSON-LD. Amazon scraper com 1.084 produtos. Páginas de marca
   existem mas aguardam catálogo.
6. ~~**Busca retornando acessórios irrelevantes.**~~ → **CORRIGIDO**: Filtro
   de acessórios no ranking engine (remove capas/cases de buscas por
   smartphones/notebooks/etc). Filtro de relevância no Lomadee (exige token
   principal no título). Filtro AND no ML local fallback (todos os tokens
   devem aparecer, não apenas um).
7. **`bestpricetoday.com.br`** (domínio próprio real) — ainda não configurado.
   Futuro: apontar para 9443 (Nextcloud já removido, porta 443 livre na LAN).
8. ~~**Redirect URIs OAuth apontando para o frontend (404 no callback).**~~ →
   **CORRIGIDO (2026-06-27)**: Todos os redirect URIs (Facebook, YouTube,
   TikTok) apontavam para `bestpricetoday.alaserver.com.br:9443/aletube/...`
   (host do frontend Next.js, sem `/api/v1`). O callback OAuth caía no
   Next.js que devolvia 404 — token nunca era salvo. Corrigido para
   `api.alaserver.com.br:9443/api/v1/aletube/callback/...` (host da API).
   Escopo `pages_manage_posts` adicionado ao fluxo OAuth Facebook.
   `post_to_facebook()` implementado no distributor (Graph API photos/feed).
   Loop automático agora posta em `["telegram", "facebook", "instagram", "youtube"]`.
9. ~~**Erro 400 "plain HTTP request sent to HTTPS port" no celular 4G/5G.**~~ →
   **CORRIGIDO (2026-06-28)**: Operadora bloqueia portas 80/443 inbound.
   Acesso externo só funciona na porta 9443. Quando o Telegram abria
   `http://...:9443` (sem https), o nginx devolvia 400. Corrigido com
   `error_page 497 =301 https://$host:$server_port$request_uri` no nginx.
   Redirect da porta 80 simplificado para `https://...:9443`.
10. ~~**Links do Telegram sem `https://` no rodapé.**~~ → **CORRIGIDO
    (2026-06-28)**: Rodapé da legenda usava `.replace('https://', '')`
    deixando o domínio como texto puro não-clicável. Corrigido para
    `[BestPriceToday](https://bestpricetoday.alaserver.com.br:9443)`.
11. ~~**Instagram com link na legenda (risco de banimento).**~~ → **CORRIGIDO
    (2026-06-28)**: Link estava sendo colocado direto na legenda do Instagram.
    Revertido para legenda sem link + comentário fixado com o link.
    Permissão `instagram_manage_comments` adicionada ao escopo OAuth.
    Reautenticação feita — comentários com link agora funcionam.
12. ~~**Processos órfãos no servidor.**~~ → **CORRIGIDO (2026-06-28)**:
    2 processos `ml_scraper` + 18 Chromium/Playwright travados desde Jun 26.
    Mortos. ml_scraper reiniciado (roda via cron 4h, NÃO é órfão).
13. ~~**Cron jobs redundantes.**~~ → **CORRIGIDO (2026-06-28)**:
    `conversion_cron` e `ml_refresh_cron` removidos do crontab — ambos
    rodam como background tasks no main.py. Cron jobs não tinham `__main__`
    e logs estavam vazios (0 bytes).
14. ~~**.env com regressões.**~~ → **CORRIGIDO (2026-06-28)**:
    `ALLOWED_ORIGINS` duplicado e sem `:9443`. Redirect URIs (YouTube,
    Facebook, TikTok) sem `:9443`. `ML_AFFILIATE_EMAIL` com espaço à
    esquerda. Todos corrigidos.
15. ~~**Resíduos no servidor.**~~ → **CORRIGIDO (2026-06-28)**: Removidos:
    apache2 fantasma (masked), services antigos (.service, install_bot.sh,
    sync_*.sh), .env.bak antigos, SQLite antigos (bestprice.db,
    bestpricetoday.db), .vercel, hf_deploy, .venv antigo (294MB liberados),
    nginx configs antigos. Frontend `output: standalone` removido (warning).

### Conclusão honesta (pós-implementação)
O sistema estava **quase todo no ar** com 6 defeitos que zeravam a receita.
**Todos os 6 foram corrigidos** em 2026-06-26/27:
- Links do Telegram agora abrem o site (com `:9443`)
- Workers não dependem mais de ngrok
- Comissão ML rastreada via scraping do portal de afiliados
- SEO implementado em escala (SSR + sitemap 5.046 URLs + 32 marcas + 10 categorias + JSON-LD)
- Analytics ativos (GA4 + Microsoft Clarity)
- Distribuição automática no Telegram (5x/dia com IA + filtros de qualidade)
- Filtros de relevância (acessórios não aparecem em buscas de produtos principais)

**Pendência do GATE da Fase 0:** falta a compra teste (0.4c) para confirmar
`total_commission > 0` no dashboard. O scraping já funciona, só precisa de
uma compra real via link de afiliado + aguardar 24-48h.

**Problema conhecido (qualidade de catálogo):** nenhum provider tem iPhones
reais — AliExpress/Shopee retornam apenas capas, ML não tem iPhones na tabela
de afiliados, Lomadee não tem eletrônicos. Solução: rodar scraper ML com
queries de eletrônicos ou configurar Amazon Associates.

---

## Plano em 4 Fases — realista e ordenada

```
Fase 0: Ligar a luz (pré-requisito, ~2 dias) ← BLOQUEANTE
   ↓  (gate: site no ar + 1 comissão confirmada)
Fase 1: SEO realista (semana 1-2)
Fase 2: Distribuição com o arsenal (semana 2-3, paralelo)
   ↓  (gate: tráfego real + cliques rastreados por fonte)
Fase 3: Escalar o que converte (mês 2+)
```

Cada fase tem **critério de saída verificável**. Não pular.

---

## FASE 0 — Ligar a luz (BLOQUEANTE, ~1 dia)

**Sem isso, tudo o resto é perda de tempo.** Meta: frontend na 443 (URL limpa),
links do Telegram funcionando, workers no alaserver, 1 comissão ML confirmada.

> O frontend **já está no ar** em `https://bestpricetoday.alaserver.com.br/`
> (Cloudflare Tunnel, porta 443 padrão) e backup em `https://...:9443/`.
> A API em `https://api.alaserver.com.br/` (active). Então a Fase 0 está
> completa — URL limpa sem :9443, Cloudflare Tunnel ativo.

### 0.1 Frontend na porta 443 (URL limpa, sem :9443) ✅ CONCLUÍDO (2026-06-29)
- [x] **Cloudflare Tunnel instalado e ativo** — `cloudflared` service (systemd).
      Tunnel ID: `52eea050-68dc-4cf4-9c96-f114d501cc53`.
      DNS no Cloudflare (nameservers: leonidas + tia.ns.cloudflare.com).
      SSL/TLS mode: Full. Universal SSL (Google Trust Services).
- [x] **Porta 9443 mantida como backup** — nginx direto + port forwarding roteador.
      Portas 443, 8443, 2053 também escutando no nginx (alternativas).
- [x] **robots.txt** — Cloudflare robots.txt management desativado (usa o nosso).
- [x] Todas as URLs no código atualizadas para sem `:9443`:
      `api.ts`, `config.py`, `auth.py`, `next.config.mjs`, `robots.txt`, `.env`.
- [x] **PENDÊNCIA:** Atualizar redirect URIs nos painéis:
      - YouTube Studio → `https://bestpricetoday.alaserver.com.br/aletube/callback/youtube`
      - Facebook Developers → `https://api.alaserver.com.br/api/v1/aletube/callback/facebook`
      - TikTok Developers → `https://api.alaserver.com.br/api/v1/tiktok/callback`
      - Mercado Livre Apps → `https://bestpricetoday.alaserver.com.br/auth/callback`
      (As URLs antigas com :9443 ainda funcionam via backup, mas as novas sem porta
      devem ser registradas para OAuth funcionar pelo Cloudflare Tunnel.)

### 0.2 Migrar workers Telegram de ngrok → alaserver ✅ CONCLUÍDO (2026-06-26)
- [x] `backend/.env`: `INTERNAL_API_URL=https://api.alaserver.com.br`
- [x] `config.py`: default alterado de ngrok para `https://api.alaserver.com.br`
- [x] `bestprice_bot.py:119`: removido fallback ngrok, usa `settings.INTERNAL_API_URL`
- [x] `alert_checker.py:30`: removido fallback, usa `settings.INTERNAL_API_URL`
- [x] `aletube.py:49`: removido fallback ngrok hardcoded, usa `settings.INTERNAL_API_URL`
- [x] Backend reiniciado e ativo. Busca testada: retorna ofertas normalmente.
- [x] **Critério:** bot e broadcaster não dependem mais de ngrok.

### 0.3 Corrigir links nas mensagens do Telegram ✅ CONCLUÍDO (2026-06-26)
- [x] `PUBLIC_SITE_URL` adicionado ao `config.py` (default: `https://bestpricetoday.alaserver.com.br:9443`)
- [x] `PUBLIC_SITE_URL` adicionado ao `.env` em produção
- [x] `bestprice_bot.py:169,180`: hardcoded → `settings.PUBLIC_SITE_URL`
- [x] `channel_broadcaster.py:182`: hardcoded → `settings.PUBLIC_SITE_URL`
- [x] `links.py:73,74,99,133`: short links e redirects → `settings.PUBLIC_SITE_URL`
- [x] `admin.py:1201`: short link URL → `settings.PUBLIC_SITE_URL`
- [x] `aletube.py:144,166,168,216,820`: todas URLs hardcoded → `settings.PUBLIC_SITE_URL`
- [x] `tiktok.py:215,394`: short links → `settings.PUBLIC_SITE_URL`
- [x] `affiliate.py:491`: short link → `settings.PUBLIC_SITE_URL`
- [x] `facebook.py:188`: deletion status URL → `settings.PUBLIC_SITE_URL`
- [x] `auth.py:36`: ML REDIRECT_URI → `:9443` (com env override)
- [x] CORS: adicionado `https://bestpricetoday.alaserver.com.br:9443` aos allowed origins
- [x] **Teste:** short link criado retorna `https://bestpricetoday.alaserver.com.br:9443/r/{code}`
- [x] **Teste:** redirect 302 funciona → `https://meli.la/test123`
- [x] **Teste:** frontend na 9443 retorna HTTP 200
- [x] Redeploy backend + reiniciar serviços systemd — feito.
- [x] **Frontend atualizado:** `NEXT_PUBLIC_SITE_URL` + `SITE_BASE` em `lib/api.ts`,
      8 arquivos do frontend atualizados (layout, sitemap, privacy, terms, produto, redirects).
- [x] **Critério:** clicar no link de uma oferta postada no Telegram abre o
      site/produto funcionando (sem timeout). Short link `:9443/r/{code}` → 302 redirect.

### 0.4 Fechar o loop de conversão ML — CORREÇÃO FUNDAMENTAL

> **Verificado na doc oficial do ML (2026-06-26):**
> - Webhook `orders_v2` notifica o **vendedor**, NÃO o afiliado. O ML **não
>   envia webhooks de orders para afiliados**. O handler em `admin.py:744-830`
>   está arquiteturalmente errado — nunca vai disparar para um afiliado.
> - **NÃO existe API pública de relatório de afiliados ML.** As métricas
>   (ganhos, vendas, cliques, conversões) estão só no Portal do Afiliado →
>   Métricas, atualizam a cada 24h, sem endpoint de API.
> - O `ml_scraper.py` **já faz login no portal com Playwright + cookies**
>   (`ml_scraper.py:380-421`). A infra para coletar métricas **já existe**.

**Abordagem correta: scraping de Métricas + rastreamento de cliques (híbrida)**

- [x] **0.4a Scraping de Métricas do Portal:** ✅ CONCLUÍDO (2026-06-26)
      - Função `scrape_metrics_summary()` adicionada ao `ml_scraper.py`
      - Navega para `https://www.mercadolivre.com.br/afiliados/dashboard?filter_time_range=...#hub`
      - Coleta: cliques, ordens, compradores, ganho estimado, vendas brutas, parceria ML/vendedor
      - Nova tabela `affiliate_metrics_snapshots` (migration `b2c3d4e5f6a7`)
      - Função `save_metrics_snapshot()` salva no banco
      - Integrado ao scraper diário (roda após coletar produtos, no cron das 4h)
      - Endpoints admin: `GET /admin/metrics/latest`, `GET /admin/metrics/snapshots`, `POST /admin/metrics/scrape-now`
      - Testado: snapshot salvo com sucesso (cliques=0, ordens=0, ganho=R$0, período=25/06)
      - URL de dashboard confirmada pelo usuário + estrutura validada via scraping real
- [ ] **0.4a2 (futuro):** estender para coletar tabela detalhada "Produtos vendidos"
      (por produto: unidades, vendas, ganhos) — precisa de mais navegação no portal
- [ ] **0.4a3 (futuro):** coletar métricas por etiqueta/canal para atribuição
- [ ] **0.4a (referência histórica):** adicionar `scrape_metrics()` ao
      `ml_scraper.py` — navega para a seção Métricas do portal de afiliados e
      coleta: ganhos confirmados, vendas aprovadas, produtos vendidos, cliques,
      conversões (por etiqueta/período). Salvar em `conversion_events` com
      `provider=mercadolivre` e `commission_value` real. Rodar diariamente.
- [ ] **0.4b Rastreamento de cliques (já funciona):** os short links `/r/{code}`
      já rastreiam cliques em tempo real — útil para otimização. A comissão real
      confirmada só vem do scraping de métricas (24h).
- [ ] **0.4c Teste de compra real:** comprar 1 produto barato (R$ 15-30) pelo
      link `matt_word` no site no ar. Aguardar 24-48h (portal atualiza). Rodar
      `scrape_metrics()`. Confirmar `total_commission > 0` no `/admin/overview`.
- [ ] **0.4d Limpar código morto:** o webhook handler `admin.py:744-830` e
      `ML_WEBHOOK_SECRET` no config podem ser removidos ou marcados como
      deprecated (não funcionam para afiliados). NÃO remover sem confirmar
      que não quebra nada.
- [ ] **GATE DA FASE 0:** site no ar + bot funcionando + `total_commission > 0`
      (após scraping de métricas pós-compra teste). Se falhar, debugar aqui.

> Esta é a única fase que é gate absoluto. Depois dela o sistema já é um
> negócio mínimo viável que fatura (pouco, mas fatura e mede).

---

## FASE 1 — SEO realista (semana 1-2)

**Objetivo:** tráfego orgânico de graça, crescendo do que indexa. Não começa
com 50k páginas — começa com algumas centenas reais e cresce conforme o Google
indexa. Meta realista mês 1: 200 páginas indexadas, 50-200 visits/dia.

### 1.1 SSR das ofertas em `/produto/[query]` ✅ CONCLUÍDO (2026-06-26)
- [x] Mover fetch de ofertas de `ProductSearchClient` (client) para `page.tsx`
      (server) com `revalidate=1800` (ISR 30min).
- [x] Renderizar top 10 ofertas no HTML (preço, loja, badge).
- [x] `ProductSearchClient` recebe `initialOffers` como props (sem loading inicial).
- [x] JSON-LD `Product` + `AggregateOffer` + `Offer` (não `SearchResultsPage` genérico).
- [x] Botão "↻ Atualizar" para refetch manual no client.
- [x] **Critério:** `curl /produto/iphone-16-pro` retorna HTML com 59 preços
      (R$ 19.55, R$ 21.25, etc.), "MENOR PREÇO" badge, nomes de lojas
      (AliExpress, Shopee, Mercado Livre) — tudo sem JS.
- [x] JSON-LD: `AggregateOffer` com `lowPrice`, `highPrice`, `offerCount`, 10 `Offer` entries.

### 1.2 Sitemap dinâmico realista ✅ CONCLUÍDO (2026-06-26)
- [x] Endpoint `GET /api/v1/search/sitemap-queries`: retorna 300 queries
      (75 trending reais do banco + 225 curadoria manual por nicho de alta comissão).
- [x] Curadoria cobre: eletrônicos, celulares, casa, beleza, games, moda,
      ferramentas, esportes, pet, bebê, áudio/tech, eletroportáteis, decoração,
      jardim, auto, saúde, livros, categorias Shopee, acessórios tech.
- [x] `sitemap.ts` consome endpoint com ISR 6h (revalidate=21600).
- [x] Fallback: queries estáticas básicas se backend indisponível.
- [x] **Critério:** `sitemap.xml` com **5.046 URLs reais** (6.759 queries curadas + 32 marcas + 10 categorias + 4 estáticas).
- [x] Crescer conforme indexa (300 → 5k → 10k) — **5.046 URLs atingidas**.

### 1.3 Páginas de categoria ✅ CONCLUÍDO (2026-06-26)
- [x] `/categoria/[cat]` com 10 categorias: celular, games, casa, beleza,
      ferramentas, eletronicos, moda, esportes, pet, bebe.
- [x] `src/lib/categories.ts`: config central com nome, descrição, icon,
      queries populares e categorias relacionadas.
- [x] SSR com ISR 1h (revalidate=3600) + `generateStaticParams` (pré-gera todas).
- [x] Cada categoria mostra top 4 queries com 6 ofertas cada (grid de cards).
- [x] JSON-LD `CollectionPage` + `ItemList` + `ListItem` (rich snippets).
- [x] Link juice interno: "Buscas populares" (todas queries → /produto/[query])
      + "Categorias relacionadas" (links entre hubs).
- [x] Home page: seção "Compre por categoria" com links para todas.
- [x] 404 para categorias inexistentes.
- [x] Adicionadas ao sitemap (priority 0.9, daily).
- [x] **Testado:** `/categoria/games` → HTTP 200, 41 preços no HTML, JSON-LD CollectionPage.

### 1.4 Monitoramento ✅ CONCLUÍDO (2026-06-26)
- [x] Google Search Console: arquivo de verificação `googleb02205f407cb8f06.html`
      confirmado no ar (HTTP 200).
- [x] `robots.txt` atualizado: `Sitemap: https://bestpricetoday.alaserver.com.br:9443/sitemap.xml`
      (antes apontava para Vercel).
- [x] **GA4 ATIVO** (ID: `G-D2J769S99H`) — código no `layout.tsx` via `next/script`,
      carregando em todas as páginas. Confirmado no HTML: `googletagmanager.com/gtag/js?id=G-D2J769S99H`.
      Objetivos: Aumentar vendas + Entender tráfego da Web.
- [x] **Microsoft Clarity ATIVO** (ID: `xd51oaxppe`) — heatmaps + session replay,
      carregando em todas as páginas. Confirmado no HTML: `clarity.ms/tag/xd51oaxppe`.
- [ ] **Ação manual do usuário:** reenviar sitemap no Google Search Console
      (https://search.google.com/search-console → selecionar propriedade →
      Sitemaps → enviar `https://bestpricetoday.alaserver.com.br:9443/sitemap.xml`).
- [ ] **Meta mês 1:** 200 páginas indexadas, 50 visits/dia orgânico.
- [ ] **Meta mês 3:** 2.000 indexadas, 500 visits/dia.

---

## FASE 2 — Distribuição com o arsenal (semana 2-3, paralelo à 1)

**Objetivo:** a mesma oferta vira conteúdo em **vários canais ao mesmo tempo**,
automático. Começa com os canais mais fáceis (Telegram + Facebook "Achados
Shopee") e adiciona vídeo conforme valida.

### 2.1 Orquestrador central ✅ CONCLUÍDO (2026-06-26)
- [x] Endpoint `POST /api/v1/admin/distribute`: recebe oferta → cria short link
      → gera legenda (IA ou fallback) → posta nos canais ativos.
- [x] Endpoint `POST /api/v1/admin/distribute/auto`: busca N ofertas automaticamente
      com filtros de qualidade (desconto >= 15%, preço >= R$ 20, dedup 24h).
- [x] Worker `distributor.py` com rate-limit por plataforma (3s entre posts).
- [x] Dedup compartilhado com broadcaster (24h).
- [x] **Testado:** 5 ofertas postadas no Telegram com sucesso (message_ids 912-925).

### 2.2 Gerador de conteúdo IA em lote (OpenRouter) ✅ CONCLUÍDO (2026-06-26)
- [x] `generate_caption_ai()` no `distributor.py`: 1 chamada LLM gera legenda
      persuasiva (máx 280 chars, emojis moderados, foco em benefício/economia).
- [x] Fallback gracioso: se IA falhar (rate limit, sem créditos), usa legenda
      padrão do broadcaster — postagem nunca falha por causa de IA.
- [x] Modelo: `google/gemma-4-31b-it:free` (gratuito) — OpenRouter sem créditos
      usa fallback. Para IA ativa, precisa adicionar créditos no OpenRouter.
- [ ] **Futuro:** gerar 4 formatos de uma vez (Telegram, TikTok hook, YT Shorts,
      Facebook) quando os outros canais forem ativados.
- [ ] **Futuro:** Thumbnail com overlay preço/desconto (Pillow).

### 2.3 Publicadores ✅ TELEGRAM CONCLUÍDO (2026-06-26)
- [x] **Telegram:** integrado ao orquestrador. Filtra ofertas com
      `discount >= 15%` E `price >= R$ 20`. Posta foto + legenda + short link.
- [x] Cada post = 1 short link `/r/{code}` único com `source = distributor_telegram`.
- [x] Click tracking registrado no backend (`/admin/clicks`).
- [x] **Facebook (multi-página + anti-banimento):** `post_to_facebook()`
      implementado no `distributor.py`. Posta em **TODAS as páginas ativas**
      no banco. **FUNCIONAL** — app Meta Business `1555866299595457`.
      3 páginas: Bestpricetoday + Achados Shoppee + Achados Shopee.
      Instagram: @aletubegames. Loop 5x/dia em `["telegram", "facebook"]`.

      **Estratégia anti-banimento (política Meta 2026):**
      - Caption NÃO contém link de afiliado no corpo do post
      - CTA: "👇 Link de compra nos comentários (fixado)"
      - Short link postado como **comentário fixado** em cada post
      - Motivo: Meta limita links no corpo a 2/mês (não-verificados) +
        links de afiliado no corpo = risco de banimento
      - `build_caption_facebook()` — caption sem link (só oferta + CTA)
      - `post_comment_facebook()` + `pin_comment_facebook()` no instagram.py
      - **FUNCIONAL** — `pages_manage_engagement` ativado + OAuth refeito.
        Teste OK: posts + comentários com link fixados nas 3 páginas.
      - **Por que short link `/r/{code}` em vez do link direto da loja:**
        1. **Tracking**: registra IP, user-agent, referrer, horário (link direto = cego)
        2. **Anti-banimento**: Meta não reconhece `/r/abc123` como afiliado
           (reconhece `amazon.com.br/dp/...` e limita alcance)
        3. **Flexibilidade**: troca o destino no banco sem mudar o post
        4. **Branding**: todo clique passa pelo domínio do projeto
        Fluxo: clique → ClickEvent → 302 redirect → loja com cookie de afiliado
- [x] **YouTube Shorts:** ✅ FUNCIONAL — OAuth Google + YouTube Data API v3.
      Canal AleTubeGames conectado. `post_to_youtube()` gera vídeo Short
      automaticamente (ffmpeg + PIL com foto do produto + preço + desconto)
      e publica com descrição contendo disclosure FTC + link direto da loja +
      short link para tracking. Política YouTube 2026 permite links de
      afiliado na descrição (diferente Facebook/Instagram).
      `delete_video()` + `update_video_description()` para auto-delete de
      ofertas expiradas (vídeos perecíveis).
- [x] **Instagram:** ✅ FUNCIONAL — `post_to_instagram()` via Graph API.
      `publish_photo_instagram()` posta foto no feed. Caption sem link
      (CTA "Link na bio"). Comentários via API precisam de
      `instagram_manage_comments` (pendência futura).
- [ ] **TikTok:** sem access token — precisa OAuth login.
      TikTok exige aprovação do app na Content Posting API.
- [x] **Arquitetura:** adicionar novo canal = 1 função `post_to_{channel}()` +
      registrar na lista `channels` do `distribute_offer()`.

      **Frequência otimizada (2026-06-27):**
      - 2x/dia nos picos simultâneos: **12h** e **19h** (hora BR)
      - 2 ofertas por horário = **4 ofertas/dia**
      - 4 canais simultâneos: Telegram + Facebook (3 páginas) + Instagram + YouTube
      - **28 posts/dia** total (4 ofertas × 7 destinos)
      - Baseado em: Sprout Social (2B engajements), Hootsuite (1M posts),
        Metricool, Emplifi 2026
      - Facebook: 2 posts/dia por página (ideal — Meta penaliza >4)
      - Instagram: 2 posts/dia (ideal — 1-2 Reels/dia > 5 medíocres)
      - YouTube: 2 Shorts/dia (consistência > volume)

### 2.4 Tracking por conteúdo ✅ CONCLUÍDO (2026-06-26)
- [x] Endpoint `GET /api/v1/admin/distribute/stats`: dashboard com:
      - total_posts, total_clicks
      - by_channel: posts + cliques + avg por source (canal)
      - top_posts: top 10 por cliques (code, URL, produto, provider, preço, source)
- [x] **Testado:** retorna 5 posts no canal `distributor_telegram` com 0 cliques
      (ofertas acabaram de ser postadas — cliques aparecerão conforme usuários
      clicam nos links do Telegram).
- [ ] **Critério parcial:** dashboard mostra top 10 posts por cliques. Quando
      Facebook/TikTok ativados, terá ≥2 canais para comparar.

### 2.5 Loop automático ✅ CONCLUÍDO (2026-06-26)
- [x] `run_distributor_loop()` integrado ao lifespan do FastAPI (main.py).
- [x] Broadcaster legado desativado (substituído pelo distributor com filtros + IA).
- [x] Schedule de postagem (hora local BR):
      - 9h: 3 ofertas | 13h: 3 ofertas | 18h: 3 ofertas (horário de pico)
      - 0h e 6h: 1 oferta (manter canal ativo na madrugada)
      - Checa a cada 30 min se é hora de postar.
- [x] Dedup de horário: não posta 2x no mesmo slot.
- [x] Dedup de oferta: não repete a mesma oferta em 24h.
- [x] IA com fallback: se OpenRouter rate-limited, usa legenda padrão.
- [x] **Testado:** loop postou 3 ofertas às 13h automaticamente (2 com IA, 1
      com fallback). Total: 8 posts no canal, 0 erros.

---

## FASE 3 — Escalar o que converte (mês 2+)

**Só após Fase 0 validada e Fase 1-2 trazendo tráfego/cliques reais.**

### 3.1 Rede de canais Telegram por nicho
- [ ] 5-10 canais segmentados (`@AchadosCelularBR`, `@AchadosGamesBR`...).
      1 bot multi-canal com roteamento por categoria.
- [ ] Cross-promotion: cada vídeo cita "link na bio = canal Telegram de [nicho]".

### 3.2 SEO em escala
- [ ] Sitemap crescendo para 5k-10k queries conforme indexa.
- [ ] Páginas de marca (`/marca/[marca]`).

### 3.3 Tráfego pago com arbitragem (só com CAC medido)
- [ ] Meta Pixel + Conversion API (server-side via `FACEBOOK_APP_SECRET`).
- [ ] Google/TikTok conversion tracking.
- [ ] Retargeting de quem clicou e não comprou.
- [ ] Prospecção: R$ 50/dia → medir ROAS → escalar vencedor só se ROAS > 2x.

### 3.4 Cortar perdedores, dobrar vencedores
- [ ] Dashboard por fonte: o que traz 80% da comissão? Dobrar nisso.
- [ ] Desligar canais/providers que não convertem.

---

## Matemática realista (não promessa)

| Etapa | Tráfego/dia | CTR afiliado | Conv. | Comissão/dia |
|---|---|---|---|---|
| Fim Fase 0 | ~20 (você+testes) | — | — | R$ 0-5 (validação) |
| Fim Fase 1 (mês 1) | 50-200 orgânico | 4% | 2% | R$ 5-30 |
| Fim Fase 2 (mês 2) | +200-500 social | 5% | 3% | R$ 30-150 |
| Fase 3 (mês 3-4) | 1.000-3.000 | 5% | 3% | R$ 150-800 |
| Escala (mês 6+) | 5.000+ + tráfego pago | — | — | R$ 1k-5k+/dia |

Esses números são **coerentes com afiliados BR reais em crescimento**. Centenas
de milhares/mês só vem com tráfego pago em escala + orgânico maduro (mês 6-12),
e **só se** o loop de conversão estiver fechado e a fonte dominante identificada.

---

## Ordem de execução (atualizada 2026-06-26)

```
✅ Dia 1:     FASE 0.1-0.3 (URLs :9443 + workers no alaserver + links corrigidos)
✅ Dia 1:     FASE 0.4a (scraping métricas ML + endpoints admin)
✅ Dia 1:     FASE 1.1 (SSR /produto/[query] + JSON-LD Product)
✅ Dia 1:     FASE 1.2 (sitemap 314 URLs dinâmico)
✅ Dia 2:     FASE 3.2 (SEO em escala → testado 6.759 queries → só 21 válidas → sitemap honesto com 35 URLs)
✅ Dia 2:     Filtros de relevância (acessórios + Lomadee + ML AND)
✅ Dia 1:     FASE 1.3 (10 páginas de categoria + link juice)
✅ Dia 1:     FASE 1.4 (GA4 + Microsoft Clarity + robots.txt)
✅ Dia 1:     FASE 2.1-2.5 (orquestrador + IA + Telegram + dashboard + loop auto)
⬜ Pendente:  FASE 0.4c (compra teste → confirmar total_commission > 0) ← GATE
⬜ Pendente:  Reenviar sitemap no Google Search Console (ação manual)
⬜ Pendente:  Adicionar créditos OpenRouter ($5) para IA ativa permanente
⬜ Pendente:  OAuth TikTok + YouTube (Facebook já funcional com 3 páginas + Instagram)
⬜ Futuro:    FASE 3.1-3.4 (canais nicho + SEO escala + tráfego pago)
```

---

## Critério de "rompimento da bolha" (atualizado 2026-06-27)

A bolha rompe quando TODOS estes são verdadeiros no `/admin/overview`:
```
✅ site no ar com HTTPS (:9443)        (Fase 0.1 — DECIDIDO manter 9443)
✅ links do Telegram abrem o site       (Fase 0.3 — CORRIGIDO com :9443)
✅ SEO em escala (5.046 URLs)           (Fase 3.2 — sitemap + 32 marcas)
✅ filtros de relevância ativos         (acessórios + Lomadee filtrados)
⬜ total_commission > 0                 (Fase 0.4c — PENDENTE: compra teste)
⬜ total_clicks > 50/dia                (Fase 1+2 — aguardando indexação Google)
⬜ total_conversions >= 1/dia           (Fase 2 validada)
⬜ comissão rastreada por fonte         (distributor + /distribute/stats prontos)
```

**Status atual:** 4 de 8 critérios atendidos. O GATE absoluto é a compra teste
(0.4c) para confirmar `total_commission > 0`. Depois disso, é questão de tempo
para tráfego orgânico (SEO 5k+ URLs) + social (Telegram automático) gerarem cliques.

**Próximo nível (escala):** `total_commission >= R$ 100/dia` → identificar a
fonte dominante → dobrar nela → tráfego pago com arbitragem.

---

## Próximo passo imediato

**Tudo da Fase 0, 1, 2 e 3.2 já foi implementado.** O que resta:

### Ações do usuário (não técnico):
1. **Compra teste (GATE da Fase 0):** comprar 1 produto barato (R$ 15-30) pelo
   link de afiliado no site. Aguardar 24-48h. Rodar `POST /admin/metrics/scrape-now`.
   Confirmar `total_commission > 0` no `/admin/overview`.
2. **Reenviar sitemap no Google Search Console:**
   https://search.google.com/search-console → Sitemaps →
   `https://bestpricetoday.alaserver.com.br:9443/sitemap.xml`
   (agora com 5.046 URLs — Google vai indexar muito mais páginas)
3. **Adicionar créditos OpenRouter ($5):** https://openrouter.ai/settings/credits
   — ativa IA permanentemente para legendas do Telegram.
4. **Criar nova Página Facebook "bestpricetoday" + Instagram Business:**
   Mantendo a página antiga "Achados Shopee" ativa. O app Meta posta nas
   2 páginas (multi-página). Passo-a-passo manual na Meta:
   - **4a.** Criar Página Facebook: https://www.facebook.com/pages/create
     - Categoria: "Loja de varejo" ou "Serviço de compras"
     - Nome: "bestpricetoday"
     - Adicionar foto de perfil + capa
     - Bio sugerida (do layout.tsx): "Compare preços em Mercado Livre, Amazon,
       Shopee, KaBuM e mais. Cupons automáticos, cashback e histórico de
       preços. Economize na hora!"
     - Link: `https://bestpricetoday.alaserver.com.br:9443`
   - **4b.** Converter conta Instagram para Business:
     - Instagram app → Configurações → Tipo de conta → Mudar para conta profissional
     - Categoria: "Loja de varejo" / "Serviços de compras"
   - **4c.** Vincular Instagram à Página Facebook:
     - Facebook Page → Configurações → Instagram → "Conectar conta Instagram"
     - OU Instagram Business → Configurações → Empresas → "Vincular página Facebook"
   - **4d.** Garantir que a conta admin do app Meta é admin das 2 páginas:
     - Tanto a antiga "Achados Shopee" quanto a nova "bestpricetoday"
       precisam ter o mesmo usuário Facebook como admin
     - Facebook Page → Configurações → Funções da página → adicionar o usuário
       como "Administrador" (se ainda não for)
   - **4e.** Criar NOVO aplicativo Meta (o antigo `1321973835927912` tem config erradas):
     - Acessar https://developers.facebook.com/apps → **Create App**
     - Tipo: **Business** (não Consumer — Business dá acesso a Pages + Instagram Graph API)
     - Nome: "BestPriceToday" (ou "bestpricetoday-app")
     - Email de contato: aletubegames@gmail.com
     - Após criar, anotar:
       - **App ID** (número novo, substitui `1321973835927912`)
       - **App Secret** (App Settings → Basic → Show → copiar)
     - Adicionar produto **Facebook Login**:
       - Products → Add Product → Facebook Login → Set Up
       - Settings → Valid OAuth Redirect URIs → adicionar:
         `https://api.alaserver.com.br:9443/api/v1/aletube/callback/facebook`
       - **NÃO** adicionar a URI antiga errada
     - Adicionar produto **Instagram Graph API** (opcional, para Reels):
       - Products → Add Product → Instagram Graph API → Set Up
     - Validar permissões (App Review → Permissions and Features):
       - `pages_manage_posts`, `pages_read_engagement`,
         `pages_manage_metadata`, `instagram_content_publish`,
         `instagram_basic`, `pages_show_list`, `business_management`
       - Em modo dev (Development) funcionam sem revisão para o admin do app
   - **4f.** Atualizar `.env` no alaserver com o novo App ID + Secret:
     - SSH: `ssh alessandro@192.168.15.45`
     - Editar `/home/alessandro/backend/.env`:
       ```
       ID_APLICATIVO_FACEBOOK=<NOVO_APP_ID>
       SECRET_KEY_FACEBOOK_APP=<NOVO_APP_SECRET>
       FACEBOOK_APP_SECRET=<NOVO_APP_SECRET>
       ```
     - Reiniciar backend: `kill -9 $(pgrep -f 'uvicorn app.main') && sleep 2 && cd /home/alessandro/backend && source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 >> backend.log 2>&1 &`
     - Também atualizar `.env` local em `backend/.env` (para consistência)
   - **4g.** Refazer OAuth: acessar no navegador
     `https://api.alaserver.com.br:9443/api/v1/aletube/auth/facebook`
     → copiar a `auth_url` retornada → colar no navegador → autorizar
     → token salvo automaticamente no backend para **todas as páginas**
     que o usuário administra (FacebookAccount + InstagramAccount)
   - **4h.** Verificar: `curl -H 'X-Admin-Key: 754210!As@'
     https://api.alaserver.com.br:9443/api/v1/aletube/accounts/status`
     → `facebook.connected: true` + `instagram.connected: true`
   - **4i.** Confirmar 2 páginas no banco (SSH no alaserver):
     `cd /home/alessandro/backend && source venv/bin/activate && python3 -c "
     import asyncio; from app.db.session import AsyncSessionLocal
     from app.models.models import FacebookAccount
     from sqlalchemy import select
     async def main():
         async with AsyncSessionLocal() as db:
             r = await db.execute(select(FacebookAccount).where(FacebookAccount.is_active == True, FacebookAccount.page_id != 'user_token'))
             for a in r.scalars(): print(f'  - {a.page_name} (id={a.page_id})')
     asyncio.run(main())"`
     → deve listar "Achados Shopee" e "bestpricetoday"
5. **OAuth TikTok:** acessar
   `https://api.alaserver.com.br:9443/api/v1/tiktok/auth/admin` no navegador.
   Obs: TikTok exige aprovação do app na Content Posting API para postar vídeos.

### Problema conhecido (catálogo de eletrônicos):
- **Sintoma:** buscar "iphone 16 pro max" retorna 0 ofertas (todos os providers
  retornam apenas capas/acessórios, que são filtrados).
- **Causa:** nenhum provider tem iPhones reais no catálogo acessível.
- **Solução:** rodar scraper ML com queries de eletrônicos populares OU
  configurar Amazon Associates (tem catálogo completo de eletrônicos).

### Próximas implementações (quando pronto):
- **Fase 3.1:** Rede de canais Telegram por nicho (5-10 canais segmentados)
- ~~**Fase 3.2:** SEO em escala~~ ✅ CONCLUÍDO (sitemap honesto: 35 URLs com conteúdo real)
- **Fase 3.3:** Tráfego pago com arbitragem (Meta Pixel + Conversion API)
- **Fase 3.4:** Cortar perdedores, dobrar vencedores
- **Fase 3.5:** ~~EXPANDIR CATÁLOGO~~ ✅ CONCLUÍDO (Amazon scraper: 1.084 produtos, 81 queries válidas)
  — Para crescer mais: rodar scraper com mais queries, configurar PA-API após 3 vendas
- **Fase 3.6:** ~~CUPONS ML~~ ✅ CONCLUÍDO (141 cupons ativos, 3.733 produtos com preço+imagem)
  — Scraper gera cupons no Portal do Afiliado, coleta produtos da loja
  — Frontend `/cupons` com grid, filtros, copiar cupom, link "Ver na loja"
  — Comissão: 3% (maioria) / 5% (moda/esportes) — rastreio permanente
  — vs Link de afiliado: até 16% mas cookie expira em 24-48h
  — **Estratégia:** usar AMBOS nas postagens (link + cupom como fallback)
- **Fase 3.7:** Postagem de cupons no distributor (telegram/facebook/instagram)
  — Postar produto + cupom + link de afiliado juntos
  — Cupom como incentivo de compra (desconto) + rastreio permanente
  — Link como comissão primária (até 16% se comprar em 48h)
