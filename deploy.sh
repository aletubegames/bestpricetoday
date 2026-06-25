#!/bin/bash
# deploy.sh — Build e deploy para produção (frontend Vercel + backend alaserver)
# Uso: ./deploy.sh
# Primeiro sincroniza o backend no alaserver, depois deploya frontend no Vercel.

set -e

ROOT_DIR="$(dirname "$0")"

echo "🖥️  Deployando backend no alaserver..."
"$ROOT_DIR/deploy_backend.sh"

cd "$ROOT_DIR/frontend"

echo "🔨 Building para produção com API alaserver (ngrok)..."
NEXT_PUBLIC_API_URL="https://sacrament-subduing-confined.ngrok-free.dev" \
  vercel build --prod

echo "🚀 Deployando para Vercel..."
vercel deploy --prebuilt --prod

echo "✅ Deploy completo! Backend no alaserver + frontend no Vercel."
