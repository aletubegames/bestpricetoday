#!/usr/bin/env python3
"""
Shopee Safe Scraper - Extração com proteção anti-ban
- Delays adaptativos (3-15s entre requests)
- Headers realistas (browsers reais)
- Rate-limit detection + backoff exponencial
- User-Agent rotation
- Session persistence com cookies
"""
import json
import time
import csv
import random
import sys
import requests
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime

# User-Agents reais (browsers modernos)
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]

class ShopeeSession:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        self.backoff_multiplier = 1.0
        self.rate_limit_detected = False
        
    def get_random_ua(self):
        return random.choice(USER_AGENTS)
    
    def get_adaptive_delay(self):
        """Delay adaptativo: começa 3s, vai pra 15s se detectar rate-limit"""
        base = 3 if not self.rate_limit_detected else 8
        jitter = random.uniform(0, 5)
        return base + jitter
    
    def fetch_product(self, offer_url: str, attempt=1):
        """Fetch com retry e backoff"""
        self.session.headers["User-Agent"] = self.get_random_ua()
        
        max_attempts = 3
        if attempt > max_attempts:
            return {"status": "max_retries", "error": "Excedeu tentativas"}
        
        try:
            delay = self.get_adaptive_delay()
            print(f"  ⏸ aguardando {delay:.1f}s...", end="", flush=True)
            time.sleep(delay)
            print("\r" + " " * 30 + "\r", end="", flush=True)
            
            response = self.session.get(
                offer_url,
                timeout=15,
                allow_redirects=True
            )
            
            # Rate-limit detection
            if response.status_code == 429:
                self.rate_limit_detected = True
                backoff = 10 * (2 ** attempt)
                print(f"  ⚠ HTTP 429 - aguardando {backoff}s antes de retry")
                time.sleep(backoff)
                return self.fetch_product(offer_url, attempt + 1)
            
            if response.status_code == 403:
                return {"status": "http_403", "error": "Acesso bloqueado"}
            
            if response.status_code != 200:
                return {"status": f"http_{response.status_code}", "error": f"Status {response.status_code}"}
            
            # Parse HTML pra extrair video URL
            video_url = extract_video_url(response.text)
            if video_url:
                self.rate_limit_detected = False  # reset se sucesso
                return {
                    "status": "ok",
                    "src": video_url,
                    "error": None
                }
            else:
                return {"status": "no_video", "error": "Nenhum vídeo encontrado"}
        
        except requests.Timeout:
            return {"status": "timeout", "error": "Timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

def extract_video_url(html: str) -> str | None:
    """Parse básico: procura por data-src ou src com .mp4"""
    import re
    
    # Padrões comuns em Shopee
    patterns = [
        r'"video":\s*"([^"]+\.mp4[^"]*)"',
        r'data-src="([^"]+\.mp4[^"]*)"',
        r'src="([^"]+\.mp4[^"]*)"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            url = match.group(1)
            # Desescapar JSON
            url = url.replace("\\", "")
            return url
    
    return None

def main():
    csv_file = Path("shopee_batch_20250522.csv")
    output_file = Path("shopee_videos.json")
    
    if not csv_file.exists():
        print(f"❌ {csv_file} não encontrado")
        sys.exit(1)
    
    # Ler URLs do CSV
    offers = []
    with open(csv_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if url := row.get("Offer Link"):
                offers.append(url)
    
    print(f"📥 {len(offers)} produtos pra extrair\n")
    
    session = ShopeeSession()
    results = []
    
    for i, offer_url in enumerate(offers, 1):
        slug = offer_url.split("/")[-1]
        print(f"[{i:3d}/{len(offers)}] {slug[:12]:12s}", end=" ", flush=True)
        
        data = session.fetch_product(offer_url)
        data["slug"] = slug
        data["offer"] = offer_url
        results.append(data)
        
        status_sym = "✔" if data["status"] == "ok" else "—"
        print(f"{status_sym} ({data['status']})")
    
    # Salvar JSON
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    success = len([r for r in results if r["status"] == "ok"])
    print(f"\n✅ Concluído!")
    print(f"✔ {success}/{len(offers)} vídeos encontrados")
    print(f"📁 Salvo em: {output_file.absolute()}")

if __name__ == "__main__":
    main()
