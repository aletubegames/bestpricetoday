/**
 * ML Affiliate Extractor — OFFLINE SAFE
 * ========================================
 * 1. Carregue a página de produtos afiliados do ML
 * 2. Role para baixo até carregar todos os produtos
 * 3. FIQUE OFFLINE (modo avião / desconecte o WiFi)
 * 4. Cole este script no F12 Console e pressione Enter
 * 5. Copie o JSON gerado e cole no chat
 *
 * Zero requests de rede — só lê o DOM local.
 */

(function () {

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // XPaths base fornecidos:
  // li container: /html/body/main/div/div[3]/div/div/div/div[5]/div/div/div[3]/li[N]
  // link produto:  li[N]/div[2]/a
  // imagem/título: li[N]/div[2]/div[1]
  // preço:         li[N]/div[2]/div[2]
  // botão share:   li[N]/div[2]/div[3]/div/div/button/span

  function xp(path, context) {
    const r = document.evaluate(path, context || document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    return r.singleNodeValue;
  }

  function xpAll(path, context) {
    const r = document.evaluate(path, context || document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    const nodes = [];
    for (let i = 0; i < r.snapshotLength; i++) nodes.push(r.snapshotItem(i));
    return nodes;
  }

  function parsePrice(text) {
    if (!text) return null;
    const clean = text.replace(/[^\d,]/g, '').replace(',', '.');
    const val = parseFloat(clean);
    return isNaN(val) || val <= 0 ? null : val;
  }

  async function run() {
    console.log("🔍 Procurando produtos na página...");

    // Encontrar todos os li de produtos
    const liBase = "/html/body/main/div/div[3]/div/div/div/div[5]/div/div/div[3]";
    const items = xpAll(`${liBase}/li`, document);
    console.log(`📦 ${items.length} produtos encontrados`);

    if (items.length === 0) {
      // Tentar seletor alternativo
      const alt = document.querySelectorAll("main li");
      console.log(`Alternativo: ${alt.length} li encontrados`);
      if (alt.length === 0) {
        console.warn("⚠️ Nenhum produto encontrado. A página foi carregada completamente?");
        return;
      }
    }

    const results = [];

    for (let i = 0; i < items.length; i++) {
      const li = items[i];
      const liXP = `${liBase}/li[${i + 1}]`;

      // ── Extrair título e imagem de div[1] ──
      const div1 = xp(`${liXP}/div[2]/div[1]`, document) || li.querySelector("div:nth-child(2) > div:nth-child(1)");
      const imgEl = div1?.querySelector("img");
      const title = div1?.querySelector("[class*='title'], h2, h3, span, p")?.textContent?.trim()
                 || imgEl?.alt?.trim()
                 || div1?.textContent?.trim().split('\n')[0].trim()
                 || null;
      const image = imgEl?.getAttribute("data-src") || imgEl?.src || null;

      // ── Extrair preço de div[2] ──
      const div2 = xp(`${liXP}/div[2]/div[2]`, document) || li.querySelector("div:nth-child(2) > div:nth-child(2)");
      const price = parsePrice(div2?.textContent || "");

      // ── Extrair link do produto de a ──
      const aEl = xp(`${liXP}/div[2]/a`, document) || li.querySelector("div:nth-child(2) > a");
      const productUrl = aEl?.href || null;

      // ── Clicar no botão share para revelar código S5L99N ──
      const btn = xp(`${liXP}/div[2]/div[3]/div/div/button`, document)
               || li.querySelector("div:nth-child(2) > div:nth-child(3) button")
               || li.querySelectorAll("button")[li.querySelectorAll("button").length - 1];

      let code = null;
      let meliLink = null;

      if (btn) {
        btn.click();
        await sleep(600);

        // Procurar código no DOM local (já carregado, sem request)
        const bodyText = document.body.innerText;
        const allCodes = [...new Set(bodyText.match(/S5L99N-[A-Z0-9]{4}/g) || [])];
        // Pegar o que ainda não foi capturado
        const newCode = allCodes.find(c => !results.find(r => r.code === c));
        if (newCode) code = newCode;

        // Pegar link meli.la do modal
        const inputs = document.querySelectorAll("input[value*='meli.la'], a[href*='meli.la']");
        for (const el of inputs) {
          const v = el.value || el.href;
          if (v && !results.find(r => r.meli_link === v)) {
            meliLink = v;
            break;
          }
        }

        // Textos com meli.la
        if (!meliLink) {
          const m = document.body.innerHTML.match(/https:\/\/meli\.la\/[A-Za-z0-9]+/g);
          if (m) {
            const newLink = m.find(l => !results.find(r => r.meli_link === l));
            if (newLink) meliLink = newLink;
          }
        }

        // Fechar modal (ESC — sem request)
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
        await sleep(300);
      }

      const item = { index: i + 1, code, meli_link: meliLink, title, price, image, product_url: productUrl };
      results.push(item);
      console.log(`  [${i+1}] ${code || '???'} | ${(title||'').substring(0,40)} | R$${price}`);
    }

    // Output JSON
    const json = JSON.stringify(results, null, 2);
    console.log("\n=== JSON RESULTADO ===");
    console.log(json);

    // Também colocar numa textarea para copiar fácil
    const ta = document.createElement("textarea");
    ta.style.cssText = "position:fixed;top:10px;right:10px;width:400px;height:300px;z-index:99999;font-size:11px;";
    ta.value = json;
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    console.log("\n✅ JSON também disponível na caixa de texto no canto superior direito da página.");
    console.log("Ctrl+A e Ctrl+C para copiar tudo.");

    return results;
  }

  run().catch(console.error);

})();
