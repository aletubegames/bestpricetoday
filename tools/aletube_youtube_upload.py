#!/usr/bin/env python3
"""
aletube_youtube_upload.py — upload local de vídeos para o YouTube.

Para vídeos grandes (>100MB) que não passam pelo ingress do HF Space free.
Sobe directamente da tua máquina via YouTube Data API v3 (resumable upload),
e regista o resultado no backend AleTubeGames para aparecer no dashboard.

Uso:
  ./tools/aletube_youtube_upload.py video.mp4 \\
      --title "Meu Vídeo" \\
      --description "Descrição..." \\
      --tags gameplay,sf3 \\
      --privacy public

Setup (uma vez):
  export ALETUBE_API_URL="https://aletubegames-bestpricetoday-api.hf.space"
  export ALETUBE_ADMIN_KEY="<X-Admin-Key>"

Requer: Python 3.9+, httpx (já no requirements do projecto).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    sys.exit("Falta httpx. Instala: pip install httpx")


CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB — múltiplo de 256 KiB exigido pela API
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
CACHE_DIR = Path.home() / ".aletube"
CACHE_FILE = CACHE_DIR / "youtube.json"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Falta variável de ambiente: {name}")
    return v


def _human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TiB"


def _backend_get_credentials() -> dict:
    """Busca client_id/secret/refresh_token do backend (cache local)."""
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if all(k in data for k in ("client_id", "client_secret", "refresh_token")):
                print(f"✓ Credenciais em cache ({CACHE_FILE})")
                return data
        except Exception:
            pass

    api  = _env("ALETUBE_API_URL").rstrip("/")
    key  = _env("ALETUBE_ADMIN_KEY")
    url  = f"{api}/api/v1/aletube/local/youtube-credentials"
    print(f"→ A obter credenciais YouTube de {url}")
    r = httpx.get(url, headers={"X-Admin-Key": key}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Erro a obter credenciais: HTTP {r.status_code} — {r.text[:200]}")
    data = r.json()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(CACHE_FILE, 0o600)
    print(f"✓ Credenciais guardadas em {CACHE_FILE} (modo 600)")
    return data


def _refresh_access_token(creds: dict) -> str:
    print("→ A renovar access token Google…")
    r = httpx.post(GOOGLE_TOKEN_URL, data={
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "grant_type":    "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Falha refresh token: HTTP {r.status_code} — {r.text[:200]}")
    tok = r.json().get("access_token")
    if not tok:
        sys.exit("Resposta sem access_token")
    print("✓ Access token renovado")
    return tok


# ─── Upload ──────────────────────────────────────────────────────────────────

def _initiate_upload(
    access_token: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str,
    privacy: str,
    file_size: int,
) -> str:
    metadata = {
        "snippet": {
            "title":       title[:100],
            "description": description[:5000],
            "tags":        tags[:15],
            "categoryId":  category_id,
        },
        "status": {
            "privacyStatus":           privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    headers = {
        "Authorization":              f"Bearer {access_token}",
        "Content-Type":               "application/json; charset=UTF-8",
        "X-Upload-Content-Type":      "video/*",
        "X-Upload-Content-Length":    str(file_size),
    }
    r = httpx.post(
        f"{YOUTUBE_UPLOAD_URL}?uploadType=resumable&part=snippet,status",
        headers=headers,
        content=json.dumps(metadata).encode(),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        sys.exit(f"Initiate falhou: HTTP {r.status_code} — {r.text[:300]}")
    upload_url = r.headers.get("Location")
    if not upload_url:
        sys.exit("Sem Location header na resposta de initiate")
    return upload_url


def _upload_chunked(upload_url: str, file_path: Path, file_size: int) -> dict:
    uploaded = 0
    started = time.monotonic()
    with file_path.open("rb") as f, httpx.Client(timeout=httpx.Timeout(None, read=300)) as client:
        while uploaded < file_size:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            chunk_end = uploaded + len(chunk) - 1
            content_range = f"bytes {uploaded}-{chunk_end}/{file_size}"
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range":  content_range,
            }
            for attempt in range(5):
                try:
                    r = client.put(upload_url, content=chunk, headers=headers)
                    break
                except httpx.RequestError as exc:
                    wait = 2 ** attempt
                    print(f"  ! Erro de rede ({exc}). Retry em {wait}s…")
                    time.sleep(wait)
            else:
                sys.exit("Falhou após 5 tentativas de chunk")

            if r.status_code in (308,):  # Resume incomplete — esperado entre chunks
                uploaded += len(chunk)
            elif r.status_code in (200, 201):
                uploaded += len(chunk)
                elapsed = time.monotonic() - started
                speed = uploaded / max(elapsed, 0.001)
                print(f"  ✓ {_human(uploaded)}/{_human(file_size)} em {elapsed:.0f}s ({_human(int(speed))}/s)")
                return r.json()
            else:
                sys.exit(f"Chunk falhou: HTTP {r.status_code} — {r.text[:300]}")

            elapsed = time.monotonic() - started
            speed = uploaded / max(elapsed, 0.001)
            pct = uploaded * 100 // file_size
            print(f"  · {pct:3d}% — {_human(uploaded)}/{_human(file_size)} ({_human(int(speed))}/s)")

    sys.exit("Upload terminou sem resposta final do YouTube")


def _register_in_backend(
    youtube_video_id: str,
    title: str,
    filename: str,
    file_size: int,
    video_id: Optional[str],
) -> Optional[dict]:
    api = os.environ.get("ALETUBE_API_URL", "").rstrip("/")
    key = os.environ.get("ALETUBE_ADMIN_KEY")
    if not (api and key):
        print("⚠ ALETUBE_API_URL/ALETUBE_ADMIN_KEY não definidos — saltando registo no backend")
        return None
    print("→ A registar no backend…")
    data = {
        "youtube_video_id": youtube_video_id,
        "title":            title,
        "filename":         filename,
        "file_size_bytes":  str(file_size),
    }
    if video_id:
        data["video_id"] = video_id
    r = httpx.post(
        f"{api}/api/v1/aletube/local/register-youtube-result",
        headers={"X-Admin-Key": key},
        data=data,
        timeout=30,
    )
    if r.status_code != 200:
        print(f"⚠ Registo falhou: HTTP {r.status_code} — {r.text[:200]}")
        return None
    return r.json()


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Upload local de vídeo para o YouTube")
    p.add_argument("video", type=Path, help="caminho para o ficheiro mp4/mov/etc")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tags", default="", help="lista separada por vírgulas")
    p.add_argument("--category", default="22", help="22=People&Blogs, 20=Gaming, 28=Tech")
    p.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    p.add_argument("--video-id", default=None, help="UUID de AdminVideo existente (opcional)")
    p.add_argument("--no-register", action="store_true", help="não registar no backend")
    args = p.parse_args()

    if not args.video.is_file():
        sys.exit(f"Ficheiro não encontrado: {args.video}")

    file_size = args.video.stat().st_size
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    print(f"Ficheiro: {args.video.name} ({_human(file_size)})")
    print(f"Título:   {args.title}")
    print(f"Tags:     {tags}")
    print(f"Privacy:  {args.privacy}")
    print()

    creds = _backend_get_credentials()
    access_token = _refresh_access_token(creds)

    print("→ A iniciar upload resumable…")
    upload_url = _initiate_upload(
        access_token=access_token,
        title=args.title,
        description=args.description,
        tags=tags,
        category_id=args.category,
        privacy=args.privacy,
        file_size=file_size,
    )
    print(f"✓ Upload URL: {upload_url[:80]}…")

    print("→ A enviar chunks de 8 MiB…")
    result = _upload_chunked(upload_url, args.video, file_size)
    yt_id = result.get("id")
    if not yt_id:
        sys.exit(f"YouTube não devolveu video id: {result}")
    yt_url = f"https://youtube.com/watch?v={yt_id}"
    print()
    print(f"✓ Vídeo no YouTube: {yt_url}")
    print(f"  Status: {result.get('status', {}).get('uploadStatus')}")

    if not args.no_register:
        reg = _register_in_backend(
            youtube_video_id=yt_id,
            title=args.title,
            filename=args.video.name,
            file_size=file_size,
            video_id=args.video_id,
        )
        if reg:
            print(f"✓ Registado no backend: video_id={reg.get('video_id')}")

    print()
    print()
    print("💡 DICA DE QUALIDADE:")
    print("   Use sempre o vídeo ORIGINAL (sem compressão) para upload no YouTube.")
    print("   O YouTube re-encodeia o vídeo automaticamente — se ele já chegar")
    print("   comprimido, a dupla compressão piora a qualidade visivelmente.")
    print("   NÃO use o aletube_compress.sh antes deste upload.")
    print()
    print("Concluído. Podes apagar o ficheiro local se quiseres:")
    print(f"  rm {args.video}")


if __name__ == "__main__":
    main()
