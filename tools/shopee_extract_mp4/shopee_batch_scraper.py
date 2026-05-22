#!/usr/bin/env python3
"""
Shopee Batch Video Scraper
Extrai URLs de vídeo de produtos Shopee a partir de CSV exportado

Uso:
  python3 shopee_batch_scraper.py <csv_input> [--output <dir>]
"""
import csv
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

def generate_console_script(links: list, output_dir: Path) -> Path:
    """Gera script JavaScript para extrair vídeos dos produtos"""
    
    head = '{\nconst LINKS = ' + json.dumps(links, ensure_ascii=False) + ';\n'
    
    # Script otimizado para evitar bloqueio: delays adaptativos, UA rotation, headers anti-bot
    body = r"""const sleep = ms => new Promise(r=>setTimeout(r,ms));
const results = [];

// User-Agents realistas
const UAS = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
];

document.getElementById("__sdl")?.remove();
const P = document.createElement("div");
P.id = "__sdl";
P.style.cssText = "position:fixed;right:12px;bottom:12px;width:520px;max-height:380px;overflow-y:auto;background:#0a0a0a;color:#0f0;font:11px monospace;padding:14px;border-radius:10px;z-index:2147483647;white-space:pre-wrap;border:1px solid #0f0;";
document.body.appendChild(P);
const log = (m,c="#0f0")=>{ const d=document.createElement("div"); d.style.color=c; d.textContent=m; P.appendChild(d); P.scrollTop=99999; };

const getRandomUA = () => UAS[Math.floor(Math.random() * UAS.length)];
const randomDelay = (min, max) => min + Math.random() * (max - min);

(async()=>{
  log("▶ Extraindo vídeos de "+LINKS.length+" produtos...","#ff0");
  log("⚠ Evitando bloqueios com delays adaptativos","#ff9");
  
  let successCount = 0;
  let failCount = 0;
  let blocked = false;
  
  for(let i=0;i<LINKS.length;i++){
    if(blocked) {
      log("🚫 BLOQUEADO por Shopee. Pausando...","#f44");
      await sleep(15000); // pausa 15s se bloqueado
      blocked = false;
    }
    
    const {product,offer} = LINKS[i];
    const m = product.match(/\/product\/(\d+)\/(\d+)/);
    if(!m){ 
      results.push({slug:offer.split("/").pop(),offer,src:null,status:"invalid_url"}); 
      failCount++;
      continue; 
    }
    
    const [,shopid,itemid] = m;
    const slug = offer.split("/").pop();
    
    try{
      // Delay adaptativo: aumenta com # de requests
      const baseDelay = 800 + (i % 20) * 150;
      const jitter = randomDelay(baseDelay, baseDelay + 500);
      await sleep(jitter);
      
      // Request com headers realistas
      const opts = {
        credentials:"include",
        headers: {
          "User-Agent": getRandomUA(),
          "Accept": "application/json, text/plain, */*",
          "Accept-Language": "pt-BR,pt;q=0.9",
          "Referer": "https://shopee.com.br/",
          "X-Requested-With": "XMLHttpRequest",
        }
      };
      
      const r = await fetch("/api/v4/item/get?itemid="+itemid+"&shopid="+shopid, opts);
      
      // Detecta rate limit
      if(r.status === 429) {
        blocked = true;
        log("⚠ Rate limit (429) detectado!","#f90");
        results.push({slug,offer,src:null,status:"rate_limited"});
        failCount++;
        continue;
      }
      
      if(!r.ok) {
        log("  [err "+(i+1)+"] HTTP "+r.status+" - "+slug,"#f88");
        results.push({slug,offer,src:null,status:"http_"+r.status});
        failCount++;
        continue;
      }
      
      const j = await r.json();
      const v = j?.data?.video_info_list?.[0];
      const src = v?.video_url?.replace("{0}","mp4")||v?.default_format?.url||v?.url||null;
      
      results.push({slug,offer,src,status:src?"ok":"no_video"});
      
      const icon = src ? "✔" : "—";
      const color = src ? "#0f0" : "#888";
      log("  [" + String(i+1).padStart(3) + "/"+LINKS.length+"] " + slug.padEnd(16) + " " + icon, color);
      
      successCount += src ? 1 : 0;
      failCount += src ? 0 : 1;
      
    }catch(e){
      log("  [err "+(i+1)+"] "+e.message+" - "+slug,"#f44");
      results.push({slug,offer,src:null,status:"fetch_error",error:e.message});
      failCount++;
    }
    
    // Pausa maior a cada 15 itens
    if((i+1) % 15 === 0 && i+1 < LINKS.length){
      const pauseTime = 5000 + Math.random() * 3000;
      log("  ⏸ pausa " + (pauseTime/1000).toFixed(1) + "s (proteção anti-bot)...","#ff0");
      await sleep(pauseTime);
    }
  }
  
  // Download resultado
  const blob = new Blob([JSON.stringify(results,null,2)],{type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "shopee_videos.json";
  document.body.appendChild(a); 
  a.click(); 
  setTimeout(()=>a.remove(),3000);
  
  log("","#0f0");
  log("✔ CONCLUÍDO: "+successCount+" vídeos encontrados, "+failCount+" sem vídeo","#0f0");
  log("✔ shopee_videos.json salvo! Agora rode o Python.","#ff0");
})();
}
"""
    
    out_file = output_dir / 'shopee_console.js'
    out_file.write_text(head + body)
    return out_file

