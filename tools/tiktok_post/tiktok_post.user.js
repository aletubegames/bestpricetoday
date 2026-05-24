// ==UserScript==
// @name         Bot TikTok Fiel
// @namespace    http://tampermonkey.net/
// @version      9.1
// @description  Bot orientado ao video escolhido pelo usuario - corrigido perda de estado
// @author       Alessandro
// @match        https://www.tiktok.com/tiktokstudio*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(async () => {
    if (window.__tt_bot_running__) return;
    window.__tt_bot_running__ = true;

    const PK = 'tt_progress';
    const SK = 'tt_state';
    const LISTA = [
  {
    "slug": "10zxusHSxq",
    "video": "10zxusHSxq.mp4",
    "offer_link": "https://s.shopee.com.br/10zxusHSxq",
    "caption": "Mesa de Cabeceira Retrô Compacta com Nicho para Quarto Sala Casal ou Solteiro Pa\nDe R$49.90 por R$29.90 (40% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "1VwEVnFYwz",
    "video": "1VwEVnFYwz.mp4",
    "offer_link": "https://s.shopee.com.br/1VwEVnFYwz",
    "caption": "Percarbonato 100% Puro Tira Manchas Roupas Brancas e Coloridas\nDe R$29.90 por R$19.90 (33% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "1qZ4uPEIH5",
    "video": "1qZ4uPEIH5.mp4",
    "offer_link": "https://s.shopee.com.br/1qZ4uPEIH5",
    "caption": "Areia Catbio Biodegradável 4 Kg - Max Clean - Grãos Finos\nDe R$48.90 por R$46.90 (4% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "20sV6iDew8",
    "video": "20sV6iDew8.mp4",
    "offer_link": "https://s.shopee.com.br/20sV6iDew8",
    "caption": "Jogo de Lençol 400 fios toque Suave e Acetinado Berço Solteiro Casal Queen King \nDe R$160.00 por R$14.60 (91% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "2BBvJ1D1bB",
    "video": "2BBvJ1D1bB.mp4",
    "offer_link": "https://s.shopee.com.br/2BBvJ1D1bB",
    "caption": "Tira manchas alvejante 1kg + Percarbonato de sódio 1kg\nDe R$38.00 por R$17.86 (53% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "2LVLVKCOGE",
    "video": "2LVLVKCOGE.mp4",
    "offer_link": "https://s.shopee.com.br/2LVLVKCOGE",
    "caption": "40 Peças / 46 Peças Jogo De Chave Catraca Caixa De Ferramentas Completa Reversív\nDe R$51.98 por R$25.97 (50% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "3VhItT7wtZ",
    "video": "3VhItT7wtZ.mp4",
    "offer_link": "https://s.shopee.com.br/3VhItT7wtZ",
    "caption": "Kit 1 ou 2 Unidades de Veda Porta Ajustável Protetor Rolinho Impermeável 80cm 90\nDe R$19.00 por R$12.99 (32% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "3qK9I56gDf",
    "video": "3qK9I56gDf.mp4",
    "offer_link": "https://s.shopee.com.br/3qK9I56gDf",
    "caption": "Kit 3 Peneira Coador De Peneiras Aço Inoxidável Para Cozinha Peneira De Cozinha\nDe R$25.98 por R$15.99 (38% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "40dZUO62si",
    "video": "40dZUO62si.mp4",
    "offer_link": "https://s.shopee.com.br/40dZUO62si",
    "caption": "Sapateira 4 ou 5 Andares Multiuso Desmontável Organizadora Multiuso Sapatos Livr\nDe R$50.00 por R$17.98 (64% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "4LGPt04mCo",
    "video": "4LGPt04mCo.mp4",
    "offer_link": "https://s.shopee.com.br/4LGPt04mCo",
    "caption": "Lencol Queen 400 Fios Micropercal Cama Casal Solteiro Tecido Super Macio\nDe R$45.00 por R$25.89 (42% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "4VZq5J48rr",
    "video": "4VZq5J48rr.mp4",
    "offer_link": "https://s.shopee.com.br/4VZq5J48rr",
    "caption": "Creatina Suplemento Monohidratada em Pó 100% Pura Importada - Soldiers Nutrition\nDe R$69.90 por R$29.90 (57% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "4ftGHc3VWu",
    "video": "4ftGHc3VWu.mp4",
    "offer_link": "https://s.shopee.com.br/4ftGHc3VWu",
    "caption": "Trava Óculos Antiderrapante Silicone Kit Não Cai Do Rosto Gancho Orelha Haste Co\nDe R$7.50 por R$5.50 (27% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "4qCgTv2sBx",
    "video": "4qCgTv2sBx.mp4",
    "offer_link": "https://s.shopee.com.br/4qCgTv2sBx",
    "caption": "Kit Limpador Pastilha de máquina de lavar roupa, comprimido efervescente sólido \nDe R$15.00 por R$8.59 (43% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "50W6gE2Er0",
    "video": "50W6gE2Er0.mp4",
    "offer_link": "https://s.shopee.com.br/50W6gE2Er0",
    "caption": "Tapete de Banheiro Absorvente Antiderrapante Secagem Rápida\nDe R$50.00 por R$11.99 (76% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "5VSNH90Kq9",
    "video": "5VSNH90Kq9.mp4",
    "offer_link": "https://s.shopee.com.br/5VSNH90Kq9",
    "caption": "Kit 10 Panos De Limpeza Microfibra alta absorção Multiuso\nDe R$99.99 por R$17.48 (83% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "5flnTRzhVC",
    "video": "5flnTRzhVC.mp4",
    "offer_link": "https://s.shopee.com.br/5flnTRzhVC",
    "caption": "Mulheres com Deus - 365 Dias de Fé - Devocional\nDe R$39.90 por R$20.51 (49% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "5q5Dfkz4AF",
    "video": "5q5Dfkz4AF.mp4",
    "offer_link": "https://s.shopee.com.br/5q5Dfkz4AF",
    "caption": "Kit 5/10/20/50/100 Un Saco Saquinho Organza Tule Saquinho 7x9 9x12 10x15 Branco \nDe R$45.90 por R$5.90 (87% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "60Ods3yQpI",
    "video": "60Ods3yQpI.mp4",
    "offer_link": "https://s.shopee.com.br/60Ods3yQpI",
    "caption": "Balança Bioimpedância Digital Profissional Suporta Até 140kg via Bluethooth\nDe R$99.00 por R$29.96 (70% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "6Ai44MxnUL",
    "video": "6Ai44MxnUL.mp4",
    "offer_link": "https://s.shopee.com.br/6Ai44MxnUL",
    "caption": "Espuma Spray Zip Clean 300ml Limpa a Seco Sofá, Estofado, Banco de Carro Limpeza\nDe R$29.99 por R$15.99 (47% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "6VKuSywWoR",
    "video": "6VKuSywWoR.mp4",
    "offer_link": "https://s.shopee.com.br/6VKuSywWoR",
    "caption": "ROMANTIC CROWN Copo Térmico Inox Portátil 1200ml/600ml/1.2L Garrafa Térmica Inox\nDe R$60.00 por R$39.98 (33% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "6feKfHvtTU",
    "video": "6feKfHvtTU.mp4",
    "offer_link": "https://s.shopee.com.br/6feKfHvtTU",
    "caption": "Organizador de Sacolas Dispenser Organizadora De Plástico Para Armazenamento De \nDe R$29.99 por R$10.00 (67% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "70HB3tucna",
    "video": "70HB3tucna.mp4",
    "offer_link": "https://s.shopee.com.br/70HB3tucna",
    "caption": "Kit Jogo De Lençol Cama Box Solteiro Casal Queen King 02 e 03 Peças\nDe R$60.00 por R$25.80 (57% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "7VDReosimj",
    "video": "7VDReosimj.mp4",
    "offer_link": "https://s.shopee.com.br/7VDReosimj",
    "caption": "Kit2/1 Cartão Memória Micro SD Ultra 32GB-256GB Com Adaptador p/Vendas diretas d\nDe R$29.99 por R$12.99 (57% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "7pqI3QrS6p",
    "video": "7pqI3QrS6p.mp4",
    "offer_link": "https://s.shopee.com.br/7pqI3QrS6p",
    "caption": "Depilador Indolor Caneta Sobrancelha Removedor Instantâneo A Pilha\nDe R$48.00 por R$12.39 (74% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "809iFjqols",
    "video": "809iFjqols.mp4",
    "offer_link": "https://s.shopee.com.br/809iFjqols",
    "caption": "Protetor Impermeável para Colchão SUPER SILENCIOSO 100% Impermeável Tecido Jacqu\nDe R$119.97 por R$47.97 (60% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "8AT8S2qBQv",
    "video": "8AT8S2qBQv.mp4",
    "offer_link": "https://s.shopee.com.br/8AT8S2qBQv",
    "caption": "Bermuda Modeladora Anágua Cinta Short Feminino Modelador Alta Compressão Reduz M\nDe R$38.99 por R$20.90 (46% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "8fPP2xoHQ4",
    "video": "8fPP2xoHQ4.mp4",
    "offer_link": "https://s.shopee.com.br/8fPP2xoHQ4",
    "caption": "Lencol Micropercal 400 Fios Jogo De Cama Casal, Queen, King 03 Peças Barato Solt\nDe R$25.90 por R$19.36 (25% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "9ALfdsmNPD",
    "video": "9ALfdsmNPD.mp4",
    "offer_link": "https://s.shopee.com.br/9ALfdsmNPD",
    "caption": "Creme Gel Regenerador Facial Gota de Colágeno Kokeshi 45g\nDe R$46.90 por R$31.90 (32% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "9UyW2Ul6jJ",
    "video": "9UyW2Ul6jJ.mp4",
    "offer_link": "https://s.shopee.com.br/9UyW2Ul6jJ",
    "caption": "Chave T  Longa Para máquina de lavar 10mm Agitador Brastemp/Consul/Electrolux Un\nDe R$24.99 por R$12.75 (49% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "9pbMR6jq3P",
    "video": "9pbMR6jq3P.mp4",
    "offer_link": "https://s.shopee.com.br/9pbMR6jq3P",
    "caption": "Aparelho Medidor De Pressão Arterial Digital De Braço\nDe R$59.67 por R$32.99 (45% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "9zumdPjCiS",
    "video": "9zumdPjCiS.mp4",
    "offer_link": "https://s.shopee.com.br/9zumdPjCiS",
    "caption": "ROMANTIC CROWN Copo Térmico Portátil 1200ml/600ml com Tampa e Canudo Garrafa Tér\nDe R$70.00 por R$39.98 (43% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  },
  {
    "slug": "17Qj2LH0b",
    "video": "17Qj2LH0b.mp4",
    "offer_link": "https://s.shopee.com.br/17Qj2LH0b",
    "caption": "kit Coala Home Chá Branco\nDe R$80.65 por R$72.90 (10% OFF)\nLink nos comentarios 👇\n#shopee #oferta #promocao"
  }
];

    const readLocal = (k, fb) => { try { const r = localStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } };
    const readSession = (k, fb) => { try { const r = sessionStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } };

    let progress = readLocal(PK, {});
    let state = readSession(SK, { current: { step: 'START', slug: null }, history: [], future: [] });

    const saveState = (step, slug = state.current.slug, pushToHistory = true) => {
        if (pushToHistory && (state.history.length === 0 || state.history[state.history.length - 1].step !== state.current.step)) {
            state.history.push(state.current);
            state.future = [];
        }
        state.current = { step, slug };
        sessionStorage.setItem(SK, JSON.stringify(state));
    };

    const saveProgress = () => localStorage.setItem(PK, JSON.stringify(progress));

    const navigateTo = (url, step, slug = state.current.slug, pushToHistory = true) => {
        saveState(step, slug, pushToHistory);
        location.href = url;
    };

    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const log = (msg, status = 'INFO', color = '#fff') => {
        const s = document.getElementById('bot-status');
        const m = document.getElementById('bot-msg');
        if (s) s.innerText = 'Status: ' + status;
        if (m) {
            m.innerText = msg;
            m.style.color = color;
        }
        console.log('[BOT]', status, '-', msg);
    };

    const waitXP = async (xpPrimary, xpFallback = null, timeout = 15000) => {
        const deadline = Date.now() + timeout;
        while (Date.now() < deadline) {
            let el = null;
            try {
                el = document.evaluate(xpPrimary, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            } catch (e) {}
            if (!el && xpFallback) {
                try {
                    el = document.evaluate(xpFallback, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                } catch (e) {}
            }
            if (el && el.isConnected) return el;
            await sleep(1000);
        }
        return null;
    };

    const safePaste = async (el, text) => {
        el.focus();
        el.click();
        await sleep(500);
        try {
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);

            const ev = new ClipboardEvent('paste', {
                bubbles: true,
                cancelable: true,
                clipboardData: new DataTransfer()
            });

            ev.clipboardData.setData('text/plain', text);
            el.dispatchEvent(ev);
            await sleep(1000);

            if (!el.textContent.trim()) document.execCommand('insertText', false, text);
        } catch (e) {
            el.textContent = text;
        }

        el.dispatchEvent(new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: text
        }));

        await sleep(1000);
    };

    const detectarProduto = () => {
        const pageText = document.body.innerText + document.body.innerHTML;

        for (const p of LISTA) {
            if (pageText.includes(p.video) || pageText.includes(p.slug)) return p;
        }

        try {
            const desc = document.evaluate(
                '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                document,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null
            ).singleNodeValue;

            if (desc) {
                const txt = desc.textContent.trim();
                for (const p of LISTA) {
                    if (txt.includes(p.slug)) return p;
                }
            }
        } catch (e) {}

        return null;
    };

    if (!document.getElementById('bot-panel')) {
        const panel = document.createElement('div');
        panel.id = 'bot-panel';
        panel.style = 'position:fixed;top:10px;right:10px;z-index:999999;background:rgba(0,0,0,0.9);color:#0f0;padding:15px;border:1px solid #ff0050;font-family:monospace;width:340px;border-radius:8px;box-shadow:0 0 10px #ff0050;';
        panel.innerHTML = `
            <h4 style="color:#ff0050;margin:0">BOT TIKTOK v9</h4>
            <div id="bot-status" style="margin-top:10px;font-weight:bold;">Iniciando...</div>
            <div id="bot-msg" style="font-size:12px;color:#fff;margin-top:5px;word-wrap:break-word;min-height:40px;"></div>
            <div id="bot-produto" style="font-size:11px;color:#0ff;margin-top:5px;word-wrap:break-word;"></div>
            <div style="margin-top:10px;display:flex;gap:5px;">
                <button id="btn-back" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Voltar</button>
                <button id="btn-forward" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Avancar</button>
                <button id="btn-reset" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Recarregar</button>
                <button id="btn-clear" style="cursor:pointer;background:#500;color:white;border:1px solid #f00;padding:5px;flex:1;border-radius:4px;font-size:11px;font-weight:bold;">Apagar Memoria</button>
            </div>`;
        document.body.appendChild(panel);

        document.getElementById('btn-reset').addEventListener('click', () => {
            sessionStorage.removeItem(SK);
            location.reload();
        });

        document.getElementById('btn-back').addEventListener('click', () => {
            if (state.history.length > 0) {
                state.future.unshift(state.current);
                state.current = state.history.pop();
                sessionStorage.setItem(SK, JSON.stringify(state));
                location.reload();
            }
        });

        document.getElementById('btn-forward').addEventListener('click', () => {
            if (state.future.length > 0) {
                state.history.push(state.current);
                state.current = state.future.shift();
                sessionStorage.setItem(SK, JSON.stringify(state));
                location.reload();
            }
        });

        document.getElementById('btn-clear').addEventListener('click', () => {
            if (confirm('Apagar memoria? O bot vai repostar os mesmos videos.')) {
                localStorage.removeItem(PK);
                progress = {};
                sessionStorage.removeItem(SK);
                alert('Memoria limpa!');
                location.reload();
            }
        });
    }

    const logProduto = (p) => {
        const el = document.getElementById('bot-produto');
        if (el) el.innerText = p ? `Produto: ${p.slug}` : '';
    };

    await sleep(1500);

    while (true) {
        state = readSession(SK, { current: { step: 'START', slug: null }, history: [], future: [] });

        const PASSOS_COM_PRODUTO = ['POSTAR', 'IR_COMENTARIOS', 'ENVIAR_LINK'];
        if (PASSOS_COM_PRODUTO.includes(state.current.step) && !state.current.slug) {
            log('Estado invalido (sem slug). Reiniciando...', 'AUTO-RESET', '#ff0');
            saveState('START', null);
            await sleep(1000);
            continue;
        }

        const produtoAtual = state.current.slug ? LISTA.find(p => p.slug === state.current.slug) : null;
        if (produtoAtual) logProduto(produtoAtual);
        log(`Passo: ${state.current.step}${state.current.slug ? ' | ' + state.current.slug : ''}`);

        try {
            switch (state.current.step) {
                case 'START': {
                    if (!location.pathname.includes('/upload')) {
                        navigateTo(
                            'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                            'AGUARDAR_VIDEO',
                            null
                        );
                        return;
                    }

                    saveState('AGUARDAR_VIDEO', null, false);
                    await sleep(2000);
                    break;
                }

                case 'AGUARDAR_VIDEO': {
                    const btnSel = await waitXP(
                        '//*[@data-e2e="select_video_button"]',
                        '//button[@aria-label="Selecionar vídeo" or @aria-label="Selecionar video"]',
                        15000
                    );
                    if (!btnSel) throw new Error('Botao Selecionar Video nao encontrado');

                    log('Escolha o video na janela do Windows', 'AGUARDANDO USUARIO', '#0ff');
                    btnSel.click();

                    const campoTexto = await waitXP(
                        '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                        '//div[@contenteditable="true"]',
                        300000
                    );
                    if (!campoTexto) throw new Error('Timeout: nenhum video selecionado');

                    log('Video detectado! Aguardando tela estabilizar...', 'AGUARDANDO', '#ff0');
                    await sleep(10000);

                    let produto = detectarProduto();

                    if (!produto) {
                        log('Nao identifiquei o video. Clique no produto correto abaixo:', 'ESCOLHA', '#ff0');
                        produto = await new Promise(resolve => {
                            const wrap = document.createElement('div');
                            wrap.id = 'manual-picker';
                            wrap.style = 'max-height:180px;overflow-y:auto;margin-top:6px;';
                            const disponiveis = LISTA.filter(p => progress[p.slug] !== 'ok');
                            disponiveis.forEach(p => {
                                const b = document.createElement('button');
                                b.textContent = p.slug;
                                b.style = 'display:block;width:100%;margin:2px 0;background:#111;color:#0ff;border:1px solid #0ff;padding:4px 6px;font-size:10px;cursor:pointer;border-radius:3px;text-align:left;';
                                b.onclick = () => {
                                    wrap.remove();
                                    resolve(p);
                                };
                                wrap.appendChild(b);
                            });
                            document.getElementById('bot-panel').appendChild(wrap);
                        });
                    }

                    if (progress[produto.slug] === 'ok') {
                        log(`Aviso: "${produto.slug}" ja foi postado antes.`, 'AVISO', '#ff0');
                    }

                    log(`Produto: ${produto.slug}`, 'IDENTIFICADO', '#0f0');
                    logProduto(produto);
                    saveState('POSTAR', produto.slug, true);
                    await sleep(1000);
                    break;
                }

                case 'POSTAR': {
                    if (!produtoAtual) throw new Error('Produto nao identificado. Reinicie.');

                    const descBox = await waitXP(
                        '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                        '//div[@contenteditable="true"]',
                        30000
                    );
                    if (!descBox) throw new Error('Campo de legenda nao encontrado');

                    log('Preenchendo legenda...', 'AGUARDANDO', '#ff0');
                    await safePaste(descBox, produtoAtual.caption);
                    await sleep(4000);

                    if ((descBox.textContent || '').trim().length < 5) {
                        throw new Error('Legenda ficou vazia, tentando novamente...');
                    }

                    try {
                        for (const xp of [
                            '//*[@id=":rbv:"]/div[1]/div/svg',
                            '//div[starts-with(@id,":r")]/div[1]/div/svg',
                            '//div[@role="dialog"]//svg'
                        ]) {
                            const svg = document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (svg) {
                                const btn = svg.closest('button') || svg.closest('div[role="button"]') || svg.parentElement;
                                if (btn) {
                                    btn.click();
                                    await sleep(2000);
                                }
                                break;
                            }
                        }
                    } catch (e) {}

                    const btnPub = await waitXP(
                        '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[6]/div/button[1]',
                        null,
                        10000
                    );
                    if (!btnPub) throw new Error('Botao Publicar nao encontrado');

                    btnPub.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    await sleep(2000);

                    log('Publicando video...', 'PUBLICANDO', '#0f0');
                    btnPub.click();

                    progress[produtoAtual.slug] = 'ok';
                    saveProgress();

                    await sleep(15000);

                    saveState('IR_COMENTARIOS', produtoAtual.slug, true);
                    break;
                }

                case 'IR_COMENTARIOS': {
                    log('Abrindo comentarios...', 'COMENTARIOS', '#0ff');

                    const comentariosBtn = await waitXP(
                        '//span[contains(text(),"Comentarios")]',
                        '//button[contains(.,"Comentarios")]',
                        20000
                    );

                    if (comentariosBtn) {
                        comentariosBtn.click();
                        await sleep(4000);
                    }

                    saveState('ENVIAR_LINK', produtoAtual.slug, true);
                    break;
                }

                case 'ENVIAR_LINK': {
                    if (!produtoAtual) throw new Error('Produto perdido');

                    log('Enviando link afiliado...', 'LINK', '#ff0');

                    const campoComentario = await waitXP(
                        '//div[@contenteditable="true"]',
                        '//textarea',
                        20000
                    );

                    if (!campoComentario) {
                        throw new Error('Campo comentario nao encontrado');
                    }

                    await safePaste(campoComentario, produtoAtual.offer_link);
                    await sleep(2000);

                    const enviarBtn = await waitXP(
                        '//button[contains(.,"Postar")]',
                        '//button[contains(.,"Enviar")]',
                        10000
                    );

                    if (enviarBtn) {
                        enviarBtn.click();
                        await sleep(3000);
                    }

                    log('Postagem finalizada!', 'OK', '#0f0');

                    saveState('START', null, true);
                    await sleep(5000);

                    navigateTo(
                        'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                        'AGUARDAR_VIDEO',
                        null
                    );
                    return;
                }

                default: {
                    log('Estado desconhecido. Resetando...', 'RESET', '#f00');
                    saveState('START', null);
                    await sleep(2000);
                    break;
                }
            }
        } catch (err) {
            console.error(err);
            log(err?.message || 'Erro desconhecido', 'ERRO', '#f00');
            await sleep(5000);
        }
    }
})();
