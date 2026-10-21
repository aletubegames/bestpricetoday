# PLANO_RENDA.md — Por que o BestPriceToday não gera renda e como sair do zero

> **Auditado em 2026-10-21** via SSH read-only no alaserver (192.168.15.45) —
> serviços, logs, crontab e Postgres local (`bestpricetoday`). Todos os números
> abaixo são medidos, não estimados.
> **KPI único:** R$ de comissão confirmada no portal de afiliados.
> **Complementa (não substitui)** `Grow_up.md` — aquele plano construiu a
> máquina; este plano é sobre o que a máquina nunca teve: **gente**.

---

## 1. VERDADE MEDIDA (2026-10-21)

### A máquina funciona — isso NÃO é o problema

| Componente | Estado medido |
|---|---|
| Serviços | `bestprice-backend`, `bestprice-frontend`, `cloudflared`: **active** |
| Sessão ML afiliados | Viva — `.ml_session_last_ok` hoje 14:00, sem `EXPIRED_FILE` |
| Scraper ML | Rodou hoje: **3.304 produtos** coletados |
| Scraper Amazon | Rodou 3h: **1.191 produtos** (64 queries) |
| Scraper cupons ML | Rodou 23h ontem: **2.874 cupons** (modelo novo funciona) |
| Catálogo | `affiliate_products`: **4.397 ativos** / 27.785 total |
| Distributor | Postou hoje em FB (2 páginas) + IG + YouTube Short c/ vídeo XTTS |
| CouponDistributor | Postou hoje 10h (Telegram + Facebook), 1 cupom/dia |
| Links | `short_links` criados hoje (`/r/{code}` funcionando) |

### O dinheiro JÁ passou uma vez — o gate técnico está provado

**2026-09-30 (portal ML): 88 cliques → 2 PEDIDOS → R$ 598,23 vendidos →
R$ 24,53 de comissão estimada (1 comprador).** Atribuição funciona
de ponta a ponta — clique nosso virou pedido e comissão. Único dia com
ordens em todos os 24 snapshots; `confirmed_earnings` ainda vazio
(ML marca como "estimado" — confirmar no portal se liquidou).
Outubro inteiro: **0 pedidos**.

### O que mede ZERO — este é o problema

| Métrica | Valor real |
|---|---|
| `conversion_events` (tabela própria) | **0 linhas** (venda real só existe no portal ML) |
| `clicks_afiliados` | **0 linhas** |
| ML portal — outubro inteiro | **0 pedidos** — cliques/dia do portal: 0–14 |
| Cliques `source='web'` | **8 em 30 dias** (o site propriamente dito) |
| Cliques `distributor_telegram` | **1 em 30 dias** |
| Cliques humanos reais estimados | **≈ 0–10/dia** (ver raio-X abaixo; o dia 30/set com 88 foi exceção) |

### Raio-X dos 1.264 cliques dos últimos 30 dias

Parecia tráfego crescendo (189 cliques em 17/out). Não é:

| User-Agent | Cliques | O que é |
|---|---|---|
| `facebookexternalhit` | **849 (67%)** | Crawler do Facebook buscando preview dos links postados |
| Googlebot / Nexus 5X / Google-Safety | ~83 | Google rastreando/validando URLs |
| trendictionbot + Mediatoolkitbot + AHC | ~45 | Crawlers de monitoramento |
| "Chrome" desktop/Android genérico | ~242 | Em sua maioria verificadores de link automáticos (safe-browsing, ad-checkers que seguem posts do FB) |
| **Humanos de verdade** | **~dúzias, na melhor hipótese** | — |

`searches`: ~176k linhas/30d (`web`+`ssr`) — é hammering de bots/scanners, **não é usuário**. Não usar como métrica de tração.

### Conclusão do diagnóstico (causa raiz única)

> **Construímos uma emissora de TV completa — estúdio, transmissor, programação
> diária — transmitindo para uma cidade sem nenhum morador.**
>
> O loop dinheiro já foi provado uma vez (R$ 24,53 em 30/set) — **o problema
> não é atribuição, é que dias assim são exceção aleatória, não sistema**.
> O gargalo é **aquisição de audiência ≈ 0**: sem humanos clicando todo dia,
> vendas acontecem por acidente, não por processo.

### Bugs menores achados na auditoria (não são a causa, mas valem fix)

