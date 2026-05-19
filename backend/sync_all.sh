#!/usr/bin/env bash
# sync_all.sh — Sincroniza backend/app/ → hf_deploy/app/ e hf_space/app/
#
# backend/app/ é a ÚNICA fonte da verdade.
# Execute antes de cada deploy.
#
# NÃO sincronizados (exclusivos do backend principal):
#   - workers/ (cron, broadcaster, bot, alert_checker)
#   - integrations/conversion_tracker.py
#   - integrations/shopee/, integrations/aliexpress/  (clientes raw)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$ROOT/app"
HF_DEPLOY="$ROOT/hf_deploy/app"
HF_SPACE="$(dirname "$ROOT")/hf_space/app"

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

sync_to() {
  local target="$1"
  local label="$2"
  echo ""
  echo "══════════════════════════════════════════════════"
  echo "  Destino: $label"
  echo "══════════════════════════════════════════════════"

  echo "── API endpoints ──────────────────────────────────"
  for f in alerts.py favorites.py auth.py products.py search.py; do
    sync_file "$APP/api/v1/endpoints/$f" "$target/api/v1/endpoints/$f"
  done
  # links.py e tiktok.py vão para ambos
  sync_file "$APP/api/v1/endpoints/links.py"  "$target/api/v1/endpoints/links.py"
  sync_file "$APP/api/v1/endpoints/tiktok.py" "$target/api/v1/endpoints/tiktok.py"

  echo ""
  echo "── Router ─────────────────────────────────────────"
  # Router inclui tiktok em ambos destinos
  cat > "$target/api/v1/router.py" << 'ROUTER'
from fastapi import APIRouter
from app.api.v1.endpoints import search, alerts, favorites, products, auth, admin, links, tiktok

api_router = APIRouter()
api_router.include_router(search.router, tags=["search"])
api_router.include_router(alerts.router, tags=["alerts"])
api_router.include_router(favorites.router, tags=["favorites"])
api_router.include_router(products.router, tags=["products"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(links.router, tags=["links"])
api_router.include_router(tiktok.router, prefix="/tiktok", tags=["tiktok"])
ROUTER
  echo "  ✅ api/v1/router.py (com tiktok)"

  echo ""
  echo "── Schemas ────────────────────────────────────────"
  sync_file "$APP/schemas/schemas.py" "$target/schemas/schemas.py"

  echo ""
  echo "── Providers ──────────────────────────────────────"
  for f in base.py aliexpress.py amazon.py awin.py cuponomia.py kabum.py lomadee.py mercadolivre.py shopee.py; do
    sync_file "$APP/services/providers/$f" "$target/services/providers/$f"
  done

  echo ""
  echo "── Services ───────────────────────────────────────"
  sync_file "$APP/services/ranking/engine.py"    "$target/services/ranking/engine.py"
  sync_file "$APP/services/search.py"            "$target/services/search.py"
  sync_file "$APP/services/ml_token_service.py"  "$target/services/ml_token_service.py"

  echo ""
  echo "── Core ────────────────────────────────────────────"
  for f in config.py cache.py logging.py; do
    sync_file "$APP/core/$f" "$target/core/$f"
  done

  echo ""
  echo "── Models / DB ─────────────────────────────────────"
  sync_file "$APP/models/models.py" "$target/models/models.py"
  sync_file "$APP/db/session.py"    "$target/db/session.py"
}

echo "🔄 Sincronizando backend → hf_deploy e hf_space..."

sync_to "$HF_DEPLOY" "hf_deploy"
sync_to "$HF_SPACE"  "hf_space"

echo ""
echo "════════════════════════════════════════════════════"
echo "✅ Sync completo."
echo ""
echo "Próximos passos:"
echo "  git diff backend/hf_deploy/ hf_space/"
echo "  git add backend/hf_deploy/ hf_space/ && git commit -m 'sync: hf_deploy + hf_space com backend latest'"
echo "  git push"
