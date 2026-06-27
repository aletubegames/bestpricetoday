"""Intercepta a API createLink para pegar o link de afiliado."""
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

        create_link_responses = []

        async def on_response(resp):
            if "createLink" in resp.url:
                try:
                    body = await resp.text()
                    create_link_responses.append({"url": resp.url, "status": resp.status, "body": body[:500]})
                except Exception:
                    pass

        page.on("response", on_response)

        await page.goto("https://www.mercadolivre.com.br/afiliados/hub#menu-lateral", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Ativa Ganhos extras
        extra_btn = await page.query_selector("#extra_commission")
        if extra_btn:
            await extra_btn.click()
            await page.wait_for_timeout(2000)

        # Clica no Compartilhar do primeiro card
        cards = await page.query_selector_all(".poly-card__content")
        if cards:
            share_btn = await cards[0].query_selector(".andes-button--quiet")
            if share_btn:
                print("Clicando Compartilhar...")
                await share_btn.click()
                await page.wait_for_timeout(3000)

        print(f"\n{len(create_link_responses)} respostas createLink:")
        for r in create_link_responses:
            print(f"  URL: {r['url']}")
            print(f"  Status: {r['status']}")
            print(f"  Body: {r['body']}")

        await browser.close()


asyncio.run(main())
