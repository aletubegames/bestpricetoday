"""
quemfornece_scraper.py — Scraper/automador do portal Quem Fornece.

Faz login, cria solicitações de cotação e coleta contatos de fornecedores.

Uso:
  cd backend && python3 -m app.workers.quemfornece_scraper --login-only
  cd backend && python3 -m app.workers.quemfornece_scraper --create-solicitations
  cd backend && python3 -m app.workers.quemfornece_scraper --scrape-suppliers
  cd backend && python3 -m app.workers.quemfornece_scraper --all

Requer:
  playwright (pip install playwright && python -m playwright install chromium)

Variáveis no .env:
  QUEMFORNECE_EMAIL=seu@email.com
  QUEMFORNECE_SENHA=sua_senha
"""

import asyncio
import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("quemfornece_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"
SCREENSHOTS_DIR = BACKEND_DIR / ".quemfornece_screenshots"
COOKIES_FILE = BACKEND_DIR / ".quemfornece_cookies.json"

SCREENSHOTS_DIR.mkdir(exist_ok=True)

BASE_URL = "https://quemfornece.com"
LOGIN_URL = f"{BASE_URL}/login"
PANEL_URL = f"{BASE_URL}/painel"
SOLICITACAO_URL = f"{BASE_URL}/painel/solicitacoes/nova"
FORNECEDORES_URL = f"{BASE_URL}/fornecedores-de/dropshipping"

# ── env loader ────────────────────────────────────────────────────────────────


def load_env():
    """Carrega variáveis do .env manualmente."""
    if not ENV_FILE.exists():
        logger.error(f".env não encontrado em {ENV_FILE}")
        sys.exit(1)
    env = {}
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


# ── solicitações pré-definidas ───────────────────────────────────────────────

SOLICITACOES = [
    {
        "titulo": "Busco fornecedor de panelas e utensílios domésticos para dropshipping",
        "categoria_texto": "Produtos para Dropshipping",
        "descricao": (
            "Sou revendedor MEI (CNPJ 66.991.964/0001-57) e busco fornecedor "
            "que faça dropshipping (envio direto ao meu cliente final) de:\n"
            "- Panelas antiaderentes\n"
            "- Conjuntos de panelas\n"
            "- Utensílios de cozinha\n"
            "- Itens para casa (cozinha, decoração)\n\n"
            "Requisitos:\n"
            "- Envio para todo Brasil\n"
            "- Preço de atacado\n"
            "- Emissão de NF-e em meu CNPJ\n"
            "- Sem pedido mínimo (ou pedido mínimo baixo)\n"
            "- Prazo de envio em até 48h\n"
            "- Catálogo com fotos e descrições dos produtos\n\n"
            "Região preferencial: Minas Gerais\n"
            "Contato: aletubegames@gmail.com"
        ),
    },
    {
        "titulo": "Busco fornecedor de moda fitness e básica para dropshipping",
        "categoria_texto": "Roupas",
        "descricao": (
            "Sou revendedor MEI (CNPJ 66.991.964/0001-57) e busco fornecedor "
            "de roupas para dropshipping (envio direto ao cliente final):\n\n"
            "Produtos de interesse:\n"
            "- Leggings e calças fitness\n"
            "- Camisetas básicas (masculinas e femininas)\n"
            "- Tops e conjuntos fitness\n"
            "- Shorts e bermudas\n"
            "- Moda básica em geral\n\n"
            "Requisitos:\n"
            "- Envio para todo Brasil\n"
            "- Preço de atacado\n"
            "- Emissão de NF-e em meu CNPJ\n"
            "- Catálogo com fotos e descrições\n"
            "- Sem pedido mínimo\n"
            "- Tamanhos variados (P ao GG)\n\n"
            "Região: Minas Gerais (ou todo Brasil)\n"
            "Contato: aletubegames@gmail.com"
        ),
    },
]


# ── scraper principal ─────────────────────────────────────────────────────────


async def login(page, email: str, senha: str) -> bool:
    """Faz login no Quem Fornece. Retorna True se sucesso."""
    logger.info(f"Acessando {LOGIN_URL}...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    await page.screenshot(path=str(SCREENSHOTS_DIR / "01_login_page.png"))

    # Aguardar campos de login
    await page.wait_for_timeout(2000)

    # Procurar campo de email
    email_selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[id*="email"]',
        'input[placeholder*="mail"]',
        'input[placeholder*="Email"]',
    ]
    email_input = None
    for sel in email_selectors:
        email_input = await page.query_selector(sel)
        if email_input:
            break

    if not email_input:
        logger.error("Campo de email não encontrado!")
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01b_login_error.png"))
        return False

    await email_input.fill(email)
    logger.info(f"Email preenchido: {email}")

    # Procurar campo de senha
    senha_selectors = [
        'input[type="password"]',
        'input[name="password"]',
        'input[name="senha"]',
        'input[id*="password"]',
        'input[id*="senha"]',
    ]
    senha_input = None
    for sel in senha_selectors:
        senha_input = await page.query_selector(sel)
        if senha_input:
            break

    if not senha_input:
        logger.error("Campo de senha não encontrado!")
        return False

    await senha_input.fill(senha)
    logger.info("Senha preenchida")

    # Procurar botão de submit
    btn_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Entrar")',
        'button:has-text("Login")',
        'button:has-text("Confirmar")',
        'button:has-text("Acessar")',
    ]
    btn = None
    for sel in btn_selectors:
        btn = await page.query_selector(sel)
        if btn:
            break

    if not btn:
        logger.error("Botão de login não encontrado!")
        return False

    await btn.click()
    logger.info("Botão de login clicado, aguardando redirect...")

    # Aguardar navegação
    await page.wait_for_timeout(5000)
    await page.screenshot(path=str(SCREENSHOTS_DIR / "02_after_login.png"))

    # Verificar se logou (URL mudou para painel ou dashboard)
    current_url = page.url
    logger.info(f"URL após login: {current_url}")

    if "login" in current_url.lower():
        logger.error("Login falhou — ainda na página de login")
        return False

    logger.info("✅ Login realizado com sucesso!")
    return True


