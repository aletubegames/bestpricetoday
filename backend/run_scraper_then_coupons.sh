#!/bin/bash
# Roda ml_scraper, espera terminar, depois roda ml_coupon_scraper
cd /home/alessandro/backend
source venv/bin/activate

echo "[$(date)] Aguardando ml_scraper terminar..."
while pgrep -f 'python -m app.workers.ml_scraper' > /dev/null 2>&1; do
    sleep 60
done
echo "[$(date)] ml_scraper terminou. Iniciando ml_coupon_scraper..."

# Espera 30s pra liberar lock do perfil
sleep 30

xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' python -m app.workers.ml_coupon_scraper --headless=True >> ml_coupon_scraper.log 2>&1
echo "[$(date)] ml_coupon_scraper concluido."
