# 🎬 AleTubeGames — Stack Iniciado ✅

## Status da Stack

✅ **Backend FastAPI**
- Rodando em `http://localhost:8000`
- API disponível em `http://localhost:8000/docs`
- Endpoints `/aletube/*` prontos

✅ **Frontend Next.js**
- Rodando em `http://localhost:3000`
- Pronto para conectar OAuth

✅ **Credenciais OAuth**
- YouTube ✅ Configurado
- Instagram/Facebook ✅ Configurado
- TikTok ✅ Configurado

❌ **Contas Conectadas**
- YouTube ❌ Não conectada
- Instagram ❌ Não conectada
- Facebook ❌ Não conectada
- TikTok ❌ Não conectada

---

## 🎯 Por que os vídeos não postam?

Três motivos críticos:

### 1. **Nenhuma Conta Conectada**
```
SELECT * FROM youtube_accounts;
# Resultado: Vazio ❌

SELECT * FROM instagram_accounts;
# Resultado: Vazio ❌

SELECT * FROM tiktok_accounts;
# Resultado: Vazio ❌
```

Quando você clica em "Publicar", o sistema:
1. Procura `YouTubeAccount` com `is_active=true` → NÃO ENCONTRA
2. Procura `InstagramAccount` com `is_active=true` → NÃO ENCONTRA
3. Procura `TikTokAccount` com `is_active=true` → NÃO ENCONTRA
4. **Todas as plataformas falharam** → status = **FAILED**

### 2. **Arquivo de Vídeo em Caminho Local**
```python
# aletube.py linha 611
video_url = video.file_path  # Ex: /tmp/aletube_videos/video.mp4

# Mas TikTok e Instagram esperam URL PÚBLICA
ig_result = await ig_fb_client.publish_reel_instagram(
    video_url = video.file_path,  # ❌ Deve ser URL como https://...
)

tt_result = await tiktok_client.admin_publish_video(
    video_url = video.file_path,  # ❌ Deve ser URL pública para Pull
)
```

**APIs não conseguem acessar arquivo local.**

### 3. **YouTube Upload Pode Falhar com Token Expirado**
```python
# aletube.py linha 633-636
if yt_acct.token_expires_at and yt_acct.token_expires_at < datetime.now(timezone.utc):
    refreshed = await youtube_client.refresh_token(yt_acct.refresh_token)
    yt_acct.access_token = refreshed["access_token"]
```

**Se não há account, não há token.**

---

## ✅ Solução: Conectar Contas (em 5 passos)

### **Passo 1: Abrir AleTubeGames**
```
Navegador: http://localhost:3000/aletube
```

### **Passo 2: Conectar YouTube**

**Botão:** "Conectar YouTube" (ou "🔗 YouTube")

**O que acontece:**
1. Redirecionamento para: `http://localhost:8000/aletube/auth/youtube`
2. Google OAuth: `https://accounts.google.com/o/oauth2/v2/auth?client_id=...`
3. Você autoriza acesso
4. Google redireciona para: `http://localhost:3000/aletube/callback/youtube?code=XXX&state=YYY`
5. Backend salva em `youtube_accounts`:
   ```sql
   INSERT INTO youtube_accounts (
     channel_id,
     channel_title,
     access_token,
     refresh_token,
     is_active
   ) VALUES (
     'UC...',
     'Seu Canal',
     'ya29...',
     'refresh_...',
     true
   );
   ```
6. Interface mostra: ✅ YouTube conectado

### **Passo 3: Conectar Instagram/Facebook**

**Botão:** "Conectar Facebook" (fornece acesso ao Instagram)

**O que acontece:**
1. Redirecionamento para: `http://localhost:8000/aletube/auth/facebook`
2. Facebook OAuth
3. Você autoriza acesso às páginas e Instagram Business
4. Backend salva em `instagram_accounts` + `facebook_accounts`
5. Interface mostra: ✅ Instagram conectado, ✅ Facebook conectado

### **Passo 4: Conectar TikTok**

**Botão:** "Conectar TikTok"

