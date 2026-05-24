async function extrairAfiliados() {
  const vistos = new Set();
  const produtos = [];
  let semNovos = 0;
  console.log('🚀 Iniciando coleta...');

  while (semNovos < 8) {
    const cards = document.querySelectorAll('.poly-card__content');
    let novosNestaCiclo = 0;

    for (const card of cards) {
      const nome = card.querySelector('a.poly-component__title')?.innerText?.trim() || '';
      if (!nome || vistos.has(nome)) continue;
      vistos.add(nome);
      novosNestaCiclo++;

      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise(r => setTimeout(r, 300));

      const badge     = card.querySelector('.poly-component__highlight')?.innerText?.trim() || '';
      const avaliacao = card.querySelector('.poly-phrase-label.poly-fs-xs.poly-fw-regular')?.innerText?.trim() || '';
      const vendidos  = (card.querySelector('.poly-phrase-label.poly-fs-xs:not(.poly-fw-regular)')?.innerText?.trim() || '').replace(/^\|\s*\+?/, '').trim();
      const ganhos    = card.querySelector('.poly-component__label.poly-fw-semibold')?.innerText?.trim() || '';
      const preco     = card.querySelector('.poly-price__current')?.innerText?.replace(/\s+/g, ' ').trim() || '';
      const parcelas  = card.querySelector('.poly-price__installments')?.innerText?.replace(/\s+/g, ' ').trim() || '';
      const desconto  = card.querySelector('[class*="discount__amount"], .poly-price__original')?.innerText?.replace(/\s+/g, ' ').trim() || '';

      let link_prod = '';
      let Codigo_ML = '';

      const writeTextOriginal = navigator.clipboard.writeText.bind(navigator.clipboard);

      // Abre o modal
      card.querySelector('.andes-button--quiet')?.click();
      await new Promise(r => setTimeout(r, 900));

      // --- Captura link curto (button[1]) ---
      navigator.clipboard.writeText = async (text) => { link_prod = text; return Promise.resolve(); };

      const btnLink = document.evaluate(
        '/html/body/div[6]/div/div/div/div[2]/div/button[1]/div/div',
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      ).singleNodeValue;
      btnLink?.click();
      await new Promise(r => setTimeout(r, 700));

      // --- Captura código ML (button[3]) ---
      navigator.clipboard.writeText = async (text) => { Codigo_ML = text; return Promise.resolve(); };

      const btnCodigo = document.evaluate(
        '/html/body/div[6]/div/div/div/div[2]/div/button[3]',
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      ).singleNodeValue;
      btnCodigo?.click();
      await new Promise(r => setTimeout(r, 700));

      // Restaura clipboard original
      navigator.clipboard.writeText = writeTextOriginal;

      // Limpa o código ML (pega só a parte após ":")
      Codigo_ML = Codigo_ML.match(/:\s*([A-Z0-9]+-[A-Z0-9]+)/)?.[1] || Codigo_ML;

      // Fecha modal
      document.querySelector('.andes-modal__close, [aria-label="Fechar"]')?.click();
      await new Promise(r => setTimeout(r, 300));

      produtos.push({ nome, badge, preco, parcelas, desconto, ganhos, avaliacao, vendidos, link_prod, Codigo_ML });
      console.log(`[${produtos.length}] ${nome.slice(0, 60)} → link: "${link_prod}" | código: "${Codigo_ML}"`);
    }

    semNovos = novosNestaCiclo === 0 ? semNovos + 1 : 0;
    window.scrollBy(0, 800);
    await new Promise(r => setTimeout(r, 1500));
  }

  const json = JSON.stringify(produtos, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url;
  a.download = `afiliados_ml_${new Date().toISOString().slice(0, 10)}.json`;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 2000);

  console.log(`\n✅ CONCLUÍDO: ${produtos.length} produtos → arquivo baixado`);
  return produtos;
}

extrairAfiliados();