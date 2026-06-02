# 🔍 Investigação: Por que AleTubeGames não posta vídeos

## Problema Identificado

Todos os 3 vídeos enviados para AleTubeGames têm status **FAILED**:

```
Sfiii3Nr1 0 Tricksonme Vs New Hex Long  →  failed
Onepiece Demo                           →  failed
Onepiece Demo                           →  failed
```

## Raiz Causa 🎯

**Nenhuma conta de rede social está conectada ao sistema.**

A lógica de publicação em `aletube.py` (linha 629):

```python
yt_acct = (await db.execute(
    select(YouTubeAccount).where(YouTubeAccount.is_active == True)
)).scalar()

if not yt_acct:
    results_by_platform["youtube"] = {
        "status": "error", 
        "error": "Conta YouTube não conectada"
    }
```

### Estado Atual do Banco de Dados

| Tabela | Status |
|--------|--------|
| `youtube_accounts` | 🔴 VAZIA |
| `instagram_accounts` | 🔴 VAZIA |
| `facebook_accounts` | 🔴 VAZIA |
| `tiktok_accounts` | 🔴 VAZIA |

Quando tenta publicar:
1. Sistema procura por conta YouTube ativa → não encontra → erro
2. Sistema procura por conta Instagram ativa → não encontra → erro
3. Sistema procura por conta Facebook ativa → não encontra → erro
4. Sistema procura por conta TikTok ativa → não encontra → erro
5. **Todas as plataformas falharam** → status = **FAILED**

## Fluxo Correto de Funcionamento

```
1. Admin conecta conta YouTube
   ↓
2. Sistema salva em "youtube_accounts":
   - access_token (OAuth token)
   - refresh_token (para renovar)
   - channel_id
   - channel_title
   - is_active = true
   ↓
3. Admin faz upload de vídeo
   ↓
4. Admin clica "Publicar"
   ↓
5. Sistema:
   - Busca conta YouTube com is_active=true ✅ ENCONTRA
   - Valida token (refresh se expirado)
   - Upload vídeo para YouTube API
   - Salva video_id
   - status = PUBLISHED ✅
```

## Solução: Conectar Contas

### Passo 1: Acessar endpoints de autenticação

Você precisa fazer OAuth com cada plataforma:

**YouTube:**
```
GET /aletube/auth/youtube
→ Redireciona para Google
→ Usuário autoriza
→ Google redireciona para /aletube/callback/youtube?code=XYZ&state=ABC
→ Sistema salva access_token em youtube_accounts
→ is_active = true
```

**Instagram/Facebook:**
```
GET /aletube/auth/facebook
→ Redireciona para Facebook
→ Usuário autoriza
→ Facebook redireciona para /aletube/callback/facebook?code=XYZ
→ Sistema salva access_token em instagram_accounts
→ Sistema salva access_token em facebook_accounts
→ is_active = true
```

**TikTok:**
```
GET /aletube/auth/tiktok
→ Redireciona para TikTok
→ Usuário autoriza
→ TikTok redireciona para /aletube/callback/tiktok?code=XYZ
→ Sistema salva access_token em tiktok_accounts
→ account_type = admin
→ is_active = true
```

### Passo 2: Verificar contas conectadas

```bash
# Verificar quais contas estão configuradas
GET /aletube/accounts

# Esperado:
{
  "youtube": {"status": "connected", "channel": "..."},
  "instagram": {"status": "connected", "username": "..."},
  "facebook": {"status": "connected", "page": "..."},
  "tiktok": {"status": "connected", "user": "..."}
}
```

### Passo 3: Testar publicação

Depois de conectar as contas:
```bash
POST /aletube/publish
{
  "video_id": "...",
  "platforms": ["youtube", "instagram", "facebook", "tiktok"]
}
→ status = "published" ✅
```

## Checklist para Fix

### Backend

- [ ] **OAuth Credentials configurados em `.env`**
  - `YOUTUBE_CLIENT_ID`
  - `YOUTUBE_CLIENT_SECRET`
  - `INSTAGRAM_APP_ID`
  - `INSTAGRAM_APP_SECRET`
  - `TIKTOK_CLIENT_KEY`
  - `TIKTOK_CLIENT_SECRET`
  - etc.

- [ ] **Backend rodando**
  ```bash
  cd backend
  python -m uvicorn app.main:app --reload
  ```

- [ ] **Banco PostgreSQL rodando**
  ```bash
  docker run -d -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres
  ```

- [ ] **Tabelas criadas**
  ```bash
  alembic upgrade head
  ```

### Frontend

- [ ] **Acessar AleTubeGames no frontend**
  ```
  http://localhost:3000/aletube
  ```

- [ ] **Clicar em "Conectar YouTube"**
  → Ser redirecionado para Google
  → Autorizar
  → Retornar ao AleTubeGames
  → Ver mensagem "✅ YouTube conectado"

- [ ] **Clicar em "Conectar Instagram"**
  → Mesmo processo

- [ ] **Clicar em "Conectar Facebook"**
  → Mesmo processo

- [ ] **Clicar em "Conectar TikTok"**
  → Mesmo processo

### Testa Publicação

- [ ] **Upload vídeo**
  ```
  POST /aletube/upload
  body: form-data
    file: (seu_video.mp4)
    title: "Teste"
    platforms: ["youtube", "instagram", "facebook", "tiktok"]
  ```

- [ ] **Publicar**
  ```
  POST /aletube/publish
  body: {"video_id": "...", "platforms": ["youtube"]}
  ```

- [ ] **Verificar resultado**
  ```
  GET /aletube/videos
  → status deve ser "published", não "failed"
  → youtube_video_id deve estar preenchido
  ```

## Visualização do Problema

```
┌─────────────────────────────────────────────────────┐
│           AleTubeGames - Status Atual               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  YouTube:  ❌ Não Conectado                        │
│  Instagram:❌ Não Conectado                        │
│  Facebook: ❌ Não Conectado                        │
│  TikTok:   ❌ Não Conectado                        │
│                                                     │
│  Resultado: Publicação IMPOSSÍVEL                  │
│                                                     │
│  Ação Necessária:                                  │
│  → Conectar pelo menos 1 plataforma                │
│                                                     │
└─────────────────────────────────────────────────────┘

         ↓ Depois de conectar

┌─────────────────────────────────────────────────────┐
│           AleTubeGames - Status Esperado            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  YouTube:  ✅ Conectado (channel_id: UC...)       │
│  Instagram:✅ Conectado (username: @...)          │
│  Facebook: ✅ Conectado (page: BestPriceToday)   │
│  TikTok:   ✅ Conectado (admin mode)              │
│                                                     │
│  Resultado: Publicação FUNCIONANDO                 │
│                                                     │
│  Videos será publicado em todas as plataformas!   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Próximas Ações

1. **Configurar `.env` com credenciais corretas**
2. **Iniciar backend + banco de dados**
3. **Acessar frontend em http://localhost:3000/aletube**
4. **Conectar contas (YouTube, Instagram, Facebook, TikTok)**
5. **Tentar publicar vídeo novamente**
6. **Verificar se o vídeo aparece nas plataformas**

---

**Status:** 🔴 BLOQUEADO  
**Razão:** Nenhuma conta conectada  
**Impacto:** 100% dos uploads falham  
**Severidade:** CRÍTICA