async def criar_solicitacao(page, solicitacao: dict, index: int) -> bool:
    """Cria uma solicitação no painel do Quem Fornece."""
    logger.info(f"Criando solicitação {index + 1}: {solicitacao['titulo']}")

    # Navegar para nova solicitação
    await page.goto(PANEL_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)

    # Procurar botão/link "Nova Solicitação"
    nova_selectors = [
        'a:has-text("Nova Solicitação")',
        'button:has-text("Nova Solicitação")',
        'a:has-text("Nova")',
        'a[href*="solicitacao"]',
        'a[href*="nova"]',
    ]
    nova_btn = None
    for sel in nova_selectors:
        nova_btn = await page.query_selector(sel)
        if nova_btn:
            break

    if nova_btn:
        await nova_btn.click()
        logger.info("Botão 'Nova Solicitação' clicado")
    else:
        # Tentar URL direta
        await page.goto(SOLICITACAO_URL, wait_until="domcontentloaded", timeout=60000)

    await page.wait_for_timeout(3000)
    await page.screenshot(path=str(SCREENSHOTS_DIR / f"03_solicitacao_form_{index}.png"))

    # Preencher título
    titulo_selectors = [
        'input[name="titulo"]',
        'input[name="title"]',
        'input[id*="titulo"]',
        'input[id*="title"]',
        'input[placeholder*="título"]',
        'input[placeholder*="Título"]',
        'input[placeholder*="titulo"]',
    ]
    titulo_input = None
    for sel in titulo_selectors:
        titulo_input = await page.query_selector(sel)
        if titulo_input:
            break

    if titulo_input:
        await titulo_input.fill(solicitacao["titulo"])
        logger.info(f"Título preenchido: {solicitacao['titulo']}")
    else:
        logger.warning("Campo de título não encontrado — tentando primeiro input text")
        # Tentar primeiro input text visível
        all_inputs = await page.query_selector_all('input[type="text"]')
        for inp in all_inputs:
            if await inp.is_visible():
                await inp.fill(solicitacao["titulo"])
                logger.info("Título preenchido (primeiro input text)")
                break

    # Preencher descrição
    desc_selectors = [
        'textarea[name="descricao"]',
        'textarea[name="description"]',
        'textarea[id*="descricao"]',
        'textarea[id*="description"]',
        'textarea[placeholder*="descri"]',
        "textarea",
    ]
    desc_input = None
    for sel in desc_selectors:
        desc_input = await page.query_selector(sel)
        if desc_input:
            break

    if desc_input:
        await desc_input.fill(solicitacao["descricao"])
        logger.info("Descrição preenchida")
    else:
        logger.warning("Campo de descrição não encontrado!")

    # Tentar selecionar categoria (pode ser select ou input)
    cat_selectors = [
        'select[name="categoria"]',
        'select[name="category"]',
        'select[id*="categoria"]',
        'select[id*="category"]',
    ]
    cat_select = None
    for sel in cat_selectors:
        cat_select = await page.query_selector(sel)
        if cat_select:
            break

    if cat_select:
        # Tentar selecionar por texto
        options = await cat_select.query_selector_all("option")
        for opt in options:
            text = await opt.inner_text()
            if solicitacao["categoria_texto"].lower() in text.lower():
                await cat_select.select_option(label=text)
                logger.info(f"Categoria selecionada: {text}")
                break
    else:
        logger.warning("Select de categoria não encontrado — pode ser input text")

    # Aguardar e screenshot antes de enviar
    await page.wait_for_timeout(2000)
    await page.screenshot(path=str(SCREENSHOTS_DIR / f"04_solicitacao_filled_{index}.png"))

    # Procurar botão de enviar
    submit_selectors = [
        'button[type="submit"]',
        'button:has-text("Enviar")',
        'button:has-text("Publicar")',
        'button:has-text("Salvar")',
        'button:has-text("Criar")',
        'button:has-text("Confirmar")',
    ]
    submit_btn = None
    for sel in submit_selectors:
        submit_btn = await page.query_selector(sel)
        if submit_btn:
            break

    if submit_btn:
        await submit_btn.click()
        logger.info("Botão de envio clicado!")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / f"05_solicitacao_result_{index}.png"))
        logger.info(f"✅ Solicitação {index + 1} enviada!")
        return True
    else:
        logger.error("Botão de envio não encontrado!")
        return False


