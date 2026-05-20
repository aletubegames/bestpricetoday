/**
 * PARTE 1 v2 — Rode COM WiFi ligado
 * =====================================
 * Versão corrigida: seleciona corretamente título, preço e imagem
 * da página de "Meus Produtos" (aba com os seus S5L99N).
 *
 * IMPORTANTE: Navegue até a aba "Meus Produtos" antes de rodar,
 * não a aba "Ganhos Extras".
 */

(async function parte1() {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  console.log("📥 PARTE 1 v2: Iniciando...");

  // Rolar para carregar todos
  for (let i = 0; i < 15; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(400);
  }
  window.scrollTo(0, 0);
  await sleep(800);

  // Encontrar os li de produtos
  function xpAll(path) {
    const r = document.evaluate(path, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    const nodes = [];
    for (let i = 0; i < r.snapshotLength; i++) nodes.push(r.snapshotItem(i));
    return nodes;
  }
  function xp1(path) {
    const r = document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    return r.singleNodeValue;
  }

  const base = "/html/body/main/div/div[3]/div/div/div/div[5]/div/div/div[3]";
  const items = xpAll(`${base}/li`);
  console.log(`📦 ${items.length} produtos`);

  const cache = [];

  for (let i = 0; i < items.length; i++) {
    const li = items[i];
    const liXP = `${base}/li[${i+1}]`;

    // ── Título: vem do alt da imagem ou de span específico ──────────────────
    // Tentar vários seletores em ordem de prioridade
    const imgEl   = li.querySelector("img[alt]:not([alt=''])");
    const titleEl = li.querySelector("[class*='title']:not([class*='badge']):not([class*='label'])") ||
                    li.querySelector("p[class*='name'], span[class*='name'], h2, h3");

    let title = imgEl?.alt?.trim() || titleEl?.textContent?.trim() || null;

    // Limpar título: remover texto de badge/percentual que começa com números ou "GANHOS"
    if (title) {
      title = title.split('\n').map(l => l.trim())
        .find(l => l.length > 8 && !/^(GANHOS|MAIS VENDIDO|[0-9]+%)/.test(l)) || title;
    }

    // ── Imagem ───────────────────────────────────────────────────────────────
    let image = imgEl?.getAttribute("data-src") || imgEl?.src || null;
    // Ignorar placeholders pequenos
    if (image && (image.includes("placeholder") || image.includes("data:image"))) image = null;

    // ── Preço: buscar elementos específicos de preço ─────────────────────────
    // O ML usa classes como "andes-money-amount__fraction"
    const fractionEl = li.querySelector("[class*='fraction'], [class*='price-tag-fraction']");
    const centsEl    = li.querySelector("[class*='cents'], [class*='price-tag-cents']");

    let price = null;
    if (fractionEl) {
      const frac  = fractionEl.textContent.replace(/\./g, '').replace(/[^\d]/g, '');
      const cents = centsEl?.textContent?.replace(/[^\d]/g, '') || '00';
      price = parseFloat(`${frac}.${cents.padEnd(2,'0').substring(0,2)}`);
    }

    // ── Comissão % ───────────────────────────────────────────────────────────
    const commEl = li.querySelector("[class*='commission'], [class*='percentage'], [class*='percent']");
    let commission = null;
    if (commEl) {
      const m = commEl.textContent.match(/(\d+)%/);
      if (m) commission = parseInt(m[1]);
    }
    // Fallback: procurar "X%" no texto do card, excluindo desconto
    if (!commission) {
      const texts = [...li.querySelectorAll("span, p")].map(el => el.textContent.trim());
      for (const t of texts) {
        const m = t.match(/^(\d{1,2})%$/);
        if (m && parseInt(m[1]) >= 5 && parseInt(m[1]) <= 40) {
          commission = parseInt(m[1]);
          break;
        }
      }
    }

    // ── Clicar no botão share ────────────────────────────────────────────────
    const btn = xp1(`${liXP}/div[2]/div[3]/div/div/button`) ||
                li.querySelector("button[class*='share'], button[aria-label*='ompartilhar']") ||
                [...li.querySelectorAll("button")].find(b =>
                  b.querySelector("svg") || b.className.toLowerCase().includes("share")
                );

    let code = null;
    let meliLink = null;

    if (btn) {
      btn.click();
      await sleep(900);

      // Capturar do modal/DOM
      const bodyText = document.body.innerText;
      const allCodes = [...new Set(bodyText.match(/S5L99N-[A-Z0-9]{4}/g) || [])];
      code = allCodes.find(c => !cache.find(x => x.code === c)) || null;

      const allLinks = [...new Set(document.body.innerHTML.match(/https:\/\/meli\.la\/[A-Za-z0-9]+/g) || [])];
      meliLink = allLinks.find(l => !cache.find(x => x.meli_link === l)) || null;

      // Fechar
      const closeBtn = document.querySelector("[aria-label*='echar'],[aria-label*='lose'],[class*='close-button'],[class*='modal__close']");
      if (closeBtn) closeBtn.click();
      else document.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape",keyCode:27,bubbles:true}));
      await sleep(400);
    }

    cache.push({ index: i+1, code, meli_link: meliLink, title, price, commission, image });
    console.log(`  [${i+1}] ${code||'???'} | ${(title||'').substring(0,40)} | R$${price} | ${commission||'?'}%`);
  }

  localStorage.setItem("ml_affiliate_cache", JSON.stringify(cache));
  sessionStorage.setItem("ml_affiliate_cache", JSON.stringify(cache));

  console.log(`\n✅ ${cache.length} produtos cacheados`);
  console.log("🔌 Agora desconecte o WiFi e rode a PARTE 2");
})();
