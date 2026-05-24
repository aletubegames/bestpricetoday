# 📊 ML Extract - Extrator de Afiliados Mercado Livre

## O que é?
Script que coleta automaticamente dados de produtos afiliados do Mercado Livre, incluindo preço, avaliações, links curtos e códigos de afiliação.

## Como usar

### 1. Preparação
1. Acesse [Mercado Livre Afiliados](https://afiliados.mercadolivre.com.br)
2. Navegue até a seção de produtos afiliados
3. Abra o console do navegador (F12)

### 2. Executar o script
```javascript
// Cole o conteúdo de ml_extract.js no console do navegador
// O script começará automaticamente:
// 🚀 Iniciando coleta...
```

### 3. Processo de coleta
- O script scrolla a página automaticamente
- Coleta dados de cada produto:
  - Nome do produto
  - Badge/destaque
  - Preço e parcelamento
  - Desconto e preço original
  - Avaliações e vendas
  - Link curto do produto
  - Código de afiliação (formato: ABC-123456)
- Pausa quando não encontra mais produtos novos
- Exporta arquivo JSON automaticamente

### 4. Saída gerada
Um arquivo JSON com nome `afiliados_ml_YYYY-MM-DD.json` é baixado com estrutura:
```json
[
  {
    "nome": "Nome do Produto",
    "badge": "Melhor preço",
    "preco": "R$ 99,90",
    "parcelas": "3x de R$ 33,30",
    "desconto": "R$ 199,90",
    "ganhos": "Sua comissão",
    "avaliacao": "4.8 ★",
    "vendidos": "1000+",
    "link_prod": "https://s.mercadolivre.com.br/...",
    "Codigo_ML": "ABC-123456"
  }
]
```

## Arquivos
- `ml_extract.js` - Script de extração
- `afiliados_ml_*.json` - Dados coletados (exemplo: `afiliados_ml_2026-05-21.json`)
- `product_images/` - Imagens dos produtos (se salvas)

## Dicas
- ✅ Deixe a aba ativa enquanto coleta
- ✅ A coleta pode levar alguns minutos
- ✅ Arquivo JSON é baixado automaticamente
- ⚠️ Respeite o rate limit do site
- ⚠️ Mantenha a página visível (não minimize)

## Troubleshooting
| Problema | Solução |
|----------|--------|
| Seletores CSS não encontram elementos | Mercado Livre atualizou HTML, edite os seletores no script |
| Não captura links | Verifique se os botões de cópia do site estão disponíveis |
| Modal não fecha | Aguarde mais tempo no setTimeout |

## Integrar com o Banco de Dados

### Automático (post-commit hook)

Após commitar um novo JSON, o hook `.git/hooks/post-commit` detecta automaticamente e roda o import:

```bash
git add tools/ml_extract/afiliados_ml_YYYY-MM-DD.json
git commit -m "dados ml 2026-05-24"
# output: Rodando import... [NEW/UPD por produto] Import concluído.
```

### Manual (CLI)

```bash
# Importar o JSON mais recente
python tools/ml_extract/import.py

# Importar arquivo específico
python tools/ml_extract/import.py --file afiliados_ml_2026-05-24.json

# Simular sem escrever no BD
python tools/ml_extract/import.py --dry-run

# Log detalhado (NEW/UPD/SKIP por produto)
python tools/ml_extract/import.py --verbose
```

### Parse de campos

O script extrai automaticamente dos JSON:
- `nome` → `title`
- `preco` → `price` (parse "R$ 1.998 9% OFF" → 1998.0)
- `ganhos` → `commission_pct` (parse "15%" → 15.0)
- `link_prod` → `affiliate_url` (chave única, upsert)
- `Codigo_ML` → `ml_code`
- `badge`, `avaliacao`, `vendidos` → `notes`

### Uso manual alternativo
Os dados JSON também podem ser importados em:
- Excel/Google Sheets
- Sistema de gestão de afiliados
- Scripts de automação (tiktok_post, por exemplo)
