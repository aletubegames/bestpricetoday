"""
Instagram/Facebook integration — BestPriceToday / AleTubeGames
Instagram Graph API via Facebook Login
Requer: conta Business ou Creator + Facebook App aprovado
"""
import httpx
import urllib.parse
from typing import Dict, Any, Optional
from app.core.config import settings

FB_AUTH_URL  = "https://www.facebook.com/v19.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
GRAPH_API    = "https://graph.facebook.com/v19.0"

# Escopos necessários para publicar no Instagram + Facebook
FB_SCOPES = ",".join([
    "pages_manage_posts",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_insights",
    "public_profile",
])


class InstagramFacebookClient:
    def __init__(self):
        # Facebook OAuth usa ID_APLICATIVO_FACEBOOK como client_id
        self.app_id       = settings.ID_APLICATIVO_FACEBOOK or settings.INSTAGRAM_APP_ID
        self.app_secret   = settings.FACEBOOK_APP_SECRET or settings.SECRET_KEY_INSTAGRAM_APP or settings.INSTAGRAM_APP_SECRET
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
        async with httpx.AsyncClient() as client:
            r = await client.get(FB_TOKEN_URL, params={
                "client_id":     self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri":  self.redirect_uri,
                "code":          code,
            })
            r.raise_for_status()
            return r.json()

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
        Fluxo: create container → wait → publish
        """
        async with httpx.AsyncClient(timeout=60) as client:
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

            # Step 2: publish
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


ig_fb_client = InstagramFacebookClient()