def download_videos(json_path: Path, output_dir: Path | None = None):
    """Baixa vídeos do JSON extraído usando yt-dlp"""
    
    if not json_path.exists():
        print(f'❌ Erro: {json_path} não encontrado', file=sys.stderr)
        return False
    
    output_dir = output_dir or json_path.parent
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        import subprocess
        results = json.loads(json_path.read_text(encoding='utf-8'))
    except ImportError:
        print('❌ yt-dlp não instalado. Instale com: pip install yt-dlp', file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f'❌ Erro ao ler JSON: {e}', file=sys.stderr)
        return False
    
    # Filtrar resultados com vídeo
    videos = [r for r in results if r.get('src')]
    print(f'📥 {len(videos)} vídeos para baixar...\n')
    
    video_dir = output_dir / 'videos'
    video_dir.mkdir(exist_ok=True)
    
    for i, item in enumerate(videos, 1):
        slug = item.get('slug', f'video_{i}')
        url = item.get('src')
        
        if not url:
            continue
        
        out_template = str(video_dir / f'{i:03d}_{slug}.%(ext)s')
        
        cmd = [
            'yt-dlp',
            '--quiet',
            '--no-warnings',
            '--socket-timeout', '30',
            '--max-sleep-interval', '5',
            '--sleep-interval', '2',
            '-f', 'best[ext=mp4]',
            '-o', out_template,
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60, text=True)
            if result.returncode == 0:
                print(f'  ✔ [{i:3d}/{len(videos)}] {slug}')
            else:
                print(f'  ✗ [{i:3d}/{len(videos)}] {slug} (yt-dlp: {result.stderr[:60]})')
        except subprocess.TimeoutExpired:
            print(f'  ✗ [{i:3d}/{len(videos)}] {slug} (timeout)')
        except FileNotFoundError:
            print(f'  ❌ yt-dlp não encontrado. Instale: pip install yt-dlp', file=sys.stderr)
            return False
    
    print(f'\n✔ Downloads concluídos em: {video_dir}')
    return True

def main():
    parser = argparse.ArgumentParser(description='Shopee Batch Video Scraper')
    subparsers = parser.add_subparsers(dest='command', help='Comando')
    
    # Subcommand: extract
    extract_parser = subparsers.add_parser('extract', help='Gerar script de extração')
    extract_parser.add_argument('csv_input', help='Arquivo CSV exportado de Shopee')
    extract_parser.add_argument('--output', '-o', type=Path, default=None, help='Diretório de saída')
    
    # Subcommand: download
    download_parser = subparsers.add_parser('download', help='Baixar vídeos do JSON')
    download_parser.add_argument('json_input', help='Arquivo JSON com URLs dos vídeos')
    download_parser.add_argument('--output', '-o', type=Path, default=None, help='Diretório de saída')
    
    args = parser.parse_args()
    
    if args.command == 'extract':
        csv_path = Path(args.csv_input).resolve()
        if not csv_path.exists():
            print(f'❌ Erro: {csv_path} não encontrado', file=sys.stderr)
            sys.exit(1)
        
        output_dir = (args.output or csv_path.parent).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(csv_path, encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            links = [
                {'product': r['Product Link'].strip(), 'offer': r['Offer Link'].strip()}
                for r in rows if r.get('Product Link')
            ]
            print(f'✔ {len(links)} produtos lidos de {csv_path.name}')
        except Exception as e:
            print(f'❌ Erro ao ler CSV: {e}', file=sys.stderr)
            sys.exit(1)
        
        js_file = generate_console_script(links, output_dir)
        print(f'✔ Script gerado: {js_file}')
        print(f'\n📋 Próximas etapas:')
        print(f'  1. Acesse https://shopee.com.br em uma aba')
        print(f'  2. Abra DevTools (F12) → Console')
        print(f'  3. Cole o conteúdo completo de: {js_file}')
        print(f'  4. Aguarde extração (pode levar 5-10 min com proteção anti-bot)')
        print(f'  5. Baixe shopee_videos.json')
        print(f'  6. Rode: python3 shopee_batch_scraper.py download shopee_videos.json')
        
    elif args.command == 'download':
        json_path = Path(args.json_input).resolve()
        output_dir = (args.output or json_path.parent).resolve()
        download_videos(json_path, output_dir)
    else:
        # Fallback: se apenas um argumento, assume 'extract'
        if len(sys.argv) == 2:
            csv_path = Path(sys.argv[1]).resolve()
            if csv_path.exists():
                output_dir = csv_path.parent
                try:
                    with open(csv_path, encoding='utf-8-sig') as f:
                        rows = list(csv.DictReader(f))
                    links = [
                        {'product': r['Product Link'].strip(), 'offer': r['Offer Link'].strip()}
                        for r in rows if r.get('Product Link')
                    ]
                    js_file = generate_console_script(links, output_dir)
                    print(f'✔ {len(links)} produtos → {js_file}')
                except Exception as e:
                    print(f'❌ Erro: {e}', file=sys.stderr)
                    sys.exit(1)
            else:
                parser.print_help()
        else:
            parser.print_help()

if __name__ == '__main__':
    main()
