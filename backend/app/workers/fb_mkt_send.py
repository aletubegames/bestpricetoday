#!/usr/bin/env python3
"""Envia UMA resposta numa conversa do Messenger — chamado pelo Devin.

Uso: DISPLAY=:99 venv/bin/python -m app.workers.fb_mkt_send "<conv_url>" "<texto>"

Digitação humanizada (delay por tecla + pensar antes/depois).
Se a Meta pedir login/checkpoint, pausa o sistema e alerta.
"""
import sys, time, random

sys.path.insert(0, "/home/alessandro/backend")
from app.workers.fb_mkt_common import (
    h_sleep, tg_alert, open_browser, detect_block, pause_all, is_paused)

from playwright.sync_api import sync_playwright


def type_human(page, text):
    """Digita com delay por tecla (50-180ms) e pausas ocasionais."""
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(50, 180))
        if random.random() < 0.03:      # pausa de "pensar" ocasional
            time.sleep(random.uniform(0.4, 1.6))


def main(conv_url, text):
    if is_paused():
        print("pausado")
        sys.exit(3)
    with sync_playwright() as p:
        ctx, page = open_browser(p)
        try:
            page.goto(conv_url, timeout=60000)
            h_sleep(5, 9)
            block = detect_block(page)
            if block:
                pause_all(block)
                tg_alert("🚫 FB MKT PAUSADO no send — " + block)
                sys.exit(4)
            # composer do messenger: contenteditable
            box = page.locator(
                '[contenteditable="true"][role="textbox"], '
                'div[aria-label*="ensagem"][contenteditable="true"], '
                'div[contenteditable="true"]').last
            box.click()
            h_sleep(1, 3)
            type_human(page, text)
            h_sleep(2, 5)              # "relê" antes de enviar
            page.keyboard.press("Enter")
            h_sleep(2, 4)
            print("enviado")
        finally:
            ctx.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: fb_mkt_send <conv_url> <texto>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
