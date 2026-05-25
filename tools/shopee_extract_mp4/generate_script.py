#!/usr/bin/env python3
"""
generate_script.py — Lê shopee_products.csv e gera:
  1. console_script.js  com shopid/itemid populados (pronto para colar no F12)
  2. shopee_videos.csv  (template com headers, para o browser preencher)

O script JS NÃO resolve links curtos — usa shopid/itemid direto do CSV
via fetch('/api/v4/item/get?itemid=...&shopid=...'), evitando redirects.

Uso:
  python3 generate_script.py                              # usa shopee_products.csv mais recente
  python3 generate_script.py --file produtos.csv          # CSV específico
  python3 generate_script.py --output-js custom.js        # nome customizado
  python3 generate_script.py --min-commission 5           # filtra comissão mínima %
  python3 generate_script.py --limit 50                   # limita N produtos
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR / "shopee_products.csv"
DEFAULT_JS  = SCRIPT_DIR / "console_script.js"
DEFAULT_VIDEOS_CSV = SCRIPT_DIR / "shopee_videos.csv"

# ── template do console_script.js ─────────────────────────────────────────────
# Recebe lista de objetos {slug, shopid, itemid, offer_link} — sem resolver redirects
JS_TEMPLATE = """(async () => {
  const STORAGE_KEY = 'shopee_dl_progress';
  const CSV_KEY     = 'shopee_csv_data';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const human = () => sleep(3000 + Math.random() * 3000);

  // ── PRODUTOS (gerado pelo generate_script.py) ────────────
  const PRODUTOS = __PRODUTOS_JSON__;
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

  const pending = PRODUTOS.filter(p => !progress[p.slug] || progress[p.slug] === 'timeout');

  const feitos = PRODUTOS.length - pending.length;
  log(`Total: ${PRODUTOS.length} | Feitos: ${feitos} | Pendentes: ${pending.length}`, '#ff0');

  if (!pending.length) {
    log('Tudo processado! Gerando CSV...', '#0f0');
    exportCsv();
    return;
  }

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
    const prod = pending[i];
    const { slug, shopid, itemid } = prod;
    log(`\\n[${i+1}/${pending.length}] ${slug} (shop=${shopid} item=${itemid})`);

    try {
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
      const urlFinal  = `https://shopee.com.br/product/${shopid}/${itemid}`;
      const temVideo  = !!(d.video_info_list?.length);

      log(`  📦 ${nome.slice(0,45)} | R$${preco} | ⭐${avaliacao} | 🛒${vendidos}`, '#0ff');

      // ── vídeo via API ──────────────────────────────────────
      const vlist = d.video_info_list;
      let videoUrl = null;

      if (vlist?.length) {
        const v = vlist[0];
        videoUrl =
          v?.formats?.sort((a,b) => (b.width||0) - (a.width||0))?.[0]?.url ||
          v?.default_format?.url || null;
      }

      if (!videoUrl) {
        log('  — sem vídeo na API', '#888');
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

  log(`\\n══════════════════════════════`, '#ff0');
  log(`✓ vídeos baixados : ${ok}`,            '#0f0');
  log(`— sem vídeo       : ${sem}`,            '#888');
  log(`⟳ timeout (retry) : ${timeout}`,        timeout ? '#f90' : '#555');
  log(`✗ erros           : ${erro}`,            erro    ? '#f00' : '#555');
  log(`══════════════════════════════`, '#ff0');

  exportCsv();

  log('\\nPara resetar: localStorage.removeItem("shopee_dl_progress"); localStorage.removeItem("shopee_csv_data")', '#555');
})();"""


# ── CSV helpers ────────────────────────────────────────────────────────────────
def read_products_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_commission_pct(raw: str) -> float | None:
    if not raw:
        return None
    import re
    m = re.search(r"([\d.,]+)", raw.replace(",", "."))
    return float(m.group(1)) if m else None


def extract_products(products: list[dict]) -> list[dict]:
    """
    Extrai shopid/itemid do CSV de produtos.
    Usa Product Link (formato: shopee.com.br/product/{shopid}/{itemid})
    Fallback: Item Id do CSV como itemid, shopid vazio (não funciona sem shopid).
    """
    result = []
    for row in products:
        offer = row.get("Offer Link", "").strip()
        slug = offer.split("/").pop() if offer else ""

        product_link = row.get("Product Link", "").strip()
        shopid = ""
        itemid = ""

        # extrai shopid/itemid do Product Link
        if "/product/" in product_link:
            parts = product_link.split("/product/")[-1].split("/")
            if len(parts) >= 2:
                shopid = parts[0]
                itemid = parts[1].split("?")[0]  # remove query params

        # fallback: Item Id como itemid
        if not itemid:
            itemid = row.get("Item Id", "").strip()

        if not shopid or not itemid:
            print(f"  AVISO: sem shopid/itemid para {slug} — pulando")
            continue

        result.append({
            "slug": slug,
            "shopid": shopid,
            "itemid": itemid,
            "offer_link": offer,
        })

    return result


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Gera console_script.js a partir do shopee_products.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python3 generate_script.py
  python3 generate_script.py --min-commission 10
  python3 generate_script.py --limit 50
""",
    )
    parser.add_argument("--file", type=str, help="Caminho do CSV de produtos")
    parser.add_argument("--output-js", type=str, default=str(DEFAULT_JS))
    parser.add_argument("--output-csv", type=str, default=str(DEFAULT_VIDEOS_CSV))
    parser.add_argument("--min-commission", type=float, default=0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    csv_path = Path(args.file) if args.file else DEFAULT_CSV
    if not csv_path.is_absolute():
        csv_path = SCRIPT_DIR / csv_path

    if not csv_path.exists():
        print(f"ERRO: CSV nao encontrado: {csv_path}")
        sys.exit(1)

    print(f"Lendo: {csv_path}")
    products = read_products_csv(csv_path)
    print(f"  {len(products)} produtos no CSV")

    if args.min_commission > 0:
        products = [r for r in products
                    if (pct := parse_commission_pct(r.get("Commission Rate", "")))
                    and pct >= args.min_commission]
        print(f"  Filtro comissao >= {args.min_commission}%: {len(products)}")

    items = extract_products(products)
    print(f"  {len(items)} produtos com shopid/itemid")

    if not items:
        print("ERRO: nenhum produto valido (verificar coluna Product Link)")
        sys.exit(1)

    if args.limit > 0:
        items = items[:args.limit]
        print(f"  Limitado a {args.limit}")

    # ── gera JS ──────────────────────────────────────────────────────────────
    js_content = JS_TEMPLATE.replace(
        "__PRODUTOS_JSON__",
        json.dumps(items, ensure_ascii=False, indent=2),
    )

    js_path = Path(args.output_js)
    if not js_path.is_absolute():
        js_path = SCRIPT_DIR / js_path

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"\\n✅ JS gerado: {js_path} ({len(items)} produtos)")

    # ── gera videos CSV template ──────────────────────────────────────────────
    csv_path_out = Path(args.output_csv)
    if not csv_path_out.is_absolute():
        csv_path_out = SCRIPT_DIR / csv_path_out

    if csv_path_out.exists():
        backup = csv_path_out.with_suffix(f".csv.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        csv_path_out.rename(backup)
        print(f"   Backup: {backup.name}")

    with open(csv_path_out, "w", encoding="utf-8-sig") as f:
        f.write("slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao\\n")

    print(f"✅ CSV template: {csv_path_out}")
    print(f"\\nProximo passo:")
    print(f"  1. Abra https://shopee.com.br (logado)")
    print(f"  2. F12 → Console")
    print(f"  3. Cole o conteudo de {js_path.name}")


if __name__ == "__main__":
    main()
