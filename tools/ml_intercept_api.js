/**
 * ML API Interceptor — Captura a API interna que a página usa
 * =============================================================
 * Cole com WiFi LIGADO na página de afiliados.
 * Role a página para baixo para disparar os requests.
 * O script captura todos os produtos das respostas de API.
 */

(async function() {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const captured = { products: [], urls: new Set() };

  // Interceptar fetch
  const origFetch = window.fetch;
  window.fetch = async function(...args) {
    const res = await origFetch.apply(this, args);
    const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
    if (url.includes("affiliate") || url.includes("product") || url.includes("item")) {
      try {
        const clone = res.clone();
        const text = await clone.text();
        if (text.includes("S5L99N") || text.includes("meli.la") || text.includes("affiliate_url")) {
          console.log("🎯 API com dados:", url.substring(0,100));
          console.log("   Amostra:", text.substring(0,300));
          captured.urls.add(url);
          localStorage.setItem("ml_captured_url", url);
          localStorage.setItem("ml_captured_sample", text.substring(0,1000));
        }
      } catch(e) {}
    }
    return res;
  };

  // Interceptar XHR também
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {
    this._url = url;
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function() {
    this.addEventListener("load", function() {
      const url = this._url || "";
      if (url.includes("affiliate") || url.includes("product")) {
        console.log("🎯 XHR:", url.substring(0,100));
        console.log("   Resp:", this.responseText.substring(0,200));
      }
    });
    return origSend.apply(this, arguments);
  };

  console.log("✅ Interceptor ativo. Role a página para disparar os requests...");
  console.log("Aguardando 30 segundos enquanto você rola...");

  await sleep(30000);

  console.log("\n=== URLs capturadas ===");
  console.log([...captured.urls].join("\n") || "Nenhuma URL capturada ainda");
  console.log("\nURL no localStorage:", localStorage.getItem("ml_captured_url"));
  console.log("Amostra:", localStorage.getItem("ml_captured_sample")?.substring(0,500));
})();
