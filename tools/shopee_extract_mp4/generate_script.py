#!/usr/bin/env python3
"""
generate_script.py — Lê shopee_products.csv e gera:
  1. console_script.js  com os links populados (pronto para colar no F12)
  2. shopee_videos.csv  (template com headers, para o browser preencher)

Uso:
  python generate_script.py                              # usa shopee_products.csv mais recente
  python generate_script.py --file produtos.csv          # CSV específico
  python generate_script.py --output-js custom.js        # nome customizado
  python generate_script.py --min-commission 5           # filtra comissão mínima %
  python generate_script.py --only-with-video            # só produtos que têm vídeo (se coluna existir)
  python generate_script.py --limit 50                   # limita N produtos
"""

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent              # tools/shopee_extract_mp4/
PROJECT_ROOT = SCRIPT_DIR.parent.parent                    # repo root

DEFAULT_CSV = SCRIPT_DIR / "shopee_products.csv"
DEFAULT_JS  = SCRIPT_DIR / "console_script.js"
DEFAULT_VIDEOS_CSV = SCRIPT_DIR / "shopee_videos.csv"

# ── template do console_script.js ─────────────────────────────────────────────
# O template é o console_script.js original com os links substituídos por placeholder
JS_TEMPLATE_PREFIX = """(async () => {
  const STORAGE_KEY = 'shopee_dl_progress';
  const CSV_KEY     = 'shopee_csv_data';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const human = () => sleep(3000 + Math.random() * 3000);

  // ── COLE SEUS LINKS AQUI ──────────────────────────────────
  const links = `
"""

