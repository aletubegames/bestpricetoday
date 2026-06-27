"""Testa seletores de imagem no card."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent / ".ml_cookies.json"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium-browser",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()
        cookies = json.loads(COOKIES_FILE.read_text())
        await context.add_cookies(cookies)
        page = await context.new_page()

        await page.goto("https://www.mercadolivre.com.br/afiliados/hub#menu-lateral", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        extra_btn = await page.query_selector("#extra_commission")
        if extra_btn:
            await extra_btn.click()
            await page.wait_for_timeout(2000)

        cards = await page.query_selector_all(".poly-card__content")
        print(f"Cards: {len(cards)}")
        if cards:
            card = cards[0]
            # Teste 1: img.poly-component__picture dentro do card
            img1 = await card.query_selector("img.poly-component__picture")
            print(f"img.poly-component__picture no card: {img1 is not None}")

            # Teste 2: qualquer img dentro do card
            all_imgs = await card.query_selector_all("img")
            print(f"Total imgs no card: {len(all_imgs)}")
            for i, img in enumerate(all_imgs[:3]):
                src = await img.get_attribute("src") or ""
                cls = await img.get_attribute("class") or ""
                print(f"  img[{i}] class={cls[:40]} src={src[:60]}")

            # Teste 3: closest .poly-card
            parent = await card.evaluate_handle("el => el.closest('.poly-card, li.poly-card, article')")
            if parent:
                img2 = await parent.query_selector("img.poly-component__picture")
                print(f"img no parent .poly-card: {img2 is not None}")
                all_imgs2 = await parent.query_selector_all("img")
                print(f"Total imgs no parent: {len(all_imgs2)}")
                for i, img in enumerate(all_imgs2[:3]):
                    src = await img.get_attribute("src") or ""
                    cls = await img.get_attribute("class") or ""
                    print(f"  parent img[{i}] class={cls[:40]} src={src[:60]}")

            # Teste 4: poly-card direto
            poly_cards = await page.query_selector_all("li.poly-card, .poly-card")
            print(f"\n.poly-card direto: {len(poly_cards)}")
            if poly_cards:
                img3 = await poly_cards[0].query_selector("img.poly-component__picture")
                if img3:
                    src = await img3.get_attribute("src") or ""
                    print(f"  img src: {src[:80]}")

        await browser.close()


asyncio.run(main())
