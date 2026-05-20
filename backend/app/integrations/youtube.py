"""
YouTube integration — BestPriceToday / AleTubeGames
OAuth2 Google + YouTube Data API v3
"""
import httpx
import urllib.parse
from typing import Dict, Any, Optional
from app.core.config import settings

YOUTUBE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE  = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"

YOUTUBE_SCOPES = " ".join([
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
])


class YouTubeClient:
    def __init__(self):
        self.client_id     = settings.YOUTUBE_CLIENT_ID
        self.client_secret = settings.YOUTUBE_CLIENT_SECRET
        self.redirect_uri  = settings.YOUTUBE_REDIRECT_URI

    def get_auth_url(self, state: str) -> str:
        params = {
            "client_id":     self.client_id,
            "redirect_uri":  self.redirect_uri,
            "response_type": "code",
            "scope":         YOUTUBE_SCOPES,
            "access_type":   "offline",
            "prompt":        "consent",
            "state":         state,
        }
        return f"{YOUTUBE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(YOUTUBE_TOKEN_URL, data={
                "code":          code,
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri":  self.redirect_uri,
                "grant_type":    "authorization_code",
            })
            r.raise_for_status()
            return r.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.post(YOUTUBE_TOKEN_URL, data={
                "refresh_token": refresh_token,
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
                "grant_type":    "refresh_token",
            })
            r.raise_for_status()
            return r.json()

    async def get_channel_info(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{YOUTUBE_API_BASE}/channels", params={
                "part": "snippet,statistics",
                "mine": "true",
            }, headers={"Authorization": f"Bearer {access_token}"})
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            if not items:
                return {}
            ch = items[0]
            return {
                "channel_id":    ch["id"],
                "channel_title": ch["snippet"]["title"],
                "channel_url":   f"https://youtube.com/channel/{ch['id']}",
                "thumbnail_url": ch["snippet"].get("thumbnails", {}).get("default", {}).get("url"),
            }

    async def upload_video(
        self,
        access_token: str,
        file_path: str,
        title: str,
        description: str,
        tags: list,
        category_id: str = "22",  # 22 = People & Blogs; 28 = Science & Technology
        privacy: str = "public",
    ) -> Dict[str, Any]:
        """Upload via resumable upload (YouTube Data API v3)."""
        # Step 1: initiate resumable upload
        metadata = {
            "snippet": {
                "title":       title[:100],
                "description": description[:5000],
                "tags":        tags[:15],
                "categoryId":  category_id,
            },
            "status": {
                "privacyStatus":          privacy,
                "selfDeclaredMadeForKids": False,
            }
        }
        import json as _json
        async with httpx.AsyncClient(timeout=300) as client:
            # Initiate
            init_r = await client.post(
                f"{YOUTUBE_UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization":  f"Bearer {access_token}",
                    "Content-Type":   "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/*",
                },
                content=_json.dumps(metadata).encode(),
            )
            init_r.raise_for_status()
            upload_url = init_r.headers.get("Location")
            if not upload_url:
                raise Exception("YouTube não retornou upload URL")

            # Upload file
            with open(file_path, "rb") as f:
                video_data = f.read()
            upload_r = await client.put(
                upload_url,
                content=video_data,
                headers={"Content-Type": "video/*"},
            )
            upload_r.raise_for_status()
            result = upload_r.json()
            return {
                "video_id":  result.get("id"),
                "video_url": f"https://youtube.com/watch?v={result.get('id')}",
                "status":    result.get("status", {}).get("uploadStatus"),
            }


youtube_client = YouTubeClient()
