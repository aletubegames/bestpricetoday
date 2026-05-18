import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

class TikTokClient:
    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET
        self.redirect_uri = settings.TIKTOK_REDIRECT_URI
        self.base_url = "https://open.tiktokapis.com/v2"

    def get_auth_url(self, state: str) -> str:
        """Gera a URL de autorização do TikTok."""
        scopes = "user.info.basic,video.upload,video.publish"
        return (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={self.client_key}"
            f"&scope={scopes}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
        )

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Troca o código de autorização pelo token de acesso."""
        url = f"{self.base_url}/auth/token/"
        data = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()

    async def publish_video(self, access_token: str, video_url: str, title: str, description: str) -> Dict[str, Any]:
        """Inicia o upload de um vídeo para o TikTok."""
        # Nota: A API do TikTok requer primeiro uma requisição de 'init' e depois o upload do binário.
        # Este é um exemplo simplificado do fluxo de publicação.
        url = f"{self.base_url}/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        data = {
            "post_info": {
                "title": title,
                "description": description,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
                "video_ad_tag": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

tiktok_client = TikTokClient()
