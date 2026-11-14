#!/usr/bin/env python3
"""Gerencia anúncios no Facebook Marketplace — catálogo BestPriceToday.

Regras de negócio (do dono):
- MÁX 10 anúncios/dia, MÁX 1000 anúncios ativos
- ANTES de criar: auditar existentes — atualizar preço dos que
  divergirem do banco (o link de afiliado vai na conversa, nunca no anúncio)
- ANTES de publicar: manda o anúncio pro Devin revisar (job na fila) —
  só publica se APROVADO
- SEM link no anúncio (Face bloqueia); o link /r/ de afiliado vai na
  resposta do bot quando o cliente chama
- Randomização total; kill switch em checkpoint

Uso: xvfb-run -a venv/bin/python -m app.workers.fb_mkt_poster
Cron: 3-4x/dia em janelas aleatórias; o script decide o que fazer.
"""
import csv, io, json, os, random, subprocess, sys, time
from datetime import datetime

sys.path.insert(0, "/home/alessandro/backend")
from app.workers.fb_mkt_common import (
    BASE, QUEUE_DIR, h_sleep, tg_alert, load_state, save_state,
    open_browser, detect_block, pause_all, is_paused)
from playwright.sync_api import sync_playwright

MAX_POSTS_PER_DAY = 10
MAX_ACTIVE_ADS = 1000
AUDIT_MAX_PER_RUN = 20          # audita até 20 anúncios por rodada (rotativo)
MIN_GAP_MIN = 40                # mínimo entre anúncios (10/dia ≈ 1/90min útil)
WINDOWS = [(8, 11), (14, 17), (19, 22)]
DEVIN = "/home/alessandro/.local/bin/devin"
WORKDIR = "/home/alessandro/alaserver-bot"
REVIEW_DIR = f"{BASE}/fb_mkt_review"
SELLING_URL = "https://www.facebook.com/marketplace/you/selling"


def sql(sql):
    r = subprocess.run(
        ["psql", "-h", "127.0.0.1", "-U", "bestpricetoday",
         "-d", "bestpricetoday", "-A", "-F", "\t", "-t", "-c", sql],
        capture_output=True, text=True, timeout=30)
    return r.stdout.strip()


def pick_product():
    line = sql("""
      SELECT p.id, p.title, p.price, p.original_price, p.image_url,
             p.affiliate_url, p.provider
      FROM affiliate_products p
      WHERE p.is_active
        AND p.price > 40 AND p.price < 3000
        AND p.image_url IS NOT NULL AND p.affiliate_url IS NOT NULL
        AND p.original_price > p.price * 1.15
      ORDER BY random() LIMIT 1
    """)
    if not line:
        return None
    f = next(csv.reader(io.StringIO(line), delimiter="\t"))
    keys = ["id", "title", "price", "original_price", "image_url",
            "affiliate_url", "provider"]
    d = dict(zip(keys, f))
    for k in ("price", "original_price"):
        d[k] = float(d[k]) if d[k] not in ("", None) else None
    return d


def db_price_by_title(title):
    safe = title.replace("'", "''")[:60]
    line = sql(f"""
      SELECT price FROM affiliate_products
      WHERE is_active AND title ILIKE '%{safe}%'
      ORDER BY updated_at DESC NULLS LAST LIMIT 1
    """)
    try:
        return float(line.split("\t")[0]) if line else None
    except Exception:
        return None


def in_window(now):
    return any(a <= now.hour < b for a, b in WINDOWS)


def download_image(url, dest):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def type_human(page, text):
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(50, 190))
        if random.random() < 0.02:
            time.sleep(random.uniform(0.5, 1.8))


def click_txt(page, txt):
    return page.evaluate("""(txt) => {
      const el=[...document.querySelectorAll('span,div,a,button')]
        .find(e=>e.textContent.trim()===txt);
      if(!el) return 'nf';
      let t=el;
      for(let i=0;i<8&&t;i++){
        if(t.tagName==='A'||t.getAttribute('role')==='button'
           ||t.tagName==='BUTTON'){t.click();return 'ok'}
        t=t.parentElement}
      el.click(); return 'ok';
    }""", txt)


