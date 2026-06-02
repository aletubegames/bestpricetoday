# 📤 Guia de Push e Deploy — BestPriceToday / AleTubeGames

> Como o deploy realmente flui neste repo, com as armadilhas que já apanhámos.

## Índice
1. [Mapa dos Repos e Deploys](#mapa-dos-repos-e-deploys)
2. [Fluxo de Push (caso comum)](#fluxo-de-push-caso-comum)
3. [Fluxo de Vídeos — AleTubeGames](#fluxo-de-vídeos--aletubegames)
4. [Deploy: Vercel (Frontend)](#deploy-vercel-frontend)
5. [Deploy: Hugging Face Spaces (Backend)](#deploy-hugging-face-spaces-backend)
6. [Limitações de Storage no HF Free](#limitações-de-storage-no-hf-free)
7. [Segurança](#segurança)
8. [Erros Comuns (e como resolvi cada um)](#erros-comuns-e-como-resolvi-cada-um)
9. [Checklist Pre-Deploy](#checklist-pre-deploy)
10. [Rollback](#rollback)

---

## Mapa dos Repos e Deploys

```
/home/alessandro/bin/Git_Repo/BestPriceToday/   ← repo principal (master)
├── frontend/      ─→ Vercel (auto-deploy ao push em github)
├── backend/       ─→ HF Space "aletubegames/bestpricetoday-api"  (push manual: git push hf master)
└── hf_space/      ← repo INDEPENDENTE (main), espelho do backend, deploya em
                     HF Space "alessandro2090/bestpricetoday-api"
                     ⚠ Auto-sincronizado do GitHub via GH Action (commits "AleBot — deploy: sync from GitHub <hash>")
```

**Remotes do repo principal** (`git remote -v`):
- `github` → `https://github.com/aletubegames/bestpricetoday.git`
- `hf`     → `https://huggingface.co/spaces/aletubegames/bestpricetoday-api`

**Remote do `hf_space/`** (subdir, repo separado):
- `origin` → `https://huggingface.co/spaces/alessandro2090/bestpricetoday-api`

> **Implicação chave:** mudanças em `backend/` precisam de push manual para `hf` (e o GH Action propaga até `hf_space/`). Mudanças feitas diretamente em `hf_space/` ficam **fora-de-sync** com `backend/` e podem ser sobrescritas pelo auto-sync. **Edita sempre `backend/`**, nunca `hf_space/` à mão.

---

## Fluxo de Push (caso comum)

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

# 1. Verificar estado
git status
git diff                                      # mudanças unstaged
python -m py_compile backend/app/api/v1/endpoints/*.py    # sintaxe Python

# 2. Stage + commit
git add -A
git diff --cached                             # rever antes
git commit -m "feat: descrição clara

- ponto 1
- ponto 2"

# 3. Push GitHub (dispara Vercel + GH Action de sync para hf_space/)
git push                                      # equivale a: git push github master

# 4. Push HF Space (backend → aletubegames/bestpricetoday-api)
git push hf master
```

**Após push, esperar:**
- Vercel: ~1–2 min para o build do frontend.
- HF Space (`aletubegames`): ~2–5 min para rebuild.
- HF Space (`alessandro2090`): aguarda o GH Action correr + push automático.

---

## Fluxo de Vídeos — AleTubeGames

Endpoint principal: `POST /aletube/publish`. Caminho que um `.mp4` faz:

```
Upload  → /app/videos/{video_id}.mp4   (configurável via ALETUBE_VIDEOS_DIR)
Publish → YouTube  (upload bytes via API)
       → Facebook (upload bytes via API)
       → TikTok    (envia URL pública /aletube/serve/{video_id})
       → Instagram (envia URL pública /aletube/serve/{video_id})
Cleanup → se TODAS as plataformas selecionadas retornaram "ok",
          ficheiro local é apagado em background após 180s
          (delay dá tempo a TikTok/IG buscarem por URL antes de sumir).
```

**Endpoint de fallback `/aletube/serve/{video_id}`** procura o ficheiro em:
1. `video.file_path` (caminho gravado no DB)
2. `/app/videos/{id}.mp4`
3. `/tmp/aletube_videos/{id}.mp4`

Se nenhum existe → 404 com instrução de re-upload.

**Status final no DB:**
- `published` → pelo menos 1 plataforma OK
- `failed`   → todas erro

> O cleanup **só** corre se TODAS deram `ok`. Se uma falhou, o ficheiro fica para retry.

---

## Deploy: Vercel (Frontend)

**`vercel.json` (raiz):**
```json
{
  "buildCommand": "cd frontend && npm run build",
  "installCommand": "cd frontend && npm install",
  "outputDirectory": "frontend/.next",
  "root": "frontend"
}
```

⚠ Propriedades **não suportadas** (causam erro de build): `startCommand`, `runCommand`.

**Testar local antes:**
```bash
cd frontend
npm run build       # tem de compilar sem erros
npm run dev         # smoke test
```

---

## Deploy: Hugging Face Spaces (Backend)

```bash
# Edita backend/, NUNCA hf_space/
cd backend
# ... edita ...
python -m py_compile app/api/v1/endpoints/aletube.py

cd ..
git add backend/
git commit -m "fix: ..."
git push                    # GitHub + dispara GH Action de sync para hf_space/
git push hf master          # HF Space aletubegames
```

**Verificar deploy:**
- https://huggingface.co/spaces/aletubegames/bestpricetoday-api → tab **Logs**
- https://alessandro2090-bestpricetoday-api.hf.space/docs

**Se o GH Action falhar** (sync para `alessandro2090` não acontece): pode-se forçar manualmente
```bash
cd hf_space
git pull --rebase origin main
# (se necessário copiar mudanças de backend/ aqui à mão — última opção)
git push origin main
```

---

## Limitações de Storage no HF Free

> Esta foi a causa raiz do bug "todos os vídeos com status failed" em 1 Jun 2026.

- HF Spaces na **conta free não têm filesystem persistente**. Tanto `/tmp` como `/app/videos` são apagados em qualquer **rebuild ou restart** do container.
- O `os.makedirs(VIDEOS_DIR, exist_ok=True)` à boot recria a pasta vazia.
- Logo, após reboot, vídeos antigos ficam órfãos no DB e o endpoint `/aletube/serve/{id}` devolve 404 → TikTok/Instagram falham → status `failed`.

**Mitigações já em produção:**
1. `ALETUBE_VIDEOS_DIR=/app/videos` (em vez de `/tmp`, ligeiramente mais estável durante a vida do container).
2. Fallback multi-path no `/aletube/serve/{id}`.
3. **Cleanup automático após publish bem-sucedido** → mantém disco limpo, evita vídeos antigos a acumular e a desaparecer só no próximo restart.

**Soluções definitivas (futuro, opcional):**
- HF Persistent Storage (pago, ~$5/mês) → monta `/data` permanente.
- Cloudflare R2 grátis (10 GB) — **NÃO está configurado neste projeto** (verificado: só há referências a `CF-Connecting-IP` em `app/core/rate_limit.py`, nada de R2/S3).
- Upload direto bytes para TikTok/IG (eliminar URL pública intermediária).

---

## Segurança

⚠ **Token HF exposto em `hf_space/.git/config`** (descoberto em 1 Jun 2026):

```
url = https://alessandro2090:hf_oQjGYG...@huggingface.co/...
```

**Acção recomendada:**
1. Revogar o token em https://huggingface.co/settings/tokens
2. Gerar novo token
3. Reconfigurar com credential helper:
   ```bash
   git remote set-url origin https://huggingface.co/spaces/alessandro2090/bestpricetoday-api
   git config --global credential.helper store
   # próximo push pede credenciais e armazena em ~/.git-credentials (modo 600)
   ```

Mesma verificação em `.git/config` do repo principal (remote `hf`).

**Outros segredos:** `.env` está no `.gitignore` (verificar `git ls-files | grep env` → não deve listar nada com segredo).

---

## Erros Comuns (e como resolvi cada um)

### `416 RANGE_MISSING_UNIT` ao publicar vídeo
**Causa:** servir ficheiro local sem suporte a range requests, ou o ficheiro não existir.
**Fix:** endpoint dedicado com `FileResponse` e fallback multi-path.

### Todos os vídeos com `status: failed` após upload OK
**Causa:** filesystem efêmero do HF — ficheiros somem entre upload e publish.
**Fix:** mover para `/app/videos`, fallback multi-path, cleanup pós-publish.

### `SyntaxError: unexpected character after line continuation character`
**Causa:** aspas escapadas (`\"`) em código Python puro (típico de copy/paste de JSON).
**Fix:** usar aspas normais `"..."` em decoradores/strings Python.

### `! [rejected] HEAD -> main (fetch first)` em `git push origin` (hf_space)
**Causa:** GH Action criou commit `AleBot — deploy: sync from GitHub <hash>` antes do meu push manual.
**Fix:** `git pull --rebase origin main` e re-push. Ou, melhor, **não editar `hf_space/` à mão**.

### `fatal: no submodule mapping found in .gitmodules for path 'hf_space'`
**Causa:** `hf_space/` parece submódulo mas não tem entrada `.gitmodules`. É repo independente colocalizado.
**Fix:** entrar com `cd hf_space` e tratar como repo separado.

### `vercel.json - should NOT have additional property`
**Causa:** propriedade não suportada (`startCommand`).
**Fix:** remover. Propriedades válidas: `buildCommand`, `installCommand`, `outputDirectory`, `root`, `env`.

### Build HF falha com `ModuleNotFoundError`
**Causa:** dependência ausente em `backend/requirements.txt`.
**Fix:** adicionar, commit, push.

---

## Checklist Pre-Deploy

- [ ] **Editaste `backend/`, não `hf_space/`?** (regra dura)
- [ ] `python -m py_compile backend/app/**/*.py` sem erros
- [ ] `cd frontend && npm run build` sem erros (se mexeste no frontend)
- [ ] `git status` limpo após `git add`
- [ ] `git diff --cached` revisado
- [ ] `requirements.txt` / `package.json` actualizados se houver dep nova
- [ ] Mensagem de commit descritiva (`feat:`, `fix:`, `docs:`, `refactor:`)
- [ ] **Push duplo:** `git push` **e** `git push hf master`
- [ ] Verificar logs do HF Space após ~3 min
- [ ] Smoke test: abrir frontend e fazer 1 acção real

---

## Rollback

```bash
# Ver últimos commits
git log --oneline -10

# Rollback seguro (cria commit revert, preserva histórico)
git revert <hash>
git push
git push hf master

# Rollback hard (⚠ apenas se ninguém puxou)
git reset --hard <hash>
git push --force-with-lease
git push hf master --force-with-lease
```

---

**Última atualização:** 1 Jun 2026 — após bug-fix de persistência de vídeos AleTubeGames.
