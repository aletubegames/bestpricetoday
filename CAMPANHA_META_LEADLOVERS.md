# Campanha Meta Ads — LEADLOVERS (Hotmart) — EM VEICULAÇÃO

> Status (14/nov): **campanha DUPLICADA** — a original ficou "Ativa" ~24h com
> R$0,00 gasto / 0 impressões (Meta segurando entrada no leilão em conta nova;
> conta verificada OK: saldo R$100, limite R$229/dia, sem alertas).
> Original **pausada**. Cópia publicada → anúncio "AD1 | Leadlovers | Aviao — Cópia"
> **Em análise** (variante da recomendação Meta — criativo Advantage+ ativado;
> a cópia direta do AD1 saiu com erro e foi excluída do rascunho antes de publicar).
> Mesmo orçamento: R$10/dia compartilhado. Saldo R$100 pré-pago.
> Monitoramento automático no alaserver 2×/dia (`check_meta_ads.py`, 8h/20h →
> `check_meta_ads.log` + `check_analytics.py` 8h30/20h30 GA4+Clarity +
> `check_hotmart.py` 8h45/20h45 vendas).

## Produto
- **Leadlovers** — plataforma de automação de marketing/vendas (funil, e-mail, WhatsApp)
- Hotlink afiliado: `https://go.hotmart.com/I108467743A`
- Afiliação: **ativa** (aprovação em 1 clique, 12/nov)
- Comissão: **~20% recorrente** (~R$48/mês por cliente na assinatura ~R$240/mês)
- Condições: exige **Nota Fiscal pra sacar** (MEI resolve) + vender 1×/mês pra manter afiliação
- Materiais do produtor: `app.hotmart.com/hotlinks/42903` — pasta "Materiais de Divulgação ADS"
  (8 vídeos + banners + 4 PNGs 2160×2700 4:5 em `~/Downloads/leadlovers_ads/`)

## Por que Leadlovers (e não produto físico)
- Comissão recorrente muda a matemática: 2 vendas = ~R$96/mês entrando **todo mês**
- Público = donos de pequenos negócios (B2B) — mass market no Brasil
- São Miguelito segue como candidato melhor encaixado quando a afiliação aprovar
  (ver `CAMPANHA_META_SAOMIGUELITO.md`)

## Conta de anúncios
- Conta: `act_198788012286128` (Business "Alessandro Souza", CNPJ MEI)
- Pixel: `879356861433720` ("BestPriceToday") — 161 eventos/28d
- Saldo pré-pago: **R$100** creditados (R$87,85 de mídia + ~R$12 imposto)
- Limite diário da conta: ~R$229

## Estrutura publicada

**Campanha:** `LEADLOVERS | SEM1 | TRAFEGO` — ID `120250093461690724`
- Objetivo: **Tráfego** (otimiza por visualização da página de destino)
- Motivo: compra acontece no checkout Hotmart sem nosso pixel → "Vendas" seria
  tráfego disfarçado. Quando o pixel de afiliado for cadastrado na Hotmart,
  considerar trocar pra Vendas na semana 2.

**Conjunto:** `CONJ1 | Leadlovers | BR 25-55` — ID `120250093461710724`
- Orçamento: **R$10/dia compartilhado (CBO)** — máx semanal R$70
- Brasil, 25–55, ambos os sexos, Advantage+ público e posicionamentos

**Anúncio:** `AD1 | Leadlovers | Aviao`
- Criativo: `ADS1_aviao.png` do produtor ("Você tá pilotando ou empurrando o avião?")
- Texto principal: "Cada lead sem resposta em segundos compra do concorrente.
  A Leadlovers automatiza resposta, nutrição e venda — e-mail, WhatsApp e funil
  num só lugar. Teste e veja suas vendas no automático."
- Título: "Venda no automático com a Leadlovers"
- CTA: "Ver detalhes" (recomendação da Meta p/ CVR)
- Destino: `https://go.hotmart.com/I108467743A`
- Params: `src=meta_sem1&utm_source=meta&utm_medium=paid&utm_campaign=leadlovers_sem1`
- Identidade: página **Bestpricetoday** (FB) + "usar identidade da página" (IG/Threads)
  — trocado de "Achados Shoppee"/aletubegames a pedido do dono (12/nov)

## Monitoramento (alaserver)
- `check_meta_ads.py` — cron `0 8,20 * * *` → status + gasto + impressões
- `check_analytics.py` — cron `30 8,20 * * *` → GA4 (a399395754) + Clarity (xd51oaxppe)
- `check_hotmart.py` — cron `45 8,20 * * *` → vendas/saldo do painel de afiliado
- Cookies: `.meta_cookies.json` / `.analytics_cookies.json` / `.hotmart_cookies.json` (600) — se `SESSION_DEAD`
  no log, reexportar do Chrome/Edge local
- Cliques da campanha chegam no backend por `source='meta_sem1'` (tabela click_events)
- **Vendas não passam pelo alaserver** — conferir no painel de afiliado da Hotmart

## Regras de gestão (7 dias)
| Dia | Ação |
|---|---|
| 1–2 | Não mexer — aprendizado da Meta |
| 3 | CTR <1% ou CPC >R$1 → pausar criativo e subir ADS2_relogio.png |
| 4–5 | 0 cliques pro checkout → revisar público/copy |
| Corte duro | **R$40 gastos sem nenhum checkout = pausa tudo, guarda o resto** |

## Metas da semana
- Mínimo viável: 1 venda = ~R$48/mês recorrente (paga a campanha em 2 meses)
- Meta: 2 vendas = ~R$96/mês recorrente (+100% em ~1 mês de recorrência)
- Recorrência é o diferencial: cada cliente paga todo mês enquanto assinar

## Pendências
- [ ] Pixel de afiliado no checkout Leadlovers (wizard Hotmart instável — tentar de novo)
- [ ] São Miguelito: aguardar aprovação da afiliação
- [ ] Se Leadlovers performar: subir ADS2/ADS3/ADS4 como variações de criativo
- [ ] Popup Telegram na home mede conversão do tráfego orgânico (`popup_*` no GA4)
