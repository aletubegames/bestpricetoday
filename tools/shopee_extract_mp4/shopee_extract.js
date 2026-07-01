
(async () => {
  const STORAGE_KEY = 'tiktok_post_progress';
  const lista = [
  {
    "slug": "qgXiZI6In",
    "video": "qgXiZI6In.mp4",
    "offer_link": "https://s.shopee.com.br/qgXiZI6In",
    "caption": "Kit 6/12/18/24 Panos De Limpeza Aço Premium Arear Panela Fogão Toalha Louça Tira\nDe R$24.99 por R$10.00 (60% OFF)\n⭐ 4.7 | +157796 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "10zxusHSxq",
    "video": "10zxusHSxq.mp4",
    "offer_link": "https://s.shopee.com.br/10zxusHSxq",
    "caption": "Mesa de Cabeceira Retrô Compacta com Nicho para Quarto Sala Casal ou Solteiro Pa\nDe R$49.90 por R$29.90 (40% OFF)\n⭐ 4.8 | +500563 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "1BJO7BGpct",
    "video": "1BJO7BGpct.mp4",
    "offer_link": "https://s.shopee.com.br/1BJO7BGpct",
    "caption": "KIT BODY SPLASH MASCULINO BARBARIUS E MIDTOWN 200ML - PRIMACIAL PERFUME FRESCO A\nDe R$139.90 por R$56.61 (60% OFF)\n⭐ 4.8 | +48906 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "1LcoJUGCHw",
    "video": "1LcoJUGCHw.mp4",
    "offer_link": "https://s.shopee.com.br/1LcoJUGCHw",
    "caption": "Kit Jogo de Lençol Roupa de Cama Box Berço Solteiro Casal Queen King 400 fios To\nDe R$26.00 por R$14.40 (45% OFF)\n⭐ 4.8 | +838445 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "1VwEVnFYwz",
    "video": "1VwEVnFYwz.mp4",
    "offer_link": "https://s.shopee.com.br/1VwEVnFYwz",
    "caption": "Percarbonato 100% Puro Tira Manchas Roupas Brancas e Coloridas\nDe R$29.90 por R$19.90 (33% OFF)\n⭐ 4.9 | +269029 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "1qZ4uPEIH5",
    "video": "1qZ4uPEIH5.mp4",
    "offer_link": "https://s.shopee.com.br/1qZ4uPEIH5",
    "caption": "Areia Catbio Biodegradável 4 Kg - Max Clean - Grãos Finos\nDe R$48.90 por R$46.90 (4% OFF)\n⭐ 4.9 | +296218 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "20sV6iDew8",
    "video": "20sV6iDew8.mp4",
    "offer_link": "https://s.shopee.com.br/20sV6iDew8",
    "caption": "Jogo de Lençol 400 fios toque Suave e Acetinado Berço Solteiro Casal Queen King \nDe R$160.00 por R$14.60 (91% OFF)\n⭐ 4.9 | +197676 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "2BBvJ1D1bB",
    "video": "2BBvJ1D1bB.mp4",
    "offer_link": "https://s.shopee.com.br/2BBvJ1D1bB",
    "caption": "Tira manchas alvejante 1kg + Percarbonato de sódio 1kg\nDe R$38.00 por R$17.86 (53% OFF)\n⭐ 4.8 | +341288 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "2LVLVKCOGE",
    "video": "2LVLVKCOGE.mp4",
    "offer_link": "https://s.shopee.com.br/2LVLVKCOGE",
    "caption": "40 Peças / 46 Peças Jogo De Chave Catraca Caixa De Ferramentas Completa Reversív\nDe R$51.98 por R$25.97 (50% OFF)\n⭐ 4.8 | +344066 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "3B4SUr9DZT",
    "video": "3B4SUr9DZT.mp4",
    "offer_link": "https://s.shopee.com.br/3B4SUr9DZT",
    "caption": "Fita Dupla Face Extra Forte Transparente NanoGel Silicone Mágica Adesiva Cola na\nDe R$25.00 por R$10.00 (60% OFF)\n⭐ 4.8 | +176184 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "3VhItT7wtZ",
    "video": "3VhItT7wtZ.mp4",
    "offer_link": "https://s.shopee.com.br/3VhItT7wtZ",
    "caption": "Kit 1 ou 2 Unidades de Veda Porta Ajustável Protetor Rolinho Impermeável 80cm 90\nDe R$19.00 por R$12.99 (32% OFF)\n⭐ 4.8 | +175531 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "3qK9I56gDf",
    "video": "3qK9I56gDf.mp4",
    "offer_link": "https://s.shopee.com.br/3qK9I56gDf",
    "caption": "Kit 3 Peneira Coador De Peneiras Aço Inoxidável Para Cozinha Peneira De Cozinha\nDe R$25.98 por R$15.99 (38% OFF)\n⭐ 4.7 | +124023 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "40dZUO62si",
    "video": "40dZUO62si.mp4",
    "offer_link": "https://s.shopee.com.br/40dZUO62si",
    "caption": "Sapateira 4 ou 5 Andares Multiuso Desmontável Organizadora Multiuso Sapatos Livr\nDe R$50.00 por R$17.98 (64% OFF)\n⭐ 4.6 | +166204 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "4LGPt04mCo",
    "video": "4LGPt04mCo.mp4",
    "offer_link": "https://s.shopee.com.br/4LGPt04mCo",
    "caption": "Lencol Queen 400 Fios Micropercal Cama Casal Solteiro Tecido Super Macio\nDe R$45.00 por R$25.89 (42% OFF)\n⭐ 4.9 | +129185 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "4VZq5J48rr",
    "video": "4VZq5J48rr.mp4",
    "offer_link": "https://s.shopee.com.br/4VZq5J48rr",
    "caption": "Creatina Suplemento Monohidratada em Pó 100% Pura Importada - Soldiers Nutrition\nDe R$69.90 por R$29.90 (57% OFF)\n⭐ 4.9 | +121857 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "4ftGHc3VWu",
    "video": "4ftGHc3VWu.mp4",
    "offer_link": "https://s.shopee.com.br/4ftGHc3VWu",
    "caption": "Trava Óculos Antiderrapante Silicone Kit Não Cai Do Rosto Gancho Orelha Haste Co\nDe R$7.50 por R$5.50 (27% OFF)\n⭐ 4.8 | +44014 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "4qCgTv2sBx",
    "video": "4qCgTv2sBx.mp4",
    "offer_link": "https://s.shopee.com.br/4qCgTv2sBx",
    "caption": "Kit Limpador Pastilha de máquina de lavar roupa, comprimido efervescente sólido \nDe R$15.00 por R$8.59 (43% OFF)\n⭐ 4.7 | +123629 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "50W6gE2Er0",
    "video": "50W6gE2Er0.mp4",
    "offer_link": "https://s.shopee.com.br/50W6gE2Er0",
    "caption": "Tapete de Banheiro Absorvente Antiderrapante Secagem Rápida\nDe R$50.00 por R$11.99 (76% OFF)\n⭐ 4.8 | +60781 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "5VSNH90Kq9",
    "video": "5VSNH90Kq9.mp4",
    "offer_link": "https://s.shopee.com.br/5VSNH90Kq9",
    "caption": "Kit 10 Panos De Limpeza Microfibra alta absorção Multiuso\nDe R$99.99 por R$17.48 (83% OFF)\n⭐ 4.8 | +169336 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "5flnTRzhVC",
    "video": "5flnTRzhVC.mp4",
    "offer_link": "https://s.shopee.com.br/5flnTRzhVC",
    "caption": "Mulheres com Deus - 365 Dias de Fé - Devocional\nDe R$39.90 por R$20.51 (49% OFF)\n⭐ 5.0 | +108496 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "5q5Dfkz4AF",
    "video": "5q5Dfkz4AF.mp4",
    "offer_link": "https://s.shopee.com.br/5q5Dfkz4AF",
    "caption": "Kit 5/10/20/50/100 Un Saco Saquinho Organza Tule Saquinho 7x9 9x12 10x15 Branco \nDe R$45.90 por R$5.90 (87% OFF)\n⭐ 4.9 | +212936 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "60Ods3yQpI",
    "video": "60Ods3yQpI.mp4",
    "offer_link": "https://s.shopee.com.br/60Ods3yQpI",
    "caption": "Balança Bioimpedância Digital Profissional Suporta Até 140kg via Bluethooth\nDe R$99.00 por R$29.96 (70% OFF)\n⭐ 4.9 | +57574 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "6Ai44MxnUL",
    "video": "6Ai44MxnUL.mp4",
    "offer_link": "https://s.shopee.com.br/6Ai44MxnUL",
    "caption": "Espuma Spray Zip Clean 300ml Limpa a Seco Sofá, Estofado, Banco de Carro Limpeza\nDe R$29.99 por R$15.99 (47% OFF)\n⭐ 4.8 | +29298 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "6VKuSywWoR",
    "video": "6VKuSywWoR.mp4",
    "offer_link": "https://s.shopee.com.br/6VKuSywWoR",
    "caption": "ROMANTIC CROWN Copo Térmico Inox Portátil 1200ml/600ml/1.2L Garrafa Térmica Inox\nDe R$60.00 por R$39.98 (33% OFF)\n⭐ 5.0 | +93287 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "6feKfHvtTU",
    "video": "6feKfHvtTU.mp4",
    "offer_link": "https://s.shopee.com.br/6feKfHvtTU",
    "caption": "Organizador de Sacolas Dispenser Organizadora De Plástico Para Armazenamento De \nDe R$29.99 por R$10.00 (67% OFF)\n⭐ 4.7 | +47561 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "70HB3tucna",
    "video": "70HB3tucna.mp4",
    "offer_link": "https://s.shopee.com.br/70HB3tucna",
    "caption": "Kit Jogo De Lençol Cama Box Solteiro Casal Queen King 02 e 03 Peças\nDe R$60.00 por R$25.80 (57% OFF)\n⭐ 4.9 | +58595 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "7VDReosimj",
    "video": "7VDReosimj.mp4",
    "offer_link": "https://s.shopee.com.br/7VDReosimj",
    "caption": "Kit2/1 Cartão Memória Micro SD Ultra 32GB-256GB Com Adaptador p/Vendas diretas d\nDe R$29.99 por R$12.99 (57% OFF)\n⭐ 4.5 | +33144 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "7pqI3QrS6p",
    "video": "7pqI3QrS6p.mp4",
    "offer_link": "https://s.shopee.com.br/7pqI3QrS6p",
    "caption": "Depilador Indolor Caneta Sobrancelha Removedor Instantâneo A Pilha\nDe R$48.00 por R$12.39 (74% OFF)\n⭐ 4.8 | +47657 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "809iFjqols",
    "video": "809iFjqols.mp4",
    "offer_link": "https://s.shopee.com.br/809iFjqols",
    "caption": "Protetor Impermeável para Colchão SUPER SILENCIOSO 100% Impermeável Tecido Jacqu\nDe R$119.97 por R$47.97 (60% OFF)\n⭐ 4.9 | +102882 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "8AT8S2qBQv",
    "video": "8AT8S2qBQv.mp4",
    "offer_link": "https://s.shopee.com.br/8AT8S2qBQv",
    "caption": "Bermuda Modeladora Anágua Cinta Short Feminino Modelador Alta Compressão Reduz M\nDe R$38.99 por R$20.90 (46% OFF)\n⭐ 4.7 | +148043 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "8fPP2xoHQ4",
    "video": "8fPP2xoHQ4.mp4",
    "offer_link": "https://s.shopee.com.br/8fPP2xoHQ4",
    "caption": "Lencol Micropercal 400 Fios Jogo De Cama Casal, Queen, King 03 Peças Barato Solt\nDe R$25.90 por R$19.36 (25% OFF)\n⭐ 4.9 | +61225 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "902FRZn0kA",
    "video": "902FRZn0kA.mp4",
    "offer_link": "https://s.shopee.com.br/902FRZn0kA",
    "caption": "Extensão elétrica 2 Metros Extensão de Energia 3 Tomadas com 3 metros 5 metros 1\nDe R$18.90 por R$12.89 (32% OFF)\n⭐ 4.9 | +154406 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "9ALfdsmNPD",
    "video": "9ALfdsmNPD.mp4",
    "offer_link": "https://s.shopee.com.br/9ALfdsmNPD",
    "caption": "Creme Gel Regenerador Facial Gota de Colágeno Kokeshi 45g\nDe R$46.90 por R$31.90 (32% OFF)\n⭐ 4.9 | +38491 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "9UyW2Ul6jJ",
    "video": "9UyW2Ul6jJ.mp4",
    "offer_link": "https://s.shopee.com.br/9UyW2Ul6jJ",
    "caption": "Chave T  Longa Para máquina de lavar 10mm Agitador Brastemp/Consul/Electrolux Un\nDe R$24.99 por R$12.75 (49% OFF)\n⭐ 4.9 | +60980 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "9pbMR6jq3P",
    "video": "9pbMR6jq3P.mp4",
    "offer_link": "https://s.shopee.com.br/9pbMR6jq3P",
    "caption": "Aparelho Medidor De Pressão Arterial Digital De Braço\nDe R$59.67 por R$32.99 (45% OFF)\n⭐ 4.9 | +23846 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "9zumdPjCiS",
    "video": "9zumdPjCiS.mp4",
    "offer_link": "https://s.shopee.com.br/9zumdPjCiS",
    "caption": "ROMANTIC CROWN Copo Térmico Portátil 1200ml/600ml com Tampa e Canudo Garrafa Tér\nDe R$70.00 por R$39.98 (43% OFF)\n⭐ 5.0 | +55637 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "AKXd21hw2Y",
    "video": "AKXd21hw2Y.mp4",
    "offer_link": "https://s.shopee.com.br/AKXd21hw2Y",
    "caption": "Chave T Longa 10mm + Pastilha para Abrir Agitador de Máquina de Lavar – Uso Univ\nR$13.99\n⭐ 4.7 | +60650 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "AUr3EKhIhb",
    "video": "AUr3EKhIhb.mp4",
    "offer_link": "https://s.shopee.com.br/AUr3EKhIhb",
    "caption": "Adesivos Protetores de Ralo Tela Descartavel Anti Entupimento e Anti Insetos Par\nDe R$15.00 por R$6.99 (53% OFF)\n⭐ 4.6 | +72573 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "17Qj2LH0b",
    "video": "17Qj2LH0b.mp4",
    "offer_link": "https://s.shopee.com.br/17Qj2LH0b",
    "caption": "kit Coala Home Chá Branco\nDe R$80.65 por R$72.90 (10% OFF)\n⭐ 5.0 | +204298 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  },
  {
    "slug": "W3hJxJMzi",
    "video": "W3hJxJMzi.mp4",
    "offer_link": "https://s.shopee.com.br/W3hJxJMzi",
    "caption": "Kit ate 24 Pares Meias masculina SPORT Algodão cano alto/longo\nDe R$17.99 por R$16.95 (6% OFF)\n⭐ 4.8 | +52555 vendidos\nLink nos comentários 👇\n#shopee #oferta #promocao #desconto #compras"
  }
];

  let progress = {};
  try { progress = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch(e) {}
  const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));

  // overlay
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;bottom:0;right:0;width:500px;max-height:400px;overflow-y:auto;background:#111;color:#0f0;font:12px monospace;z-index:2147483647;padding:10px 14px;border-top:3px solid #ff0050;border-left:3px solid #ff0050';
  document.body.appendChild(box);
  const log = (msg, c='#0f0') => {
    const d = document.createElement('div');
    d.style.color = c; d.textContent = msg;
    box.appendChild(d); box.scrollTop = box.scrollHeight;
  };

  const sleep  = ms => new Promise(r => setTimeout(r, ms));
  const human  = ()  => sleep(2000 + Math.random() * 2000);

  const byXP = xp => {
    try { return document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; }
    catch(e) { return null; }
  };

  const waitXP = (xp, ms=25000) => new Promise((res, rej) => {
    const t0 = Date.now();
    const iv = setInterval(() => {
      const el = byXP(xp);
      if (el) { clearInterval(iv); res(el); return; }
      if (Date.now()-t0 > ms) { clearInterval(iv); rej(new Error('timeout: '+xp.slice(0,60))); }
    }, 500);
  });

  const clickEl = async el => {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await sleep(400 + Math.random() * 400);
    el.click();
    await sleep(400);
  };

  const typeInto = async (el, text) => {
    el.focus();
    await sleep(400);
    document.execCommand('selectAll', false, null);
    document.execCommand('delete',    false, null);
    await sleep(200);
    for (const ch of text) {
      document.execCommand('insertText', false, ch);
      await sleep(20 + Math.random() * 50);
    }
  };

  const pending = lista.filter(p => !progress[p.slug] || progress[p.slug] === 'erro');

  log('═══ TikTok Auto Post ═══', '#ff0050');
  log(`Total: ${lista.length} | Feitos: ${lista.length-pending.length} | Pendentes: ${pending.length}`, '#ff0');
  if (!pending.length) { log('Tudo postado!', '#0f0'); return; }

  for (let i = 0; i < pending.length; i++) {
    const p = pending[i];
    log(`\n[${i+1}/${pending.length}] ${p.slug}`, '#ff0050');
    log(`  ${p.caption.split('\n')[0].slice(0,50)}`, '#aaa');

    try {
      // 1 — abre upload
      const btnUp = await waitXP('//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[1]/div/div[2]/div/button');
      await clickEl(btnUp);
      await human();

      // 2 — botão escolher arquivo
      const btnFile = await waitXP('//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[1]/div/div/div[1]/div/div/div[2]/button');
      await clickEl(btnFile);
      await sleep(1000);

      // 3 — avisa usuário qual arquivo selecionar
      log(`  ⚠ SELECIONE: ${p.video}`, '#ff0');
      log('  aguardando upload (max 120s)...', '#888');

      // 4 — confirma vídeo
      const btnOk = await waitXP(
        '//*[@id="react-joyride-step-0"]/div/div/div[1]/div[1]/div/div/div[2]/button',
        120000
      );
      await clickEl(btnOk);
      await human();

      // 5 — digita descrição
      log('  digitando descrição...', '#aaa');
      const descEl = await waitXP('//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[5]/div[1]/div[2]/div[1]/div[2]/div/div[1]');
      await typeInto(descEl, p.caption);
      await human();

      // 6 — publica
      log('  publicando...', '#ff0');
      const btnPub = await waitXP('//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[6]/div/button[1]');
      await clickEl(btnPub);
      await sleep(7000 + Math.random() * 5000);

      // 7 — comentário com offer link
      log('  postando link no comentário...', '#aaa');
      const cmtBox = await waitXP(
        '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[2]/div/div/div[2]/div[2]/div[1]/div/div[3]/div/div/div[3]/div/div/div',
        30000
      );
      await typeInto(cmtBox, p.offer_link);
      await sleep(500 + Math.random() * 500);
      cmtBox.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
      await human();

      progress[p.slug] = 'ok';
      save();
      log('  ✓ postado!', '#0f0');

    } catch(e) {
      log(`  ✗ ERRO: ${e.message}`, '#f00');
      progress[p.slug] = 'erro';
      save();
    }

    if (i < pending.length - 1) {
      const w = 12000 + Math.random() * 8000;
      log(`  próximo em ${(w/1000).toFixed(0)}s...`, '#888');
      await sleep(w);
    }
  }

  log('\n═══════════════════════', '#ff0050');
  log(`✓ postados: ${Object.values(progress).filter(v=>v==='ok').length}`, '#0f0');
  log(`✗ erros:    ${Object.values(progress).filter(v=>v==='erro').length}`, '#f00');
  log('Reset: localStorage.removeItem("tiktok_post_progress")', '#555');
})();