JS_TEMPLATE_SUFFIX = """`.trim().split('\\n').map(s => s.trim()).filter(Boolean);
  // ─────────────────────────────────────────────────────────

  let progress = {};
  let csvRows  = [];
  try { progress = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch(e) {}
  try { csvRows  = JSON.parse(localStorage.getItem(CSV_KEY)     || '[]'); } catch(e) {}

  const save = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    localStorage.setItem(CSV_KEY,     JSON.stringify(csvRows));
  };

  // overlay
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;bottom:0;right:0;width:500px;max-height:380px;overflow-y:auto;background:#111;color:#0f0;font:12px monospace;z-index:2147483647;padding:10px 14px;border-top:3px solid #0f0;border-left:3px solid #0f0';
  document.body.appendChild(box);
  const log = (msg, c='#0f0') => {
    const d = document.createElement('div');
    d.style.color = c; d.textContent = msg;
    box.appendChild(d); box.scrollTop = box.scrollHeight;
  };

  const exportCsv = () => {
    if (!csvRows.length) { log('Nenhum dado para CSV', '#f90'); return; }
    const header = 'slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao';
    const esc = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const body = csvRows.map(r =>
      [r.slug, r.nome, r.preco, r.precoOrig, r.desconto, r.avaliacao,
       r.vendidos, r.estoque, r.temVideo, r.urlFinal, r.descricao]
      .map(esc).join(',')
    ).join('\\n');
    const blob = new Blob(['\\ufeff' + header + '\\n' + body], { type: 'text/csv;charset=utf-8' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob), download: 'shopee_videos.csv'
    });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    log(`\\n📥 shopee_videos.csv (${csvRows.length} linhas)`, '#0ff');
  };

  const pending = links.filter(l => {
    const slug = l.split('/').pop();
    return !progress[slug] || progress[slug] === 'timeout';
  });

  const feitos = links.length - pending.length;
  log(`Total: ${links.length} | Feitos: ${feitos} | Pendentes: ${pending.length}`, '#ff0');

  if (!pending.length) {
    log('Tudo processado! Gerando CSV...', '#0f0');
    exportCsv();
    return;
  }

  const tab = window.open('about:blank', '_blank');
  if (!tab) { log('✗ popup bloqueado — libere e rode de novo', '#f00'); return; }
  window.focus();
  await sleep(1000);

  const resolveUrl = (link) => new Promise(resolve => {
    tab.location.href = 'about:blank';
    setTimeout(() => {
      tab.location.href = link;
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        try {
          const h = tab.location.href;
          if (h && !h.includes('about:blank') && !h.includes('s.shopee.com.br')) {
            clearInterval(t); resolve(h);
          }
        } catch(e) {}
        if (tries > 100) { clearInterval(t); resolve(null); }
      }, 300);
    }, 800);
  });

  const downloadBlob = async (url, filename) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const blob = await res.blob();
    const burl = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), { href: burl, download: filename });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(burl), 15000);
  };

  let ok = 0, sem = 0, erro = 0, timeout = 0;

  for (let i = 0; i < pending.length; i++) {
    const link = pending[i];
    const slug = link.split('/').pop();
    log(`\\n[${i+1}/${pending.length}] ${slug}`);

    try {
      const finalUrl = await resolveUrl(link);
      window.focus();

      if (!finalUrl) {
        log('  ✗ timeout — retry na próxima rodada', '#f90');
        progress[slug] = 'timeout'; save(); timeout++;
        await human(); continue;
      }

      log('  → ' + finalUrl.split('?')[0], '#555');

      const nums = new URL(finalUrl).pathname.split('/').filter(p => /^\\d{6,}$/.test(p));
      if (nums.length < 2) {
        log('  ✗ IDs não encontrados', '#f90');
        progress[slug] = 'erro'; save(); erro++;
        await human(); continue;
      }

      const shopid = nums[nums.length - 2];
      const itemid = nums[nums.length - 1];
      log(`  shopid=${shopid} itemid=${itemid}`, '#aaa');

      await sleep(1500 + Math.random() * 1500);

      const res = await fetch(`/api/v4/item/get?itemid=${itemid}&shopid=${shopid}`, { credentials: 'include' });
      const j = await res.json().catch(() => null);

      if (!j?.data) {
        log('  ✗ API sem dados', '#f90');
        progress[slug] = 'erro'; save(); erro++;
        await human(); continue;
      }

      const d = j.data;

      const nome      = (d.name || '').replace(/[\\r\\n]+/g, ' ');
      const precoRaw  = d.price || d.price_min || 0;
      const origRaw   = d.price_before_discount || 0;
      const preco     = (precoRaw / 100000).toFixed(2);
      const precoOrig = origRaw ? (origRaw / 100000).toFixed(2) : preco;
      const desconto  = origRaw ? (((origRaw - precoRaw) / origRaw) * 100).toFixed(0) + '%' : '0%';
      const avaliacao = d.item_rating?.rating_star?.toFixed(1) || '';
      const vendidos  = d.historical_sold || d.sold || 0;
      const estoque   = d.stock || 0;
      const descricao = (d.description || '').replace(/[\\r\\n\\t]+/g, ' ').slice(0, 500);
      const urlFinal  = finalUrl.split('?')[0];
      const temVideo  = !!(d.video_info_list?.length);

      log(`  📦 ${nome.slice(0,45)} | R$${preco} | ⭐${avaliacao} | 🛒${vendidos}`, '#0ff');

      // ── vídeo ─────────────────────────────────────────────
      const vlist = d.video_info_list;
      let videoUrl = null;

      if (vlist?.length) {
        const v = vlist[0];
        videoUrl =
          v?.formats?.sort((a,b) => (b.width||0) - (a.width||0))?.[0]?.url ||
          v?.default_format?.url || null;
      }

      // fallback: clica no botão de play na página e pega src do <video>
      if (!videoUrl) {
        log('  API sem vídeo — tentando via página...', '#f90');
        try {
          tab.location.href = finalUrl;
          await sleep(5000);

          const xp = '//*[@id="sll2-normal-pdp-main"]/div/div/div/div[2]/section/section[1]/div[2]/div[2]/button/svg';
          const btn = document.evaluate(xp, tab.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
          if (btn) {
            btn.click();
            log('  clicou no play — aguardando vídeo...', '#aaa');
            await sleep(3000);
          }

          const vidEl = tab.document.querySelector('video');
          videoUrl = vidEl?.currentSrc || vidEl?.src || null;

          tab.location.href = 'about:blank';
        } catch(e) {
          log('  fallback falhou: ' + e.message, '#f90');
          tab.location.href = 'about:blank';
        }
      }

      if (!videoUrl) {
        log('  — sem vídeo em nenhuma fonte', '#888');
        sem++;
      } else {
        log('  baixando vídeo...', '#ff0');
        await downloadBlob(videoUrl, slug + '.mp4');
        log('  ✓ ' + slug + '.mp4', '#0f0');
        ok++;
      }

      csvRows = csvRows.filter(r => r.slug !== slug);
      csvRows.push({ slug, nome, preco, precoOrig, desconto, avaliacao, vendidos, estoque, temVideo, urlFinal, descricao });
      progress[slug] = 'ok';
      save();

    } catch(e) {
      log(`  ✗ ERRO: ${e.message}`, '#f00');
      progress[slug] = 'erro'; save(); erro++;
    }

    await human();
  }

  try { tab.close(); } catch(e) {}

  log(`\\n══════════════════════════════`, '#ff0');
  log(`✓ vídeos baixados : ${ok}`,            '#0f0');
  log(`— sem vídeo       : ${sem}`,            '#888');
  log(`⟳ timeout (retry) : ${timeout}`,        timeout ? '#f90' : '#555');
  log(`✗ erros           : ${erro}`,            erro    ? '#f00' : '#555');
  log(`══════════════════════════════`, '#ff0');

  exportCsv();

  log('\\nPara resetar tudo: localStorage.removeItem("shopee_dl_progress"); localStorage.removeItem("shopee_csv_data")', '#555');
})();"""


