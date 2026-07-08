# BestPriceToday — Documentacao Completa de Infraestrutura

> **Ultima atualizacao:** 2026-07-01
> **URL oficial:** `https://bestpricetoday.alaserver.com.br` (porta 443, sem :9443)

---

## 1. Visao Geral

O BestPriceToday roda em um servidor local (192.168.100.30) conectado a internet
via V tal (IP dinamico). A operadora bloqueia portas 80 e 443 inbound, mas a
porta 9443 funciona. O Cloudflare Tunnel resolve isso, expondo o site na porta
443 padrao sem precisar abrir portas no roteador.

**Fluxo de trafego:**
```
Internet → Cloudflare (porta 443) → Cloudflare Tunnel → Servidor (localhost:3000/8000)
```

**Backup (porta 9443):**
```
Internet → Roteador (port forwarding 9443) → Nginx (porta 9443 SSL) → localhost:3000/8000
```

---

## 2. URLs

| Servico | URL Oficial | URL Backup |
|---|---|---|
| Frontend | `https://bestpricetoday.alaserver.com.br` | `https://bestpricetoday.alaserver.com.br:9443` |
| API | `https://api.alaserver.com.br` | `https://api.alaserver.com.br:9443` |
| Root | `https://alaserver.com.br` | `https://alaserver.com.br:9443` |
| Webmail | `https://webmail.alaserver.com.br` | — |
| Health | `https://api.alaserver.com.br/health` | — |

---

## 3. DNS — Cloudflare

### Nameservers
- `leonidas.ns.cloudflare.com`
- `tia.ns.cloudflare.com`

Gerenciados via **registro.br** (a Umbler e revendedora mas o registro.br
permite trocar nameservers diretamente se tiver conta).

### Registros DNS (13 total)

| Nome | Tipo | Conteudo | Proxy |
|---|---|---|---|
| `alaserver.com.br` | Tunnel | bestpricetoday | Proxied (laranja) |
| `api.alaserver.com.br` | Tunnel | bestpricetoday | Proxied (laranja) |
| `bestpricetoday.alaserver.com.br` | Tunnel | bestpricetoday | Proxied (laranja) |
| `www.alaserver.com.br` | CNAME | alaserver.com.br | Proxied (laranja) |
| `webmail.alaserver.com.br` | CNAME | webmail.umbler.com | DNS only (cinza) |
| `alaserver.com.br` | MX | mx364.umbler.com (prio 10) | DNS only |
| `alaserver.com.br` | MX | mx128.umbler.in (prio 20) | DNS only |
| `alaserver.com.br` | MX | mx783.umbler.com.br (prio 30) | DNS only |
| `alaserver.com.br` | MX | mx240.umbler.co.uk (prio 40) | DNS only |
| `_autodiscover._tcp` | SRV | 0 0 443 autodiscover832.umbler.com | DNS only |
| `alaserver.com.br` | TXT | v=spf1 include:spf.umbler.com ~all | DNS only |
| `_acme-challenge` | TXT | znGW4bapwkIP6Ox... | DNS only |
| `b5b33ba21686da77548a5d9c91d7ae9a` | CNAME | verify.bing.com | DNS only |

**Regras:**
- Registros de web/site → **Proxied** (laranja) — passa pelo Cloudflare
- Registros de email (MX, SPF, webmail, autodiscover) → **DNS only** (cinza) — nao passa pelo Cloudflare
- Bing verification CNAME → **DNS only**

---

## 4. Cloudflare Tunnel

### Instalacao
- **Binario:** `/usr/bin/cloudflared` (pacote .deb)
- **Versao:** 2026.6.1
- **Servico:** `cloudflared.service` (systemd, habilitado no boot)
- **Tunnel ID:** `52eea050-68dc-4cf4-9c96-f114d501cc53`
- **Tunnel name:** bestpricetoday

### Configuracao
- **Arquivo:** `/etc/cloudflared/config.yml`
- **Credenciais:** `/etc/cloudflared/52eea050-68dc-4cf4-9c96-f114d501cc53.json`

