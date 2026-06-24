#!/usr/bin/env python3
"""
Teste de Conexão OAuth — BestPriceToday

Este script testa a conexão com cada provedor OAuth sem fazer rotação de secrets.
Execute com: python TEST_OAUTH_CONNECTION.py

Requisitos:
  - Backend configurado em backend/.env
  - Secrets válidos nos respectivos provedores
"""

import sys
import os
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any

# Adicionar backend ao path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from app.core.config import settings
except Exception as e:
    print(f"❌ Erro ao carregar config: {e}")
    print("Certifique-se de que o .env está configurado em backend/.env")
    sys.exit(1)


class OAuthConnectionTester:
    """Testa conectividade com provedores OAuth."""
    
    def __init__(self):
        self.results = []
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def test_tiktok_connection(self) -> Dict[str, Any]:
        """Testa conexão com TikTok OAuth."""
        print("\n🎵 Testando TikTok OAuth...")
        
        if not settings.TIKTOK_CLIENT_KEY or not settings.TIKTOK_CLIENT_SECRET:
            return {
                "platform": "TikTok",
                "status": "⚠️ INCOMPLETO",
                "message": "TIKTOK_CLIENT_KEY ou TIKTOK_CLIENT_SECRET não configurados",
                "redirect_uri": settings.TIKTOK_REDIRECT_URI
            }
        
        try:
            # Verificar que a URL de autorização pode ser construída
            auth_url = (
                f"https://www.tiktok.com/oauth/authorize?"
                f"client_key={settings.TIKTOK_CLIENT_KEY[:10]}...&"
                f"response_type=code&"
                f"redirect_uri={settings.TIKTOK_REDIRECT_URI}&"
                f"scope=user.info.basic,user.info.profile"
            )
            
            # Testar conectividade básica
            response = await self.http_client.get(
                "https://www.tiktok.com/oauth/authorize",
                params={"client_key": settings.TIKTOK_CLIENT_KEY},
                follow_redirects=False
            )
            
            # OAuth redirects são esperados
            if response.status_code in [302, 303, 307, 308, 404, 403]:
                return {
                    "platform": "TikTok",
                    "status": "✅ CONECTÁVEL",
                    "message": f"API respondendo (HTTP {response.status_code})",
                    "redirect_uri": settings.TIKTOK_REDIRECT_URI,
                    "client_key_set": bool(settings.TIKTOK_CLIENT_KEY),
                    "client_secret_set": bool(settings.TIKTOK_CLIENT_SECRET)
                }
            else:
                return {
                    "platform": "TikTok",
                    "status": "⚠️ RESPOSTA INESPERADA",
                    "http_status": response.status_code,
                    "message": "Verifique se CLIENT_KEY está correto"
                }
        
        except Exception as e:
            return {
                "platform": "TikTok",
                "status": "❌ ERRO",
                "message": str(e),
                "redirect_uri": settings.TIKTOK_REDIRECT_URI
            }
    
    async def test_youtube_connection(self) -> Dict[str, Any]:
        """Testa conexão com Google OAuth (YouTube)."""
        print("\n▶️ Testando Google OAuth (YouTube)...")
        
        if not settings.YOUTUBE_CLIENT_ID or not settings.YOUTUBE_CLIENT_SECRET:
            return {
                "platform": "YouTube",
                "status": "⚠️ INCOMPLETO",
                "message": "YOUTUBE_CLIENT_ID ou YOUTUBE_CLIENT_SECRET não configurados",
                "redirect_uri": settings.YOUTUBE_REDIRECT_URI
            }
        
        try:
            # Testar conectividade com Google OAuth endpoint
            response = await self.http_client.get(
                "https://accounts.google.com/o/oauth2/v2/auth",
                params={"client_id": settings.YOUTUBE_CLIENT_ID},
                follow_redirects=False
            )
            
            # OAuth redirects são esperados
            if response.status_code in [302, 303, 307, 308, 400, 404]:
                return {
                    "platform": "YouTube",
                    "status": "✅ CONECTÁVEL",
                    "message": f"Google OAuth respondendo (HTTP {response.status_code})",
                    "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
                    "client_id_set": bool(settings.YOUTUBE_CLIENT_ID),
                    "client_secret_set": bool(settings.YOUTUBE_CLIENT_SECRET)
                }
            else:
                return {
                    "platform": "YouTube",
                    "status": "⚠️ RESPOSTA INESPERADA",
                    "http_status": response.status_code
                }
        
        except Exception as e:
            return {
                "platform": "YouTube",
                "status": "❌ ERRO",
                "message": str(e),
                "redirect_uri": settings.YOUTUBE_REDIRECT_URI
            }
    
    async def test_facebook_connection(self) -> Dict[str, Any]:
        """Testa conexão com Facebook OAuth."""
        print("\n👤 Testando Facebook/Instagram OAuth...")
        
        app_id = settings.ID_APLICATIVO_INSTAGRAM or settings.INSTAGRAM_APP_ID
        app_secret = settings.SECRET_KEY_INSTAGRAM_APP or settings.INSTAGRAM_APP_SECRET
        
        if not app_id or not app_secret:
            return {
                "platform": "Facebook/Instagram",
                "status": "⚠️ INCOMPLETO",
                "message": "ID_APLICATIVO_INSTAGRAM ou SECRET_KEY_INSTAGRAM_APP não configurados",
                "redirect_uri": settings.FACEBOOK_REDIRECT_URI
            }
        
        try:
            # Testar conectividade com Facebook Login
            response = await self.http_client.get(
                "https://www.facebook.com/v18.0/dialog/oauth",
                params={"client_id": app_id},
                follow_redirects=False
            )
            
            if response.status_code in [302, 303, 307, 308, 400, 404]:
                return {
                    "platform": "Facebook/Instagram",
                    "status": "✅ CONECTÁVEL",
                    "message": f"Facebook OAuth respondendo (HTTP {response.status_code})",
                    "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
                    "app_id_set": bool(app_id),
                    "app_secret_set": bool(app_secret)
                }
            else:
                return {
                    "platform": "Facebook/Instagram",
                    "status": "⚠️ RESPOSTA INESPERADA",
                    "http_status": response.status_code
                }
        
        except Exception as e:
            return {
                "platform": "Facebook/Instagram",
                "status": "❌ ERRO",
                "message": str(e),
                "redirect_uri": settings.FACEBOOK_REDIRECT_URI
            }
    
    async def test_database_connection(self) -> Dict[str, Any]:
        """Testa conexão com banco de dados."""
        print("\n💾 Testando Banco de Dados...")
        
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine
            
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            return {
                "platform": "PostgreSQL",
                "status": "✅ CONECTÁVEL",
                "message": "Conexão com banco de dados funcionando",
                "database_url_set": bool(settings.DATABASE_URL)
            }
        
        except Exception as e:
            return {
                "platform": "PostgreSQL",
                "status": "❌ ERRO",
                "message": f"Erro de conexão: {str(e)}",
                "database_url_set": bool(settings.DATABASE_URL)
            }
    
    async def run_all_tests(self):
        """Executa todos os testes."""
        print("\n" + "=" * 70)
        print("TESTE DE CONEXÃO OAUTH — BestPriceToday")
        print("=" * 70)
        
        results = []
        
        # Testar OAuth providers
        results.append(await self.test_tiktok_connection())
        results.append(await self.test_youtube_connection())
        results.append(await self.test_facebook_connection())
        
        # Testar infraestrutura
        results.append(await self.test_database_connection())
        
        # Exibir resultados
        print("\n" + "=" * 70)
        print("RESULTADOS")
        print("=" * 70)
        
        for result in results:
            platform = result.get("platform", "Unknown")
            status = result.get("status", "⚠️ DESCONHECIDO")
            message = result.get("message", "")
            
            print(f"\n{status} {platform}")
            if message:
                print(f"   └─ {message}")
            
            # Detalhes adicionais
            for key, value in result.items():
                if key not in ["platform", "status", "message", "http_status"]:
                    if isinstance(value, bool):
                        symbol = "✅" if value else "❌"
                        print(f"   ├─ {key}: {symbol}")
                    else:
                        print(f"   ├─ {key}: {value}")
        
        # Resumo
        print("\n" + "=" * 70)
        print("RESUMO")
        print("=" * 70)
        
        conectavel = sum(1 for r in results if "✅" in r.get("status", ""))
        incompleto = sum(1 for r in results if "⚠️" in r.get("status", ""))
        erro = sum(1 for r in results if "❌" in r.get("status", ""))
        
        print(f"✅ Conectável: {conectavel}")
        print(f"⚠️ Incompleto: {incompleto}")
        print(f"❌ Erro: {erro}")
        
        print("\n📝 Próximos passos:")
        print("  1. Verifique se todos os secrets estão configurados em backend/.env")
        print("  2. Para cada ❌ ERRO, verifique a conectividade de rede")
        print("  3. Para cada ⚠️ INCOMPLETO, adicione os secrets faltantes")
        print("  4. Para testes completos de OAuth, use a auditoria em SECURITY_AUDIT_OAUTH.md")


async def main():
    tester = OAuthConnectionTester()
    try:
        await tester.run_all_tests()
    finally:
        await tester.http_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
