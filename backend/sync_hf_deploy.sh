#!/usr/bin/env bash
# sync_hf_deploy.sh — Sincroniza backend/app/ → backend/hf_deploy/app/
# Execute antes de cada deploy para o Hugging Face Space.
#
# Regra: backend/app/ é a fonte da verdade.
# backend/hf_deploy/ é um deploy target standalone que replica os módulos comuns.
#
# NÃO sincronizados (exclusivos do backend principal):
#   - api/v1/endpoints/admin.py
#   - api/v1/endpoints/links.py
#   - workers/ (cron, broadcaster, bot, alert_checker)
#   - integrations/ (conversion_tracker)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$ROOT/app"
HF="$ROOT/hf_deploy/app"

sync_file() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "  ✅ ${src#$ROOT/}"
  else
    echo "  ⚠️  ${src#$ROOT/} não encontrado — pulando"
  fi
}

echo "🔄 Sincronizando hf_deploy com backend canonical..."
echo ""

echo "── API endpoints ──────────────────────────────────────────────"
for f in alerts.py favorites.py auth.py products.py search.py stats.py; do
  sync_file "$APP/api/v1/endpoints/$f" "$HF/api/v1/endpoints/$f"
done

echo ""
echo "── Schemas ────────────────────────────────────────────────────"
sync_file "$APP/schemas/schemas.py" "$HF/schemas/schemas.py"

echo ""
echo "── Providers (todos) ──────────────────────────────────────────"
for f in base.py aliexpress.py amazon.py awin.py cuponomia.py kabum.py lomadee.py mercadolivre.py shopee.py; do
  sync_file "$APP/services/providers/$f" "$HF/services/providers/$f"
done

echo ""
echo "── Services (ranking, search) ─────────────────────────────────"
sync_file "$APP/services/ranking/engine.py"  "$HF/services/ranking/engine.py"
sync_file "$APP/services/search.py"          "$HF/services/search.py"
sync_file "$APP/services/ml_token_service.py" "$HF/services/ml_token_service.py"

echo ""
echo "── Core ────────────────────────────────────────────────────────"
for f in config.py cache.py logging.py; do
  sync_file "$APP/core/$f" "$HF/core/$f"
done

echo ""
echo "── Models / DB ─────────────────────────────────────────────────"
sync_file "$APP/models/models.py"   "$HF/models/models.py"
sync_file "$APP/db/session.py"      "$HF/db/session.py"

echo ""
echo "✅ hf_deploy sincronizado."
echo ""
echo "Próximos passos:"
echo "  git diff backend/hf_deploy/"
echo "  git add backend/hf_deploy/ && git commit -m 'sync: hf_deploy com backend latest'"
echo "  git push"
