# 🔒 Segurança do Alaserver — Guia Completo

> **Data da auditoria:** 07/07/2026
> **Servidor:** 192.168.100.30 (alaserver)
> **Aplicação:** BestPriceToday v1.0.0

---

## ⚠️ EMERGÊNCIA — Se tudo quebrar

Se algo parar de funcionar após as mudanças de segurança, **reverte tudo com 1 comando**:

```bash
ssh alessandro@192.168.100.30 "bash /home/alessandro/RESTAURAR.sh"
```

Isso restaura:
- nginx (config original)
- backend (main.py, config.py, .env)
- UFW (regras originais)
- ngrok (reinicia se estava rodando)
- SSHd (config original)

**Backup completo em:** `/home/alessandro/backup-pre-pentest-20260707_224702/`

---

## ✅ O que foi feito (resumo)

### Proteções aplicadas (sem downtime)

| # | Proteção | Como | Impacto no BestPriceToday |
|---|----------|------|---------------------------|
| 1 | **UFW Firewall** | 26 regras ativas (libera web, bloqueia VNC/CUPS/8000) | Zero |
| 2 | **VNC/noVNC/CUPS bloqueados** | Portas 5900/6080/631 negadas no UFW | Zero |
| 3 | **fail2ban SSH** | 3 tentativas → ban 1h | Zero |
| 4 | **SSH hardening** | root no, max 3 tentativas, grace 30s, X11 off | Zero |
| 5 | **Porta 8000 bloqueada externa** | API só via Cloudflare Tunnel | Zero |
| 6 | **OpenAPI.json bloqueado** | nginx return 404 | Zero |
| 7 | **Rotas debug bloqueadas** | nginx return 404 para /debug/ | Zero |
| 8 | **ngrok desligado** | Processo morto | Zero |
| 9 | **CORS corrigido** | * → lista de origins permitidas | Zero |
| 10 | **HSTS + X-XSS-Protection** | Headers no next.config.mjs | Zero |
| 11 | **authorized_keys limpo** | Removida linha corrompida | Zero |
| 12 | **9 atualizações de segurança** | apt upgrade | Zero |

---

## 📊 Pentest — Antes vs Depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| Vulnerabilidades | 7 | **0** |
| OK (seguro) | 15/57 | **24/55** |
| OpenAPI.json público | ❌ 102 rotas | ✅ Bloqueado |
| Rotas debug expostas | ❌ 3 rotas | ✅ Bloqueadas |
| ngrok exposto | ❌ API sem Cloudflare | ✅ Desligado |
| CORS curinga (*) | ❌ Aceita tudo | ✅ Só origins permitidas |
| HSTS ausente | ❌ | ✅ Presente |
| X-XSS-Protection ausente | ❌ | ✅ Presente |

---

## 🛡️ Configuração atual detalhada

### UFW Firewall

```
ALLOW  22/tcp      # SSH
ALLOW  80/tcp      # nginx HTTP
ALLOW  443/tcp     # nginx HTTPS
ALLOW  2053/tcp    # nginx Cloudflare
ALLOW  3000/tcp    # Next.js
DENY   8000/tcp    # FastAPI (só via Cloudflare Tunnel)
ALLOW  8443/tcp    # nginx 8443
ALLOW  9443/tcp    # nginx 9443
ALLOW  9444/tcp    # nginx 9444 seller
ALLOW  lo          # loopback
DENY   5900/tcp    # VNC
DENY   6080/tcp    # noVNC
DENY   631/tcp     # CUPS
```

### SSH Hardening

Arquivo: `/etc/ssh/sshd_config.d/99-hardening.conf`
```
PermitRootLogin no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
```

### fail2ban

Arquivo: `/etc/fail2ban/jail.local`
```ini
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 1h
```

### CORS

Arquivo: `/home/alessandro/backend/app/main.py` (middleware)

Origins permitidas (do `.env` / `config.py`):
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `https://bestpricetoday.alaserver.com.br`
- `https://bestpricetoday.com.br`

Qualquer outra origin → sem headers CORS (bloqueada).

### nginx — bloqueio de rotas

Arquivo: `/etc/nginx/sites-enabled/bestprice-api-ssl`

```nginx
# Bloquear OpenAPI/Swagger publico
location = /openapi.json { return 404; }
location = /docs { return 404; }
location = /redoc { return 404; }

# Bloquear rotas debug
location /api/v1/debug/ { return 404; }
location /api/v1/admin/debug/ { return 404; }
```

### Cloudflare Tunnel

Arquivo: `/etc/cloudflared/config.yml`

```yaml
ingress:
  - hostname: bestpricetoday.alaserver.com.br
    service: http://localhost:3000
  - hostname: api.alaserver.com.br
    service: https://localhost:443        # via nginx (com bloqueios)
    originRequest:
      noTLSVerify: true
  - hostname: seller.alaserver.com.br
    service: http://localhost:8100
  - hostname: alaserver.com.br
    service: http://localhost:3000
  - service: http_status:404
```

