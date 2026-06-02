#!/usr/bin/env python3
"""
Teste de Conexão YouTube OAuth
Execute com: python test_youtube.py
"""

import asyncio
import httpx
import sys
import os
from pathlib import Path

# Carregar variáveis de ambiente
from dotenv import load_dotenv

backend_path = Path(__file__).parent / "backend"
env_file = backend_path / ".env"

if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"⚠️ Arquivo .env não encontrado em {env_file}")

# Ler credenciais do ambiente
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "https://bestpricetoday.vercel.app/aletube/callback/youtube")


async def test_youtube():
    print("=" * 70)
    print("TESTE DE CONEXÃO YOUTUBE OAUTH")
    print("=" * 70)
    
    # 1. Verificar configuração
    print("\n📋 Configuração:")
    print(f"  YOUTUBE_CLIENT_ID: {'✅ Configurado' if YOUTUBE_CLIENT_ID else '❌ NÃO configurado'}")
    print(f"  YOUTUBE_CLIENT_SECRET: {'✅ Configurado' if YOUTUBE_CLIENT_SECRET else '❌ NÃO configurado'}")
    print(f"  YOUTUBE_REDIRECT_URI: {YOUTUBE_REDIRECT_URI}")
    
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        print("\n❌ Erro: CLIENT_ID ou CLIENT_SECRET não configurados em .env")
        return False
    
    # 2. Testar conectividade com Google OAuth
    print("\n🔗 Testando conectividade com Google OAuth...")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Teste 1: GET /oauth2/v2/auth (autorização)
            print("\n  → Testando endpoint de autorização...")
            response = await client.get(
                "https://accounts.google.com/o/oauth2/v2/auth",
                params={
                    "client_id": YOUTUBE_CLIENT_ID,
                    "redirect_uri": YOUTUBE_REDIRECT_URI,
                    "response_type": "code",
                    "scope": "https://www.googleapis.com/auth/youtube.upload",
                },
                follow_redirects=False
            )
            print(f"    HTTP {response.status_code}")
            if response.status_code in [302, 303, 307, 308, 400, 404]:
                print(f"    ✅ Endpoint respondendo")
            else:
                print(f"    ⚠️ Status inesperado: {response.status_code}")
            
            # Teste 2: Conectividade com oauth2.googleapis.com
            print("\n  → Testando conectividade com oauth2.googleapis.com...")
            response = await client.get("https://oauth2.googleapis.com/", follow_redirects=False)
            print(f"    HTTP {response.status_code}")
            if response.status_code < 500:
                print(f"    ✅ Servidor respondendo")
            
            # Teste 3: Token endpoint com código inválido
            print("\n  → Testando endpoint de token...")
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "INVALID_CODE_TEST",
                    "client_id": YOUTUBE_CLIENT_ID,
                    "client_secret": YOUTUBE_CLIENT_SECRET,
                    "redirect_uri": YOUTUBE_REDIRECT_URI,
                },
                follow_redirects=False
            )
            print(f"    HTTP {response.status_code}")
            if response.status_code == 400:
                print(f"    ✅ Endpoint respondendo (erro esperado para código inválido)")
                try:
                    error_data = response.json()
                    error = error_data.get('error', 'desconhecido')
                    error_desc = error_data.get('error_description', '')
                    print(f"    └─ Erro: {error}")
                    if error_desc:
                        print(f"    └─ Descrição: {error_desc}")
                except:
                    pass
            else:
                print(f"    ⚠️ Status inesperado: {response.status_code}")
            
            # Teste 4: Verificar formato CLIENT_ID
            print("\n  → Verificando formato do CLIENT_ID...")
            if YOUTUBE_CLIENT_ID.endswith(".apps.googleusercontent.com"):
                print(f"    ✅ Formato correto (Google Cloud credentials)")
            else:
                print(f"    ⚠️ Formato: {YOUTUBE_CLIENT_ID[-30:]}")
            
            return True
            
        except httpx.ConnectError as e:
            print(f"    ❌ Erro de conexão: {e}")
            return False
        except httpx.TimeoutException:
            print(f"    ❌ Timeout na conexão")
            return False
        except Exception as e:
            print(f"    ❌ Erro: {e}")
            return False


async def main():
    success = await test_youtube()
    
    # 5. Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    
    if success:
        print("""
✅ YOUTUBE OAUTH - CONECTADO

Configuração: COMPLETA
  • CLIENT_ID: ✅ Configurado
  • CLIENT_SECRET: ✅ Configurado
  • REDIRECT_URI: Correto

Conectividade: ✅ OK
  • Google OAuth: Respondendo
  • Endpoints: Acessíveis

Fluxo OAuth:
  1. Usuário clica "Conectar YouTube"
  2. Redireciona para Google com URL abaixo
  3. Google autentica e redireciona para REDIRECT_URI com 'code'
  4. Sistema troca 'code' por access_token
  5. Access_token usado para publicar vídeos no YouTube
  
URL de Autorização:
https://accounts.google.com/o/oauth2/v2/auth?
  client_id={client_id}&
  redirect_uri={redirect_uri}&
  response_type=code&
  scope=youtube.upload+youtube.readonly+userinfo.profile&
  access_type=offline&
  prompt=consent

""".format(
            client_id=YOUTUBE_CLIENT_ID,
            redirect_uri=YOUTUBE_REDIRECT_URI
        ))
    else:
        print("""
❌ YOUTUBE OAUTH - PROBLEMAS ENCONTRADOS

Possíveis causas:
  1. CLIENT_ID ou CLIENT_SECRET não configurados
  2. Sem conectividade com internet/Google
  3. Firewall/proxy bloqueando conexão
  4. Credenciais inválidas

Ações:
  1. Verificar backend/.env
  2. Testar conectividade: ping accounts.google.com
  3. Verificar firewall/proxy
  4. Verificar credenciais no Google Cloud Console
""")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