- `lomadee._parse_product` — `'<' not supported between float and NoneType` em loop (dezenas de erros/dia no journal). `lomadee.py:384`.
- Facebook responde 641 dos cliques como crawler — **métricas contam crawler como clique**: `click_events` grava tudo. `_real_clicks_cond()` filtra só nos endpoints admin — o número bruto engana (como enganou nesta análise até filtrar por UA).
- `coupon_products.price` é NULL em ~11,9k linhas (API `/items` do ML dá 403) — cards de cupom sem preço; distributor já contorna com `discount_text`, mas o site `/cupons` fica fraco.
- YouTube do distributor: `errors=1` intermitente (21/out 12:23, recuperou depois).
- `affiliate_metrics_snapshots`: coleta funciona mas depende do ml_scraper diário — ok.

---

## 2. O QUE **NÃO** FAZER (todos já tentados ou inúteis agora)

1. **Mais features no site/backend** — o produto já sobra; o que falta é gente.
2. **Mais posts automáticos/dia** — 6 janelas/dia para 0 humanos = mesmo resultado.
3. **Tráfego pago** — proibido até EPC provado. Hoje EPC ≈ R$0/clique; comprar clique é jogar dinheiro.
4. **Mudar de provedor/adicionar redes de afiliado** — ML + Amazon já cobrem; o problema não é oferta.
5. **"Melhorar" métricas** — antes de crescer, corrigir o que conta clique (item F2.1) para não medirmos crawler como vitória.

---

## 3. O PLANO — 4 fases, cada uma com GATE verificável

```
F0  Validar o dinheiro          (2 dias, 1 ação do dono)
    ↓ GATE: pedido + comissão aparecem no portal ML
F1  Primeiros 100 humanos       (2–4 semanas)
    ↓ GATE: ≥50 cliques humanos/semana medidos sem crawler
F2  Conversão + métrica limpa   (paralelo, eu faço)
    ↓ GATE: ≥1 pedido real de terceiro
F3  Escalar o canal que deu gente (mês 2+)
    ↓ GATE: R$100+/mês confirmado → só aí pensar em escala/pago
KILL: 4 semanas de F1 com <300 cliques humanos totais → pivô (ver §6)
```

---

### FASE 0 — Validar o dinheiro — ✅ PASSOU (2026-09-30)

**Prova:** 2 pedidos / R$ 598,23 GMV / R$ 24,53 comissão **liquidada** no portal
ML (confirmado pelo dono em 21/out). Atribuição ponta a ponta funciona — não
precisa de compra teste.

- [x] **0.1 (dono, 5 min)** ✅ **CONFIRMADO pelo dono em 21/out** — os
      R$ 24,53 liquidaram no portal ML. Comissão real na conta, loop de
      dinheiro ponta a ponta validado oficialmente.
- [x] **0.2 Descobrir o que gerou o dia 30/set** — **ACHADO (2026-10-21):**
      o portal ML contou **88 cliques** no dia, mas nosso `click_events` só
      gravou 44 — **metade das saídas pro ML não passa pelo nosso tracking**.
      Confirmado no código: `frontend/src/app/afiliados/page.tsx:243` e
      `frontend/src/app/page.tsx:442` linkam `href={offer.affiliate_url}`
      **direto**, sem `/r/` nem `click_events`. O comprador de 30/set provavelmente
      saiu pela home ou pela página `/afiliados` — invisível nas nossas stats.
      → corrigido como tarefa **F2.1b** abaixo.

---

### FASE 1 — Primeiros 100 humanos (o verdadeiro gargalo)

Regra de ouro: **UM canal de cada vez, o que tiver sinal de vida real**.
Ordem por custo × probabilidade de gente real em 2026:

**1.A — YouTube Shorts (já temos a fábrica de vídeo) — prioridade 1**
- Já posta Shorts diários com narração XTTS — único canal que pode achar gente
  sozinho (feed de descoberta, não depende de inscritos).
- [ ] Dono: abrir YouTube Studio 1×/semana e anotar **views reais** por Short
      (métrica que só existe lá). Meta: qualquer Short >500 views = sinal.
- [x] Eu: revisar títulos dos Shorts — ✅ **DEPLOY 21/out:** `_youtube_title()`
      com hook primeiro: "😱 -X% OFF: produto por R$Y", "💰 ECONOMIZE R$Z",
      "🔥 produto por R$Y — menor preço agora" (variantes por discount/economy;
      spec-dump do título cortado no 1º separador). Thumbnails já mostram
      preço/desconto grandes nos overlays ffmpeg. **Pendente do dono:** medir
      views no Studio — se não subir em 2 semanas, revisar hook de narração
      (primeiros 2s) também.
- [x] Eu: descrição de todo Short com link `/r/` — ✅ **já existia:**
      `build_youtube_description` usa `short_url` rastreado + link do site.

