#!/bin/bash
# Atualiza a base de geolocalização (DB-IP City Lite, gratuita, CC BY 4.0).
# Roda mensalmente via cron. Não precisa reiniciar o backend: o serviço
# reabre o .mmdb automaticamente quando o mtime muda.
set -euo pipefail

DIR="/home/alessandro/backend/data/geoip"
MONTH=$(date -u +%Y-%m)
URL="https://download.db-ip.com/free/dbip-city-lite-${MONTH}.mmdb.gz"
TMP="$(mktemp -d)"

mkdir -p "$DIR"
cd "$TMP"

if ! curl -fsS --max-time 300 -o db.mmdb.gz "$URL"; then
    echo "ERRO: falha ao baixar $URL (base de $(date -u +%Y-%m) ainda não publicada?)"
    exit 1
fi

gunzip -f db.mmdb.gz

# sanidade: mmdb válido e com tamanho plausível
SIZE=$(stat -c%s db.mmdb)
if [ "$SIZE" -lt 50000000 ]; then
    echo "ERRO: arquivo suspeito ($SIZE bytes) — abortando"
    exit 1
fi

if ! /home/alessandro/backend/venv/bin/python - "$TMP/db.mmdb" <<'EOF'
import sys, geoip2.database
r = geoip2.database.Reader(sys.argv[1])
print("ok:", r.city("8.8.8.8").country.iso_code)
EOF
then
    echo "ERRO: mmdb baixado não abre — abortando"
    exit 1
fi

cp -f "$DIR/dbip-city-lite.mmdb" "$DIR/dbip-city-lite.mmdb.prev" 2>/dev/null || true
cp -f db.mmdb "$DIR/dbip-city-lite.mmdb"
echo "OK: base atualizada ($MONTH, $SIZE bytes)"
rm -rf "$TMP"