**O que acontece:**
1. Redirecionamento para: `http://localhost:8000/aletube/auth/tiktok`
2. TikTok OAuth
3. Você autoriza acesso
4. Backend salva em `tiktok_accounts` com `account_type="admin"`
5. Interface mostra: ✅ TikTok conectado

### **Passo 5: Tentar Publicar Novamente**

**Após conectar todas as contas:**

1. Upload vídeo
2. Clique "Publicar"
3. Sistema encontra as contas
4. Publica em todas as plataformas
5. Status muda para: ✅ **published** (não mais failed)
6. Vídeo aparece em YouTube, Instagram, Facebook, TikTok

---

## 🔧 Problema Adicional: Arquivo Local vs URL Pública

### **Situação Atual**
```python
# Vídeo salvo em:
/tmp/aletube_videos/seu_video.mp4

# Mas enviado para APIs como:
file_path = "/tmp/aletube_videos/seu_video.mp4"

# Instagram e TikTok precisam de URL PÚBLICA:
video_url = "https://yourdomain.com/videos/seu_video.mp4"
```

### **Solução**

Você precisa fazer **uma das duas**:

#### **Opção A: Enviar arquivo para Storage (Recomendado)**

```python
# 1. Upload para S3, Azure Blob, ou similar
s3.upload_file(
    "/tmp/aletube_videos/seu_video.mp4",
    "seu-bucket",
    "videos/seu_video.mp4"
)

# 2. Pegar URL pública
video_url = "https://seu-bucket.s3.amazonaws.com/videos/seu_video.mp4"

# 3. Usar URL pública para publicar
ig_result = await ig_fb_client.publish_reel_instagram(
    video_url = video_url  # ✅ URL pública
)
```

#### **Opção B: Servir arquivo via HTTP (Dev Only)**

```python
# No backend, adicionar rota para servir vídeos:

@app.get("/videos/{video_id}")
async def serve_video(video_id: str):
    file_path = f"/tmp/aletube_videos/{video_id}.mp4"
    return FileResponse(file_path, media_type="video/mp4")

# Uso:
video_url = f"http://localhost:8000/videos/{video_id}"

# Mas isto só funciona localmente, não em produção.
```

---

## 📋 Checklist para Fix Completo

### Imediato (próximos 5 min)

- [ ] 🌐 Abrir `http://localhost:3000/aletube`
- [ ] 🔓 Clicar "Conectar YouTube"
- [ ] ✅ Autorizar no Google
- [ ] 🔓 Clicar "Conectar Instagram"
- [ ] ✅ Autorizar no Facebook
- [ ] 🔓 Clicar "Conectar TikTok"
- [ ] ✅ Autorizar no TikTok
- [ ] 📤 Upload novo vídeo
- [ ] 🚀 Clicar "Publicar"
- [ ] ✅ Verificar status = "published" (não "failed")

### Médio Prazo (Próxima hora)

- [ ] Implementar upload para S3 (ou similar)
- [ ] Gerar URLs públicas dos vídeos
- [ ] Testar publicação com URLs públicas
- [ ] Monitorar logs de erro

### Longo Prazo (Esta semana)

- [ ] Criar dashboard de monitoramento
- [ ] Implementar retry automático
- [ ] Adicionar notificações de falha
- [ ] Otimizar compressão de vídeo
- [ ] Implementar analytics

---

## 📊 Diagrama do Fluxo