**1.B — Telegram: canal próprio + semeadura manual — prioridade 2**
- ✅ **RESOLVIDO 21/out:** canal criado — **@bestpricetodayBr**
  (`-1003752570488`), `@BestPriceToday_bot` é admin, post "como usar"
  pinado. `TELEGRAM_CHANNEL_ID` atualizado no alaserver + backend
  reiniciado. **Alertas separados:** novo `TELEGRAM_ALERT_CHAT_ID` = DM
  do dono — erros operacionais não vazam pro canal público.
  (Contexto: o "canal" anterior era a DM do dono — `5899**07` — o
  "1 clique/30d" era o próprio dono clicando.)
- [ ] Dono: entrar em 5–10 grupos BR de promoções/achadinhos (Telegram e
      WhatsApp — ex.: comunidades estilo Pelando/Promobit) e postar ofertas
      REAIS com o link, respeitando regra de cada grupo (sem spam = sem ban).
      15 min/dia. É o único jeito grátis comprovado de audiência de deals.
- [ ] Dono: convidar contatos/família pro canal — os primeiros 30 membros.
- [x] Eu: post "como usar" + links (`/hoje` + `/cupons`) — ✅ **publicado e
      pinado no canal** (msg_id 2, 21/out).
- [x] Eu: convite do canal em todo post automático — ✅ **DEPLOY 21/out:**
      comentário fixado FB/IG (`🛒 link + 📣 t.me/bestpricetodayBr`),
      descrição YouTube, e footer das legendas Telegram corrigido
      (`@BestPriceToday` apontava handle inexistente → `@bestpricetodayBr`).

**1.C — SEO de cauda-longa de cupom — prioridade 3 (renda passiva)**
- Googlebot já rasteja o site (provado nos cliques), mas Search Console
  nunca foi submetido.
- [ ] Dono: cadastrar `bestpricetoday.alaserver.com.br` no Google Search
      Console + enviar sitemap (10 min, conta Google).
- [x] Eu: adicionar `/cupons` ao sitemap — ✅ **DEPLOY 21/out** (daily, prio
      0.8) junto com `/hoje` (hourly, 0.9). Páginas por loja (`/cupons/<loja>`)
      ficam pra depois — hoje o filtro de loja é query param client-side,
      precisaria de rota própria pra indexar.
- [x] Eu: `title`/`meta` com desconto em texto — ✅ **DEPLOY 21/out:**
      `/cupons` virou server component com metadata próprio
      ("Cupons Mercado Livre — descontos ativos hoje") + OG + canonical;
      `/produto/[query]` já tinha `generateMetadata` com a query no título.
      `/hoje` nasceu com metadata + OG próprios.

**1.D — WhatsApp Status/Comunidade (bônus, custo zero)**
- [ ] Dono: postar 1 oferta boa/dia no Status do WhatsApp pessoal com o link.
      Zero código, audiência quente.

**Gate da Fase 1:** ≥50 cliques humanos/semana (medidos sem crawler após F2.1)
por 2 semanas seguidas → avança. Canal que zerar em 2 semanas → abandona
(Facebook orgânico de página nova: provavelmente morto — manter posts
automáticos porque é grátis, parar de contar como canal de crescimento).

---

### FASE 2 — Conversão e métrica limpa (eu executo, paralelo à F1)

- [x] **2.1 Clique humano de verdade** — ✅ **JÁ EXISTIA** (`click_integrity.py`,
      19/out): `BOT_UA_PATTERNS` cobre `facebookexternalhit`, `Google-Safety`,
      `Nexus 5X`, `AHC/`, `python-*` etc + faixa IP da Meta + dedup 60min.
      Admin já filtra via `_real_clicks_cond()`. **Humanos/dia medido: ~10–25**
      (era ~40 bruto; os "Chrome genérico" restantes ainda incluem verificadores
      não-UA óbvios — número é teto, não piso).
- [x] **2.1b Instrumentar 100% das saídas de afiliado** — ✅ **DEPLOY 2026-10-21:**
      `/cupons` (3 âncoras: imagem, título, CTA) e `/afiliados` ("Ver oferta")
      agora abrem via `openTrackedOffer` → `/links/create` → `/r/{code}` →
      clique em `click_events` + 302. Fallback gracioso: se o tracking falhar,
      abre a URL original (que já carrega `matt_*` — dinheiro nunca se perde).
      `page.tsx`/compare já era rastreado; `OfferCard` já era rastreado.
      Verificado em prod: `/r/W9QxocJR` → 302 p/ Amazon `tag=aletubegames-20`
      + clique registrado.
