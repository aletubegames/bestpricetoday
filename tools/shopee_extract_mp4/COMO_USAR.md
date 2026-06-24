# 🎬 Shopee Extract MP4 - Extrator de Produtos com Vídeos

## O que é?
Suite completa para extrair produtos do Shopee, converter em vídeos e preparar conteúdo para TikTok/Reels.

## Componentes

### 1. console_script.js - Extrator de Produtos 
### https://affiliate.shopee.com.br/offer/product_offer
selecione os varios produtos e baixe o csv que devera ser shopee_products.csv


rodar o python que vai gerar o js para ser rodado no site shopee normal nao o afiliados

#### Como usar
```javascript
// 1. Acesse https://shopee.com.br 
// 2. Abra console (F12)
// 3. Cole console_script.js
 
const links = `
https://s.shopee.com.br/gN7WGIjdk
https://s.shopee.com.br/10zxusHSxq
...
`;
// 5. Execute
```

#### Saída
- `shopee_products.csv` - Dados de produtos (Item ID, Nome, Preço, Avaliação, Link de afiliado)
- `shopee_videos.csv` - Dados para vídeos (slug, nome, preço, desconto, avaliação, URL, descrição)

### 2. tiktok_post.js - Processador de Vídeos
Script que processa os dados dos CSVs e cria vídeos para TikTok.

#### Como usar
```bash
# Execute via Node.js ou browser console
node tiktok_post.js
# ou cole no console do navegador
```

#### Entrada
- `shopee_products.csv` - Dados extraídos do Shopee
- `shopee_videos.csv` - Informações para legendas

#### Saída
- `videos/` - Pasta com vídeos MP4 gerados
- Cada vídeo contém:
  - Imagem do produto
  - Preço e desconto
  - Legenda personalizada
  - QR Code para link curto

## Estrutura de dados

### shopee_products.csv
```csv
Item Id,Item Name,Price,Sales,Shop Name,Commission Rate,Commission,Product Link,Offer Link
16692338189,Produto XYZ,29.90,1mi+,Loja A,14%,R$1.93,https://shopee.com.br/...,https://s.shopee.com.br/...
```

### shopee_videos.csv
```csv
slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao
gN7WGIjdk,Produto XYZ,29.90,49.90,40%,4.8,500mil+,1932,true,https://...,"Descrição..."
```

## Workflow completo

```mermaid
graph LR
    A["Links do Shopee"] -->|console_script.js| B["CSV de Produtos"]
    B -->|Processamento| C["Videos MP4"]
    C -->|Edição| D["Conteúdo para TikTok"]
    D -->|Upload| E["TikTok/Reels"]
```

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `console_script.js` | Script para extrair produtos |
| `tiktok_post.js` | Processador de vídeos |
| `shopee_productBatchProductLinks20260524142349-e67c6901b0e24c49af9176940b20537as.csv` | Dados dos produtos (gerado) |
| `shopee_videos.csv` | Dados para vídeos (gerado) |
| `videos/` | Vídeos MP4 gerados |
| `product_images/` | Imagens dos produtos |

## Gerenciamento de URLs

### Remover URLs
Edite diretamente os CSVs ou use grep:
```bash
# Remover linhas com URLs específicas
grep -v "AUr3EKhIhb\|W3hJxJMzi\|902FRZn0kA" shopee_products.csv > temp.csv && mv temp.csv shopee_products.csv
```

### Adicionar novos produtos
1. Abra o link no Shopee
2. Copie o link curto (s.shopee.com.br/...)
3. Adicione à lista em `console_script.js`
4. Execute novamente

## Dicas

- ✅ Use links curtos do Shopee (s.shopee.com.br/...)
- ✅ Verifique images antes de criar vídeos
- ✅ Remova produtos com estoque zerado
- ✅ Atualize regularmente para novos produtos
- ⚠️ Respeite os termos do Shopee
- ⚠️ Não copie vídeos com direitos autorais

## Integração com TikTok

Os vídeos gerados podem ser:
- Enviados diretamente para TikTok
- Editados em ferramentas como DaVinci Resolve
- Adicionados a playlists automáticas
- Processados pelo `tiktok_bot_fiel_completo.py`

## Problemas comuns

| Problema | Solução |
|----------|--------|
| "CSV não encontrado" | Verifique se console_script.js rodou com sucesso |
| Vídeos não geram | Verifique permissões da pasta `videos/` |
| Imagens não carregam | Aguarde o download das imagens dos produtos |
| Links quebrados | Remova links expirados do Shopee |