# ---------- AUDITORIA: atualizar anúncios existentes ----------

def audit_ads(page, st):
    """Abre 'seus anúncios', lê itens, atualiza preço divergente.
    Retorna (n_anuncios_visiveis, n_atualizados)."""
    page.goto(SELLING_URL, timeout=60000)
    h_sleep(6, 10)
    items = page.evaluate("""() => {
      const rows=[...document.querySelectorAll(
        'a[href*="/marketplace/item/"]')];
      const out=[];
      for(const a of rows){
        const box=a.closest('div');
        const t=(a.innerText||a.getAttribute('aria-label')||'').trim();
        if(t) out.push(t.slice(0,300));
      }
      const seen=new Set();
      return out.filter(x=>!seen.has(x)&&seen.add(x)).slice(0,25);
    }""")
    updated = 0
    offset = st.get("audit_offset", 0)
    batch = items[offset:offset + AUDIT_MAX_PER_RUN] or items[:AUDIT_MAX_PER_RUN]
    st["audit_offset"] = offset + AUDIT_MAX_PER_RUN
    for it in batch:
        title = it.split("\n")[0].strip()[:60]
        if len(title) < 6:
            continue
        dbp = db_price_by_title(title)
        if not dbp:
            continue
        # preço exibido no card
        import re
        m = re.search(r"R\$\s*([\d\.,]+)", it)
        if not m:
            continue
        shown = float(m.group(1).replace(".", "").replace(",", "."))
        if abs(shown - dbp) / dbp > 0.02:     # divergiu >2%
            # abre o anúncio e edita o preço
            click_txt(page, title.split("\n")[0][:40])
            h_sleep(4, 7)
            click_txt(page, "Editar") or click_txt(page, "Editar anúncio")
            h_sleep(3, 5)
            price_box = page.locator(
                'input[aria-label*="reço"], input[placeholder*="reço"]'
            ).first
            if price_box.count():
                price_box.click()
                page.keyboard.press("Control+a")
                type_human(page, f"{dbp:.2f}".replace(".", ","))
                h_sleep(2, 4)
                click_txt(page, "Salvar") or click_txt(page, "Atualizar")
                h_sleep(3, 6)
                updated += 1
            page.goto(SELLING_URL, timeout=60000)
            h_sleep(4, 7)
    return len(items), updated


# ---------- REVISÃO: Devin aprova antes de publicar ----------

