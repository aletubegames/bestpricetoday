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

### 2. Gerar script para TikTok
Após gerar os CSVs, use o `tiktok_bot_fiel_completo.py` na pasta `tools/tiktok_post/` para criar o script Tampermonkey de postagem.

#### Como usar
```bash
cd ../tiktok_post
python tiktok_bot_fiel_completo.py
```

#### Entrada
- `shopee_products.csv` - Dados extraídos do Shopee
- `shopee_videos.csv` - Informações para legendas

#### Saída
- `tiktok_post.user.js` - Script Tampermonkey gerado

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
    B -->|tiktok_bot_fiel_completo.py| C["Script Tampermonkey"]
    C -->|Navegador| D["Postagem no TikTok"]
```

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `console_script.js` | Script para extrair produtos |
| `shopee_products.csv` | Dados dos produtos (gerado) |
| `shopee_videos.csv` | Dados para vídeos (gerado) |
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

Após gerar os CSVs:
1. Vá para `tools/tiktok_post/`
2. Execute `python tiktok_bot_fiel_completo.py` para gerar `tiktok_post.user.js`
3. Instale o script no Tampermonkey e use no TikTok Studio

## Problemas comuns

| Problema | Solução |
|----------|--------|
| "CSV não encontrado" | Verifique se console_script.js rodou com sucesso |
| Script do TikTok não gera | Verifique se os CSVs estão no caminho esperado pelo gerador |
| Links quebrados | Remova links expirados do Shopee |

---

**Última atualização:** 1 de julho de 2026
