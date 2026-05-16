#!/usr/bin/env bash
# sync_hf_deploy.sh — Sincroniza endpoints canônicos para hf_deploy
# Execute antes de cada deploy para o Hugging Face Space.
#
# Regra: backend/app/ é a fonte da verdade.
# backend/hf_deploy/ é um deploy target standalone que replica os endpoints comuns.
#
# Endpoints sincronizados (copiados 1:1):
#   - alerts.py
#   - favorites.py
#   - auth.py       (se existir)
#   - products.py   (se existir)
#
# NÃO sincronizados (admin, links) — exclusivos do backend principal.

set -euo pipefail

CANONICAL="$(dirname "$0")/app/api/v1/endpoints"
HF_ENDPOINTS="$(dirname "$0")/hf_deploy/app/api/v1/endpoints"

SYNC_FILES=("alerts.py" "favorites.py")

echo "🔄 Sincronizando endpoints para hf_deploy..."
for f in "${SYNC_FILES[@]}"; do
  src="$CANONICAL/$f"
  dst="$HF_ENDPOINTS/$f"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "  ✅ $f"
  else
    echo "  ⚠️  $f não encontrado em canonical, pulando"
  fi
done

# Sincroniza schemas (fonte da verdade: backend/app/schemas/schemas.py)
cp "$(dirname "$0")/app/schemas/schemas.py" \
   "$(dirname "$0")/hf_deploy/app/schemas/schemas.py"
echo "  ✅ schemas.py"

echo ""
echo "✅ hf_deploy sincronizado. Verifique o diff antes de fazer push:"
echo "   git diff backend/hf_deploy/"