- [x] **2.2 Fix `lomadee._parse_product`** — ✅ **DEPLOY 2026-10-21:** guard
      `if not price: return None` movido ANTES da comparação `list_price <= price`
      (era `float <= None` → TypeError → ~dezenas de erros/dia). Mesmo resultado
      (produto sem preço era descartado), zero spam de erro.
- [x] **2.3 Preço nos cupons** — ⚠️ **DEPLOY 2026-10-21 com ressalva:** fallback
      implementado (query extra por `ml_code` em `affiliate_products` quando
      `coupon_products.price` é NULL) — **mas o overlap real é só 13 produtos
      de 13.564** (0,1%). Código funciona; o dado é que não existe — a API
      `/items` do ML dá 403 e páginas de produto caem em captcha. Preço nos
      cards de cupom segue majoritariamente ausente; `discount_text` continua
      sendo a headline real (como o fix do distributor de 12/out já fazia).
- [x] **2.4 Página pública de ofertas "top do dia"** — ✅ **DEPLOY 2026-10-21:**
      `GET /api/v1/offers/today` — curadoria determinística: preço < máximo
      dos últimos 30d (`affiliate_price_history`), R$20–500, marca reconhecida,
      não-acessório, dedup ml_code, ordenado por % de queda REAL (não "desconto"
      declarado pela loja). `/hoje` é SSR (ISR 30min) — 12 cards, cada âncora
      rastreada via `openTrackedOffer` (source=`hoje`). Verificado: 12 ofertas
      reais (-59% a -28%), público 200 via Cloudflare. 1 link pro dono postar.
- [x] **2.5 YouTube `errors=1`** — ✅ **DEPLOY 2026-10-21:** causa raiz achada:
      `errors=1` = "nenhuma oferta elegível nas categorias sorteadas" (filtros
      rejeitavam tudo), não falha de upload. Agora: loga a categoria+queries
      quando zera, loga erro por canal quando post falha, e streak de falhas
      dispara alerta Telegram a cada 3 janelas seguidas (também em exceção).
- [x] **2.6 Sitemap** — ✅ **DEPLOY 2026-10-21:** `/hoje` (hourly, prio 0.9) e
      `/cupons` (daily, prio 0.8) adicionados ao `sitemap.xml`.

**Gate da Fase 2:** ≥1 pedido de TERCEIRO em `conversion_events`/
portal ML (não a compra teste do dono).

---

### FASE 3 — Escalar o que deu gente (mês 2+, só com F1+F2 passando)

- Dobrar no canal que produziu cliques humanos: Shorts→volume e séries
  recorrentes; Telegram→canais por nicho (tech, casa, games — como o
  `Grow_up.md` já previa em 3.1); SEO→mais categorias de cupom.
- WhatsApp/Telegram **broadcast** (lista de transmissão) para quem já
  interage — retenção, não só aquisição.
- Tráfego pago **somente** depois de EPC medido:
  `EPC = comissão_confirmada_30d / cliques_humanos_30d`.
  Regra: só comprar clique se `EPC ≥ 2× CPC`.
- Cortar perdedores todo mês: canal que não move `cliques_humanos` em 30d
  sai da rota (menos posts automáticos nele).

---

## 4. MÉTRICAS — onde olhar (copiar e colar)

Rodar no alaserver (`ssh alessandro@192.168.15.45`):

```bash
# Cliques HUMANOS por dia (depois do fix F2.1 usar flag is_bot;
# enquanto isso, este filtro manual já serve):
psql -h 127.0.0.1 -U bestpricetoday -d bestpricetoday -c "
SELECT date_trunc('day',clicked_at)::date d, count(*)
FROM click_events
WHERE clicked_at>now()-interval '14 days'
  AND user_agent !~* 'facebookexternalhit|google-safety|bot|crawler|spider|trendiction|mediatoolkit|AHC/|python|curl|headless'
GROUP BY 1 ORDER BY 1;"

# Comissão real (portal ML, coletado pelo scraper):
psql -h 127.0.0.1 -U bestpricetoday -d bestpricetoday -c "
SELECT collected_at::date, clicks, orders, estimated_earnings
FROM affiliate_metrics_snapshots ORDER BY collected_at DESC LIMIT 10;"

# Pedidos atribuídos:
psql -h 127.0.0.1 -U bestpricetoday -d bestpricetoday -c "
SELECT count(*), max(converted_at) FROM conversion_events;"
```

