/**
 * ML Affiliate BULK Extractor v3
 * ================================
 * Clica automaticamente no botão "Compartilhar" de cada produto,
 * captura o código S5L99N + dados do produto e salva no BestPrice.
 *
 * Cole no F12 Console na página de produtos afiliados do ML.
 * URL: mercadolivre.com.br/afiliados/produtos
 */

(async function () {

  const API_BASE  = "https://alessandro2090-bestpricetoday-api.hf.space";
  const ADMIN_KEY = "***";

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // ── 1. BUSCAR PRODUTOS DA BASE ────────────────────────────────────────────
  console.log("🔄 Buscando produtos na base BestPrice...");
  let baseProducts = [];
  try {
    const r = await fetch(`${API_BASE}/api/v1/affiliate/products`, {
      headers: { "X-Admin-Key": ADMIN_KEY }
    });
    const d = await r.json();
    baseProducts = d.products || [];
    console.log(`📦 Base: ${baseProducts.length} produtos | Sem título: ${baseProducts.filter(p=>!p.title).length}`);
  } catch(e) {
    console.error("❌ Erro API:", e.message);
    return;
  }

  const byCode = {};
  baseProducts.forEach(p => { if (p.ml_code) byCode[p.ml_code] = p; });

  // ── 2. ENCONTRAR TODOS OS CARDS DE PRODUTO ────────────────────────────────
  // Seletor baseado no xpath que você forneceu:
  // /html/body/main/div/div[3]/div/div/div/div[5]/div/div/div[3]/li[N]/div[2]/div[3]/div/div/button
  const listItems = [...document.querySelectorAll(
    "main li, [class*='product-list'] li, [class*='results'] li, [class*='items'] li"
  )].filter(li => li.querySelector("button"));

  console.log(`\n🔍 Cards encontrados: ${listItems.length}`);

  if (listItems.length === 0) {
    // Tentar seletor mais genérico
    const allButtons = [...document.querySelectorAll("button")].filter(b =>
      b.textContent.includes("Compartilhar") ||
      b.querySelector("span") ||
      b.closest("li")
    );
    console.log("Botões encontrados:", allButtons.length);
    console.log("Exemplo botão:", allButtons[0]?.outerHTML?.substring(0, 200));
    return;
  }

  const results = [];

  // ── 3. PARA CADA CARD: clicar no botão, capturar código, fechar ───────────
  for (let i = 0; i < listItems.length; i++) {
    const li = listItems[i];

    // Extrair título e preço ANTES de clicar (já visíveis no card)
    const titleEl = li.querySelector("[class*='title'], h2, h3, [class*='name'], [class*='label']");
    const priceEl = li.querySelector("[class*='price'], [class*='amount'], [class*='fraction']");
    const imgEl   = li.querySelector("img");

    const title = titleEl?.textContent?.trim() || null;
    const priceText = priceEl?.textContent?.trim() || "";
    const priceClean = priceText.replace(/[^\d,.]/g,"").replace(/\./g,"").replace(",",".");
    const price = parseFloat(priceClean) || null;
    let image = imgEl?.getAttribute("data-src") || imgEl?.src || null;
    if (image) image = image.replace(/\?.*$/,"").replace(/-[A-Z]\.jpg/,"-O.jpg");

    // Encontrar o botão de compartilhar dentro do li
    // Baseado no xpath: li[N]/div[2]/div[3]/div/div/button
    const shareBtn = li.querySelector(
      "div:nth-child(2) > div:nth-child(3) button, " +
      "button[class*='share'], " +
      "button[aria-label*='ompartilhar'], " +
      "button[aria-label*='hare'], " +
      "button span span"  // o span/span que você mencionou
    )?.closest("button") || li.querySelectorAll("button")[li.querySelectorAll("button").length - 1];

    if (!shareBtn) {
      console.warn(`⚠️ Card ${i+1}: botão não encontrado`);
      continue;
    }

    console.log(`\n🖱️ Card ${i+1}/${listItems.length}: clicando em compartilhar...`);
    shareBtn.click();
    await sleep(800); // aguardar modal abrir

    // Capturar o código S5L99N do modal/overlay que abriu
    let code = null;

    // O modal pode aparecer como overlay, dialog, ou inline
    const modalSelectors = [
      "[role='dialog']",
      "[class*='modal']",
      "[class*='overlay']",
      "[class*='share']",
      "[class*='popup']",
      "[class*='tooltip']",
      ".andes-modal",
      ".andes-tooltip",
    ];

    let modalEl = null;
    for (const sel of modalSelectors) {
      modalEl = document.querySelector(sel);
      if (modalEl && modalEl.textContent.includes("S5L99N")) break;
    }

    // Se não achou no modal, procurar em qualquer texto novo na página
    if (!modalEl) {
      const allText = document.body.innerText;
      const match = allText.match(/S5L99N-[A-Z0-9]{4}/);
      if (match) code = match[0];
    } else {
      const match = modalEl.innerText.match(/S5L99N-[A-Z0-9]{4}/);
      if (match) code = match[0];

      // Também tentar pegar o link meli.la do modal
      const linkEl = modalEl.querySelector("a[href*='meli.la'], input[value*='meli.la']");
      const meliLink = linkEl?.href || linkEl?.value || null;
      if (meliLink) console.log(`  Link: ${meliLink}`);
    }

    if (!code) {
      // Último recurso: buscar no HTML completo da página
      const allHTML = document.body.innerHTML;
      const allCodes = [...new Set(allHTML.match(/S5L99N-[A-Z0-9]{4}/g) || [])];
      // Pegar código que ainda não foi capturado
      const newCode = allCodes.find(c => !results.find(r => r.code === c));
      if (newCode) code = newCode;
    }

    console.log(`  Código: ${code || "❌ não encontrado"}`);
    console.log(`  Título: ${(title||"").substring(0,50)}`);
    console.log(`  Preço: R$${price}`);

    results.push({ code, title, price, image });

    // Fechar o modal
    const closeBtn = document.querySelector(
      "[aria-label*='echar'], [aria-label*='lose'], " +
      "button[class*='close'], .andes-modal__close, " +
      "[class*='close-button'], [data-testid*='close']"
    );
    if (closeBtn) {
      closeBtn.click();
    } else {
      // ESC para fechar
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
    }
    await sleep(400);
  }

  // ── 4. SALVAR NO BESTPRICE ────────────────────────────────────────────────
  console.log("\n=== RESULTADO ===");
  const toUpdate = results.filter(r => r.code && byCode[r.code]);
  const notFound = results.filter(r => r.code && !byCode[r.code]);
  const noCode   = results.filter(r => !r.code);

  console.log(`✅ Para atualizar: ${toUpdate.length}`);
  console.log(`❌ Código não na base: ${notFound.map(r=>r.code).join(", ")}`);
  console.log(`⚠️ Sem código: ${noCode.length}`);

  let updated = 0, failed = 0;

  for (const item of toUpdate) {
    const prod = byCode[item.code];
    const payload = {};
    if (item.title?.length > 3) payload.title     = item.title;
    if (item.price)              payload.price     = item.price;
    if (item.image)              payload.image_url = item.image;

    if (!Object.keys(payload).length) continue;

    try {
      const r = await fetch(`${API_BASE}/api/v1/affiliate/products/${prod.id}`, {
        method: "PATCH",
        headers: { "X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await r.json();
      if (r.ok) {
        console.log(`✅ ${item.code} → ${res.title} | R$${res.price}`);
        updated++;
      } else {
        console.error(`❌ ${item.code}:`, res);
        failed++;
      }
    } catch(e) {
      failed++;
    }
    await sleep(150);
  }

  console.log(`\n🎉 CONCLUÍDO: ${updated} atualizados | ${failed} erros`);
  alert(`✅ ${updated} produtos atualizados\n${failed} erros\nVeja o console para detalhes.`);

})();
