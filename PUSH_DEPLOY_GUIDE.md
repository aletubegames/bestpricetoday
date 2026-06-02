# 📤 Guia de Push e Deploy — BestPriceToday

> Evitar erros comuns ao fazer push e deploy para Vercel e Hugging Face

## Índice
1. [Push para GitHub](#push-para-github)
2. [Deploy no Vercel](#deploy-no-vercel)
3. [Deploy no Hugging Face](#deploy-no-hugging-face)
4. [Checklist Pre-Deploy](#checklist-pre-deploy)
5. [Erros Comuns](#erros-comuns)

---

## Push para GitHub

### ✅ Bom Processo

```bash
# 1. Verificar status
cd /home/alessandro/bin/Git_Repo/BestPriceToday
git status

# 2. Adicionar mudanças
git add -A  # ou git add <arquivo> para arquivo específico

# 3. Verificar diff antes de commitar
git diff --cached  # Verificar o que vai ser commitado

# 4. Commitar com mensagem clara
git commit -m "feat: descrição clara da mudança

- Ponto 1
- Ponto 2
- Ponto 3"

# 5. Fazer push para GitHub (remoto principal)
git push

# 6. Fazer push para Hugging Face (se aplicável)
git push hf master
```

### ❌ Erros Comuns ao Fazer Push

#### Erro: "Nenhuma mudança para fazer push"
```bash
# Causa: Repositório já está sincronizado com remoto
git log --oneline -5  # Verificar commits recentes
git status  # Deve estar "working tree clean"

# Solução: Fazer as mudanças necessárias antes de fazer push
```

#### Erro: Git push lento para Hugging Face
```bash
# Causa: HF pode demorar para processar
# Solução: Usar timeout e monitorar em background

git push hf master  # Deixar rodando
# Ou com timeout:
timeout 120 git push hf master  # Aguarda 2 minutos

# Verificar status depois:
git log --oneline -1  # Ver se o commit está no HEAD
```

---

## Deploy no Vercel

### 🔧 Configuração Inicial

**Arquivo: `vercel.json` (raiz do repositório)**

```json
{
  "buildCommand": "cd frontend && npm run build",
  "installCommand": "cd frontend && npm install",
  "outputDirectory": "frontend/.next",
  "root": "frontend",
  "env": {
    "NEXT_PUBLIC_API_URL": "@next_public_api_url"
  }
}
```

⚠️ **Importante:** 
- `root`: Especifica o diretório da aplicação Next.js
- `outputDirectory`: Onde o Next.js coloca o build
- **NÃO** incluir `startCommand` (erro de configuração)

### ✅ Fluxo de Deploy

```bash
# 1. Fazer mudanças no frontend
cd /home/alessandro/bin/Git_Repo/BestPriceToday/frontend
# ... editar arquivos ...

# 2. Testar localmente
npm run build  # Deve compilar sem erros
npm run dev    # Testar no navegador

# 3. Commitar mudanças
cd /home/alessandro/bin/Git_Repo/BestPriceToday
git add frontend/
git commit -m "feat: descrição da mudança"

# 4. Fazer push (dispara deploy automático)
git push

# ⏳ Vercel detects push → Inicia build automático
# Verificar em: https://vercel.com/aletubegames/bestpricetoday
```

### ❌ Erros Comuns no Vercel

#### Erro: "Couldn't find any `pages` or `app` directory"
```
Causa: vercel.json não está configurado corretamente

Solução:
1. Adicionar `"root": "frontend"` no vercel.json
2. Adicionar `"buildCommand": "cd frontend && npm run build"`
3. Fazer git push para triggar novo deploy
```

#### Erro: "Invalid vercel.json - should NOT have additional property"
```
Causa: Propriedade inválida (ex: startCommand)

Solução:
✅ VÁLIDO:
- buildCommand
- installCommand
- outputDirectory
- root
- env

❌ INVÁLIDO:
- startCommand (não suportado)
- runCommand (não suportado)
```

#### Erro: 416 RANGE_MISSING_UNIT
```
Causa: Arquivo de vídeo sendo servido sem suporte a range requests

Solução:
- Adicionar endpoint que serve vídeos corretamente
- Usar FileResponse do FastAPI
- Converter caminho local para URL pública
```

---

## Deploy no Hugging Face

### ✅ Fluxo de Deploy

```bash
# 1. Fazer mudanças no backend
cd /home/alessandro/bin/Git_Repo/BestPriceToday/backend
# ... editar arquivos ...

# 2. Testar localmente
python -m uvicorn app.main:app --reload

# 3. Verificar sintaxe Python
python -m py_compile app/api/v1/endpoints/aletube.py  # Sem erros = OK

# 4. Commitar mudanças
cd /home/alessandro/bin/Git_Repo/BestPriceToday
git add backend/
git commit -m "fix: descrição da mudança"

# 5. Fazer push (dispara deploy automático)
git push hf master

# ⏳ HF detects push → Inicia rebuild
# Verificar em: https://huggingface.co/spaces/aletubegames/bestpricetoday-api
```

### ❌ Erros Comuns no Hugging Face

#### Erro: "SyntaxError: unexpected character after line continuation character"
```python
# ❌ ERRADO (aspas escapadas incorretamente):
@router.get(\"/serve/{video_id}\")
def serve_video():
    \"\"\"Serve video.\"\"\"
    pass

# ✅ CORRETO:
@router.get("/serve/{video_id}")
def serve_video():
    """Serve video."""
    pass
```

**Por que falhou?** 
- `\` é caractere de escape em Python
- `\"` é para escapar aspas em strings
- Mas em código Python puro, não precisa escapar aspas em decoradores

**Solução:**
```bash
# 1. Verificar sintaxe antes de fazer push
python -m py_compile arquivo.py

# 2. Se houver erro, corrigir antes de commitar
git diff  # Ver mudanças
git add arquivo.py
git commit -m "fix: corrigir sintaxe"
git push hf master
```

#### Erro: "ModuleNotFoundError: No module named 'xyz'"
```
Causa: Dependência não está instalada

Solução:
1. Adicionar ao backend/requirements.txt
2. Commitar
3. Fazer git push hf master
4. HF vai instalar automaticamente
```

#### Erro: "Build falhou" (vago)
```bash
# Verificar logs:
# 1. Acessar https://huggingface.co/spaces/aletubegames/bestpricetoday-api
# 2. Clique em "Settings" → "Logs"
# 3. Ver última build

# Cause comum: Import inválido no app/main.py
# Solução: Testar import localmente:
python -c "from app.api.v1.endpoints import aletube; print('OK')"
```

---

## Checklist Pre-Deploy

### Antes de fazer push (para AMBOS GitHub + HF)

- [ ] **Código**
  - [ ] Sem erros de sintaxe: `python -m py_compile arquivo.py`
  - [ ] Imports corretos e funcionando
  - [ ] Sem caracteres escapados incorretos (`\"` em Python puro)
  - [ ] Funções testadas localmente

- [ ] **Ambiente**
  - [ ] `.env` atualizado se necessário
  - [ ] `requirements.txt` atualizado (backend)
  - [ ] `package.json` atualizado (frontend)
  - [ ] `vercel.json` válido (raiz do repo)

- [ ] **Git**
  - [ ] `git status` limpo (working tree clean)
  - [ ] Commits com mensagens claras
  - [ ] `git diff --cached` revisado antes de commitar

- [ ] **Deploy**
  - [ ] Build local OK: `npm run build` (frontend) ou `python -m uvicorn` (backend)
  - [ ] Sem warnings ou erros

### Após fazer push

- [ ] **GitHub**: `git log --oneline -1` mostra commit
- [ ] **Vercel**: Acessar https://bestpricetoday.vercel.app e testar
- [ ] **Hugging Face**: Acessar https://alessandro2090-bestpricetoday-api.hf.space

---

## Scripts Rápidos

### Deploy Rápido (tudo)

```bash
#!/bin/bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

echo "🔍 Verificando sintaxe Python..."
python -m py_compile backend/app/api/v1/endpoints/*.py || exit 1

echo "📤 Fazendo push para GitHub..."
git push || exit 1

echo "📤 Fazendo push para Hugging Face..."
git push hf master || exit 1

echo "✅ Todos os pushes completos!"
```

### Verificar Deploy Status

```bash
#!/bin/bash

echo "📊 Vercel Status:"
curl -s https://bestpricetoday.vercel.app | grep -o "<title>.*</title>"

echo ""
echo "📊 Hugging Face Status:"
curl -s https://alessandro2090-bestpricetoday-api.hf.space/docs | grep -o "<title>.*</title>" || echo "⏳ HF ainda buildando..."
```

---

## Boas Práticas

### Mensagens de Commit

✅ Boas:
```
feat: adicionar endpoint /aletube/serve para servir vídeos publicamente
fix: corrigir erro 416 convertendo caminho local para URL pública
docs: adicionar guia de push e deploy
refactor: simplificar lógica de publicação de vídeos
```

❌ Ruins:
```
alterações
fix bug
update
ajustes
```

### Frequência de Deploy

- **Local** → **GitHub**: a cada funcionalidade completa
- **GitHub** → **Vercel/HF**: automático ao fazer push
- **Manual** (se necessário): `vercel --prod` (CLI do Vercel)

### Rollback (desfazer deploy)

```bash
# Ver commits recentes
git log --oneline -10

# Voltar para commit anterior
git revert <commit-hash>  # Cria novo commit desfazendo mudanças
git push  # Faz deploy do rollback

# Ou rebase (⚠️ apenas se ninguém fez push depois):
git reset --hard <commit-hash>
git push --force  # ⚠️ Cuidado! Sobrescreve histórico
```

---

## Contato/Debug

Se algum deploy falhar:

1. Verificar logs: `git log --oneline -5`
2. Verificar status: `git status`
3. Verificar remoto: `git remote -v`
4. Verificar sintaxe: `python -m py_compile arquivo.py`
5. Testar local: `npm run build` ou `python -m uvicorn`

---

**Última atualização:** June 1, 2026  
**Autor:** Sistema de Deploy  
**Status:** ✅ Ativo