async def scrape_fornecedores(page, max_fornecedores: int = 20):
    """Coleta dados de fornecedores de dropshipping."""
    logger.info(f"Acessando lista de fornecedores: {FORNECEDORES_URL}")
    await page.goto(FORNECEDORES_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    await page.screenshot(path=str(SCREENSHOTS_DIR / "06_fornecedores_list.png"))

    # Coletar TODOS os hrefs dos cards ANTES de navegar (evita context destroyed)
    cards = await page.query_selector_all('a:has-text("Ver perfil")')
    perfil_urls = []
    for card in cards[:max_fornecedores]:
        href = await card.get_attribute("href")
        if href:
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            perfil_urls.append(url)
    logger.info(f"Encontrados {len(perfil_urls)} links 'Ver perfil'")

    # Também coletar nomes/cidades dos cards da lista
    nomes_cards = []
    nomes = await page.query_selector_all("h2, h3, .fornecedor-nome, .card-title")
    for nome_el in nomes[:max_fornecedores]:
        try:
            nome = await nome_el.inner_text()
            if nome and len(nome) > 3 and "Ver perfil" not in nome:
                nomes_cards.append(nome.strip())
        except Exception:
            pass

    fornecedores = []
    perfis_visitados = 0

    # Visitar cada perfil (sem voltar pra lista — já temos as URLs)
    for i, perfil_url in enumerate(perfil_urls):
        try:
            logger.info(f"Visitando perfil {i + 1}/{len(perfil_urls)}: {perfil_url}")
            await page.goto(perfil_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)

            # Coletar dados do perfil
            page_text = await page.inner_text("body")

            # Procurar WhatsApp, email, telefone, site
            contato = {}

            # WhatsApp
            wa_links = await page.query_selector_all('a[href*="wa.me"], a[href*="whatsapp"]')
            if wa_links:
                contato["whatsapp"] = await wa_links[0].get_attribute("href")

            # Email
            email_links = await page.query_selector_all('a[href*="mailto:"]')
            if email_links:
                raw_href = await email_links[0].get_attribute("href")
                contato["email"] = raw_href.replace("mailto:", "") if raw_href else None

            # Site próprio (não quemfornece)
            site_links = await page.query_selector_all('a[href*="http"]:not([href*="quemfornece"])')
            if site_links:
                contato["site"] = await site_links[0].get_attribute("href")

            # Nome do fornecedor (h1 ou fallback)
            h1 = await page.query_selector("h1")
            nome_fornecedor = (await h1.inner_text()) if h1 else (
                nomes_cards[i] if i < len(nomes_cards) else f"Fornecedor {i+1}"
            )

            # Cidade/estado (procurar no texto)
            cidade = None
            for line in page_text.split("\n"):
                line = line.strip()
                if "/" in line and len(line) < 40 and any(
                    uf in line for uf in ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
                ):
                    cidade = line
                    break

            # Categorias/produtos (procurar seções relevantes)
            categorias = []
            for keyword in ["dropshipping", "atacado", "varejo", "categoria", "segmento"]:
                if keyword in page_text.lower():
                    categorias.append(keyword)

            fornecedor_data = {
                "nome": nome_fornecedor.strip(),
                "url": perfil_url,
                "cidade": cidade,
                "contato": contato,
                "categorias_encontradas": list(set(categorias)),
            }
            fornecedores.append(fornecedor_data)
            logger.info(f"  → {nome_fornecedor.strip()} | {cidade or 'cidade?'} | {contato}")

            perfis_visitados += 1
            await page.screenshot(
                path=str(SCREENSHOTS_DIR / f"07_perfil_{i+1}.png")
            )

        except Exception as e:
            logger.warning(f"Erro ao visitar perfil {i + 1}: {e}")
            continue

    logger.info(f"Perfis visitados: {perfis_visitados}/{len(perfil_urls)}")

    # Salvar resultados
    output_file = BACKEND_DIR / ".quemfornece_fornecedores.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(fornecedores, f, ensure_ascii=False, indent=2)
    logger.info(f"Fornecedores salvos em {output_file}")

    return fornecedores


async def main():
    parser = argparse.ArgumentParser(description="Scraper do Quem Fornece")
    parser.add_argument("--login-only", action="store_true", help="Apenas fazer login e salvar sessão")
    parser.add_argument("--create-solicitations", action="store_true", help="Criar solicitações de cotação")
    parser.add_argument("--scrape-suppliers", action="store_true", help="Coletar contatos de fornecedores")
    parser.add_argument("--all", action="store_true", help="Login + criar solicitações + coletar fornecedores")
    parser.add_argument("--headless", default="true", help="Modo headless (true/false)")
    args = parser.parse_args()

    if not any([args.login_only, args.create_solicitations, args.scrape_suppliers, args.all]):
        args.all = True

    env = load_env()
    email = env.get("QUEMFORNECE_EMAIL")
    senha = env.get("QUEMFORNECE_SENHA")

    if not email or not senha:
        logger.error("QUEMFORNECE_EMAIL ou QUEMFORNECE_SENHA não encontrados no .env")
        sys.exit(1)

    headless = args.headless.lower() != "false"

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # Detecta chromium disponível: sistema (servidor) ou playwright (local)
        chromium_path = None
        for cpath in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]:
            if Path(cpath).exists():
                chromium_path = cpath
                break

        launch_kwargs = {
            "headless": headless,
            "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        }
        if chromium_path:
            launch_kwargs["executable_path"] = chromium_path
            logger.info(f"Usando chromium do sistema: {chromium_path}")
        else:
            logger.info("Usando chromium do playwright")

        browser = await p.chromium.launch(**launch_kwargs)

        # Usa cookies salvos se existirem (evita login toda vez)
        context_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if COOKIES_FILE.exists():
            context_kwargs["storage_state"] = str(COOKIES_FILE)
            logger.info(f"Usando sessão salva em {COOKIES_FILE}")

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            # Verificar se já está logado (via cookies)
            logged_in = False
            if COOKIES_FILE.exists():
                logger.info("Verificando sessão existente...")
                await page.goto(PANEL_URL, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                current_url = page.url
                if "login" not in current_url.lower():
                    logged_in = True
                    logger.info("✅ Sessão ativa via cookies!")
                else:
                    logger.info("Sessão expirada, fazendo login...")

            # Login se necessário
            if not logged_in:
                logged_in = await login(page, email, senha)
                if not logged_in:
                    logger.error("Não foi possível fazer login. Verifique as credenciais.")
                    await page.screenshot(path=str(SCREENSHOTS_DIR / "ERROR_login.png"))
                    # Salvar HTML para debug
                    html = await page.content()
                    with open(SCREENSHOTS_DIR / "ERROR_login.html", "w") as f:
                        f.write(html)
                    return

                # Salvar cookies/sessão
                storage = await context.storage_state()
                with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(storage, f, ensure_ascii=False, indent=2)
                logger.info(f"Sessão salva em {COOKIES_FILE}")

            if args.login_only:
                logger.info("Login-only mode. Saindo.")
                return

            # Criar solicitações
            if args.create_solicitations or args.all:
                for i, sol in enumerate(SOLICITACOES):
                    success = await criar_solicitacao(page, sol, i)
                    if not success:
                        logger.warning(f"Solicitação {i+1} pode não ter sido criada. Verifique screenshots.")
                    await page.wait_for_timeout(3000)

            # Coletar fornecedores
            if args.scrape_suppliers or args.all:
                await scrape_fornecedores(page, max_fornecedores=20)

        except Exception as e:
            logger.error(f"Erro durante execução: {e}", exc_info=True)
            await page.screenshot(path=str(SCREENSHOTS_DIR / "ERROR.png"))
        finally:
            await browser.close()
            logger.info("Browser fechado.")


if __name__ == "__main__":
    asyncio.run(main())
