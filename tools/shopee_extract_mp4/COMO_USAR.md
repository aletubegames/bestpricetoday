# 🎬 Shopee Extract MP4 - Extrator de Produtos com Vídeos

## O que é?
Suite para extrair produtos do Shopee via links curtos, baixar vídeos MP4 e gerar CSVs para conteúdo TikTok/Reels.

## Fluxo completo

```
shopee_products.csv
        │
        ▼
  generate_script.py          ← Python lê CSV, gera JS com links
        │
        ▼
  console_script.js           ← Cole no F12 da Shopee (logado)
        │
        ├─── shopee_videos.csv (gerado pelo browser)
        │         slug,nome,preco,preco_original,desconto_pct,
        │         avaliacao,vendidos,estoque,tem_video,url,descricao
        │
        └─── *.mp4 (vídeos baixados na pasta de downloads)
```

## Passo a passo

### 1. Preparar shopee_products.csv
CSV com colunas: `Item Id, Item Name, Price, Sales, Shop Name, Commission Rate, Commission, Product Link, **Offer Link**`

A coluna `Offer Link` deve conter links curtos `s.shopee.com.br/xxxxx`.

### 2. Gerar o script JS
```bash
cd tools/shopee_extract_mp4/

# básico (todos os produtos)
python3 generate_script.py

# filtrar por comissão mínima
python3 generate_script.py --min-commission 10

# limitar quantidade
python3 generate_script.py --limit 50

# ambos filtros
python3 generate_script.py --min-commission 5 --limit 30

# CSV customizado
python3 generate_script.py --file /caminho/produtos.csv

# output customizado
python3 generate_script.py --output-js meu_script.js --output-csv videos.csv
```

Saída:
- `console_script.js` — pronto para colar no F12
- `shopee_videos.csv` — template vazio (backup do anterior se existir)

### 3. Executar no navegador
1. Acesse `https://shopee.com.br` (logado)
2. Abra F12 → Console
3. Cole o conteúdo de `console_script.js`
4. Aguarde (cada produto leva ~8-12s)

O script mostra progresso em overlay no canto inferior direito:
- Total / Feitos / Pendentes
- Nome, preço, avaliação de cada produto
- Ícones: ✓ vídeo baixado | — sem vídeo | ✗ erro

### 4. Resultado
Ao final o script gera download automático de:
- `shopee_videos.csv` — dados de todos os produtos processados
- `*.mp4` — um vídeo por produto (pasta de downloads do browser)

### 5. Retry automático
Timeout é salvo em `localStorage`. Na próxima rodada os produtos com timeout
são reprocessados. Para resetar:
```javascript
localStorage.removeItem('shopee_dl_progress');
localStorage.removeItem('shopee_csv_data');
```

## Argumentos do generate_script.py

| Arg | Default | Descrição |
|-----|---------|-----------|
| `--file` | `shopee_products.csv` | CSV de origem |
| `--output-js` | `console_script.js` | JS de saída |
| `--output-csv` | `shopee_videos.csv` | CSV template de saída |
| `--min-commission` | `0` | Filtra comissão mínima % |
| `--limit` | `0` (todos) | Limita N produtos |

## Estrutura de dados

### shopee_products.csv (entrada)
```csv
Item Id,Item Name,Price,Sales,Shop Name,Commission Rate,Commission,Product Link,Offer Link
16692338189,Produto XYZ,29.90,1mi+,Loja A,14%,R$1.93,https://...,https://s.shopee.com.br/xxxxx
```

### shopee_videos.csv (saída do browser)
```csv
slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao
xxxxx,Produto XYZ,29.90,49.90,40%,4.8,500,1932,true,https://...,"Descrição..."
```

## Problemas comuns

| Problema | Solução |
|----------|---------|
| "popup bloqueado" | Libere popups para shopee.com.br |
| Timeout em produto | Re-rodar o script (retry automático) |
| 0 links extraídos | Verificar coluna `Offer Link` no CSV |
| Vídeo não baixa | Produto não tem vídeo na API; fallback tenta via <video> src |
| COMO_USAR.md desatualizado | Rodar `generate_script.py` novamente |

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `generate_script.py` | **NOVO** — Gera JS a partir do CSV |
| `console_script.js` | Script para extrair (gerado pelo generate) |
| `shopee_products.csv` | Dados dos produtos (entrada manual) |
| `shopee_videos.csv` | Dados para vídeos (gerado pelo browser) |
| `shopee_videos.csv.bak.*` | Backups automáticos do videos.csv |
| `tiktok_post.js` | Processador de vídeos (próximo passo) |

## Dicas
- ✅ Use shopee.com.br logado (sessão ativa)
- ✅ Deixe a aba em foco durante a execução
- ✅ `--min-commission 10` filtra produtos mais lucrativos
- ✅ `--limit 10` para testar antes de processar tudo
- ⚠️ Respeite os termos do Shopee
- ⚠️ Não em paralelo — uma rodada por vez