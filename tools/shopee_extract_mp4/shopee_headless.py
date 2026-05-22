#!/usr/bin/env python3
"""
Shopee Headless Scraper
Executa extração de vídeos via Playwright (sem manual copy-paste)
"""
import asyncio
import json
from pathlib import Path
import sys
import csv

async def scrape_shopee_videos(csv_path: Path, output_dir: Path):
    """Acessa Shopee com Playwright, executa JS e extrai vídeos"""
    
    from playwright.async_api import async_playwright
    
    print(f"📥 Lendo CSV: {csv_path.name}")
    
    # Ler CSV
    with open(csv_path, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    
    links = [
        {'product': r['Product Link'].strip(), 'offer': r['Offer Link'].strip()}
        for r in rows if r.get('Product Link')
    ]
    print(f"✔ {len(links)} produtos extraídos do CSV\n")
    
    # Serializar links como JSON seguro
    links_json = json.dumps(links, ensure_ascii=False)
    
    # JS que será executado no browser
    js_code = f"""
(async () => {{
  const LINKS = {links_json};
  const sleep = ms => new Promise(r=>setTimeout(r,ms));
  const results = [];
  
  const UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  ];
  
  const getRandomUA = () => UAS[Math.floor(Math.random() * UAS.length)];
  const randomDelay = (min, max) => min + Math.random() * (max - min);
  
  let successCount = 0;
  let blocked = false;
  
  for(let i=0; i<LINKS.length; i++){{
    if(blocked) {{
      console.log("🚫 BLOQUEADO. Pausando 15s...");
      await sleep(15000);
      blocked = false;
    }}
    
    const {{product, offer}} = LINKS[i];
    const m = product.match(/\\/product\\/(\\d+)\\/(\\d+)/);
    if(!m) {{ 
      results.push({{slug:offer.split("/").pop(), offer, src:null, status:"invalid_url"}}); 
      continue; 
    }}
    
    const [,shopid,itemid] = m;
    const slug = offer.split("/").pop();
    
    try {{
      const baseDelay = 800 + (i % 20) * 150;
      const jitter = randomDelay(baseDelay, baseDelay + 500);
      await sleep(jitter);
      
      const opts = {{
        credentials: "include",
        headers: {{
          "User-Agent": getRandomUA(),
          "Accept": "application/json, text/plain, */*",
          "Accept-Language": "pt-BR,pt;q=0.9",
          "Referer": "https://shopee.com.br/",
        }}
      }};
      
      const r = await fetch("/api/v4/item/get?itemid="+itemid+"&shopid="+shopid, opts);
      
      if(r.status === 429) {{
        blocked = true;
        results.push({{slug, offer, src:null, status:"rate_limited"}});
        console.log(`⚠ [${{i+1}}/${{LINKS.length}}] Rate limit 429`);
        continue;
      }}
      
      if(!r.ok) {{
        results.push({{slug, offer, src:null, status:`http_${{r.status}}`}});
        console.log(`✗ [${{i+1}}/${{LINKS.length}}] ${{slug}} (HTTP ${{r.status}})`);
        continue;
      }}
      
      const j = await r.json();
      const v = j?.data?.video_info_list?.[0];
      const src = v?.video_url?.replace("{{0}}","mp4") || v?.default_format?.url || v?.url || null;
      
      results.push({{slug, offer, src, status: src ? "ok" : "no_video"}});
      console.log(`${{src ? "✔" : "—"}} [${{i+1}}/${{LINKS.length}}] ${{slug}}`);
      if(src) successCount++;
      
    }} catch(e) {{
      results.push({{slug, offer, src:null, status:"error", error:e.message}});
      console.log(`✗ [${{i+1}}/${{LINKS.length}}] ${{slug}} - ${{e.message}}`);
    }}
    
    if((i+1) % 15 === 0 && i+1 < LINKS.length) {{
      const pauseTime = 5000 + Math.random() * 3000;
      console.log(`⏸ pausa ${{(pauseTime/1000).toFixed(1)}}s...`);
      await sleep(pauseTime);
    }}
  }}
  
  console.log(`\\n✔ Concluído: ${{successCount}} vídeos encontrados`);
  return results;
}})();
"""
    
    async with async_playwright() as p:
        print("🌐 Iniciando Chromium...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capturar console logs
        page.on("console", lambda msg: print(f"  {msg.text}"))
        
        print("📍 Navegando para shopee.com.br...")
        try:
            await page.goto("https://shopee.com.br", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"⚠ Aviso ao carregar página: {e}")
        
        # Aguardar carregamento
        await asyncio.sleep(3)
        
        print("▶ Executando extração de vídeos...\n")
        
        # Executar JS
        results = await page.evaluate(js_code)
        
        await browser.close()
    
    # Salvar resultado
    output_file = Path(output_dir) / 'shopee_videos.json'
    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    
    print(f"\n✔ Resultado salvo: {output_file}")
    
    videos_count = len([r for r in results if r.get('src')])
    print(f"📊 Total: {videos_count} vídeos com URL")
    
    return results

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Shopee Headless Scraper')
    parser.add_argument('csv_input', help='Arquivo CSV')
    parser.add_argument('--output', '-o', type=Path, default=None)
    
    args = parser.parse_args()
    csv_path = Path(args.csv_input).resolve()
    output_dir = (args.output or csv_path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not csv_path.exists():
        print(f"❌ {csv_path} não encontrado", file=sys.stderr)
        sys.exit(1)
    
    await scrape_shopee_videos(csv_path, output_dir)

if __name__ == '__main__':
    asyncio.run(main())
