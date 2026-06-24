# 🧪 Teste YouTube OAuth

## Como executar

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

# Instalar dependências (primeira vez)
pip install httpx python-dotenv

# Rodar teste
python test_youtube.py
```

## O que o teste faz

✅ **Apenas testa**, não modifica nada:

1. **Lê credenciais do .env**
   - YOUTUBE_CLIENT_ID
   - YOUTUBE_CLIENT_SECRET
   - YOUTUBE_REDIRECT_URI

2. **Testa 3 endpoints Google**
   - Autorização: `accounts.google.com/o/oauth2/v2/auth`
   - Token: `oauth2.googleapis.com/token`
   - Conectividade geral

3. **Valida formato das credenciais**
   - Verifica se CLIENT_ID tem formato correto
   - Verifica se secrets estão configurados

## Saída esperada

```
======================================================================
TESTE DE CONEXÃO YOUTUBE OAUTH
======================================================================

📋 Configuração:
  YOUTUBE_CLIENT_ID: ✅ Configurado
  YOUTUBE_CLIENT_SECRET: ✅ Configurado
  YOUTUBE_REDIRECT_URI: https://bestpricetoday.vercel.app/aletube/callback/youtube

🔗 Testando conectividade com Google OAuth...

  → Testando endpoint de autorização...
    HTTP 302
    ✅ Endpoint respondendo

  → Testando conectividade com oauth2.googleapis.com...
    HTTP 302
    ✅ Servidor respondendo

  → Testando endpoint de token...
    HTTP 400
    ✅ Endpoint respondendo (erro esperado para código inválido)
    └─ Erro: invalid_grant

  → Verificando formato do CLIENT_ID...
    ✅ Formato correto (Google Cloud credentials)

======================================================================
RESUMO
======================================================================

✅ YOUTUBE OAUTH - CONECTADO

Configuração: COMPLETA
  • CLIENT_ID: ✅ Configurado
  • CLIENT_SECRET: ✅ Configurado
  • REDIRECT_URI: Correto

Conectividade: ✅ OK
  • Google OAuth: Respondendo
  • Endpoints: Acessíveis
```

## Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| `❌ NÃO configurado` | SECRET não em .env | Adicionar em backend/.env |
| `❌ Erro de conexão` | Sem internet/firewall | Verificar conectividade |
| `⚠️ Status inesperado` | Resposta HTTP incomum | Verificar credenciais |

## Próximas etapas

Se teste passar:
1. Usuário clica "Conectar YouTube" no frontend
2. Sistema redireciona para Google com URL de autorização
3. Google autentica usuário
4. Google redireciona para REDIRECT_URI com `code`
5. Backend troca `code` por `access_token`
6. Backend publica vídeo no YouTube

## Segurança

✅ Este teste:
- Apenas testa conectividade
- Não modifica credenciais
- Não faz requisições autenticadas
- Não acessa dados sensíveis
