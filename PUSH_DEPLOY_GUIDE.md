# 📤 Guia de Push e Deploy — BestPriceToday / AleTubeGames

> Como o deploy realmente flui neste repo, com as armadilhas que já apanhámos.

## Índice
1. [Mapa dos Repos e Deploys](#mapa-dos-repos-e-deploys)
2. [Playbook 5 Min (copiar e colar)](#playbook-5-min-copiar-e-colar)
3. [Auto-Deploy: o que é automático e o que não é](#auto-deploy-o-que-é-automático-e-o-que-não-é)
4. [Fluxo Padrão Sem Repetição](#fluxo-padrão-sem-repetição)
5. [Diagnóstico: "não chegou no deploy"](#diagnóstico-não-chegou-no-deploy)
6. [Fluxo de Push (caso comum)](#fluxo-de-push-caso-comum)
7. [Fluxo de Vídeos — AleTubeGames](#fluxo-de-vídeos--aletubegames)
8. [Deploy: Vercel (Frontend)](#deploy-vercel-frontend)
9. [Deploy: Hugging Face Spaces (Backend)](#deploy-hugging-face-spaces-backend)
10. [Limitações de Storage no HF Free](#limitações-de-storage-no-hf-free)
11. [Segurança](#segurança)
12. [Erros Comuns (e como resolvi cada um)](#erros-comuns-e-como-resolvi-cada-um)
13. [Checklist Pre-Deploy](#checklist-pre-deploy)
14. [Rollback](#rollback)

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

## Playbook 5 Min (copiar e colar)

Quando estiver tudo confuso, usa este fluxo exatamente nessa ordem:

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

# 0) Estado local e remoto
git status -sb
git remote -v
git branch --show-current

# 1) Confirmar commit no GitHub
git rev-parse HEAD
git ls-remote github -h refs/heads/master

# 2) Deploy Vercel manual (independe do webhook do GitHub)
vercel whoami
vercel --prod --yes

# 3) Verificar se deploy Vercel ficou Ready
vercel ls bestpricetoday --yes | head -n 20

# 4) Push para HF (backend)
git push hf master
```

Se o passo 4 travar/pedir credencial, vai para a seção de diagnóstico abaixo.

---

## Auto-Deploy: o que é automático e o que não é

- `git push github master`:
  - Vercel do frontend costuma atualizar automaticamente.
  - GH Action pode sincronizar `backend/` para o repo `hf_space/` (espelho `alessandro2090`).
- `git push hf master`:
  - Continua necessário para atualizar diretamente o Space `aletubegames/bestpricetoday-api`.

Resumo prático:
- Para frontend, evita repetir `vercel --prod --yes` em todo push.
- Usa deploy manual da Vercel apenas quando o webhook falhar, conta estiver errada, ou precisares forçar um rebuild imediato.

---

## Fluxo Padrão Sem Repetição

Usa este fluxo para evitar loops e comandos duplicados:

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday

# 1) Commit + push no GitHub
git add -A
git commit -m "fix: ..."
git push github master

# 2) Verifica auto-deploy do frontend (sem forçar manual)
vercel inspect bestpricetoday-aaswilel-9706s-projects.vercel.app

# 3) Só se NÃO ficar Ready após alguns minutos, forçar manual
vercel --prod --yes

# 4) Backend no Space principal (obrigatório)
git push hf master
```

Regra anti-loop:
- Não executar `vercel --prod --yes` repetidamente enquanto já existe build em andamento.
- Esperar status passar de `Building` para `Ready` antes de novo trigger.

---

## Diagnóstico: "não chegou no deploy"

### A) Vercel não atualiza

**1. Conta errada no CLI**
```bash
vercel whoami
cat .vercel/project.json
```
- `whoami` e `orgId` precisam apontar para o mesmo projeto.

**2. Push no GitHub não era o problema**
```bash
git rev-parse HEAD
git ls-remote github -h refs/heads/master
```
- Se hashes iguais, o GitHub recebeu.

**3. Forçar produção manual**
```bash
vercel --prod --yes
vercel inspect <url-do-deploy>
```

### B) HF não atualiza

**1. Remote incorreto**
```bash
git remote -v | grep '^hf'
git remote set-url hf https://aletubegames@huggingface.co/spaces/aletubegames/bestpricetoday-api
```

**2. Sem credencial salva para huggingface.co**
```bash
git config --global credential.helper store
# depois execute push e informe:
# Username: aletubegames
# Password: hf_xxx (token write)
git push hf master
```

**3. `git push hf master` trava sem erro claro**
```bash
timeout 25 git ls-remote hf -h refs/heads/master; echo EXIT:$?
```
- `EXIT:124` indica timeout (rede/proxy/firewall/VPN/canal TLS) ou prompt oculto de credencial.

**4. Teste HTTP do Space retorna 401**
```bash
curl -I -m 15 https://huggingface.co/spaces/aletubegames/bestpricetoday-api
```
- `401 Invalid username or password` confirma problema de autenticação para o Space.

### C) Mudanças de `.env` "não sobem"

Isso é esperado: `.env` é ignorado pelo git.

```bash
git check-ignore -v backend/.env .env.local
```

Se precisa dessas variáveis em produção:
- Vercel: configurar no painel de Environment Variables.
- Hugging Face Space: configurar em Settings > Variables and secrets.

### D) Regra de ouro para não perder tempo

1. Primeiro confirme hash local vs GitHub.
2. Depois force Vercel manualmente.
3. Depois faça push HF.
4. Se HF falhar: corrigir remote + credencial antes de qualquer outra coisa.
5. Nunca debuggar código antes de validar conta/token/remotes.

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

### `telegram.error.Conflict: terminated by other getUpdates request`
**Causa:** mais de uma instância com polling Telegram ativo usando o mesmo token.
**Sinais:** logs alternam entre `HTTP/1.1 200 OK` e `HTTP/1.1 409 Conflict` em `getUpdates`.
**Fix operacional:**
1. Escolher apenas uma instância para polling (ex.: apenas `aletubegames` ou apenas `alessandro2090`).
2. Desligar polling nas outras instâncias via variável de ambiente e restart.
3. Garantir que só uma instância rode broadcaster/polling por token.
4. Confirmar em logs que `getUpdates` parou de retornar 409 repetidamente.

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
- [ ] Push GitHub: `git push github master`
- [ ] Push HF principal: `git push hf master`
- [ ] Se Vercel auto-deploy já estiver `Ready`, **não** disparar deploy manual
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
