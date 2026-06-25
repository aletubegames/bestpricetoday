#!/bin/bash
# deploy_backend.sh — Sincroniza backend local com alaserver e reinicia o servico
# Uso: ./deploy_backend.sh
set -e

SERVER="alessandro@192.168.100.30"
REMOTE_DIR="/home/alessandro/backend"
LOCAL_DIR="$(dirname "$0")/backend"

echo "🔁 Sincronizando backend para alaserver..."
rsync -avz --checksum \
  "$LOCAL_DIR/app/" \
  "$SERVER:$REMOTE_DIR/app/"

echo "🔄 Reiniciando backend no alaserver..."
ssh "$SERVER" "
  for pid in \$(pgrep -f 'uvicorn app.main:app'); do
    if [ \"\$pid\" != \"\$\$\" ]; then
      kill -9 \$pid 2>/dev/null || true
    fi
  done
  sleep 2
  ( cd $REMOTE_DIR && source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 >> backend.log 2>&1 & )
  sleep 5
  curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/health
"

echo "✅ Backend deployado no alaserver!"
