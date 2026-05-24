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

### 2. 📊 [ml_extract](./ml_extract/COMO_USAR.md)
**Extrator de Afiliados Mercado Livre**

Coleta automaticamente dados de produtos afiliados do Mercado Livre, incluindo preços, avaliações, links e códigos de afiliação.

- Extração automática de dados
- Exporta JSON com informações completas
- Coleta links curtos e códigos de afiliação

👉 [Leia o guia completo](./ml_extract/COMO_USAR.md)

**Saída:**
- `afiliados_ml_YYYY-MM-DD.json` - Dados dos produtos

---

### 3. 🎬 [shopee_extract_mp4](./shopee_extract_mp4/COMO_USAR.md)
**Extrator de Produtos Shopee com Conversão para Vídeo**

Suite completa para extrair produtos do Shopee, converter em vídeos MP4 e preparar conteúdo para TikTok/Reels.

- Extração de dados do Shopee via links curtos
- Conversão automática em vídeos
- Geração de legendas e metadados
- Integração com TikTok

**Arquivos principais:**
- `console_script.js` - Extrator de produtos
- `tiktok_post.js` - Processador de vídeos
- `shopee_products.csv` - Dados dos produtos
- `shopee_videos.csv` - Dados para vídeos

👉 [Leia o guia completo](./shopee_extract_mp4/COMO_USAR.md)

---

### 4. 🎵 [tiktok_post](./tiktok_post/COMO_USAR.md)
**Bot de Automação para TikTok**

Automatiza a postagem de vídeos no TikTok com suporte a múltiplas contas, agendamento e integração com dados do Shopee.

- Bot Python com automação completa
- Script Tampermonkey para navegador
- Suporte a agendamento
- Integração com Shopee Extract

**Arquivos principais:**
- `tiktok_bot_fiel_completo.py` - Bot Python
- `tiktok_post.user.js` - Script Tampermonkey
- `tiktop_post.py` - Versão alternativa

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
│                  PROCESSAMENTO DE VÍDEOS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Shopee Extract MP4 (tiktok_post.js)                        │
│  ↓                                                           │
│  videos/ (MP4 gerados com legendas e metadados)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PUBLICAÇÃO NO TIKTOK                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TikTok Post (tiktok_bot_fiel_completo.py)                  │
│  ↓                                                           │
│  Vídeos publicados no TikTok com descrição e hashtags       │
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

### 2. Gerar vídeos
```bash
# Execute tiktok_post.js ou Python
# Resultado: vídeos na pasta videos/
```

### 3. Postar no TikTok
```bash
cd ../tiktok_post
python tiktok_bot_fiel_completo.py --post
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
- Python 3.8+
- Selenium, PyAutoGUI, Pillow
- Conta TikTok para testes

### Para Mercado Livre Extract
- Navegador moderno
- Acesso a afiliados.mercadolivre.com.br

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

**Última atualização:** 24 de maio de 2026

Feito com ❤️ para automação de e-commerce
