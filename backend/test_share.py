"""Testa interceptar a API que gera links de afiliado meli.la."""
import asyncio
import json
import re
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

        # Intercepta requisições de rede
        api_calls = []

        def on_request(req):
            url = req.url.lower()
            if "meli.la" in url or "short" in url or "affiliate" in url or "share" in url or "deeplink" in url:
                api_calls.append(f"REQ: {req.method} {req.url}")

        def on_response(resp):
            url = resp.url.lower()
            if "meli.la" in url or "short" in url or "affiliate" in url or "share" in url or "deeplink" in url:
                api_calls.append(f"RESP: {resp.status} {resp.url}")

        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto("https://www.mercadolivre.com.br/afiliados/hub#menu-lateral", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Ativa filtro Ganhos extras
        extra_btn = await page.query_selector("#extra_commission")
        if extra_btn:
            await extra_btn.click()
            await page.wait_for_timeout(2000)
            print("Filtro Ganhos extras ativado")
        else:
            print("Botão #extra_commission NÃO encontrado")

        print(f"URL após filtro: {page.url}")

        # Espera mais e procura cards com vários seletores
        await page.wait_for_timeout(3000)
        cards = await page.query_selector_all(".poly-card__content")
        print(f"Cards .poly-card__content: {len(cards)}")
        if not cards:
            cards2 = await page.query_selector_all("[class*='poly-card']")
            print(f"Cards [class*=poly-card]: {len(cards2)}")
            cards3 = await page.query_selector_all("article")
            print(f"Articles: {len(cards3)}")
            # Screenshot
            await page.screenshot(path="/home/alessandro/backend/test_debug.png", full_page=True)
            html = await page.content()
            Path("/home/alessandro/backend/test_debug.html").write_text(html)
            print("Screenshot + HTML salvos")

        # Clica no primeiro card
        cards = await page.query_selector_all(".poly-card__content")
        print(f"Cards encontrados: {len(cards)}")
        if cards:
            # Procura botão de share
            share_btn = await cards[0].query_selector(".andes-button--quiet")
            if share_btn:
                print("Botão share encontrado, clicando...")
                await share_btn.click()
                await page.wait_for_timeout(3000)
            else:
                print("Botão share NÃO encontrado")
                # Lista todos os botões do card
                btns = await cards[0].query_selector_all("button")
                for b in btns:
                    txt = await b.inner_text()
                    cls = await b.get_attribute("class")
                    print(f"  Button: '{txt[:30]}' class={cls[:50] if cls else ''}")

        print("\nAPI calls interceptadas:")
        for c in api_calls:
            print(c)

        if not api_calls:
            print("Nenhuma chamada interceptada")
            # Procura meli.la no HTML
            html = await page.content()
            meli_links = re.findall(r"meli\.la/[^\s\"\\'>]+", html)
            print(f"Links meli.la no HTML: {meli_links[:5]}")

            # Procura qualquer link de afiliado
            aff_links = re.findall(r"https?://[^\s\"'<>]+(?:meli\.la|afiliado|affiliate)[^\s\"'<>]*", html)
            print(f"Links de afiliado: {aff_links[:5]}")

        await browser.close()


asyncio.run(main())
