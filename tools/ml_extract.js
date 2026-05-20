/**
 * ML Affiliate Product Extractor
 * ================================
 * Cole no Console do F12 estando na página do produto no Mercado Livre.
 * Extrai título, preço, imagem e envia para o BestPriceToday.
 *
 * USO:
 *   1. Abra o link meli.la do produto (ex: https://meli.la/2PDYyF6)
 *   2. Navegue até o produto específico no ML
 *   3. Abra F12 → Console
 *   4. Cole este script inteiro e pressione Enter
 *   5. Informe o ml_code quando pedido (ex: S5L99N-YHT3)
 */

(async function() {
  const API    = "https://alessandro2090-bestpricetoday-api.hf.space";
  const TOKEN  = localStorage.getItem("bpt_token") || prompt("Cole seu bpt_token (pegue em bestpricetoday.vercel.app → F12 → Application → localStorage):");

  // ── 1. Extrair dados da página ──────────────────────────────────────────

  // Título
  const titleEl = document.querySelector("h1.ui-pdp-title") ||
                  document.querySelector("[class*='title']");
  const title = titleEl?.textContent?.trim() || document.title.replace(" | Mercado Livre", "").trim();

  // Preço principal
  let price = null;
  const fractionEl = document.querySelector(".andes-money-amount__fraction");
  const centsEl    = document.querySelector(".andes-money-amount__cents");
  if (fractionEl) {
    const fraction = fractionEl.textContent.replace(/\./g, "").trim();
    const cents    = centsEl?.textContent?.trim() || "00";
    price = parseFloat(`${fraction}.${cents}`);
  }

  // Imagem principal
  let image = null;
  const imgEl = document.querySelector(".ui-pdp-image.ui-pdp-gallery__figure__image") ||
                document.querySelector("figure.ui-pdp-gallery__figure img") ||
                document.querySelector("[class*='gallery'] img");
  if (imgEl) {
    image = imgEl.getAttribute("data-zoom") || imgEl.src || imgEl.getAttribute("src");
    // Pegar versão maior se disponível
    if (image) image = image.replace(/\?(.*?)$/, "").replace(/-[A-Z]\.jpg/, "-O.jpg");
  }

  // Tentar pegar do __PRELOADED_STATE__ se disponível
  try {
    const scripts = [...document.querySelectorAll("script")];
    for (const s of scripts) {
      if (s.textContent.includes("__PRELOADED_STATE__")) {
        const match = s.textContent.match(/__PRELOADED_STATE__\s*=\s*(\{.*?\});?\s*(?:window\.|<\/script>)/s);
        if (match) {
          const state = JSON.parse(match[1]);
          const comp  = state?.initialState?.components?.head?.title;
          if (comp && !title) title = comp;
          const pComp = state?.initialState?.components?.price?.value;
          if (pComp && !price) price = parseFloat(pComp);
          break;
        }
      }
    }
  } catch(e) {}

  console.log("=== DADOS EXTRAÍDOS ===");
  console.log("Título:", title);
  console.log("Preço: R$", price);
  console.log("Imagem:", image?.substring(0, 80));
  console.log("URL:", location.href);

  if (!title) {
    alert("❌ Não consegui extrair o título. Tente em outra página do produto.");
    return;
  }

  // ── 2. Identificar qual produto atualizar ───────────────────────────────

  // Buscar lista de produtos sem título
  let products = [];
  try {
    const r = await fetch(`${API}/api/v1/affiliate/products`, {
      headers: { "Authorization": `Bearer ${TOKEN}` }
    });
    const d = await r.json();
    products = (d.products || []).filter(p => !p.title);
  } catch(e) {
    console.error("Erro ao buscar produtos:", e);
    alert("❌ Erro ao conectar com a API. Verifique o token.");
    return;
  }

  console.log(`\nProdutos sem título: ${products.length}`);
  products.forEach(p => console.log(`  ${p.ml_code} → ${p.id}`));

  // Pedir o ml_code para identificar qual produto atualizar
  const mlCode = prompt(
    `Qual o código ML deste produto?\n\n` +
    `Produtos sem título:\n${products.map(p => p.ml_code).join("\n")}\n\n` +
    `(ex: S5L99N-YHT3)`
  );

  if (!mlCode) { console.log("Cancelado."); return; }

  const product = products.find(p => p.ml_code === mlCode.trim().toUpperCase());
  if (!product) {
    // Tentar buscar em todos os produtos (pode já ter título mas querer atualizar)
    const r2 = await fetch(`${API}/api/v1/affiliate/products`, {
      headers: { "Authorization": `Bearer ${TOKEN}` }
    });
    const d2 = await r2.json();
    const all = d2.products || [];
    const found = all.find(p => p.ml_code === mlCode.trim().toUpperCase());
    if (!found) {
      alert(`❌ Código ${mlCode} não encontrado na base.`);
      return;
    }
    Object.assign(product || {}, found);
    // product agora é found
    const productToUpdate = found;

    // ── 3. Enviar para a API ──────────────────────────────────────────────
    await sendUpdate(productToUpdate, title, price, image, TOKEN, API);
    return;
  }

  await sendUpdate(product, title, price, image, TOKEN, API);

  async function sendUpdate(prod, t, p, img, tok, api) {
    const payload = {};
    if (t)   payload.title     = t;
    if (p)   payload.price     = p;
    if (img) payload.image_url = img;

    console.log("\n=== ENVIANDO ===");
    console.log("product_id:", prod.id);
    console.log("payload:", payload);

    const res = await fetch(`${api}/api/v1/affiliate/products/${prod.id}`, {
      method: "PATCH",
      headers: {
        "Authorization": `Bearer ${tok}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (res.ok) {
      console.log("✅ Atualizado com sucesso:", result.title, "R$", result.price);
      alert(`✅ Produto atualizado!\n\nTítulo: ${result.title}\nPreço: R$ ${result.price}\nImagem: ${result.image_url ? "✅" : "❌"}`);
    } else {
      console.error("❌ Erro:", result);
      alert(`❌ Erro: ${JSON.stringify(result)}`);
    }
  }

})();
