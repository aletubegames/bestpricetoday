# BestPriceToday

> Comparador de preços inteligente para o Brasil — menor preço em tempo real com cupons automáticos, cashback e histórico de preços.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.12-green) ![Next.js](https://img.shields.io/badge/next.js-14-black)

---

## ✨ Features

- 🔍 **Busca paralela** em 7 lojas: Mercado Livre, Amazon, Shopee, KaBuM, AliExpress, Awin, Lomadee
- 🎟️ **Cupons automáticos** via Cuponomia
- 💰 **Cashback** integrado
- 📈 **Histórico de preços** com gráficos
- 🚨 **Alertas de preço** via Telegram
- 🤖 **Detecção de falso desconto** por IA
- 📱 **PWA** instalável no celular
- ⚡ **Cache Redis** agressivo
- 🆓 **100% gratuito** até R$40k/mês

---

## 🏗️ Arquitetura

```
/frontend        Next.js 14 + Tailwind + Framer Motion
/backend         FastAPI + Python + AsyncIO
/shared          Tipos compartilhados
/infra           Docker + CI/CD
/scripts         Bootstrap + Seeds
/docs            Documentação
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/seu-usuario/bestpricetoday
cd bestpricetoday
bash scripts/bootstrap.sh
# Edite backend/.env com suas API keys
make dev
```

Acesse: http://localhost:3000  
API docs: http://localhost:8000/docs

---

## ⚙️ Stack

| Camada | Tecnologia | Plano Gratuito |
|--------|-----------|---------------|
| Frontend | Next.js + Vercel | ✅ Vercel Free |
| Backend | FastAPI + Render | ✅ Render Free |
| Banco | PostgreSQL | ✅ Neon Free |
| Cache | Redis | ✅ Upstash Free |
| Auth | Clerk | ✅ Clerk Free |
| Bot | python-telegram-bot | ✅ Grátis |
| Monitor | Sentry | ✅ Sentry Free |

---

## 📡 APIs de Afiliados

| Provedor | Registro | Comissão |
|----------|---------|----------|
| [Mercado Livre](https://afiliados.mercadolivre.com.br) | Gratuito | 2-12% |
| [Amazon Associates](https://associados.amazon.com.br) | Gratuito | 1-10% |
| [Shopee Affiliates](https://affiliate.shopee.com.br) | Gratuito | 3-15% |
| [Awin](https://www.awin.com/br) | Gratuito | Variável |
| [Lomadee](https://www.lomadee.com) | Gratuito | Variável |
| [AliExpress Portals](https://portals.aliexpress.com) | Gratuito | 3-8% |

---

## 💸 Monetização

```
Fase 1 (0-1k usuários):   Afiliados — R$0 investimento
Fase 2 (1k-10k):          Plano Premium R$9,90/mês
Fase 3 (10k+):            API paga, White Label, Ads
```

**Estimativa:**
- 1.000 usuários × 2 compras/mês × R$150 ticket × 5% = **R$15.000/mês**

---

## 📋 Comandos

```bash
make setup       # Setup inicial
make dev         # Docker completo
make dev-backend # Só backend
make dev-bot     # Só Telegram bot
make test        # Rodar testes
make lint        # Lint + type check
make migrate     # Migrations banco
```

---

## 📄 License

MIT
