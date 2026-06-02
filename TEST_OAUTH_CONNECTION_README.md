# 📋 Teste de Conexão OAuth — Instruções

## Como Executar

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

# Se usar conda/venv do backend
cd backend
python ../TEST_OAUTH_CONNECTION.py
```

## O que o Teste Faz

✅ **Sem fazer rotação de secrets**, apenas testa:

1. **TikTok OAuth**
   - Conectividade com endpoint de autorização
   - Verificar se TIKTOK_CLIENT_KEY está configurado
   - Verificar se TIKTOK_CLIENT_SECRET está configurado

2. **Google OAuth (YouTube)**
   - Conectividade com accounts.google.com
   - Verificar se YOUTUBE_CLIENT_ID está configurado
   - Verificar se YOUTUBE_CLIENT_SECRET está configurado

3. **Facebook/Instagram OAuth**
   - Conectividade com facebook.com
   - Verificar se INSTAGRAM_APP_ID está configurado
   - Verificar se INSTAGRAM_APP_SECRET está configurado

4. **Banco de Dados (PostgreSQL)**
   - Conexão com banco de dados
   - Verificar DATABASE_URL

## Saída Esperada

```
============================================================================
TESTE DE CONEXÃO OAUTH — BestPriceToday
============================================================================

🎵 Testando TikTok OAuth...
▶️ Testando Google OAuth (YouTube)...
👤 Testando Facebook/Instagram OAuth...
💾 Testando Banco de Dados...

============================================================================
RESULTADOS
============================================================================

✅ CONECTÁVEL TikTok
   ├─ API respondendo (HTTP 302)
   ├─ client_key_set: ✅
   ├─ client_secret_set: ✅
   └─ redirect_uri: https://bestpricetoday.vercel.app/tiktok/callback

✅ CONECTÁVEL YouTube
   ├─ Google OAuth respondendo (HTTP 302)
   ├─ client_id_set: ✅
   ├─ client_secret_set: ✅
   └─ redirect_uri: https://bestpricetoday.vercel.app/aletube/callback/youtube

...
```

## Possíveis Resultados

### ✅ CONECTÁVEL
- Secret está configurado
- Endpoint do provedor está respondendo
- Não há bloqueio de firewall/network

### ⚠️ INCOMPLETO
- Secret não está configurado em .env
- Ação necessária: adicionar o secret e reexecutar

### ❌ ERRO
- Erro de conectividade de rede
- Secret inválido
- Ação necessária: verificar firewall, VPN, proxy

## Pré-requisitos

```bash
# Dependências
pip install httpx sqlalchemy sqlalchemy[asyncpg]

# Ou, se usando requirements.txt do backend
cd backend
pip install -r requirements.txt
cd ..
python TEST_OAUTH_CONNECTION.py
```

## Interpretando Resultados

| Status | Significado | Ação |
|--------|-------------|------|
| ✅ CONECTÁVEL | Tudo OK | Nenhuma |
| ⚠️ INCOMPLETO | Secret faltando | Adicionar ao .env |
| ❌ ERRO | Network/config issue | Verificar firewall |

## Notas de Segurança

✅ **Este teste NÃO:**
- Rotaciona secrets
- Modifica credenciais
- Faz requisições autenticadas
- Acessa dados sensíveis

✅ **Este teste SIM:**
- Apenas testa conectividade de rede
- Verifica se secrets estão configurados
- Testa endpoints públicos de OAuth

## Auditoria Completa

Para análise completa de segurança, veja:
```
/home/alessandro/bin/Git_Repo/BestPriceToday/SECURITY_AUDIT_OAUTH.md
```

Contém:
- 12 achados de segurança
- 4 críticos (remediação 48-72h)
- 4 altos (remediação 14 dias)
- 3 médios (remediação 30 dias)
- Código de exemplo para cada fix