```
┌─────────────────────────────────────────────────────────────┐
│                    AleTubeGames                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Clique "Publicar"                                          │
│        ↓                                                    │
│  Backend verifica contas ativas                            │
│        ↓                                                    │
│  YouTube:  Encontra? ✅ → Publica | ❌ → Erro            │
│  Instagram: Encontra? ✅ → Publica | ❌ → Erro           │
│  Facebook: Encontra? ✅ → Publica | ❌ → Erro            │
│  TikTok:   Encontra? ✅ → Publica | ❌ → Erro            │
│        ↓                                                    │
│  Status Final:                                             │
│    • Todas OK     → "published" ✅                         │
│    • Todas Erro   → "failed" ❌                            │
│    • Mistas       → "published" ⚠️ (parcial)             │
│        ↓                                                    │
│  Resultado visível em:                                     │
│    • YouTube.com (seu canal)                              │
│    • Instagram (sua conta)                                │
│    • Facebook (sua página)                                │
│    • TikTok (sua conta)                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

ATUAL (❌ failed):
┌─────────────────────┐
│ Clique "Publicar"   │
└──────────┬──────────┘
           ↓
┌─────────────────────────────────────────────┐
│ Backend procura YouTubeAccount              │
│ is_active=true                              │
└──────────┬──────────────────────────────────┘
           ↓
         NÃO ENCONTRA ❌
           ↓
┌─────────────────────────────────────────────┐
│ Status = "failed"                           │
└─────────────────────────────────────────────┘

FUTURO (✅ published):
┌─────────────────────┐
│ Clique "Publicar"   │
└──────────┬──────────┘
           ↓
┌─────────────────────────────────────────────┐
│ Backend procura YouTubeAccount              │
│ is_active=true                              │
└──────────┬──────────────────────────────────┘
           ↓
         ENCONTRA ✅ (você conectou)
           ↓
┌─────────────────────────────────────────────┐
│ Publicar no YouTube                         │
│ Publicar no Instagram                       │
│ Publicar no Facebook                        │
│ Publicar no TikTok                          │
└──────────┬──────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│ Status = "published"                        │
│ Vídeos aparecem em todas as plataformas     │
└─────────────────────────────────────────────┘
```

---

## 🔗 Links Rápidos

| Recurso | URL |
|---------|-----|
| **AleTubeGames** | http://localhost:3000/aletube |
| **API Docs** | http://localhost:8000/docs |
| **Swagger UI** | http://localhost:8000/redoc |
| **Backend Health** | http://localhost:8000/health |

---

## 📝 Notas Técnicas

### Arquivos Chave

```
backend/
├── app/
│   ├── integrations/
│   │   ├── youtube.py         # YouTubeClient
│   │   ├── instagram.py       # InstagramFacebookClient
│   │   └── tiktok.py          # TikTokClient
│   ├── api/v1/endpoints/
│   │   └── aletube.py         # POST /aletube/auth/*, /aletube/publish
│   ├── models/models.py       # YouTubeAccount, InstagramAccount, etc.
│   └── core/config.py         # Credenciais OAuth (YOUTUBE_CLIENT_ID, etc.)
│
frontend/
├── src/app/aletube/
│   ├── page.tsx               # Dashboard principal
│   └── callback/
│       ├── youtube/page.tsx   # Callback YouTube
│       ├── instagram/page.tsx # Callback Instagram
│       └── tiktok/page.tsx    # Callback TikTok
```

### Variáveis de Ambiente Necessárias

```bash
# backend/.env

# YouTube
YOUTUBE_CLIENT_ID=369034326111-gb97rqk760b3t93qhs7im2l2c1e3elap.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX...m8ZH
YOUTUBE_REDIRECT_URI=http://localhost:3000/aletube/callback/youtube

# Instagram/Facebook
INSTAGRAM_APP_ID=xxx
INSTAGRAM_APP_SECRET=xxx
FACEBOOK_REDIRECT_URI=http://localhost:3000/aletube/callback/facebook

# TikTok
TIKTOK_CLIENT_KEY=awllka8qo05dhkri
TIKTOK_CLIENT_SECRET=MjJUon...h6ns
TIKTOK_REDIRECT_URI=http://localhost:3000/aletube/callback/tiktok

# Banco de Dados
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=rediss://...
```

---

## 🚨 Próximos Passos Críticos

1. **Agora**: Conectar as 4 contas de rede social
2. **Depois**: Testar publicação com novo vídeo
3. **Depois**: Resolver problema do arquivo local vs URL pública (S3)
4. **Depois**: Implementar retry automático e logging
5. **Depois**: Preparar para produção

---

**Status:** 🟡 **Em Progresso**  
**Bloqueador:** Contas não conectadas  
**ETA para Fix:** 10 minutos (conectar contas)  
**ETA para Produção:** 2-3 horas (incluindo S3)
