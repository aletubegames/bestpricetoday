#!/usr/bin/env python3
"""Backfill de geolocalização em click_events e clicks_afiliados.

Lê os IPs distintos das duas tabelas via psql (sem driver de banco),
geolocaliza com a base local DB-IP e emite um .sql com os UPDATEs.

Uso:  venv/bin/python scripts/backfill_geo.py > /tmp/geo_backfill.sql
      psql ... -f /tmp/geo_backfill.sql
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.geoip import lookup  # noqa: E402

TABLES = ("click_events", "clicks_afiliados")
PSQL = ["psql", "-h", "127.0.0.1", "-U", "bestpricetoday", "-d", "bestpricetoday", "-At"]


def q(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def ips_from(table):
    out = subprocess.run(
        PSQL + ["-c", f"select distinct ip_address from {table} where ip_address is not null and geo_source is null;"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


print("BEGIN;")
stats = {}
for table in TABLES:
    ips = ips_from(table)
    stats[table] = {"ips": len(ips), "updated": 0}
    for ip in ips:
        geo = lookup(ip)
        if not geo or geo.get("geo_source") in ("private", "dbip-notfound"):
            continue
        sets = ", ".join([
            f"country_code={q(geo.get('country_code'))}",
            f"country={q(geo.get('country'))}",
            f"region={q(geo.get('region'))}",
            f"city={q(geo.get('city'))}",
            f"latitude={q(geo.get('latitude'))}",
            f"longitude={q(geo.get('longitude'))}",
            f"geo_source={q(geo.get('geo_source'))}",
        ])
        print(f"UPDATE {table} SET {sets} WHERE ip_address={q(ip)};")
        stats[table]["updated"] += 1
print("COMMIT;")
print(f"-- {stats}", file=sys.stderr)