# ── CSV helpers ────────────────────────────────────────────────────────────────
def read_products_csv(path: Path) -> list[dict]:
    """Lê shopee_products.csv e retorna lista de dicts."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def extract_short_links(products: list[dict]) -> list[str]:
    """
    Extrai links curtos (s.shopee.com.br/xxxxx) do CSV de produtos.
    Tenta colunas na ordem: Offer Link → Product Link (se for curto).
    """
    links = []
    for row in products:
        # Offer Link é o link curto (s.shopee.com.br/xxxxx)
        offer = row.get("Offer Link", "").strip()
        if offer and "s.shopee.com.br" in offer:
            links.append(offer)
            continue
        # Fallback: Product Link pode ter formato curto
        product = row.get("Product Link", "").strip()
        if product and "s.shopee.com.br" in product:
            links.append(product)
    return links


def parse_commission_pct(raw: str) -> float | None:
    """Extrai '10%' → 10.0"""
    if not raw:
        return None
    import re
    m = re.search(r"([\d.,]+)", raw.replace(",", "."))
    return float(m.group(1)) if m else None


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Gera console_script.js a partir do shopee_products.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python generate_script.py
  python generate_script.py --file shopee_products.csv
  python generate_script.py --min-commission 5
  python generate_script.py --limit 50
  python generate_script.py --output-js meu_script.js
""",
    )
    parser.add_argument("--file", type=str, help="Caminho do CSV de produtos")
    parser.add_argument("--output-js", type=str, default=str(DEFAULT_JS), help="Caminho do JS de saída")
    parser.add_argument("--output-csv", type=str, default=str(DEFAULT_VIDEOS_CSV), help="Caminho do CSV de vídeos (template)")
    parser.add_argument("--min-commission", type=float, default=0, help="Comissão mínima %% (filtra)")
    parser.add_argument("--limit", type=int, default=0, help="Limita N produtos (0=todos)")
    args = parser.parse_args()

    # resolve CSV
    csv_path = Path(args.file) if args.file else DEFAULT_CSV
    if not csv_path.is_absolute():
        csv_path = SCRIPT_DIR / csv_path

    if not csv_path.exists():
        print(f"ERRO: CSV nao encontrado: {csv_path}")
        sys.exit(1)

    print(f"Lendo: {csv_path}")

    # read products
    products = read_products_csv(csv_path)
    print(f"  {len(products)} produtos no CSV")

    # filter by commission
    if args.min_commission > 0:
        filtered = []
        for row in products:
            pct = parse_commission_pct(row.get("Commission Rate", ""))
            if pct is not None and pct >= args.min_commission:
                filtered.append(row)
        products = filtered
        print(f"  Filtro comissao >= {args.min_commission}%: {len(products)} produtos")

    # extract links
    links = extract_short_links(products)

    if not links:
        print("ERRO: nenhum link curto (s.shopee.com.br) encontrado no CSV")
        print("  Verifique se a coluna 'Offer Link' existe e tem links curtos")
        sys.exit(1)

    # limit
    if args.limit > 0:
        links = links[:args.limit]
        print(f"  Limitado a {args.limit} links")

    print(f"  {len(links)} links curtos extraidos")

    # ── generate JS ────────────────────────────────────────────────────────
    links_block = "\n".join(links)
    js_content = JS_TEMPLATE_PREFIX + links_block + JS_TEMPLATE_SUFFIX

    js_path = Path(args.output_js)
    if not js_path.is_absolute():
        js_path = SCRIPT_DIR / js_path

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"\n✅ JS gerado: {js_path}")
    print(f"   {len(links)} links inseridos")

    # ── generate videos CSV template ─────────────────────────────────────────
    csv_path_out = Path(args.output_csv)
    if not csv_path_out.is_absolute():
        csv_path_out = SCRIPT_DIR / csv_path_out

    # Se já existe, faz backup
    if csv_path_out.exists():
        backup = csv_path_out.with_suffix(f".csv.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        csv_path_out.rename(backup)
        print(f"   Backup: {backup.name}")

    # Cria template vazio com headers
    video_header = "slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao\n"
    with open(csv_path_out, "w", encoding="utf-8-sig") as f:
        f.write(video_header)

    print(f"✅ CSV template: {csv_path_out}")

    # ── summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  Produtos no CSV origem:  {len(products)}")
    print(f"  Links curtos extraidos:  {len(links)}")
    print(f"  JS gerado:               {js_path.name}")
    print(f"  CSV template:            {csv_path_out.name}")
    print(f"{'='*50}")
    print(f"\nProximo passo:")
    print(f"  1. Abra https://shopee.com.br (logado)")
    print(f"  2. F12 → Console")
    print(f"  3. Cole o conteudo de {js_path.name}")
    print(f"  4. O script baixa MP4s + gera shopee_videos.csv")


if __name__ == "__main__":
    main()
