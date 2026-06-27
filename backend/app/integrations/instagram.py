"""
Instagram/Facebook integration — BestPriceToday / AleTubeGames
Instagram Graph API via Facebook Login
Requer: conta Business ou Creator + Facebook App aprovado
"""
import httpx
import urllib.parse
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger as log

FB_AUTH_URL  = "https://www.facebook.com/v25.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v25.0/oauth/access_token"
GRAPH_API    = "https://graph.facebook.com/v25.0"

# Escopos necessários para publicar no Instagram + Facebook.
# Usa escopos compatíveis com apps não revisados do Facebook/Instagram.
# pages_manage_posts + pages_read_engagement: postar fotos/ofertas na página Facebook
# instagram_content_publish: postar Reels no Instagram Business
FB_SCOPES = ",".join([
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_metadata",
    "pages_manage_posts",
    "pages_manage_engagement",  # necessário para postar/pinar comentários com link
    "public_profile",
    "instagram_basic",
    "instagram_content_publish",
    "business_management",
])


class InstagramFacebookClient:
    def __init__(self):
        # Facebook OAuth usa ID_APLICATIVO_FACEBOOK como client_id.
        self.app_id       = settings.ID_APLICATIVO_FACEBOOK or settings.ID_APLICATIVO_INSTAGRAM
        self.app_secret   = settings.FACEBOOK_APP_SECRET or settings.SECRET_KEY_INSTAGRAM_APP
        self.redirect_uri = settings.FACEBOOK_REDIRECT_URI

    def get_auth_url(self, state: str) -> str:
        params = {
            "client_id":     self.app_id,
            "redirect_uri":  self.redirect_uri,
            "scope":         FB_SCOPES,
            "response_type": "code",
            "state":         state,
        }
        return f"{FB_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        try:
            log.info(f"Tentando conectar com Facebook API...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(FB_TOKEN_URL, params={
                    "client_id":     self.app_id,
                    "client_secret": self.app_secret,
                    "redirect_uri":  self.redirect_uri,
                    "code":          code,
                })
                log.info(f"Facebook API status: {r.status_code}")
                log.info(f"Facebook API response: {r.text[:200]}")
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP Error: {e.response.status_code}")
            log.error(f"Response: {e.response.text[:200]}")
            raise Exception(f"Facebook API error {e.response.status_code}: {e.response.text[:100]}")
        except httpx.TimeoutException as e:
            log.error(f"Timeout error: {str(e)}")
            raise Exception(f"Timeout ao conectar com Facebook API (60s)")
        except httpx.NetworkError as e:
            log.error(f"Network error: {str(e)}")
            raise Exception(f"Erro de rede ao conectar com Facebook API: {str(e)}")
        except Exception as e:
            log.error(f"Erro na chamada Facebook API: {str(e)}")
            raise

    async def get_long_lived_token(self, short_token: str) -> Dict[str, Any]:
        """Troca short-lived token por long-lived (60 dias)."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GRAPH_API}/oauth/access_token", params={
                "grant_type":        "fb_exchange_token",
                "client_id":         self.app_id,
                "client_secret":     self.app_secret,
                "fb_exchange_token": short_token,
            })
            r.raise_for_status()
            return r.json()

    async def get_pages(self, access_token: str) -> list:
        """Retorna páginas Facebook do usuário."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GRAPH_API}/me/accounts", params={
                "access_token": access_token,
                "fields": "id,name,access_token,picture",
            })
            r.raise_for_status()
            return r.json().get("data", [])

    async def get_instagram_account(self, page_id: str, page_token: str) -> Optional[Dict[str, Any]]:
        """Busca conta Instagram Business vinculada à página."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GRAPH_API}/{page_id}", params={
                "fields":       "instagram_business_account",
                "access_token": page_token,
            })
            r.raise_for_status()
            data = r.json()
            ig_id = data.get("instagram_business_account", {}).get("id")
            if not ig_id:
                return None
            # Busca detalhes
            r2 = await client.get(f"{GRAPH_API}/{ig_id}", params={
                "fields":       "id,username,name,profile_picture_url,biography",
                "access_token": page_token,
            })
            r2.raise_for_status()
            return r2.json()

    async def publish_reel_instagram(
        self,
        ig_account_id: str,
        access_token: str,
        video_url: str,
        caption: str,
    ) -> Dict[str, Any]:
        """
        Publica Reel no Instagram via Graph API.
        O vídeo deve estar em URL pública acessível.
        Fluxo: create container → poll status → publish
        """
        import asyncio
        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: criar container
            r = await client.post(f"{GRAPH_API}/{ig_account_id}/media", params={
                "media_type":   "REELS",
                "video_url":    video_url,
                "caption":      caption[:2200],
                "access_token": access_token,
            })
            r.raise_for_status()
            container_id = r.json().get("id")
            if not container_id:
                raise Exception("Instagram não retornou container_id")

            # Step 2: polling até container estar FINISHED (máximo 90s)
            for attempt in range(18):
                await asyncio.sleep(5)
                status_r = await client.get(f"{GRAPH_API}/{container_id}", params={
                    "fields":       "status_code,status",
                    "access_token": access_token,
                })
                status_r.raise_for_status()
                status_data = status_r.json()
                status_code = status_data.get("status_code", "")
                log.info(f"Instagram container {container_id} status: {status_code} (attempt {attempt+1})")
                if status_code == "FINISHED":
                    break
                if status_code in ("ERROR", "EXPIRED"):
                    raise Exception(f"Instagram container falhou: {status_data.get('status', status_code)}")
            else:
                raise Exception("Instagram container não processou em 90s (timeout)")

            # Step 3: publish
            r2 = await client.post(f"{GRAPH_API}/{ig_account_id}/media_publish", params={
                "creation_id":  container_id,
                "access_token": access_token,
            })
            r2.raise_for_status()
            media_id = r2.json().get("id")
            return {"media_id": media_id, "container_id": container_id}

    async def publish_photo_instagram(
        self,
        ig_account_id: str,
        access_token: str,
        image_url: str,
        caption: str,
    ) -> Dict[str, Any]:
        """
        Publica foto no feed do Instagram via Graph API.
        A imagem deve estar em URL pública acessível.
        Fluxo: create container → poll status → publish
        """
        import asyncio
        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: criar container (FEED com image_url)
            r = await client.post(f"{GRAPH_API}/{ig_account_id}/media", params={
                "image_url":    image_url,
                "caption":      caption[:2200],
                "access_token": access_token,
            })
            r.raise_for_status()
            container_id = r.json().get("id")
            if not container_id:
                raise Exception("Instagram não retornou container_id")

            # Step 2: polling até container estar FINISHED (máximo 60s)
            for attempt in range(12):
                await asyncio.sleep(5)
                status_r = await client.get(f"{GRAPH_API}/{container_id}", params={
                    "fields":       "status_code,status",
                    "access_token": access_token,
                })
                status_r.raise_for_status()
                status_data = status_r.json()
                status_code = status_data.get("status_code", "")
                log.info(f"IG photo container {container_id} status: {status_code} (attempt {attempt+1})")
                if status_code == "FINISHED":
                    break
                if status_code in ("ERROR", "EXPIRED"):
                    raise Exception(f"IG container falhou: {status_data.get('status', status_code)}")
            else:
                raise Exception("IG container não processou em 60s (timeout)")

            # Step 3: publish
            r2 = await client.post(f"{GRAPH_API}/{ig_account_id}/media_publish", params={
                "creation_id":  container_id,
                "access_token": access_token,
            })
            r2.raise_for_status()
            media_id = r2.json().get("id")
            return {"media_id": media_id, "container_id": container_id}

    async def publish_video_facebook(
        self,
        page_id: str,
        page_token: str,
        file_path: str,
        title: str,
        description: str,
    ) -> Dict[str, Any]:
        """Publica vídeo em página Facebook via Graph API."""
        async with httpx.AsyncClient(timeout=300) as client:
            with open(file_path, "rb") as f:
                r = await client.post(
                    f"{GRAPH_API}/{page_id}/videos",
                    params={"access_token": page_token},
                    data={"title": title[:255], "description": description},
                    files={"source": ("video.mp4", f, "video/mp4")},
                )
            r.raise_for_status()
            return r.json()

    async def publish_photo_facebook(
        self,
        page_id: str,
        page_token: str,
        image_url: str,
        caption: str,
    ) -> Dict[str, Any]:
        """Publica foto em página Facebook via Graph API (URL pública).

        Usado pelo distributor para postar ofertas (foto do produto + legenda + short link).
        Retorna {"id": post_id, "post_id": "..."}.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{GRAPH_API}/{page_id}/photos",
                params={"access_token": page_token},
                data={
                    "url": image_url,
                    "message": caption,
                },
            )
            r.raise_for_status()
            data = r.json()
            # Graph API retorna {"id": photo_id, "post_id": "page_id_post_id"}
            return data

    async def post_comment_facebook(
        self,
        post_id: str,
        page_token: str,
        message: str,
    ) -> Dict[str, Any]:
        """Posta comentário em uma publicação de página Facebook via Graph API.

        Usado para postar o short link como comentário (estratégia anti-banimento:
        link de afiliado nunca vai no corpo do post, só nos comentários).
        Retorna {"id": comment_id}.
        """
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{GRAPH_API}/{post_id}/comments",
                params={"access_token": page_token},
                data={"message": message},
            )
            r.raise_for_status()
            return r.json()

    async def pin_comment_facebook(
        self,
        comment_id: str,
        page_token: str,
    ) -> bool:
        """Fixa um comentário no topo da publicação (Graph API).

        Requer permissão pages_manage_posts + pages_read_engagement.
        Retorna True se fixou com sucesso.
        """
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{GRAPH_API}/{comment_id}",
                params={"access_token": page_token, "pinned": "true"},
            )
            return r.status_code == 200


ig_fb_client = InstagramFacebookClient()