```yaml
tunnel: 52eea050-68dc-4cf4-9c96-f114d501cc53
credentials-file: /etc/cloudflared/52eea050-68dc-4cf4-9c96-f114d501cc53.json

ingress:
  - hostname: bestpricetoday.alaserver.com.br
    service: http://localhost:3000
  - hostname: api.alaserver.com.br
    service: http://localhost:8000
  - hostname: alaserver.com.br
    service: http://localhost:3000
  - service: http_status:404
```

### Comandos uteis
```bash
# Status
systemctl status cloudflared

# Reiniciar
sudo systemctl restart cloudflared

# Logs
sudo journalctl -u cloudflared -f

# Info do tunnel
cloudflared tunnel info bestpricetoday

# Login (gera cert.pem — raramente necessario)
cloudflared tunnel login
```

### SSL/TLS
- **Mode:** Full (nao Flexible, nao Full Strict)
- **Universal SSL:** Google Trust Services
- **Cert valido:** Jun 29 2026 → Set 28 2026

---

## 5. Cloudflare Workers

| Worker | Funcao | Status |
|---|---|---|
| `bestpricetoday-facebook-proxy` | Proxy do Facebook (legacy) | Ativo, nao mexer |
| `floral-dust-4710` | Criado para proxy de porta (nao usado) | Pode deletar |

---

## 6. Nginx

### Vhosts
- `/etc/nginx/sites-available/bestprice-frontend-ssl` — frontend (server_name: bestpricetoday + alaserver + www)
- `/etc/nginx/sites-available/bestprice-api-ssl` — API (server_name: api)
- `/etc/nginx/sites-available/bestprice-redirect` — porta 80 → HTTPS

### Portas escutando
- **443** — HTTPS (Cloudflare Tunnel + rede local)
- **9443** — HTTPS (backup externo via port forwarding)
- **8443** — HTTPS (alternativa, port forwarding configurado)
- **2053** — HTTPS (alternativa)
- **80** — HTTP redirect para HTTPS

### SSL
- **Cert:** Let's Encrypt `*.alaserver.com.br`
- **Arquivos:** `/etc/letsencrypt/live/alaserver.com.br/fullchain.pem` e `privkey.pem`
- **Renovacao:** automatica via certbot

### Comandos
```bash
# Testar config
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Ver portas
sudo ss -tlnp | grep -E '443|9443|8000|3000'
```

---

## 7. Roteador (192.168.100.1)

### Port Forwarding
| Nome | Porta Externa | Porta Interna | IP Interno | Protocolo |
|---|---|---|---|---|
| HTTP BestPrice | 80 | 80 | 192.168.100.30 | TCP |
| HTTPS | 443 | 443 | 192.168.100.30 | TCP |
| HTTPS BestPrice | 9443 | 9443 | 192.168.100.30 | TCP |
| HTTPS 8443 | 8443 | 8443 | 192.168.100.30 | TCP |
| HTTP 8080 | 8080 | 8080 | 192.168.100.30 | TCP |

**Nota:** As portas 80, 443, 8443 sao bloqueadas pela operadora (V tal) inbound.
So a porta 9443 funciona de fora. O Cloudflare Tunnel resolve isso.

---

## 8. Servicos (systemd)

| Servico | Funcao | Restart |
|---|---|---|
| `bestprice-backend` | FastAPI + uvicorn (porta 8000) + workers (distributor, coupon_distributor, alert_checker, bot, crons) | `sudo systemctl restart bestprice-backend` |
| `bestprice-frontend` | Next.js (porta 3000) | `sudo systemctl restart bestprice-frontend` |
| `cloudflared` | Cloudflare Tunnel | `sudo systemctl restart cloudflared` |
| `nginx` | Reverse proxy | `sudo systemctl reload nginx` |
| `bestprice-video-api` | API local de geracao de video (GPU, porta 8765) | `sudo systemctl restart bestprice-video-api` |

### Workers dentro do `bestprice-backend`
- `distributor.py` — orquestrador de ofertas (4x/dia: 12h, 15h, 19h, 21h)
- `coupon_distributor.py` — cupons ML (2x/dia: 12h, 19h) + geracao de video XTTS
- `bestprice_bot.py` — Telegram bot
- `alert_checker.py` — verificacao de alertas
- `conversion_cron.py` — poll de conversões
- `ml_refresh_cron.py` — renovacao de token ML

