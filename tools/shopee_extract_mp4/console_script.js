(async () => {
  const STORAGE_KEY = 'shopee_dl_progress';
  const CSV_KEY     = 'shopee_csv_data';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const human = () => sleep(3000 + Math.random() * 3000);

  // ── COLE SEUS LINKS AQUI ──────────────────────────────────
  const links = `
https://s.shopee.com.br/gN7WGIjdk
https://s.shopee.com.br/qgXiZI6In
https://s.shopee.com.br/10zxusHSxq
https://s.shopee.com.br/1BJO7BGpct
https://s.shopee.com.br/1LcoJUGCHw
https://s.shopee.com.br/1VwEVnFYwz
https://s.shopee.com.br/1gFei6Evc2
https://s.shopee.com.br/1qZ4uPEIH5
https://s.shopee.com.br/20sV6iDew8
https://s.shopee.com.br/2BBvJ1D1bB
https://s.shopee.com.br/2LVLVKCOGE
https://s.shopee.com.br/2VolhdBkvH
https://s.shopee.com.br/2g8BtwB7aK
https://s.shopee.com.br/2qRc6FAUFN
https://s.shopee.com.br/30l2IY9quQ
https://s.shopee.com.br/3B4SUr9DZT
https://s.shopee.com.br/3LNshA8aEW
https://s.shopee.com.br/3VhItT7wtZ
https://s.shopee.com.br/3g0j5m7JYc
https://s.shopee.com.br/3qK9I56gDf
https://s.shopee.com.br/40dZUO62si
https://s.shopee.com.br/4Awzgh5PXl
https://s.shopee.com.br/4LGPt04mCo
https://s.shopee.com.br/4VZq5J48rr
https://s.shopee.com.br/4ftGHc3VWu
https://s.shopee.com.br/4qCgTv2sBx
https://s.shopee.com.br/50W6gE2Er0
https://s.shopee.com.br/5ApWsX1bW3
https://s.shopee.com.br/5L8x4q0yB6
https://s.shopee.com.br/5VSNH90Kq9
https://s.shopee.com.br/5flnTRzhVC
https://s.shopee.com.br/5q5Dfkz4AF
https://s.shopee.com.br/60Ods3yQpI
https://s.shopee.com.br/6Ai44MxnUL
https://s.shopee.com.br/6L1UGfxA9O
https://s.shopee.com.br/6VKuSywWoR
https://s.shopee.com.br/6feKfHvtTU
https://s.shopee.com.br/6pxkravG8X
https://s.shopee.com.br/70HB3tucna
https://s.shopee.com.br/7AabGCtzSd
https://s.shopee.com.br/7Ku1SVtM7g
https://s.shopee.com.br/7VDReosimj
https://s.shopee.com.br/7fWrr7s5Rm
https://s.shopee.com.br/7pqI3QrS6p
https://s.shopee.com.br/809iFjqols
https://s.shopee.com.br/8AT8S2qBQv
https://s.shopee.com.br/8KmYeLpY5y
https://s.shopee.com.br/8V5yqeoul1
https://s.shopee.com.br/8fPP2xoHQ4
https://s.shopee.com.br/8pipFGne57
https://s.shopee.com.br/902FRZn0kA
https://s.shopee.com.br/9ALfdsmNPD
https://s.shopee.com.br/9Kf5qBlk4G
https://s.shopee.com.br/9UyW2Ul6jJ
https://s.shopee.com.br/9fHwEnkTOM
https://s.shopee.com.br/9pbMR6jq3P
https://s.shopee.com.br/9zumdPjCiS
https://s.shopee.com.br/AAECpiiZNV
https://s.shopee.com.br/AKXd21hw2Y
https://s.shopee.com.br/AUr3EKhIhb
https://s.shopee.com.br/BQqvLKdfc
https://s.shopee.com.br/17Qj2LH0b
https://s.shopee.com.br/W3hJxJMzi
https://s.shopee.com.br/LkH7eK0Kh
`.trim().split('\n').map(s => s.trim()).filter(Boolean);
  // ─────────────────────────────────────────────────────────

  let progress = {};
  let csvRows  = [];
  try { progress = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch(e) {}
  try { csvRows  = JSON.parse(localStorage.getItem(CSV_KEY)     || '[]'); } catch(e) {}

  const save = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    localStorage.setItem(CSV_KEY,     JSON.stringify(csvRows));
  };

  // overlay
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;bottom:0;right:0;width:500px;max-height:380px;overflow-y:auto;background:#111;color:#0f0;font:12px monospace;z-index:2147483647;padding:10px 14px;border-top:3px solid #0f0;border-left:3px solid #0f0';
  document.body.appendChild(box);
  const log = (msg, c='#0f0') => {
    const d = document.createElement('div');
    d.style.color = c; d.textContent = msg;
    box.appendChild(d); box.scrollTop = box.scrollHeight;
  };

  const exportCsv = () => {
    if (!csvRows.length) { log('Nenhum dado para CSV', '#f90'); return; }
    const header = 'slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao';
    const esc = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const body = csvRows.map(r =>
      [r.slug, r.nome, r.preco, r.precoOrig, r.desconto, r.avaliacao,
       r.vendidos, r.estoque, r.temVideo, r.urlFinal, r.descricao]
      .map(esc).join(',')
    ).join('\n');
    const blob = new Blob(['\ufeff' + header + '\n' + body], { type: 'text/csv;charset=utf-8' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob), download: 'shopee_produtos.csv'
    });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    log(`\n📥 shopee_produtos.csv (${csvRows.length} linhas)`, '#0ff');
  };

  const pending = links.filter(l => {
    const slug = l.split('/').pop();
    return !progress[slug] || progress[slug] === 'timeout';
  });

  const feitos = links.length - pending.length;
  log(`Total: ${links.length} | Feitos: ${feitos} | Pendentes: ${pending.length}`, '#ff0');

  if (!pending.length) {
    log('Tudo processado! Gerando CSV...', '#0f0');
    exportCsv();
    return;
  }

  const tab = window.open('about:blank', '_blank');
  if (!tab) { log('✗ popup bloqueado — libere e rode de novo', '#f00'); return; }
  window.focus();
  await sleep(1000);

  const resolveUrl = (link) => new Promise(resolve => {
    tab.location.href = 'about:blank';
    setTimeout(() => {
      tab.location.href = link;
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        try {
          const h = tab.location.href;
          if (h && !h.includes('about:blank') && !h.includes('s.shopee.com.br')) {
            clearInterval(t); resolve(h);
          }
        } catch(e) {}
        if (tries > 100) { clearInterval(t); resolve(null); }
      }, 300);
    }, 800);
  });

  const downloadBlob = async (url, filename) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const blob = await res.blob();
    const burl = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), { href: burl, download: filename });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(burl), 15000);
  };

  let ok = 0, sem = 0, erro = 0, timeout = 0;

  for (let i = 0; i < pending.length; i++) {
    const link = pending[i];
    const slug = link.split('/').pop();
    log(`\n[${i+1}/${pending.length}] ${slug}`);

    try {
      const finalUrl = await resolveUrl(link);
      window.focus();

      if (!finalUrl) {
        log('  ✗ timeout — retry na próxima rodada', '#f90');
        progress[slug] = 'timeout'; save(); timeout++;
        await human(); continue;
      }

      log('  → ' + finalUrl.split('?')[0], '#555');

      const nums = new URL(finalUrl).pathname.split('/').filter(p => /^\d{6,}$/.test(p));
      if (nums.length < 2) {
        log('  ✗ IDs não encontrados', '#f90');
        progress[slug] = 'erro'; save(); erro++;
        await human(); continue;
      }

      const shopid = nums[nums.length - 2];
      const itemid = nums[nums.length - 1];
      log(`  shopid=${shopid} itemid=${itemid}`, '#aaa');

      await sleep(1500 + Math.random() * 1500);

      const res = await fetch(`/api/v4/item/get?itemid=${itemid}&shopid=${shopid}`, { credentials: 'include' });
      const j = await res.json().catch(() => null);

      if (!j?.data) {
        log('  ✗ API sem dados', '#f90');
        progress[slug] = 'erro'; save(); erro++;
        await human(); continue;
      }

      const d = j.data;

      const nome      = (d.name || '').replace(/[\r\n]+/g, ' ');
      const precoRaw  = d.price || d.price_min || 0;
      const origRaw   = d.price_before_discount || 0;
      const preco     = (precoRaw / 100000).toFixed(2);
      const precoOrig = origRaw ? (origRaw / 100000).toFixed(2) : preco;
      const desconto  = origRaw ? (((origRaw - precoRaw) / origRaw) * 100).toFixed(0) + '%' : '0%';
      const avaliacao = d.item_rating?.rating_star?.toFixed(1) || '';
      const vendidos  = d.historical_sold || d.sold || 0;
      const estoque   = d.stock || 0;
      const descricao = (d.description || '').replace(/[\r\n\t]+/g, ' ').slice(0, 500);
      const urlFinal  = finalUrl.split('?')[0];
      const temVideo  = !!(d.video_info_list?.length);

      log(`  📦 ${nome.slice(0,45)} | R$${preco} | ⭐${avaliacao} | 🛒${vendidos}`, '#0ff');

      // ── vídeo ─────────────────────────────────────────────
      const vlist = d.video_info_list;
      let videoUrl = null;

      if (vlist?.length) {
        const v = vlist[0];
        videoUrl =
          v?.formats?.sort((a,b) => (b.width||0) - (a.width||0))?.[0]?.url ||
          v?.default_format?.url || null;
      }

      // fallback: clica no botão de play na página e pega src do <video>
      if (!videoUrl) {
        log('  API sem vídeo — tentando via página...', '#f90');
        try {
          // navega o tab para a página do produto
          tab.location.href = finalUrl;
          await sleep(5000); // aguarda carregar

          // clica no botão de play pelo XPath
          const xp = '//*[@id="sll2-normal-pdp-main"]/div/div/div/div[2]/section/section[1]/div[2]/div[2]/button/svg';
          const btn = document.evaluate(xp, tab.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
          if (btn) {
            btn.click();
            log('  clicou no play — aguardando vídeo...', '#aaa');
            await sleep(3000);
          }

          // pega src do elemento <video>
          const vidEl = tab.document.querySelector('video');
          videoUrl = vidEl?.currentSrc || vidEl?.src || null;

          // volta tab para blank pra não atrapalhar próximo redirect
          tab.location.href = 'about:blank';
        } catch(e) {
          log('  fallback falhou: ' + e.message, '#f90');
          tab.location.href = 'about:blank';
        }
      }

      if (!videoUrl) {
        log('  — sem vídeo em nenhuma fonte', '#888');
        sem++;
      } else {
        log('  baixando vídeo...', '#ff0');
        await downloadBlob(videoUrl, slug + '.mp4');
        log('  ✓ ' + slug + '.mp4', '#0f0');
        ok++;
      }

      csvRows = csvRows.filter(r => r.slug !== slug);
      csvRows.push({ slug, nome, preco, precoOrig, desconto, avaliacao, vendidos, estoque, temVideo, urlFinal, descricao });
      progress[slug] = 'ok';
      save();

    } catch(e) {
      log(`  ✗ ERRO: ${e.message}`, '#f00');
      progress[slug] = 'erro'; save(); erro++;
    }

    await human();
  }

  try { tab.close(); } catch(e) {}

  log(`\n══════════════════════════════`, '#ff0');
  log(`✓ vídeos baixados : ${ok}`,            '#0f0');
  log(`— sem vídeo       : ${sem}`,            '#888');
  log(`⟳ timeout (retry) : ${timeout}`,        timeout ? '#f90' : '#555');
  log(`✗ erros           : ${erro}`,            erro    ? '#f00' : '#555');
  log(`══════════════════════════════`, '#ff0');

  exportCsv();

  log('\nPara resetar tudo: localStorage.removeItem("shopee_dl_progress"); localStorage.removeItem("shopee_csv_data")', '#555');
})();