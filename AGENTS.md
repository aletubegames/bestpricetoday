# BestPriceToday — Regras do Projeto

## Deploy
- **SEMPRE que corrigir um arquivo, subir para o alaserver (192.168.100.30) imediatamente**
- SSH: `ssh alessandro@192.168.100.30` (só acessível via rede local, não 4G/5G)
- Backend: `/home/alessandro/backend/`
- Frontend: `/home/alessandro/frontend/`
- Reiniciar backend: `sudo systemctl restart bestprice-backend`
- Reiniciar frontend: `sudo systemctl restart bestprice-frontend`
- Rebuild frontend: `cd /home/alessandro/frontend && npx next build` depois reiniciar

## URLs
- **PUBLIC_SITE_URL**: `https://bestpricetoday.alaserver.com.br` (porta 443 padrão via Cloudflare Tunnel)
- **INTERNAL_API_URL**: `https://api.alaserver.com.br` (porta 443 padrão via Cloudflare Tunnel)
- Cloudflare Tunnel (cloudflared) faz proxy: edge Cloudflare → localhost:3000 (frontend) / localhost:8000 (API)
- Porta 9443 ainda funciona como backup (nginx direto + port forwarding roteador)
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
- `ml_scraper` — roda via cron 4h diario (`run_ml_scraper.sh`), usa Playwright/Chromium
- `amazon_scraper` — roda via cron 3h diario (`run_amazon_scraper.sh`)
- `ml_coupon_scraper` — gera/coleta cupons de afiliado ML via Portal do Afiliado (Playwright + cookies manuais)
- Processos Chromium/Playwright sao do ml_scraper — NAO matar
- Se ml_scraper travar (rodando >24h), pode reiniciar com `cd /home/alessandro/backend && setsid bash run_ml_scraper.sh < /dev/null > /dev/null 2>&1 &`

## Cupons ML
- Cupom = rastreio permanente (não expira em 48h como cookie do link)
- Comissão: 3% (maioria) ou 5% (moda/esportes) — fixa por cupom
- Link de afiliado: até 16% mas cookie expira em 24-48h
- Cupom vale para QUALQUER produto da loja, não só catálogo de afiliados
- Scraper coleta produtos via "Ver produtos" → URL da loja (`lista.mercadolivre.com.br/loja/{nome}/`)
- Cookies em `.ml_cookies.json` — login manual via VNC (reCAPTCHA bloqueia login programático)
- Preço: seletor `.poly-price__amount` (NÃO usar `.poly-price__current` que cola preço+desconto)
- Parser BR: "." = milhar, "," = decimal (R$1.670 = 1670, R$630,33 = 630.33)
- Cupons vencidos: DELETAR (não só desativar)
- Frontend: `/cupons` — grid com filtros, copiar cupom, link "Ver na loja"

## Distributor
- Posta às 12h e 19h (janela de 2h de tolerância)
- Canais: telegram, facebook, instagram, youtube
- YouTube roda em background (asyncio.create_task) para não travar o loop
- Links sempre sem porta (https://bestpricetoday.alaserver.com.br/r/{code})