### Crons (user `alessandro`)
| Horario | Script | O que faz |
|---|---|---|
| 2h | `ml_coupon_scraper --cleanup-only` | Deleta cupons ML vencidos |
| 3h | `run_amazon_scraper.sh` | Atualiza produtos Amazon |
| 4h | `run_ml_scraper.sh` | Coleta produtos afiliados ML |
| 5h | `ml_coupon_scraper --collect-only` | Coleta cupons ML ativos (requer cookies validos) |

### Servicos DESABILITADOS
- `bestprice-bot` — desabilitado (bot roda dentro do backend)
- `channel-broadcaster` — desabilitado (substituido por distributor.py)
- `alert-checker` — desabilitado (roda dentro do backend)

---

## 9. IP Dinamico (V tal)

A operadora V tal usa IP dinamico. Quando o IP muda:

1. **Cloudflare Tunnel** — nao precisa fazer nada. O tunnel e OUTBOUND, sempre
   conecta ao Cloudflare independente do IP publico.
2. **Porta 9443 (backup)** — para de funcionar ate atualizar o DNS. Mas como
   o Cloudflare Tunnel e a URL principal, nao tem impacto.

**Antes do Cloudflare Tunnel:** era necessario atualizar o registro A no DNS
da Umbler toda vez que o IP mudava. Agora nao precisa mais.

---

## 10. Redirect URIs (OAuth)

Quando mudar a URL do site, atualizar em TODOS os paineis:

### Facebook Developer (https://developers.facebook.com)
- App: BestPriceToday / AleTubeGames
- Facebook Login → Settings → Valid OAuth Redirect URIs:
  - `https://api.alaserver.com.br/api/v1/aletube/callback/facebook`
  - `https://api.alaserver.com.br:9443/api/v1/aletube/callback/facebook` (backup)

### Google Cloud Console (https://console.cloud.google.com)
- APIs & Services → Credentials → OAuth 2.0 Client (YouTube)
- Authorized redirect URIs:
  - `https://bestpricetoday.alaserver.com.br/aletube/callback/youtube`
  - `https://bestpricetoday.alaserver.com.br:9443/aletube/callback/youtube` (backup)

### TikTok Developer (https://developers.tiktok.com)
- App → Login configuration
  - `https://api.alaserver.com.br/api/v1/tiktok/callback`
  - `https://api.alaserver.com.br:9443/api/v1/tiktok/callback` (backup)

### Mercado Livre (https://applications.mercadolivre.com.br)
- App → Redirect URI:
  - `https://bestpricetoday.alaserver.com.br/auth/callback`
  - `https://bestpricetoday.alaserver.com.br:9443/auth/callback` (backup)

---

## 11. Google Search Console

- Propriedade: `https://bestpricetoday.alaserver.com.br` (sem porta)
- Sitemap: `https://bestpricetoday.alaserver.com.br/sitemap.xml`
- Propriedade antiga: `https://bestpricetoday.alaserver.com.br:9443/` (legacy)

---

## 12. Bing Webmaster Tools

- Site: `https://bestpricetoday.alaserver.com.br/`
- Verificacao: HTML Meta Tag (`msvalidate.01` no layout.tsx)
- Sitemap: `https://bestpricetoday.alaserver.com.br/sitemap.xml` (95 URLs)
- Arquivo: `/frontend/public/BingSiteAuth.xml`

---

## 13. Analytics

| Servico | ID | Onde configurar |
|---|---|---|
| Google Analytics 4 | `G-D2J769S99H` | `frontend/.env.local` (`NEXT_PUBLIC_GA4_ID`) |
| Microsoft Clarity | `xd51oaxppe` | `frontend/.env.local` (`NEXT_PUBLIC_CLARITY_ID`) |

---

## 14. Arquivos Importantes

### Frontend
- `frontend/src/lib/api.ts` — URLs base (API_BASE, SITE_BASE)
- `frontend/next.config.mjs` — CSP, headers, image domains
- `frontend/.env.local` — NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SITE_URL
- `frontend/public/robots.txt` — robots
- `frontend/public/BingSiteAuth.xml` — verificacao Bing
- `frontend/src/app/layout.tsx` — meta tags (msvalidate.01, OG, etc)

