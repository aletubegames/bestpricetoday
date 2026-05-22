# Shopee Batch Video Scraper

Extrai e baixa vídeos de produtos Shopee a partir de CSV exportado.

## Fluxo

### 1. Preparar CSV
Exporte produtos do Shopee Affiliate Manager como CSV. Deve conter colunas:
- `Product Link`
- `Offer Link`

Arquivo: `shopee_batch_20250522.csv` (exemplo)

### 2. Gerar Script de Extração

```bash
python3 shopee_batch_scraper.py shopee_batch_20250522.csv --output .
```

Gera: `shopee_console.js`

### 3. Executar Script no Browser

1. Abra https://shopee.com.br em uma aba
2. Pressione `F12` → aba **Console**
3. Cole **TODO** o conteúdo de `shopee_console.js`
4. Pressione Enter

O script irá:
- Extrair URLs de vídeo dos 100 produtos
- Aplicar delays adaptativos para evitar bloqueio
- Rotacionar User-Agents
- Detectar rate limits e pausar automaticamente
- Salvar resultado em `shopee_videos.json` (auto-download)

**Tempo esperado:** 5-10 minutos (com proteção anti-bot)

### 4. Baixar Vídeos

Coloque `shopee_videos.json` neste diretório e rode:

```bash
python3 shopee_batch_scraper.py download shopee_videos.json --output .
```

Requer `yt-dlp`:
```bash
pip install yt-dlp
```

Vídeos serão salvos em: `./videos/`

## Proteção Anti-Bot

Script implementa:
- ✅ User-Agent rotation (Chrome, Firefox, Edge)
- ✅ Delays adaptativos (800-1500ms entre requests)
- ✅ Headers realistas (Referer, Accept-Language, etc)
- ✅ Detecção de rate-limit (HTTP 429)
- ✅ Pausas de 5-8s a cada 15 produtos
- ✅ Pausa de 15s se bloqueado

Se Shopee bloquear (mensagens de erro crescentes):
- **Aguarde 30-60 minutos** antes de tentar novamente
- Considere usar **VPN** ou **proxy residencial**
- Divida o CSV em lotes menores (ex: 30 produtos por sessão)

## Nomes de Arquivo

Vídeos salvos com formato:
```
001_gN7WGIjdk.mp4
002_qgXiZI6In.mp4
...
```

Onde `XXX` é o índice e `slug` é a oferta Shopee.

## Troubleshooting

### "shopee_videos.json" não baixa
- Verifique se bloqueador de pop-ups está ativo (desative)
- Verifique console do browser (F12) para erros de JS

### Muitos "—" (sem vídeo)
- Normal: nem todo produto tem vídeo
- Shopee pode estar bloqueando requisições
- Tente novamente em outro horário

### yt-dlp falha em alguns vídeos
- Alguns CDNs podem ter proteção CORS
- Experimente baixar manualmente via `ffmpeg`

## Estrutura

```
shopee_extract_mp4/
├── shopee_batch_scraper.py      # Script principal
├── shopee_batch_20250522.csv    # CSV de entrada
├── shopee_console.js            # Script JS (gerado)
├── shopee_videos.json           # JSON com URLs (gerado)
└── videos/                       # Vídeos baixados (gerado)
    ├── 001_slug.mp4
    ├── 002_slug.mp4
    └── ...
```

## API

### Extrair
```bash
python3 shopee_batch_scraper.py extract <csv> [--output <dir>]
```

### Baixar
```bash
python3 shopee_batch_scraper.py download <json> [--output <dir>]
```

### Fallback (compatibilidade)
```bash
python3 shopee_batch_scraper.py shopee_batch_20250522.csv
```

---

**Última atualização:** 2025-05-22  
**Compatibilidade:** Python 3.9+ | Shopee.com.br
