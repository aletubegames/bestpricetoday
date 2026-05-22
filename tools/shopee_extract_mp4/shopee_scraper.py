#!/usr/bin/env python3
"""
Shopee Video Scraper (requests-based)
Extrai URLs de vídeo usando API direta com proteção anti-bot
"""
import json
import time
import csv
import random
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    """Cria session com retry strategy"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_random_ua():
    """User-Agent rotation"""
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    return random.choice(uas)

def extract_shopee_ids(product_url):
    """Extrai shopid e itemid de URL Shopee"""
    try:
        match = product_url.split('/product/')[-1].split('?')[0].split('/')
        if len(match) >= 2:
            return int(match[0]), int(match[1])
    except:
        pass
    return None, None

def fetch_product_videos(shopid, itemid, session, attempt=1, max_attempts=3):
    """Busca vídeos do produto via API"""
    
    if attempt > max_attempts:
        return None, "max_retries"
    
    # Delay adaptativo
    base_delay = 0.8 + random.random() * 0.7
    time.sleep(base_delay)
    
    try:
        url = f"https://shopee.com.br/api/v4/item/get?itemid={itemid}&shopid={shopid}"
        
        headers = {
            "User-Agent": get_random_ua(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://shopee.com.br/",
            "X-Requested-With": "XMLHttpRequest",
        }
        
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 429:
            # Rate limit - aguardar e tentar novamente
            wait_time = 10 + random.random() * 10
            print(f"    ⚠ Rate limit 429. Aguardando {wait_time:.1f}s...")
            time.sleep(wait_time)
            return fetch_product_videos(shopid, itemid, session, attempt+1, max_attempts)
        
        if response.status_code != 200:
            return None, f"http_{response.status_code}"
        
        data = response.json()
        video_list = data.get('data', {}).get('video_info_list', [])
        
        if not video_list:
            return None, "no_video"
        
        # Extrair URL do primeiro vídeo
        video = video_list[0]
        video_url = (
            video.get('video_url', '').replace('{0}', 'mp4') or
            video.get('url') or
            video.get('default_format', {}).get('url')
        )
        
        if video_url:
            return video_url, "ok"
        return None, "no_url"
        
    except requests.Timeout:
        return None, "timeout"
    except requests.ConnectionError:
        if attempt < max_attempts:
            time.sleep(5 + random.random() * 5)
            return fetch_product_videos(shopid, itemid, session, attempt+1, max_attempts)
        return None, "connection_error"
    except json.JSONDecodeError:
        return None, "invalid_json"
    except Exception as e:
        return None, str(e)[:30]

def scrape_videos(csv_path, output_dir):
    """Scrape principal"""
    
    csv_path = Path(csv_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📥 Lendo CSV: {csv_path.name}")
    
    # Ler CSV
    with open(csv_path, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    
    links = [
        {
            'product': r['Product Link'].strip(),
            'offer': r['Offer Link'].strip()
        }
        for r in rows if r.get('Product Link')
    ]
    
    print(f"✔ {len(links)} produtos extraídos\n")
    print("Extraindo vídeos com proteção anti-bot...\n")
    
    session = create_session()
    results = []
    success_count = 0
    
    for idx, link in enumerate(links, 1):
        product_url = link['product']
        offer_url = link['offer']
        slug = offer_url.split('/')[-1]
        
        shopid, itemid = extract_shopee_ids(product_url)
        
        if not shopid or not itemid:
            results.append({
                'slug': slug,
                'offer': offer_url,
                'src': None,
                'status': 'invalid_url'
            })
            print(f"  ✗ [{idx:3d}/{len(links)}] {slug:<15} (URL inválida)")
            continue
        
        video_url, status = fetch_product_videos(shopid, itemid, session)
        
        results.append({
            'slug': slug,
            'offer': offer_url,
            'src': video_url,
            'status': status
        })
        
        if video_url:
            print(f"  ✔ [{idx:3d}/{len(links)}] {slug:<15} {status}")
            success_count += 1
        else:
            print(f"  — [{idx:3d}/{len(links)}] {slug:<15} ({status})")
        
        # Pausa a cada 15 itens
        if idx % 15 == 0 and idx < len(links):
            pause_time = 5 + random.random() * 3
            print(f"  ⏸ pausa {pause_time:.1f}s (proteção anti-bot)...\n")
            time.sleep(pause_time)
    
    # Salvar resultado
    output_file = output_dir / 'shopee_videos.json'
    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    
    print(f"\n✅ Concluído!")
    print(f"✔ {success_count}/{len(links)} vídeos encontrados")
    print(f"📁 Salvo em: {output_file}\n")
    
    return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Shopee Video Scraper (requests-based)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 shopee_scraper.py shopee_batch_20250522.csv --output .
  python3 shopee_scraper.py shopee_batch_20250522.csv --output ./downloads
        """
    )
    parser.add_argument('csv_input', help='Arquivo CSV com links')
    parser.add_argument('-o', '--output', type=Path, default=None, help='Diretório de saída (padrão: mesmo dir do CSV)')
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv_input).resolve()
    output_dir = (args.output or csv_path.parent).resolve()
    
    if not csv_path.exists():
        print(f"❌ Erro: {csv_path} não encontrado", file=sys.stderr)
        sys.exit(1)
    
    scrape_videos(csv_path, output_dir)

if __name__ == '__main__':
    main()