### Backend
- `backend/app/core/config.py` — configuracoes (INTERNAL_API_URL, PUBLIC_SITE_URL, redirect URIs)
- `backend/.env` — todas as chaves e secrets
- `backend/app/api/v1/endpoints/auth.py` — ML redirect URI

### Cloudflare
- `/etc/cloudflared/config.yml` — config do tunnel
- `/etc/cloudflared/52eea050-68dc-4cf4-9c96-f114d501cc53.json` — credenciais
- `~/.cloudflared/cert.pem` — certificado de login

### Nginx
- `/etc/nginx/sites-available/bestprice-frontend-ssl`
- `/etc/nginx/sites-available/bestprice-api-ssl`
- `/etc/nginx/sites-available/bestprice-redirect`

---

## 15. Quando Mudar a URL do Site

Se algum dia precisar mudar a URL (ex: domínio proprio bestprice.com.br):

### Passo a passo:
1. **DNS:** Adicionar novo domínio no Cloudflare + criar tunnel route
2. **Frontend:** Atualizar `api.ts` (API_BASE, SITE_BASE) e `.env.local`
3. **Backend:** Atualizar `config.py` (INTERNAL_API_URL, PUBLIC_SITE_URL) e `.env`
4. **CSP:** Atualizar `next.config.mjs` (connect-src, script-src)
5. **robots.txt:** Atualizar sitemap URL
6. **sitemap.xml:** Regenerar (automatico na proxima build)
7. **OAuth:** Atualizar redirect URIs em TODOS os paineis (Facebook, Google, TikTok, ML)
8. **Google Search Console:** Adicionar nova propriedade + sitemap
9. **Bing Webmaster:** Adicionar novo site + sitemap + verificacao
10. **Rebuild:** `cd /home/alessandro/frontend && rm -rf .next && npx next build`
11. **Restart:** `sudo systemctl restart bestprice-frontend bestprice-backend`
12. **Testar:** `curl -sk https://NOVA_URL/` deve retornar 200

### Quando Mudar o Roteador/Operadora:
1. **IP publico muda** — Cloudflare Tunnel nao precisa de nada (e OUTBOUND)
2. **Port forwarding:** Reconfigurar 9443 (e 8443 se quiser) no novo roteador
3. **Nginx:** Nao precisa mudar nada
4. **DNS:** Nao precisa mudar nada (tunnel resolve automaticamente)

### Quando Reiniciar o Servidor:
1. Todos os servicos sao systemd e iniciam automaticamente no boot:
   - `bestprice-backend`
   - `bestprice-frontend`
   - `cloudflared`
   - `nginx`
2. Scrapers (ml_scraper, amazon_scraper) rodam via cron — tambem automaticos

---

## 16. Troubleshooting

### Site fora do ar
```bash
# 1. Verificar servicos
systemctl is-active bestprice-backend bestprice-frontend cloudflared nginx

# 2. Verificar tunnel
cloudflared tunnel info bestpricetoday

# 3. Testar localhost
curl -s http://localhost:3000/ | head -5
curl -s http://localhost:8000/health

# 4. Testar Cloudflare
curl -sk https://bestpricetoday.alaserver.com.br/ -o /dev/null -w '%{http_code}'

# 5. Testar backup 9443
curl -sk https://bestpricetoday.alaserver.com.br:9443/ -o /dev/null -w '%{http_code}'
```

### API retorna 429 (rate limit)
- Cloudflare pode rate-limitar se o servidor chamar a propria API pelo tunnel
- Solucao: adicionar `127.0.0.1 api.alaserver.com.br` em `/etc/hosts` (temporario)
- Atencao: isso pode quebrar SSL. Remover depois.

### Facebook/Instagram OAuth erro 400
- Redirect URI mismatch → atualizar no Facebook Developer

### YouTube token expirado
- Renovar via refresh_token (ver `aletube.py`)
- Dashboard mostra "❌ Expirado"

### Build do frontend falha
```bash
cd /home/alessandro/frontend
rm -rf .next node_modules/.cache
npx next build
```
