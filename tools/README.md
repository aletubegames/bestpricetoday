# 🛠️ Tools - Guia de Ferramentas

Conjunto de ferramentas e scripts para automação de coleta e publicação de produtos em plataformas de vendas e redes sociais.

## 📁 Pastas

### 1. 🎯 [extrator_x](./extrator_x/COMO_USAR.md)
**XPath Inspector - Ferramenta de Web Scraping**

Inspeciona e captura elementos DOM em qualquer página web, gerando seletores XPath e código JavaScript para automação.

- Painel visual para captura de elementos
- Geração automática de XPath
- Export de código pronto para usar

👉 [Leia o guia completo](./extrator_x/COMO_USAR.md)

---

### 2. 📊 [shopee_extract_mp4](./shopee_extract_mp4/COMO_USAR.md)
**Extrator de Produtos Shopee com Conversão para Vídeo**

Suite completa para extrair produtos do Shopee e preparar dados para vídeos TikTok/Reels.

- Extração de dados do Shopee via links curtos
- Geração de CSVs com produtos e vídeos
- Integração com o gerador de vídeos do `tiktok_post`

**Arquivos principais:**
- `console_script.js` - Extrator de produtos (console do navegador)
- `shopee_products.csv` - Dados dos produtos
- `shopee_videos.csv` - Dados para vídeos

👉 [Leia o guia completo](./shopee_extract_mp4/COMO_USAR.md)

---

### 3. 🎵 [tiktok_post](./tiktok_post/COMO_USAR.md)
**Gerador de Script Tampermonkey para TikTok**

Lê os CSVs do `shopee_extract_mp4` e gera um script `tiktok_post.user.js` para postagem semi-automática no TikTok via navegador.

- Geração de script Tampermonkey
- Leitura dos CSVs de produtos/vídeos
- Não realiza postagem direta (depende do script no navegador)

**Arquivos principais:**
- `tiktok_bot_fiel_completo.py` - Gera o script Tampermonkey
- `tiktok_post.user.js` - Script de postagem (gerado)

👉 [Leia o guia completo](./tiktok_post/COMO_USAR.md)

---

## 🔄 Fluxo de Trabalho Completo

```
┌─────────────────────────────────────────────────────────────┐
│                    COLETA DE DADOS                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Shopee Extract MP4 (console_script.js)                     │
│  ↓                                                           │
│  shopee_products.csv + shopee_videos.csv                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  GERAÇÃO DO SCRIPT TAMPERMONKEY              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TikTok Post (tiktok_bot_fiel_completo.py)                  │
│  ↓                                                           │
│  tiktok_post.user.js                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PUBLICAÇÃO NO TIKTOK                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Instale tiktok_post.user.js no Tampermonkey               │
│  ↓                                                           │
│  Vídeos publicados no TikTok via navegador                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Início Rápido

### 1. Extrair produtos do Shopee
```bash
cd shopee_extract_mp4
# Abra o console do navegador no Shopee
# Cole console_script.js
# Resultado: shopee_products.csv + shopee_videos.csv
```

### 2. Gerar script Tampermonkey
```bash
cd ../tiktok_post
python tiktok_bot_fiel_completo.py
# Resultado: tiktok_post.user.js
```

### 3. Postar no TikTok
```bash
# Instale o tiktok_post.user.js gerado no Tampermonkey
# Abra o TikTok Studio no navegador e execute o script
```

---

## 📋 Checklist de Uso

- [ ] Leia o guia de cada pasta
- [ ] Configure as credenciais necessárias
- [ ] Teste com 1-2 produtos primeiro
- [ ] Monitore os resultados
- [ ] Ajuste conforme necessário
- [ ] Automatize e escale

---

## 🔧 Requisitos

### Para Shopee Extract
- Navegador moderno (Chrome, Firefox, Edge)
- Console do navegador (DevTools)

### Para TikTok Post
- Python 3.9+
- Dependências: `pandas`, `Pillow`
- Conta TikTok para testes

---

## ⚠️ Importante

- Respeite os termos de uso das plataformas
- Use bots responsavelmente
- Não abuse do rate limit
- Mantenha credenciais seguras
- Teste antes de escalar
- Monitore possíveis bans

---

## 📞 Suporte

Para problemas:
1. Consulte o `COMO_USAR.md` de cada pasta
2. Verifique a seção "Troubleshooting"
3. Revise os logs de erro
4. Teste componentes individualmente

---

**Última atualização:** 1 de julho de 2026

Feito com amor para automação de e-commerce
