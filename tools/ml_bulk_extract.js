/**
 * ML Affiliate BULK Extractor
 * ============================
 * Cole no F12 Console estando em qualquer página do painel de afiliados ML
 * que mostre seus produtos (ex: mercadolivre.com.br/afiliados/products
 * ou na página de uma campanha específica).
 *
 * O script:
 *  1. Varre TODOS os produtos visíveis na página atual
 *  2. Extrai título, preço, imagem e o código S5L99N de cada um
 *  3. Faz PATCH em lote na API BestPriceToday
 *  4. Exibe relatório no console
 *
 * Dica: se houver paginação, rode o script em cada página.
 */

(async function () {

  // ── CONFIG ────────────────────────────────────────────────────────────────
  const API_BASE = "https://alessandro2090-bestpricetoday-api.hf.space";
  const TOKEN    = localStorage.getItem("bpt_token")
    || prompt("Cole seu bpt_token (bestpricetoday.vercel.app → F12 → Application → LocalStorage → bpt_token):");

  if (!TOKEN) { console.warn("Token não informado."); return; }

  // ── 1. BUSCAR PRODUTOS SEM TÍTULO NA BASE ─────────────────────────────────
  console.log("🔄 Buscando produtos sem título na base...");
  let baseProducts = [];
  try {
    const r = await fetch(`${API_BASE}/api/v1/affiliate/products`, {
      headers: { Authorization: `Bearer ${TOKEN}` }
    });
    const d = await r.json();
    baseProducts = (d.products || []);
    console.log(`📦 Total na base: ${baseProducts.length} | Sem título: ${baseProducts.filter(p=>!p.title).length}`);
  } catch(e) {
    alert("❌ Erro ao conectar com a API. Verifique o token.");
    return;
  }

  // Mapa ml_code → produto
  const byCode = {};
  baseProducts.forEach(p => { if (p.ml_code) byCode[p.ml_code] = p; });

  // ── 2. EXTRAIR PRODUTOS DA PÁGINA ATUAL ───────────────────────────────────
  console.log("\n🔍 Varrendo produtos na página...");

  /**
   * Tenta extrair o código S5L99N de um elemento ou seu contexto.
   * O código aparece em textos como "S5L99N-YHT3" ou em data-attributes.
   */
  function extractCode(el) {
    // Busca no texto do elemento e nos ancestrais (até 5 níveis)
    let cur = el;
    for (let i = 0; i < 5; i++) {
      if (!cur) break;
      const text = cur.textContent || "";
      const m = text.match(/S5L99N-[A-Z0-9]{4}/);
      if (m) return m[0];
      // Também checar data-attributes
      if (cur.dataset) {
        for (const v of Object.values(cur.dataset)) {
          const dm = String(v).match(/S5L99N-[A-Z0-9]{4}/);
          if (dm) return dm[0];
        }
      }
      cur = cur.parentElement;
    }
    return null;
  }

  /**
   * Extrai preço de um elemento de texto como "R$ 3.699" ou "3699,90"
   */
  function parsePrice(text) {
    if (!text) return null;
    const clean = text.replace(/[^\d,.]/g, "").replace(/\./g, "").replace(",", ".");
    const val = parseFloat(clean);
    return isNaN(val) || val <= 0 ? null : val;
  }

  // Estratégia 1: procurar por cards de produto (classe genérica ML)
  // O painel de afiliados usa polycards ou ui-search-result
  const cardSelectors = [
    "[class*='polycard']",
    "[class*='ui-search-result']",
    "[class*='product-card']",
    "[class*='item-card']",
    "[class*='affiliate']",
    "li[class*='results']",
    "[data-item-id]",
  ];

  let cards = [];
  for (const sel of cardSelectors) {
    cards = [...document.querySelectorAll(sel)];
    if (cards.length > 0) {
      console.log(`✅ Encontrei ${cards.length} cards com seletor: ${sel}`);
      break;
    }
  }

  // Estratégia 2: procurar qualquer texto com padrão S5L99N-XXXX na página
  const extracted = [];

  if (cards.length > 0) {
    for (const card of cards) {
      const code = extractCode(card);

      // Título
      const titleEl = card.querySelector("[class*='title'], h2, h3, [class*='name']");
      const title = titleEl?.textContent?.trim() || null;

      // Preço
      const priceEl = card.querySelector("[class*='price'], [class*='amount']");
      const price = priceEl ? parsePrice(priceEl.textContent) : null;

      // Imagem
      const imgEl = card.querySelector("img");
      let image = imgEl?.getAttribute("data-src") || imgEl?.src || null;
      if (image) image = image.replace(/\?(.*?)$/, "").replace(/-[A-Z]\.jpg/, "-O.jpg");

      extracted.push({ code, title, price, image });
    }
  }

  // Estratégia 3: buscar todos os padrões S5L99N-XXXX no HTML da página
  const fullText = document.body.innerHTML;
  const allCodes = [...new Set(fullText.match(/S5L99N-[A-Z0-9]{4}/g) || [])];

  if (allCodes.length > 0 && extracted.filter(e => e.code).length === 0) {
    console.log(`🔍 Encontrei ${allCodes.length} códigos no HTML: ${allCodes.join(", ")}`);
    // Para cada código, tentar extrair dados do elemento mais próximo
    for (const code of allCodes) {
      // Busca no texto visível
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        if (node.textContent.includes(code)) {
          const parent = node.parentElement?.closest("[class*='card'],[class*='item'],[class*='product'],li,article,div[data-id]") || node.parentElement;
          const titleEl = parent?.querySelector("[class*='title'],h1,h2,h3") || parent;
          const title = titleEl?.textContent?.trim().split("\n")[0].trim() || null;
          const priceEl = parent?.querySelector("[class*='price'],[class*='amount']");
          const price = priceEl ? parsePrice(priceEl.textContent) : null;
          const imgEl = parent?.querySelector("img");
          let image = imgEl?.getAttribute("data-src") || imgEl?.src || null;
          if (image) image = image.replace(/\?(.*?)$/, "").replace(/-[A-Z]\.jpg/, "-O.jpg");
          extracted.push({ code, title, price, image });
          break;
        }
      }
    }
  }

  // Deduplica por código
  const seen = new Set();
  const unique = extracted.filter(e => {
    if (!e.code || seen.has(e.code)) return false;
    seen.add(e.code);
    return true;
  });

  console.log(`\n📋 Dados extraídos (${unique.length} únicos):`);
  unique.forEach(e => console.log(`  ${e.code || "SEM_CÓDIGO"} | ${(e.title||"").substring(0,50)} | R$${e.price} | img:${e.image?"✅":"❌"}`));

  if (unique.length === 0) {
    console.warn("⚠️ Nenhum produto extraído. Tente rolar a página para carregar mais itens e rode novamente.");
    return;
  }

  // ── 3. CRUZAR COM A BASE E ENVIAR ─────────────────────────────────────────
  const toUpdate = unique.filter(e => e.code && byCode[e.code]);
  const notFound = unique.filter(e => e.code && !byCode[e.code]);
  const noCode   = unique.filter(e => !e.code);

  console.log(`\n✅ Para atualizar: ${toUpdate.length}`);
  console.log(`❌ Código não encontrado na base: ${notFound.length} — ${notFound.map(e=>e.code).join(", ")}`);
  console.log(`⚠️ Sem código identificado: ${noCode.length}`);

  if (toUpdate.length === 0) {
    console.warn("Nada para atualizar. Os códigos S5L99N da página não batem com os da base.");
    return;
  }

  let updated = 0, failed = 0;

  for (const item of toUpdate) {
    const prod = byCode[item.code];
    const payload = {};
    if (item.title && item.title.length > 3) payload.title     = item.title;
    if (item.price)                          payload.price     = item.price;
    if (item.image)                          payload.image_url = item.image;

    if (Object.keys(payload).length === 0) {
      console.log(`⏭️ ${item.code} — nada para atualizar`);
      continue;
    }

    try {
      const r = await fetch(`${API_BASE}/api/v1/affiliate/products/${prod.id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await r.json();
      if (r.ok) {
        console.log(`✅ ${item.code} → ${result.title} | R$${result.price}`);
        updated++;
      } else {
        console.error(`❌ ${item.code} → erro:`, result);
        failed++;
      }
    } catch(e) {
      console.error(`❌ ${item.code} → exceção:`, e.message);
      failed++;
    }

    // Pequeno delay para não sobrecarregar a API
    await new Promise(r => setTimeout(r, 200));
  }

  console.log(`\n🎉 CONCLUÍDO: ${updated} atualizados | ${failed} erros`);
  alert(`✅ Concluído!\n${updated} produtos atualizados\n${failed} erros\n\nVeja o console para detalhes.`);

})();
