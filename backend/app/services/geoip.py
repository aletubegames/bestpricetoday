"""
Geolocalização de visitantes (país / estado / cidade / coordenadas).

Estratégia:
  1. Headers do Cloudflare (CF-IPCountry, CF-Region, CF-IPCity,
     CF-IPLatitude, CF-IPLongitude) — custo zero, quando presentes.
  2. Fallback: base local DB-IP City Lite (mmdb, offline, sem rede por request).

Nunca faz chamada a API externa em caminho de request. IPs privados/loopback
(127.0.0.1, 10.x, 192.168.x, ::1, fc00::/7) não são geolocalizados — retornam
{"geo_source": "private"}.

Base: data/geoip/dbip-city-lite.mmdb (atualizada mensalmente por
scripts/update_geoip.sh). Caminho configurável por GEOIP_DB_PATH.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import geoip2.database
from geoip2.errors import AddressNotFoundError

logger = logging.getLogger("geoip")

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "geoip" / "dbip-city-lite.mmdb"
_DB_PATH = Path(os.getenv("GEOIP_DB_PATH") or _DEFAULT_DB)

_reader: Optional[geoip2.database.Reader] = None
_reader_mtime: float = 0.0
_lock = threading.Lock()

# Códigos que o Cloudflare usa quando não sabe a localização
_CF_UNKNOWN = {"", "XX", "T1"}


def _reader_instance() -> Optional[geoip2.database.Reader]:
    """Abre (e reabre se o arquivo foi atualizado) a base mmdb."""
    global _reader, _reader_mtime

    if not _DB_PATH.exists():
        return None
    try:
        mtime = _DB_PATH.stat().st_mtime
    except OSError:
        return None

    with _lock:
        if _reader is not None and mtime == _reader_mtime:
            return _reader
        try:
            if _reader is not None:
                _reader.close()
            _reader = geoip2.database.Reader(str(_DB_PATH))
            _reader_mtime = mtime
            logger.info("base de geolocalização carregada: %s", _DB_PATH)
        except Exception as exc:  # base corrompida/inacessível não derruba request
            logger.warning("falha ao abrir %s: %s", _DB_PATH, exc)
            _reader = None
    return _reader


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


@lru_cache(maxsize=8192)
def lookup(ip: Optional[str]) -> Dict[str, Any]:
    """
    Geolocaliza um IP via base local. Retorna dict com as chaves
    country_code, country, region, city, latitude, longitude, geo_source.
    Dict vazio-ish (só geo_source) quando não há dado aproveitável.
    """
    if not ip:
        return {}
    ip = ip.strip()
    if _is_private(ip):
        return {"geo_source": "private"}

    reader = _reader_instance()
    if reader is None:
        return {}

    try:
        rec = reader.city(ip)
    except AddressNotFoundError:
        return {"geo_source": "dbip-notfound"}
    except ValueError:
        return {}
    except Exception as exc:
        logger.debug("geo lookup falhou para %s: %s", ip, exc)
        return {}

    subdivisions = rec.subdivisions or []
    region = subdivisions[0].name if subdivisions else None

    data: Dict[str, Any] = {
        "country_code": rec.country.iso_code,
        "country": rec.country.name,
        "region": region,
        "city": rec.city.name,
        "latitude": rec.location.latitude,
        "longitude": rec.location.longitude,
        "geo_source": "dbip",
    }
    return {k: v for k, v in data.items() if v is not None}


def from_headers(request) -> Dict[str, Any]:
    """Extrai localização dos headers do Cloudflare, se o plano os enviar."""
    if request is None:
        return {}
    h = request.headers
    cc = (h.get("cf-ipcountry") or "").strip().upper()
    if cc in _CF_UNKNOWN:
        return {}

    region = (h.get("cf-region") or "").strip() or None
    city = (h.get("cf-ipcity") or "").strip() or None

    lat = lon = None
    try:
        if h.get("cf-iplatitude"):
            lat = float(h["cf-iplatitude"])
        if h.get("cf-iplongitude"):
            lon = float(h["cf-iplongitude"])
    except (TypeError, ValueError):
        lat = lon = None

    data: Dict[str, Any] = {
        "country_code": cc,
        "region": region,
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "geo_source": "cloudflare",
    }
    return {k: v for k, v in data.items() if v not in (None, "")}


def resolve(request, ip: Optional[str]) -> Dict[str, Any]:
    """
    Resolve a localização de um visitante: Cloudflare primeiro, base local
    como fallback. Nunca levanta exceção.
    """
    try:
        geo = from_headers(request)
        if geo.get("city") or geo.get("country_code"):
            # completa país/coordenadas com a base local quando o CF não manda
            if not geo.get("country") or geo.get("latitude") is None:
                local = lookup(ip)
                for k, v in local.items():
                    geo.setdefault(k, v)
            return geo
        return lookup(ip)
    except Exception as exc:  # geolocalização jamais pode quebrar o registro
        logger.warning("resolve() falhou (%s): %s", ip, exc)
        return {}
