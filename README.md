# BestPriceToday 🛍️

> Comparador de preços inteligente para o Brasil — menor preço em tempo real com cupons automáticos, cashback e histórico de preços.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.12-green) ![Next.js](https://img.shields.io/badge/next.js-14-black) ![Status](https://img.shields.io/badge/status-live-brightgreen)

---

## 🌐 URLs de Produção

| Serviço | URL |
|---------|-----|
| Frontend | https://bestpricetoday.vercel.app |
| Backend API | https://alessandro2090-bestpricetoday-api.hf.space |
| API Docs | https://alessandro2090-bestpricetoday-api.hf.space/docs |

---

## ✨ Features

- 🔍 **Busca paralela** em múltiplas lojas brasileiras
- 🎟️ **Cupons automáticos** via Cuponomia
- 💰 **Cashback** integrado
- 📈 **Histórico de preços** com gráficos
- 🚨 **Alertas de preço** via Telegram
- 🤖 **Detecção de falso desconto** por IA
- 📱 **PWA** instalável no celular
- ⚡ **Cache Redis** agressivo
- 🆓 **100% gratuito** até R$40k/mês

---

## 🏗️ Stack Completa

### Frontend
| Tecnologia | Uso | Hospedagem |
|-----------|-----|-----------|
| Next.js 14 | Framework React | Vercel (grátis) |
| Tailwind CSS | Estilização | — |
| Framer Motion | Animações | — |
| TanStack Query | Data fetching | — |
| Zustand | State management | — |
| Recharts | Gráficos | — |
| Lucide React | Ícones | — |
| next-pwa | PWA | — |

### Backend
| Tecnologia | Uso | Hospedagem |
|-----------|-----|-----------|
| FastAPI | API REST | Hugging Face Spaces (grátis) |
| Python 3.12 | Linguagem | — |
| AsyncIO | Concorrência | — |
| SQLAlchemy | ORM | — |
| Pydantic | Validação | — |
| Uvicorn | ASGI Server | — |
| Docker | Container | — |

### Banco de Dados & Cache
| Serviço | Uso | Plano |
|---------|-----|-------|
| Neon PostgreSQL | Banco principal | Free tier (grátis) |
| Upstash Redis | Cache | Free tier (grátis) |

### APIs de Afiliados
| Plataforma | Status | Comissão |
|-----------|--------|----------|
| Mercado Livre Afiliados | ✅ Ativo | 2-12% |
| Amazon Associados (aletubegames) | ✅ Ativo | 1-10% |
| Shopee Afiliados | ✅ Ativo | 3-15% |
| AliExpress Portals (bestpricetoday) | ✅ Ativo | 3-8% |

### DevOps & Monitoramento
| Ferramenta | Uso | Plano |
|-----------|-----|-------|
| Vercel | Deploy frontend + CI/CD | Free |
| Hugging Face Spaces | Deploy backend Docker | Free |
| GitHub Actions | CI/CD pipeline | Free |
| Sentry | Error tracking | Free |
| ngrok | Tunnel desenvolvimento | Free |

### Canais de Distribuição
| Canal | URL |
|-------|-----|
| YouTube | https://www.youtube.com/channel/UCDt5FafuWaqdu06fLWjYyuQ |
| X/Twitter | https://x.com/AleTubeGames |
| Instagram | https://www.instagram.com/alessandro.souza.77582 |
| TikTok | https://www.tiktok.com/@aletubegames8 |
| Facebook | https://www.facebook.com/alessandro.souza.77582/ |

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

## 💸 Monetização

```
Fase 1 (0-1k usuários):   Afiliados — R$0 investimento
Fase 2 (1k-10k):          Plano Premium R$9,90/mês
Fase 3 (10k+):            API paga, White Label, Ads
```

**Estimativa:**
- 1.000 usuários × 2 compras/mês × R$150 ticket × 5% = **R$15.000/mês**

---

## 📄 License

MIT — AleTubeGames
