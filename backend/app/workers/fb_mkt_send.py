#!/usr/bin/env python3
"""Envia UMA resposta no Business Inbox — chamado pelo Devin.

Uso:
  xvfb-run -a venv/bin/python -m app.workers.fb_mkt_send "<filtro>" "<texto>"

Abre inbox -> clica o filtro lateral (ex: "Comentários do Facebook")
-> o painel do item não lido abre -> digita no composer -> envia.
Digitação humanizada. Kill switch em checkpoint.
"""
import sys, time, random

sys.path.insert(0, "/home/alessandro/backend")
from app.workers.fb_mkt_common import (
    h_sleep, tg_alert, open_browser, detect_block, pause_all, is_paused)
from app.workers.fb_mkt_watcher import INBOX_URL, click_filtro

from playwright.sync_api import sync_playwright


def type_human(page, text):
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(50, 180))
        if random.random() < 0.03:
            time.sleep(random.uniform(0.4, 1.6))


def main(filtro, text):
    if is_paused():
        print("pausado")
        sys.exit(3)
    with sync_playwright() as p:
        ctx, page = open_browser(p)
        try:
            page.goto(INBOX_URL, timeout=60000)
            h_sleep(8, 12)
            block = detect_block(page)
            if block:
                pause_all(block)
                tg_alert("🚫 FB MKT PAUSADO no send — " + block)
                sys.exit(4)
            click_filtro(page, filtro)
            h_sleep(5, 8)
            # composer: campo de resposta do painel aberto
            box = page.locator(
                'div[contenteditable="true"][role="textbox"], '
                'textarea[placeholder*="espond"], '
                'div[aria-label*="espond"][contenteditable="true"], '
                'div[contenteditable="true"]').last
            if not box.count():
                print("composer não achado")
                sys.exit(5)
            box.click()
            h_sleep(1, 3)
            type_human(page, text)
            h_sleep(2, 5)
            page.keyboard.press("Enter")
            h_sleep(2, 3)
            send_btn = page.get_by_role(
                "button", name=lambda n: n and (
                    "nviar" in n or "Responder" in n or "Publicar" in n))
            if send_btn.count():
                send_btn.first.click()
                h_sleep(2, 4)
            print("enviado")
        finally:
            ctx.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: fb_mkt_send <filtro> <texto>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
