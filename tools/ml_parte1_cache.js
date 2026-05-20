/**
 * PARTE 1 — Rode ANTES de desconectar o WiFi
 * =============================================
 * Força o carregamento e cache de todos os dados da página.
 * Cole no F12 Console na página: mercadolivre.com.br/afiliados/produtos
 */

(async function parte1() {
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  console.log("📥 PARTE 1: Carregando e cacheando dados...");
  console.log("⚠️  NÃO desconecte ainda!");

  // 1. Rolar para baixo para garantir que todos os produtos foram renderizados
  console.log("📜 Rolando página para carregar todos os produtos...");
  for (let i = 0; i < 20; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(300);
  }
  window.scrollTo(0, 0);
  await sleep(500);

  // 2. Pré-clicar em cada botão share para revelar os modais e cacheá-los no DOM
  const liBase = "/html/body/main/div/div[3]/div/div/div/div[5]/div/div/div[3]";
  function xpAll(path) {
    const r = document.evaluate(path, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    const nodes = [];
    for (let i = 0; i < r.snapshotLength; i++) nodes.push(r.snapshotItem(i));
    return nodes;
  }

  const items = xpAll(`${liBase}/li`);
  console.log(`📦 ${items.length} produtos encontrados`);

  // Coletar dados básicos de cada item (ainda online)
  const cache = [];

  for (let i = 0; i < items.length; i++) {
    const li = items[i];
    const liXP = `${liBase}/li[${i + 1}]`;

    function xp(path) {
      const r = document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
      return r.singleNodeValue;
    }

    // Título
    const div1 = xp(`${liXP}/div[2]/div[1]`) || li.querySelector("div:nth-child(2) > div:first-child");
    const imgEl = div1?.querySelector("img");
    const title = imgEl?.alt?.trim()
      || div1?.querySelector("[class*='title'],[class*='name'],h2,h3")?.textContent?.trim()
      || div1?.textContent?.trim().split('\n').find(l => l.trim().length > 5)?.trim()
      || null;

    // Imagem — forçar carregamento
    let image = imgEl?.getAttribute("data-src") || imgEl?.src || null;
    if (image && image.startsWith("http")) {
      // Criar elemento img para forçar cache do browser
      const preload = new Image();
      preload.src = image;
    }

    // Preço
    const div2 = xp(`${liXP}/div[2]/div[2]`) || li.querySelector("div:nth-child(2) > div:nth-child(2)");
    const priceText = div2?.textContent?.trim() || "";
    const priceClean = priceText.replace(/[^\d,]/g, '').replace(',', '.');
    const price = parseFloat(priceClean) || null;

    // Link do produto
    const aEl = xp(`${liXP}/div[2]/a`) || li.querySelector("div:nth-child(2) > a, a");
    const productUrl = aEl?.href || null;

    // Clicar no botão share para revelar código (ainda online = dados carregam)
    const btn = xp(`${liXP}/div[2]/div[3]/div/div/button`)
      || li.querySelector("div:nth-child(2) > div:nth-child(3) button")
      || [...li.querySelectorAll("button")].pop();

    let code = null;
    let meliLink = null;

    if (btn) {
      btn.click();
      await sleep(800); // aguarda modal abrir e dados carregarem

      // Capturar código do DOM
      const allText = document.body.innerText;
      const allCodes = [...new Set(allText.match(/S5L99N-[A-Z0-9]{4}/g) || [])];
      code = allCodes.find(c => !cache.find(x => x.code === c)) || null;

      // Capturar link meli.la
      const allLinks = [...new Set(document.body.innerHTML.match(/https:\/\/meli\.la\/[A-Za-z0-9]+/g) || [])];
      meliLink = allLinks.find(l => !cache.find(x => x.meli_link === l)) || null;

      // Fechar modal
      const closeBtn = document.querySelector("[aria-label*='echar'],[class*='close-btn'],button[class*='close']");
      if (closeBtn) closeBtn.click();
      else document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
      await sleep(400);
    }

    cache.push({ index: i + 1, code, meli_link: meliLink, title, price, image, product_url: productUrl });
    console.log(`  [${i+1}/${items.length}] ${code || '???'} | ${(title || '').substring(0, 40)} | R$${price}`);
  }

  // 3. Salvar no sessionStorage (sobrevive a ficar offline, perdido ao fechar aba)
  sessionStorage.setItem("ml_affiliate_cache", JSON.stringify(cache));
  // Salvar também no localStorage (persiste mesmo após fechar)
  localStorage.setItem("ml_affiliate_cache", JSON.stringify(cache));

  console.log(`\n✅ PARTE 1 CONCLUÍDA — ${cache.length} produtos cacheados`);
  console.log("🔌 Agora pode DESCONECTAR o WiFi/modo avião");
  console.log("📋 Depois rode a PARTE 2 no console para extrair o JSON final");

  return cache;
})();
