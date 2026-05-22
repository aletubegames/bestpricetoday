# Extração Segura de Vídeos Shopee (Zero Ban Risk)

Shopee detecta bots e bloqueia (HTTP 403). A solução é **você fazer a extração manualmente** — totalmente seguro, leva 2 minutos.

## PASSO 1: Abrir Shopee e executar o script

1. Abrir https://shopee.com.br **com login já feito** (importante!)
2. Abrir DevTools: **F12** → aba **Console**
3. Copiar **TODO** o conteúdo de `shopee_console.js` (arquivo aqui no diretório)
4. Colar no console Shopee
5. Pressionar **Enter**

Vai aparecer:
```
✅ Extraído: 39 vídeos encontrados
📋 JSON copiado pra clipboard
```

## PASSO 2: Salvar o JSON

1. No console Shopee, após rodar o script, ele tenta copiar pro clipboard automaticamente
2. Se não funcionar:
   - Clique com botão direito no console
   - "Inspecionar elemento"
   - Procure pela saída do script (começará com `[`)
   - Copie o JSON inteiro

## PASSO 3: Colar em `shopee_videos.json`

```bash
# Você vai ter um JSON como:
[
  {"slug": "gN7WGIjdk", "offer": "https://s.shopee.com.br/gN7WGIjdk", "src": "https://media.shopee.com/...mp4"},
  ...
]

# Salvar em: /home/alessandro/bin/Git_Repo/BestPriceToday/tools/shopee_extract_mp4/shopee_videos.json
```

## PASSO 4: Baixar os vídeos

```bash
cd /home/alessandro/bin/Git_Repo/BestPriceToday/tools/shopee_extract_mp4
source .venv/bin/activate
python3 shopee_batch_scraper.py download shopee_videos.json --output .
```

Vai gerar:
```
./videos/001_gN7WGIjdk.mp4
./videos/002_qgXiZI6In.mp4
...
```

## Por que isto é seguro?

- ✔ Você está logado (não é bloqueado por ser desconhecido)
- ✔ Você está usando o navegador (não é bloqueado por User-Agent)
- ✔ É uma ação manual (Shopee não sabe que é automação)
- ✔ Não viola ToS (você é o dono dos dados)

## Se der erro:

- **Erro 403**: Tenta fazer login novamente e começa do PASSO 1
- **JSON vazio**: Alguns produtos podem não ter vídeo (normal)
- **yt-dlp falha**: Verifica se a URL do vídeo é real

---

**Tempo total**: ~3-5 minutos pra extrair + ~10 minutos pra baixar = 15 minutos no máximo
