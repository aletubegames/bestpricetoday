"""
TikTok integration — BestPriceToday
====================================
Dois fluxos distintos:

1. USUÁRIO COMUM (Login Kit + Share Kit)
   - Conecta conta TikTok pessoal via OAuth
   - Gera link de afiliado rastreado do BestPriceToday
   - Compartilha no próprio TikTok via Share Kit (usuário controla)
   - Comissão sempre vinculada ao link BestPriceToday

2. ADMIN (Login Kit + Content Posting API)
   - Admin conecta conta TikTok da plataforma
   - Pode publicar vídeos gerados pela IA nas redes associadas
   - Requer scope video.publish (uso restrito, aprovação TikTok)

NÃO usamos Content Posting API para publicar em nome de usuários comuns.
"""

import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

# ─── Scopes ──────────────────────────────────────────────────────────────────

# Usuário comum: perfil + share kit
USER_SCOPES = "user.info.basic,user.info.profile"

# Admin: perfil + publicação (Content Posting API — uso exclusivo admin)
ADMIN_SCOPES = "user.info.basic,user.info.profile,video.publish,video.upload"


class TikTokClient:
    def __init__(self):
        self.client_key    = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET
        self.redirect_uri  = settings.TIKTOK_REDIRECT_URI
        self.base_url      = "https://open.tiktokapis.com/v2"

    # ── Auth URLs ─────────────────────────────────────────────────────────────

    def get_user_auth_url(self, state: str) -> str:
        """URL OAuth para usuário comum — Login Kit (perfil + share)."""
        return (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={self.client_key}"
            f"&scope={USER_SCOPES}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
        )

    def get_admin_auth_url(self, state: str) -> str:
        """URL OAuth para admin — Login Kit + Content Posting API."""
        return (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={self.client_key}"
            f"&scope={ADMIN_SCOPES}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
        )

    # ── Token exchange ────────────────────────────────────────────────────────

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Troca o authorization code pelo access token."""
        url = f"{self.base_url}/oauth/token/"
        data = {
            "client_key":    self.client_key,
            "client_secret": self.client_secret,
            "code":          code,
            "grant_type":    "authorization_code",
            "redirect_uri":  self.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Renova o access token usando o refresh token."""
        url = f"{self.base_url}/oauth/token/"
        data = {
            "client_key":     self.client_key,
            "client_secret":  self.client_secret,
            "grant_type":     "refresh_token",
            "refresh_token":  refresh_token,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()

    # ── User info ─────────────────────────────────────────────────────────────

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Busca informações do perfil do usuário TikTok."""
        url = f"{self.base_url}/user/info/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json; charset=UTF-8",
        }
        params = {
            "fields": "open_id,union_id,avatar_url,display_name,profile_deep_link,bio_description,is_verified"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    # ── Share Kit — preparar payload para compartilhamento ───────────────────

    def build_share_url(
        self,
        short_link: str,
        caption: str,
        hashtags: str,
        video_url: Optional[str] = None,
    ) -> str:
        """
        Monta a URL do Share Kit do TikTok.
        O usuário é redirecionado para o app TikTok com o conteúdo pré-preenchido.
        O usuário decide se publica — a plataforma NÃO publica automaticamente.

        Ref: https://developers.tiktok.com/doc/web-share-kit
        """
        import urllib.parse

        full_caption = f"{caption}\n\n{short_link}\n\n{hashtags}"

        # Share Kit URL — abre o TikTok com o texto pré-preenchido
        # Se houver vídeo, inclui o link do vídeo para download
        params: Dict[str, str] = {
            "client_key": self.client_key,
            "text":       full_caption[:2200],  # limite TikTok
        }

        if video_url:
            params["media_type"] = "video"
            params["media_url"]  = video_url

        base = "https://www.tiktok.com/share"
        return f"{base}?{urllib.parse.urlencode(params)}"

    # ── Admin: Content Posting API (publicar vídeo em conta admin) ────────────

    async def admin_publish_video(
        self,
        access_token: str,
        video_url: str,
        title: str,
        description: str,
        tracked_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publica um vídeo no TikTok usando a conta ADMIN da plataforma.
        USO EXCLUSIVO ADMIN — não chamar para usuários comuns.

        O link rastreado é incluído na description para manter tracking de comissão.
        """
        url = f"{self.base_url}/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json; charset=UTF-8",
        }

        full_description = description
        if tracked_link:
            full_description = f"{description}\n\n🛒 {tracked_link}"

        data = {
            "post_info": {
                "title":           title[:150],
                "description":     full_description[:2200],
                "privacy_level":   "PUBLIC_TO_EVERYONE",
                "disable_duet":    False,
                "disable_stitch":  False,
                "disable_comment": False,
                "video_ad_tag":    False,
            },
            "source_info": {
                "source":    "PULL_FROM_URL",
                "video_url": video_url,
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()


tiktok_client = TikTokClient()
