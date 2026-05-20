/**
 * PARTE 2 — Rode DEPOIS de desconectar o WiFi
 * ==============================================
 * Lê os dados do cache local e gera o JSON final.
 * Pode ser rodado offline — zero requests de rede.
 */

(function parte2() {

  const raw = localStorage.getItem("ml_affiliate_cache") || sessionStorage.getItem("ml_affiliate_cache");

  if (!raw) {
    console.error("❌ Cache não encontrado. Rode a PARTE 1 primeiro (com WiFi ligado).");
    return;
  }

  const cache = JSON.parse(raw);
  console.log(`📦 ${cache.length} produtos no cache`);

  // Montar JSON no formato esperado pelo BestPrice
  const output = cache.map(item => ({
    ml_code:       item.code,
    affiliate_url: item.meli_link,
    title:         item.title,
    price:         item.price,
    image_url:     item.image,
    product_url:   item.product_url,
  }));

  const json = JSON.stringify(output, null, 2);

  // Mostrar no console
  console.log("\n=== JSON PARA COLAR NO CHAT ===");
  console.log(json);

  // Textarea para copiar
  document.querySelectorAll("#ml-json-output").forEach(e => e.remove());
  const container = document.createElement("div");
  container.id = "ml-json-output";
  container.style.cssText = `
    position: fixed; top: 10px; right: 10px; width: 450px; z-index: 99999;
    background: #1a1a2e; border: 2px solid #7c6aff; border-radius: 12px;
    padding: 16px; font-family: system-ui; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  `;
  container.innerHTML = `
    <div style="color:#a78bfa;font-weight:700;margin-bottom:8px;font-size:14px">
      ✅ ${cache.length} produtos extraídos — Copie o JSON abaixo
    </div>
    <textarea id="ml-json-ta" style="width:100%;height:260px;background:#0d0d1a;color:#00e5a0;
      border:1px solid #7c6aff;border-radius:8px;padding:8px;font-size:11px;
      font-family:monospace;box-sizing:border-box;resize:vertical">${json}</textarea>
    <div style="display:flex;gap:8px;margin-top:10px">
      <button onclick="
        const ta=document.getElementById('ml-json-ta');
        ta.select(); document.execCommand('copy');
        this.textContent='✅ Copiado!';
        setTimeout(()=>this.textContent='📋 Copiar JSON',2000);
      " style="flex:1;padding:8px;background:#7c6aff;color:#fff;border:none;
        border-radius:8px;cursor:pointer;font-weight:700;font-size:13px">
        📋 Copiar JSON
      </button>
      <button onclick="document.getElementById('ml-json-output').remove()"
        style="padding:8px 12px;background:transparent;color:#6b6b8a;
        border:1px solid #6b6b8a;border-radius:8px;cursor:pointer;font-size:13px">
        ✕
      </button>
    </div>
  `;
  document.body.appendChild(container);

  // Selecionar automaticamente
  setTimeout(() => {
    const ta = document.getElementById("ml-json-ta");
    if (ta) { ta.focus(); ta.select(); }
  }, 100);

  console.log("\n📋 Caixa de texto apareceu na tela — clique em 'Copiar JSON' e cole no chat.");

  return output;

})();