Painel do dono (1×/semana, 5 min):
- YouTube Studio → views dos Shorts (métrica de alcance real, grátis)
- Portal ML Afiliados → cliques/pedidos/ganhos
- Telegram → membros do canal
- Search Console → impressões/cliques orgânicos (depois de cadastrado)

**Metas numéricas honestas** (comissão ML média ~5%, ticket ~R$150 → ~R$7/pedido):

| Marco | Pedidos/mês | Cliques humanos/mês | R$/mês |
|---|---|---|---|
| Sair do zero | 1–5 | ~500 | R$7–35 |
| Trocar de fase | ~15 | ~1.500 | ~R$100 |
| Sustentável | ~70 | ~7.000 | ~R$500 |

Qualquer promessa acima disso em <6 meses é fantasia. O plano do
`Grow_up.md` continua certo — faltou só a parte que não dá pra
automatizar: **arrumar gente**.

---

## 5. RISCOS E COMO SE DEFENDE

| Risco | Sinal | Defesa |
|---|---|---|
| Ban conta ML afiliados (scraper/login) | `EXPIRED_FILE`, alertas Telegram | Keeper já tem backoffs; login manual via VNC quando cair; NÃO aumentar frequência de scrape |
| Ban página FB/IG por post de link | posts falhando em sequência | Links só no comentário fixado (já implementado); reduzir frequência se erro persistir |
| ML mudar fluxo de cupom de novo | scraper coleta 0 | Alerta: se 2 rodadas seguidas vierem 0, páginar e revisitar `/cupons` (modelo novo já mudou 1× em out/2026) |
| SPOF alaserver (disco/luz/Vivo) | site fora | Backup diário 4h já existe; restore doc = `INFRASTRUCTURE.md` |
| Vivo bloquear portas | acesso externo cai | Cloudflare Tunnel é o caminho principal (não depende de porta); 8443/2053 backup |
| Certificado expira | chamadas internas falham | `certbot-dns-cloudflare` renova; `/etc/hosts` aponta api→127.0.0.1 (atenção ao aviso do AGENTS.md) |

---

## 6. KILL CRITERIA / PIVÔ

Se após **4 semanas de Fase 1 executada de verdade** (posts manuais em grupos
+ Shorts otimizados + Search Console) os números forem:

- `< 300 cliques humanos totais` **ou** `0 pedidos`,

então o modelo "site de deals + distribuição automática" está provado sem
tração **neste formato**. Pivôs realistas, em ordem:

1. **Conteúdo primeiro, deals depois** — usar a fábrica de vídeo para um
   canal de nicho (ex.: "melhores achados da semana" como show, não catálogo)
   e monetizar a audiência com os mesmos links. É o modelo que funciona:
   audiência antes, afiliado depois.
2. **Nicho único** — ex.: só airfryers/eletroportáteis ou só periféricos
   gamer. Autoridade concentrada ranqueia; "menor preço de tudo" não.
3. **Parar** — custo de oportunidade é real; manter só scrapers+distributor
   rodando custa ~nada e pode ser revisitado.

---

## 7. ORDEM DE EXECUÇÃO IMEDIATA (esta semana)

| # | Ação | Quem | Tempo |
|---|---|---|---|
| 1 | Confirmar no portal ML se os R$24,53 liquidaram + o que gerou o dia 30/set (F0) | **Dono+Eu** | 15 min |
| 2 | Search Console + sitemap (F1.C) | **Dono** | 10 min |
| 3 | ~~Fix `is_bot` nos cliques + fix Lomadee + preço de cupom~~ ✅ DEPLOY 21/out | **Eu** | feito |
| 4 | ~~Página `/hoje` com top ofertas (F2.4)~~ ✅ DEPLOY 21/out | **Eu** | feito |
| 5 | ~~Reescrever hook/título dos Shorts (F1.A)~~ ✅ DEPLOY 21/out | **Eu** | feito |
| 6 | Postar em 5+ grupos de promoções, 15min/dia (F1.B) | **Dono** | diário |
| 7 | Revisão semanal: queries do §4 + views YT + membros TG | **Dono+Eu** | 10 min/sem |

> Regra de ouro do projeto inteiro: **nenhuma linha de código nova em
> feature enquanto a Fase 1 não mostrar gente real clicando** (a Fase 0 já
> passou — dinheiro entrou uma vez em 30/set).
> Deploy só via `ssh alessandro@192.168.15.45` + restart dos serviços
> `bestprice-*`, e commit no GitHub (`aletubegames/bestpricetoday`,
> fonte da verdade) — ver `AGENTS.md`.
