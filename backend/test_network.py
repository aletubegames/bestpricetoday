"""Intercepta requisições ao clicar Compartilhar."""
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

        # Intercepta TODAS as requisições
        all_requests = []

        def on_request(req):
            all_requests.append(f"REQ {req.method} {req.url}")

        def on_response(resp):
            # Só loga respostas que não são CSS/JS/imagem
            url = resp.url
            if not any(url.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".webp", ".svg", ".woff", ".woff2", ".ico"]):
                all_requests.append(f"RESP {resp.status} {url}")

        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto("https://www.mercadolivre.com.br/afiliados/hub#menu-lateral", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Ativa Ganhos extras
        extra_btn = await page.query_selector("#extra_commission")
        if extra_btn:
            await extra_btn.click()
            await page.wait_for_timeout(2000)

        # Limpa requests até aqui
        all_requests.clear()

        # Clica no Compartilhar do primeiro card
        cards = await page.query_selector_all(".poly-card__content")
        print(f"Cards: {len(cards)}")
        if cards:
            share_btn = await cards[0].query_selector(".andes-button--quiet")
            if share_btn:
                print("Clicando Compartilhar...")
                await share_btn.click()
                await page.wait_for_timeout(3000)

        print(f"\n{len(all_requests)} requisições após clicar Compartilhar:")
        for r in all_requests:
            if "share" in r.lower() or "meli" in r.lower() or "affiliate" in r.lower() or "short" in r.lower() or "deeplink" in r.lower() or "api" in r.lower():
                print(f"  *** {r}")
            else:
                print(f"  {r}")

        await browser.close()


asyncio.run(main())
