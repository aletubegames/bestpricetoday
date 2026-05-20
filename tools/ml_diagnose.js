/**
 * ML Affiliate BULK Extractor v2
 * ================================
 * Cole no F12 Console na página: mercadolivre.com.br/afiliados/produtos
 * (a que lista seus produtos afiliados com os códigos S5L99N)
 */

(async function () {

  const API_BASE  = "https://alessandro2090-bestpricetoday-api.hf.space";
  const ADMIN_KEY = "754210!As@";

  // ── DIAGNÓSTICO: ver o que tem nos polycards ──────────────────────────────
  console.log("=== DIAGNÓSTICO DOS POLYCARDS ===");
  const cards = [...document.querySelectorAll("[class*='polycard']")];
  console.log("Cards encontrados:", cards.length);

  if (cards.length > 0) {
    const c = cards[0];
    console.log("HTML do primeiro card (500 chars):");
    console.log(c.outerHTML.substring(0, 500));
    console.log("\nTexto do primeiro card:");
    console.log(c.innerText.substring(0, 300));
  }

  // ── BUSCAR TODO O HTML DA PÁGINA por códigos S5L99N ──────────────────────
  const allCodes = [...new Set(document.body.innerHTML.match(/S5L99N-[A-Z0-9]{4}/g) || [])];
  console.log("\nCódigos S5L99N encontrados na página:", allCodes);

  // ── BUSCAR TODA A REDE (Network) — ver se há chamada de API com os dados ─
  // Interceptar fetch para capturar respostas da API ML
  const originalFetch = window.fetch;
  const captured = [];
  window.fetch = async function(...args) {
    const res = await originalFetch.apply(this, args);
    const url = typeof args[0] === "string" ? args[0] : args[0].url;
    if (url.includes("mercadolibre") || url.includes("affiliat")) {
      try {
        const clone = res.clone();
        const text = await clone.text();
        captured.push({ url, body: text.substring(0, 500) });
        console.log("🌐 Interceptado:", url.substring(0, 80));
        console.log("   Body:", text.substring(0, 200));
      } catch(e) {}
    }
    return res;
  };
  console.log("\n⚡ Interceptor ativado. Role a página ou navegue para capturar chamadas de API.");

  // ── TENTAR EXTRAIR DE DATA-ATTRIBUTES E ARIA ──────────────────────────────
  console.log("\n=== TENTANDO EXTRAIR PRODUTOS ===");

  // Buscar elementos com data-item, data-id ou aria contendo informações
  const allEls = [...document.querySelectorAll("[data-item-id],[data-product-id],[aria-label*='R$']")];
  console.log("Elementos com data-item-id/product-id:", allEls.length);
  allEls.slice(0,3).forEach(el => {
    console.log("  data:", JSON.stringify(el.dataset).substring(0,100));
    console.log("  aria:", el.getAttribute("aria-label")?.substring(0,100));
  });

  // ── VER ESTADO DO REACT/NEXT ──────────────────────────────────────────────
  // O ML usa React — tentar acessar o state
  const reactKey = Object.keys(document.body).find(k => k.startsWith("__reactFiber") || k.startsWith("__reactInternalInstance"));
  if (reactKey) {
    console.log("\n✅ React detectado. Tentando extrair state...");
  }

  // ── VER __NEXT_DATA__ ou __PRELOADED_STATE__ ─────────────────────────────
  const nextData = document.querySelector("#__NEXT_DATA__");
  if (nextData) {
    try {
      const data = JSON.parse(nextData.textContent);
      console.log("\n✅ __NEXT_DATA__ encontrado. Keys:", Object.keys(data).join(", "));
      // Procurar produtos recursivamente
      const str = JSON.stringify(data);
      const codes = [...new Set(str.match(/S5L99N-[A-Z0-9]{4}/g) || [])];
      console.log("Códigos no __NEXT_DATA__:", codes);
    } catch(e) {}
  }

  // Procurar em scripts
  const scripts = [...document.querySelectorAll("script:not([src])")];
  for (const s of scripts) {
    if (s.textContent.includes("S5L99N") || s.textContent.includes("affiliate") || s.textContent.includes("products")) {
      console.log("\n✅ Script com dados relevantes (500 chars):");
      console.log(s.textContent.substring(0, 500));
      break;
    }
  }

  // ── TENTAR CHAMADA DIRETA À API ML ───────────────────────────────────────
  // Pegar o token ML do cookie/localStorage do site deles
  console.log("\n=== TOKENS DISPONÍVEIS ===");
  console.log("localStorage keys:", Object.keys(localStorage).filter(k => k.includes("token") || k.includes("auth") || k.includes("user")).join(", "));
  const mlToken = localStorage.getItem("access_token") || localStorage.getItem("token") || localStorage.getItem("ml_token");
  if (mlToken) {
    console.log("Token ML encontrado:", mlToken.substring(0, 30) + "...");

    // Tentar buscar produtos da API de afiliados do ML com o token deles
    try {
      const r = await fetch("https://api.mercadolibre.com/affiliates/products?limit=20", {
        headers: { Authorization: `Bearer ${mlToken}` }
      });
      console.log("API afiliados ML status:", r.status);
      if (r.ok) {
        const d = await r.json();
        console.log("Produtos:", JSON.stringify(d).substring(0, 500));
      }
    } catch(e) {
      console.log("Erro API ML:", e.message);
    }
  }

  // Ver cookies relevantes
  const cookies = document.cookie.split(";").filter(c => c.includes("token") || c.includes("auth"));
  console.log("Cookies relevantes:", cookies.map(c => c.substring(0,60)));

  console.log("\n=== FIM DO DIAGNÓSTICO ===");
  console.log("Cole o output acima e envie para análise.");

})();
