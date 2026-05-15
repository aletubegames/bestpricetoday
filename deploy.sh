#!/bin/bash
# deploy.sh — Build e deploy para produção com a API correta
# Uso: ./deploy.sh
# Mantém .env.local apontando para localhost (desenvolvimento)
# Deploy sempre usa o HF Space

set -e

cd "$(dirname "$0")/frontend"

echo "🔨 Building para produção com API HF Space..."
NEXT_PUBLIC_API_URL="https://alessandro2090-bestpricetoday-api.hf.space" \
  vercel build --prod

echo "🚀 Deployando para Vercel..."
vercel deploy --prebuilt --prod

echo "✅ Deploy concluído!"