def review_with_devin(prod, title, desc):
    os.makedirs(REVIEW_DIR, exist_ok=True)
    job = {"prod": prod, "title": title, "desc": desc,
           "ts": int(time.time())}
    fpath = f"{REVIEW_DIR}/{int(time.time())}_{prod['id']}.json"
    with open(fpath, "w") as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    prompt = f"""Revise um anúncio do Marketplace ANTES de publicar.

Leia {fpath} — tem title, desc e dados do produto (price, original_price).

Verifique e responda EXATAMENTE uma linha começando com:
- APROVADO — se: título fiel ao produto; preço confere com o banco
  (price = preço atual; original > price); descrição SEM link, SEM
  telefone, SEM promessa impossível; tom natural de vendedor.
- REJEITADO: <motivo em 1 linha> — qualquer problema acima.

Consulte o Postgres se precisar confirmar preço:
psql -h 127.0.0.1 -U bestpricetoday -d bestpricetoday -t -c
"SELECT price, original_price FROM affiliate_products
 WHERE id='{prod['id']}'"

Depois escreva a decisão também em {fpath}.decision (1 linha)."""
    try:
        subprocess.run(
            [DEVIN, "--respect-workspace-trust", "false",
             "--permission-mode", "dangerous", "--model", "swe-2-max",
             "-c", "-p", prompt],
            cwd=WORKDIR, timeout=600,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        tg_alert(f"⚠️ FB MKT review: devin falhou — {e}")
        return False
    try:
        with open(fpath + ".decision") as f:
            return f.read().strip().upper().startswith("APROVADO")
    except Exception:
        return False


# ---------- CRIAR ANÚNCIO ----------

def create_ad(page, prod, title, desc, img_path):
    page.goto("https://www.facebook.com/marketplace/create/item",
              timeout=60000)
    h_sleep(6, 10)
    page.locator('input[type="file"]').first.set_input_files(img_path)
    h_sleep(4, 8)
    title_box = page.locator(
        'input[aria-label*="ítulo"], input[placeholder*="ítulo"]').first
    title_box.click()
    type_human(page, title)
    h_sleep(2, 4)
    price_box = page.locator(
        'input[aria-label*="reço"], input[placeholder*="reço"],'
        ' input[aria-label*="rice"]').first
    price_box.click()
    type_human(page, f"{prod['price']:.2f}".replace(".", ","))
    h_sleep(2, 4)
    desc_box = page.locator('textarea, div[contenteditable="true"]').last
    desc_box.click()
    type_human(page, desc)
    h_sleep(3, 6)
    click_txt(page, "Avançar") or click_txt(page, "Continuar")
    h_sleep(4, 7)
    if click_txt(page, "Publicar") == "ok":
        h_sleep(8, 14)
        return True
    click_txt(page, "Publicar anúncio")
    h_sleep(8, 14)
    return True


def main():
    if is_paused():
        print("pausado")
        return
    now = datetime.now()
    st = load_state()
    today = now.strftime("%Y-%m-%d")
    posts_today = [t for t in st["posted_log"] if t.startswith(today)]
    if not in_window(now):
        print("fora de janela humana")
        return

    with sync_playwright() as p:
        ctx, page = open_browser(p)
        try:
            # 1) AUDITORIA — atualiza anúncios existentes
            n_ads, n_upd = audit_ads(page, st)
            save_state(st)
            block = detect_block(page)
            if block:
                pause_all(block)
                tg_alert("🚫 FB MKT PAUSADO no poster — " + block)
                return
            print(f"audit: {n_ads} anúncios, {n_upd} atualizados")
            if n_ads >= MAX_ACTIVE_ADS:
                tg_alert(f"⚠️ FB MKT: {n_ads} anúncios ≥ limite 1000 — "
                         "só manutenção, sem novos")
                return

            # 2) NOVO ANÚNCIO (se caps ok)
            if len(posts_today) >= MAX_POSTS_PER_DAY:
                print("limite 10/dia atingido")
                return
            if posts_today:
                last = datetime.fromisoformat(posts_today[-1].split("|")[1])
                if (now - last).total_seconds() < MIN_GAP_MIN * 60:
                    print("gap mínimo")
                    return

            prod = pick_product()
            if not prod:
                print("sem produto elegível")
                return
            price, orig = prod["price"], prod["original_price"] or prod["price"]
            pct = int(round((1 - price / orig) * 100)) if orig > price else 0
            title = prod["title"][:99]
            desc = (
                f"{title}\n\n"
                f"De R$ {orig:,.2f} por R$ {price:,.2f}"
                + (f" ({pct}% OFF)" if pct else "") +
                "\n\nProduto novo, loja oficial no Brasil. "
                "Me chama no chat que te passo o link de compra "
                "com o desconto direto na loja. 👍"
            ).replace(",", ".")

            # 3) REVISÃO — Devin aprova antes de publicar
            if not review_with_devin(prod, title, desc):
                tg_alert(f"🚫 FB MKT anúncio REJEITADO na revisão: "
                         f"{title[:60]}")
                return

            img_path = f"/tmp/fb_mkt_{prod['id']}.jpg"
            try:
                download_image(prod["image_url"], img_path)
            except Exception as e:
                print("falha img:", e)
                return
            if create_ad(page, prod, title, desc, img_path):
                st["posted_log"].append(f"{prod['id']}|{now.isoformat()}")
                save_state(st)
                tg_alert(f"📣 FB MKT publicado: {title[:60]} — "
                         f"R$ {price:.2f}")
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