**Importante:** `api.alaserver.com.br` passa pelo nginx (porta 443) e não direto para o uvicorn (porta 8000). Isso garante que os bloqueios de rotas debug/openapi sejam aplicados.

### Headers de segurança (frontend)

Arquivo: `/home/alessandro/frontend/next.config.mjs`

Headers adicionados em `headers()`:
- `Content-Security-Policy` (já existia)
- `X-Content-Type-Options: nosniff` (já existia)
- `X-Frame-Options: DENY` (já existia)
- `Referrer-Policy: strict-origin-when-cross-origin` (já existia)
- `Permissions-Policy: camera=(), microphone=(), geolocation=()` (já existia)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` **(NOVO)**
- `X-XSS-Protection: 1; mode=block` **(NOVO)**

---

## ⚠️ O que NÃO foi feito (e por quê)

| Item | Razão |
|------|-------|
| Desativar senha SSH | Você usa chaves, mas pode acessar de outras máquinas. Ativar só quando tiver chave em todos os dispositivos. |
| Sudo com senha | `alessandro NOPASSWD` é conveniente. Remover se quiser mais segurança. |
| Rate limiting na API | Precisa de middleware FastAPI (slowapi). Não fiz para não arriscar. |
| 2FA no SSH | Precisa `libpam-google-authenticator`. Futuro. |
| WAF Cloudflare | Já tem Cloudflare na frente, mas regras WAF customizadas não foram configuradas. |

---

## 🔧 Manutenção futura

### Verificar fail2ban
```bash
ssh alessandro@192.168.100.30 "sudo fail2ban-client status sshd"
```

### Verificar UFW
```bash
ssh alessandro@192.168.100.30 "sudo ufw status numbered"
```

### Rodar pentest novamente
```bash
cd /media/alessandro/34C0E9B1C0E97A0E/Git_Repo/BestPriceToday
python3 Pentest.py
```

### Se sessão ML expirar (precisa VNC)
O VNC está bloqueado no UFW. Para fazer login manual do ML:

```bash
# Opção 1: liberar VNC só para seu PC temporariamente
ssh alessandro@192.168.100.30 "sudo ufw allow from 192.168.100.216 to any port 5900 && sudo ufw allow from 192.168.100.216 to any port 6080"

# Fazer login via noVNC: http://192.168.100.30:6080/vnc.html

# Depois do login, bloquear novamente:
ssh alessandro@192.168.100.30 "sudo ufw delete allow from 192.168.100.216 to any port 5900 && sudo ufw delete allow from 192.168.100.216 to any port 6080"
```

### Se ngrok voltar a ser necessário
```bash
ssh alessandro@192.168.100.30 "setsid /usr/local/bin/ngrok http 8000 --log=stdout < /dev/null > /dev/null 2>&1 &"
```
**Atenção:** ngrok expõe a API sem Cloudflare. Use só temporariamente.

### Atualizações de segurança
```bash
ssh alessandro@192.168.100.30 "sudo apt update && sudo apt upgrade -y"
```

---

## 📁 Arquivos modificados no servidor

| Arquivo | O que mudou |
|---------|-------------|
| `/etc/ufw/user.rules` | 26 regras (firewall ativo) |
| `/etc/fail2ban/jail.local` | Jail sshd ativo |
| `/etc/ssh/sshd_config.d/99-hardening.conf` | Hardening SSH |
| `/etc/nginx/sites-enabled/bestprice-api-ssl` | Bloqueio openapi/debug |
| `/etc/cloudflared/config.yml` | API via nginx (não direto) |
| `/home/alessandro/backend/app/main.py` | CORS corrigido |
| `/home/alessandro/frontend/next.config.mjs` | HSTS + X-XSS-Protection |
| `/home/alessandro/backend/.env` | TELEGRAM_CHANNEL_ID corrigido, documentado |
| `/home/alessandro/.ssh/authorized_keys` | Linha corrompida removida |

## 📁 Arquivos modificados localmente

| Arquivo | O que mudou |
|---------|-------------|
| `backend/.env` | Documentação completa de todas as chaves |
| `Pentest.py` | Script de pentest não-destrutivo |
| `SEGURANCA.md` | Este arquivo |

---

## 🚨 Avisos importantes

1. **VNC bloqueado** — se precisar fazer login ML manual, desbloqueie temporariamente (ver acima)
2. **ngrok desligado** — se algo usava a URL ngrok, agora usa Cloudflare Tunnel
3. **CORS restritivo** — se adicionar um novo frontend, adicione a origin em `ALLOWED_ORIGINS` no `.env`
4. **Backup em** `/home/alessandro/backup-pre-pentest-20260707_224702/` — não deletar
5. **Script de restauração** em `/home/alessandro/RESTAURAR.sh` — não deletar
