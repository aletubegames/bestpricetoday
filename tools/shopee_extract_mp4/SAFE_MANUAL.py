#!/usr/bin/env python3
"""
Instruções pra extração manual segura (zero ban risk)

PASSO 1: Abrir Shopee no navegador
  - Ir em https://shopee.com.br
  - Abrir DevTools (F12)
  - Colar isto no console:

%s

PASSO 2: Copiar o JSON que aparece
  - Deve ter ~100 objetos com "slug", "offer", "src"
  - Pode ter alguns "src": null (produtos sem vídeo)

PASSO 3: Salvar como shopee_videos.json
  - Criar file: shopee_videos.json
  - Colar o JSON lá

PASSO 4: Baixar todos os vídeos
  source .venv/bin/activate
  python3 shopee_batch_scraper.py download shopee_videos.json --output .

  Saída: ./videos/001_slug.mp4, 002_slug.mp4, etc

GARANTIAS:
  ✔ Zero chance de ban (é você interagindo, não bot)
  ✔ Vídeos garantidos (se existem no produto)
  ✔ Rápido (1-2min pra extrair, depois ~10min pra baixar)
"""

# Ler o console.js
from pathlib import Path

js_content = Path("shopee_console.js").read_text()

print(__doc__ % js_content)
