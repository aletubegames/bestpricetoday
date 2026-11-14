#!/usr/bin/env python3
"""Cria anúncio no Facebook Marketplace — produto do catálogo BestPriceToday.

Regras duras (anti-ban):
- SEM link no anúncio (o Face bloqueia) — link só vai na conversa
- máx ~3 anúncios/dia, janelas aleatórias, intervalo mínimo 3h
- digitação humanizada + pausas longas entre campos
- se checkpoint/login: pausa tudo e alerta (nunca insiste)

Uso: DISPLAY=:99 venv/bin/python -m app.workers.fb_mkt_poster
Cron: rodar 2-3x/dia em horários variados; o script mesmo decide se posta.
"""
import asyncio, json, os, random, sys, time
from datetime import datetime

sys.path.insert(0, "/home/alessandro/backend")
from app.workers.fb_mkt_common import (
    BASE, h_sleep, tg_alert, load_state, save_state,
    open_browser, detect_block, pause_all, is_paused)
from playwright.sync_api import sync_playwright

MAX_POSTS_PER_DAY = 3
MIN_GAP_H = 3
# janelas em que "parece humano" postar (hora local)
WINDOWS = [(8, 11), (14, 17), (19, 22)]


def pick_product():
    """Produto com queda REAL de preço + imagem — bom anúncio."""
    import csv, io, subprocess
    sql = """
      SELECT p.id, p.title, p.price, p.original_price, p.image_url,
             p.affiliate_url, p.provider
      FROM affiliate_products p
      WHERE p.is_active
        AND p.price > 40 AND p.price < 3000
        AND p.image_url IS NOT NULL AND p.affiliate_url IS NOT NULL
        AND p.original_price > p.price * 1.15
      ORDER BY random() LIMIT 1
    """
    r = subprocess.run(
        ["psql", "-h", "127.0.0.1", "-U", "bestpricetoday",
         "-d", "bestpricetoday", "-A", "-F", "\t", "-t", "-c", sql],
        capture_output=True, text=True, timeout=30)
    line = r.stdout.strip()
    if not line:
        return None
    f = next(csv.reader(io.StringIO(line), delimiter="\t"))
    keys = ["id", "title", "price", "original_price", "image_url",
            "affiliate_url", "provider"]
    d = dict(zip(keys, f))
    for k in ("price", "original_price"):
        d[k] = float(d[k]) if d[k] not in ("", None) else None
    return d


def in_window(now):
    return any(a <= now.hour < b for a, b in WINDOWS)


def download_image(url, dest):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def type_human(page, text, per=3):
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(50, 190))
        if random.random() < 0.02:
            time.sleep(random.uniform(0.5, 1.8))


def main():
    if is_paused():
        print("pausado")
        return
    now = datetime.now()
    st = load_state()
    today = now.strftime("%Y-%m-%d")
    posts_today = [t for t in st["posted_log"] if t.startswith(today)]
    if len(posts_today) >= MAX_POSTS_PER_DAY:
        print("limite diário atingido")
        return
    if posts_today:
        last = datetime.fromisoformat(posts_today[-1].split("|")[1])
        if (now - last).total_seconds() < MIN_GAP_H * 3600:
            print("gap mínimo não atingido")
            return
    if not in_window(now):
        print("fora de janela humana")
        return

    prod = pick_product()
    if not prod:
        print("sem produto elegível")
        return
    price = prod["price"]
    orig = prod["original_price"] or price
    pct = int(round((1 - price / orig) * 100)) if orig > price else 0
    title = prod["title"][:99]
    desc = (
        f"{title}\n\n"
        f"De R$ {orig:,.2f} por R$ {price:,.2f}"
        + (f" ({pct}% OFF)" if pct else "") +
        "\n\nProduto novo, loja oficial no Brasil. "
        "Me chama no chat que te passo o link de compra com o desconto "
        "direto na loja. 👍"
    ).replace(",", ".")

    img_path = f"/tmp/fb_mkt_{prod['id']}.jpg"
    try:
        download_image(prod["image_url"], img_path)
    except Exception as e:
        print("falha img:", e)
        return

    with sync_playwright() as p:
        ctx, page = open_browser(p)
        try:
            page.goto("https://www.facebook.com/marketplace/create/item",
                      timeout=60000)
            h_sleep(6, 10)
            block = detect_block(page)
            if block:
                pause_all(block)
                tg_alert("🚫 FB MKT PAUSADO no poster — " + block)
                return

            # foto
            fc = page.locator('input[type="file"]').first
            fc.set_input_files(img_path)
            h_sleep(4, 8)

            # campos de texto — o form muda; pego os editáveis visíveis
            page.keyboard.press("Tab")
            h_sleep(1, 2)
            # título
            title_box = page.get_by_role(
                "textbox", name=lambda n: n and "ítulo" in n) or \
                page.locator('input[aria-label*="ítulo"], input[placeholder*="ítulo"]')
            title_box.first.click()
            type_human(page, title)
            h_sleep(2, 4)
            # preço
            price_box = page.locator(
                'input[aria-label*="reço"], input[placeholder*="reço"],'
                ' input[aria-label*="rice"]').first
            price_box.click()
            type_human(page, f"{price:.2f}".replace(".", ","))
            h_sleep(2, 4)
            # descrição
            desc_box = page.locator(
                'textarea, div[contenteditable="true"]').last
            desc_box.click()
            type_human(page, desc)
            h_sleep(3, 6)

            # Avançar / Publicar — textos variam; procuro o botão
            for label in ("Avançar", "Continuar", "Next"):
                btn = page.get_by_role("button", name=label)
                if btn.count():
                    btn.first.click()
                    h_sleep(4, 7)
                    break
            pub = page.get_by_role(
                "button", name=lambda n: n and "ublicar" in n)
            if pub.count():
                pub.first.click()
                h_sleep(8, 14)
                st["posted_log"].append(f"{prod['id']}|{now.isoformat()}")
                save_state(st)
                tg_alert(f"📣 FB MKT publicado: {title[:60]} — R$ {price:.2f}")
                print("publicado:", prod["id"])
            else:
                tg_alert("⚠️ FB MKT: não achei botão Publicar — "
                         "anúncio ficou em rascunho")
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
