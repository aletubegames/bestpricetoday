"""Testa abrir o modal de share e captura o HTML do modal."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent / ".ml_cookies.json"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()
        cookies = json.loads(COOKIES_FILE.read_text())
        await context.add_cookies(cookies)
        page = await context.new_page()

        await page.goto("https://www.mercadolivre.com.br/afiliados/hub#menu-lateral", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Ativa Ganhos extras
        extra_btn = await page.query_selector("#extra_commission")
        if extra_btn:
            await extra_btn.click()
            await page.wait_for_timeout(2000)
            print("Ganhos extras ativado")

        # Espera cards
        await page.wait_for_timeout(3000)
        cards = await page.query_selector_all(".poly-card__content")
        print(f"Cards: {len(cards)}")

        if cards:
            # Procura botão de share no primeiro card
            btns = await cards[0].query_selector_all("button")
            print(f"\nBotões no card 0: {len(btns)}")
            for i, b in enumerate(btns):
                txt = (await b.inner_text()).strip()[:40]
                cls = await b.get_attribute("class") or ""
                aria = await b.get_attribute("aria-label") or ""
                print(f"  btn[{i}]: text='{txt}' class='{cls[:60]}' aria='{aria}'")

            # Clica no botão quiet
            share_btn = await cards[0].query_selector(".andes-button--quiet")
            if share_btn:
                print("\nClicando no botão quiet...")
                await share_btn.click()
                await page.wait_for_timeout(2000)

                # Captura HTML do modal
                html = await page.content()
                # Procura por meli.la
                import re
                meli = re.findall(r"meli\.la/[^\s\"'<>]+", html)
                print(f"Links meli.la: {meli[:5]}")

                # Procura por modal
                modals = await page.query_selector_all(".andes-modal, [role='dialog'], [class*='modal']")
                print(f"Modais abertos: {len(modals)}")

                # Procura por input/textarea com link
                inputs = await page.query_selector_all("input, textarea")
                for inp in inputs:
                    val = await inp.get_attribute("value") or ""
                    if val and ("http" in val or "meli" in val):
                        print(f"Input com link: {val[:80]}")

                # Procura por qualquer elemento com texto meli.la
                meli_els = await page.query_selector_all("text=meli.la")
                print(f"Elementos com texto 'meli.la': {len(meli_els)}")

                # Screenshot
                await page.screenshot(path=".test_modal.png")
                print("Screenshot salvo: .test_modal.png")

                # Salva HTML
                Path(".test_modal.html").write_text(html)
                print("HTML salvo: .test_modal.html")

        await browser.close()


asyncio.run(main())
