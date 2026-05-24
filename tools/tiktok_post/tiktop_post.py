import os
import json
from pathlib import Path
import pandas as pd

BASE = Path('/home/alessandro/bin/Git_Repo/BestPriceToday/tools/shopee_extract_mp4/')
AFILIADOS_CSV = BASE / 'shopee_products.csv'
PRODUTOS_CSV  = BASE / 'shopee_videos.csv'
VIDEO_DIR     = BASE / 'videos'
OUTPUT_JS     = Path('/home/alessandro/bin/Git_Repo/BestPriceToday/tools/tiktok_post/tiktok_post.user.js')

def read_csv_auto(path: Path) -> pd.DataFrame:
    with path.open('r', encoding='utf-8') as f:
        first = f.readline()
    sep = '\t' if '\t' in first else ','
    return pd.read_csv(path, sep=sep, dtype=str).rename(columns=lambda c: str(c).strip())

def pick_col(df: pd.DataFrame, *needles: str):
    for col in df.columns:
        low = str(col).lower()
        if any(n.lower() in low for n in needles):
            return col
    return None

def get_col(row: pd.Series, *names: str, default: str = '') -> str:
    for name in names:
        for key in row.index:
            if str(key).lower().strip() == str(name).lower().strip():
                val = row[key]
                if pd.isna(val):
                    continue
                val = str(val).strip()
                if val and val.lower() != 'nan':
                    return val
    return default

def make_caption(row: pd.Series) -> str:
    nome  = get_col(row, 'nome', 'item name', 'name')[:80]
    preco = get_col(row, 'preco', 'price')
    orig  = get_col(row, 'preco_original')
    desc  = get_col(row, 'desconto_pct')

    if orig and desc:
        return (
            f"{nome}\n"
            f"De R${orig} por R${preco} ({desc} OFF)\n"
            f"Link nos comentarios 👇\n"
            f"#shopee #oferta #promocao"
        )
    return (
        f"{nome}\n"
        f"Oferta Especial: R${preco}\n"
        f"Link nos comentarios 👇\n"
        f"#shopee #achadinhos #promocao"
    )

def build_products() -> list[dict]:
    df_af = read_csv_auto(AFILIADOS_CSV)
    df_pr = read_csv_auto(PRODUTOS_CSV)

    offer_col = pick_col(df_af, 'offer')
    if not offer_col:
        raise ValueError('Nao achei coluna com offer em shopee_products.csv')

    df_af['slug'] = (
        df_af[offer_col]
        .astype(str).str.strip()
        .str.split('/').str[-1]
    )

    slug_col_pr = 'slug' if 'slug' in df_pr.columns else df_pr.columns[0]
    df = df_af.merge(df_pr, left_on='slug', right_on=slug_col_pr, how='inner')

    df['_tem_video'] = df['slug'].apply(
        lambda s: (VIDEO_DIR / f"{str(s).strip()}.mp4").exists()
    )
    df = df[df['_tem_video']].copy()

    produtos = []
    for _, row in df.iterrows():
        slug = str(row['slug']).strip()
        produtos.append({
            'slug':       slug,
            'video':      f'{slug}.mp4',
            'offer_link': str(row[offer_col]).strip(),
            'caption':    make_caption(row),
        })

    return produtos


JS_TEMPLATE = r"""// ==UserScript==
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
    const LISTA = PRODUTOS_JSON;

    const readLocal   = (k, fb) => { try { const r = localStorage.getItem(k);   return r ? JSON.parse(r) : fb; } catch(e) { return fb; } };
    const readSession = (k, fb) => { try { const r = sessionStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch(e) { return fb; } };

    let progress = readLocal(PK, {});
    let state    = readSession(SK, { step: 'START', slug: null });

    const saveState = (step, slug = state.slug) => {
        state = { step, slug };
        sessionStorage.setItem(SK, JSON.stringify(state));
    };
    const saveProgress = () => localStorage.setItem(PK, JSON.stringify(progress));

    // salva estado ANTES de mudar a URL para nao perder ao recarregar
    const navigateTo = (url, step, slug = state.slug) => {
        saveState(step, slug);
        location.href = url;
    };

    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const log = (msg, status = 'INFO', color = '#fff') => {
        const s = document.getElementById('bot-status');
        const m = document.getElementById('bot-msg');
        if (s) s.innerText = 'Status: ' + status;
        if (m) { m.innerText = msg; m.style.color = color; }
        console.log('[BOT]', status, '-', msg);
    };

    const waitXP = async (xpPrimary, xpFallback = null, timeout = 15000) => {
        const deadline = Date.now() + timeout;
        while (Date.now() < deadline) {
            let el = null;
            try { el = document.evaluate(xpPrimary, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; } catch(e) {}
            if (!el && xpFallback) {
                try { el = document.evaluate(xpFallback, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; } catch(e) {}
            }
            if (el && el.isConnected) return el;
            await sleep(1000);
        }
        return null;
    };

    const safePaste = async (el, text) => {
        el.focus(); el.click();
        await sleep(500);
        try {
            document.execCommand('selectAll', false, null);
            document.execCommand('delete',    false, null);
            const ev = new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: new DataTransfer() });
            ev.clipboardData.setData('text/plain', text);
            el.dispatchEvent(ev);
            await sleep(1000);
            if (!el.textContent.trim()) document.execCommand('insertText', false, text);
        } catch(e) { el.textContent = text; }
        el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: text }));
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
                document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
            ).singleNodeValue;
            if (desc) {
                const txt = desc.textContent.trim();
                for (const p of LISTA) { if (txt.includes(p.slug)) return p; }
            }
        } catch(e) {}
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
                <button id="btn-reset" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Recarregar Passo</button>
                <button id="btn-clear" style="cursor:pointer;background:#500;color:white;border:1px solid #f00;padding:5px;flex:1;border-radius:4px;font-size:11px;font-weight:bold;">Apagar Memória</button>
            </div>`;
        document.body.appendChild(panel);
        document.getElementById('btn-reset').addEventListener('click', () => { sessionStorage.removeItem(SK); location.reload(); });
        document.getElementById('btn-clear').addEventListener('click', () => {
            if (confirm('Apagar memoria? O bot vai repostar os mesmos videos.')) {
                localStorage.removeItem(PK); progress = {}; sessionStorage.removeItem(SK);
                alert('Memória limpa!'); location.reload();
            }
        });
    }

    const logProduto = (p) => {
        const el = document.getElementById('bot-produto');
        if (el) el.innerText = p ? `Produto: ${p.slug}` : '';
    };

    await sleep(1500);

    while (true) {
        state = readSession(SK, { step: 'START', slug: null });

        const PASSOS_COM_PRODUTO = ['POSTAR', 'IR_COMENTARIOS', 'ENVIAR_LINK'];
        if (PASSOS_COM_PRODUTO.includes(state.step) && !state.slug) {
            log('Estado invalido (sem slug). Reiniciando...', 'AUTO-RESET', '#ff0');
            saveState('START', null);
            await sleep(1000);
            continue;
        }

        const produtoAtual = state.slug ? LISTA.find(p => p.slug === state.slug) : null;
        if (produtoAtual) logProduto(produtoAtual);
        log(`Passo: ${state.step}${state.slug ? ' | ' + state.slug : ''}`);

        try {
            switch (state.step) {

                case 'START': {
                    if (!location.pathname.includes('/upload')) {
                        navigateTo(
                            'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                            'AGUARDAR_VIDEO',
                            null
                        );
                        return;
                    }
                    saveState('AGUARDAR_VIDEO');
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
                                b.onclick = () => { wrap.remove(); resolve(p); };
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
                    saveState('POSTAR', produto.slug);
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
                                if (btn) { btn.click(); await sleep(2000); }
                                break;
                            }
                        }
                    } catch(e) {}

                    const btnPub = await waitXP(
                        '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[6]/div/button[1]',
                        null, 10000
                    );
                    if (!btnPub) throw new Error('Botao Publicar nao encontrado');

                    btnPub.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    await sleep(1500);

                    for (let j = 0; j < 30; j++) {
                        const off = btnPub.disabled || btnPub.hasAttribute('disabled') || btnPub.getAttribute('aria-disabled') === 'true';
                        if (!off) break;
                        log(`Aguardando botao Publicar ativar (${j+1}/30)...`, 'AGUARDANDO', '#ff0');
                        await sleep(2000);
                    }

                    // salva estado ANTES de clicar: se o TikTok redirecionar imediatamente, estado ja esta gravado
                    saveState('IR_COMENTARIOS', produtoAtual.slug);

                    log('Publicando...', 'PUBLICANDO', '#0f0');
                    btnPub.click();
                    btnPub.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    btnPub.dispatchEvent(new MouseEvent('mouseup',   { bubbles: true, cancelable: true }));

                    await sleep(12000);

                    const contentLink = Array.from(document.querySelectorAll('a')).find(a => a.href.includes('/content'));
                    if (contentLink) {
                        contentLink.click();
                        await sleep(5000);
                    } else {
                        navigateTo('https://www.tiktok.com/tiktokstudio/content', 'IR_COMENTARIOS', produtoAtual.slug);
                        return;
                    }
                    break;
                }

                case 'IR_COMENTARIOS': {
                    if (!produtoAtual) throw new Error('Produto nao identificado. Reinicie.');

                    // se nao estiver na pagina de conteudo, navega primeiro
                    if (!location.href.includes('/content')) {
                        log('Navegando para pagina de conteudo...', 'AGUARDANDO', '#ff0');
                        navigateTo('https://www.tiktok.com/tiktokstudio/content', 'IR_COMENTARIOS', produtoAtual.slug);
                        return;
                    }

                    // aguarda a lista de videos carregar
                    await sleep(4000);

                    // XPath exato do botao de comentario da primeira linha da lista de videos
                    const xpBtnComentario = '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[2]/div/div/div[2]/div[2]/div[1]/div/div[3]/div/div/div[3]';

                    let btnComentario = null;
                    for (let t = 0; t < 10; t++) {
                        try {
                            const el = document.evaluate(xpBtnComentario, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (el) {
                                // pega o div com cursor=pointer dentro do elemento
                                btnComentario = el.querySelector('[cursor="pointer"]') || el;
                                break;
                            }
                        } catch(e) {}
                        log(`Aguardando botao de comentario (${t+1}/10)...`, 'AGUARDANDO', '#ff0');
                        await sleep(1500);
                    }

                    if (!btnComentario) {
                        log('Botao comentario nao encontrado. Recarregando...', 'ERRO', '#f00');
                        await sleep(3000);
                        location.reload();
                        return;
                    }

                    log('Abrindo comentarios do video...', 'AGUARDANDO', '#ff0');
                    saveState('ENVIAR_LINK', produtoAtual.slug);
                    btnComentario.click();
                    await sleep(4000);
                    break;
                }

                case 'ENVIAR_LINK': {
                    if (!produtoAtual) throw new Error('Produto nao identificado. Reinicie.');

                    // aguarda o textarea de comentario aparecer (painel inline ou pagina dedicada)
                    const textarea = await waitXP(
                        '//*[@id="comment-input"]',
                        '//textarea[contains(@class,"css-18yze8z")]',
                        15000
                    );
                    if (!textarea) {
                        // painel nao abriu — volta para tentar clicar no botao de novo
                        log('Painel de comentario nao abriu. Voltando...', 'ERRO', '#f00');
                        saveState('IR_COMENTARIOS', produtoAtual.slug);
                        await sleep(2000);
                        break;
                    }

                    textarea.focus();
                    await sleep(300);

                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(textarea, produtoAtual.offer_link);
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    textarea.dispatchEvent(new Event('change', { bubbles: true }));
                    await sleep(1500);

                    let btnPost = null;
                    for (let t = 0; t < 8; t++) {
                        btnPost = document.querySelector('[data-tt="components_CommentInputEditor_TUXButton"]');
                        if (btnPost) break;
                        await sleep(1000);
                    }


                    if (!btnPost) throw new Error('Botao de enviar comentario nao apareceu');

                    btnPost.click();

                    // === AQUI ESTÁ A CORREÇÃO PRINCIPAL ===
                    log('Aguardando servidor salvar o comentario...', 'SALVANDO', '#ff0');
                    await sleep(10000); 
                    // ======================================

                    progress[produtoAtual.slug] = 'ok';
                    saveProgress();
                    log(`Concluido: ${produtoAtual.slug}`, 'SUCESSO', '#0f0');

                    // salva START imediatamente — nao espera o sleep terminar
                    saveState('START', null);

                    const pausaMs = (3 + Math.random() * 3) * 1000;
                    log(`Aguardando ${(pausaMs/1000).toFixed(1)}s antes de continuar...`, 'PAUSANDO', '#ff0');
                    await sleep(pausaMs);

                    const homeLink = Array.from(document.querySelectorAll('a')).find(a => a.href.match(/\/tiktokstudio\/?$/));
                    if (homeLink) {
                        homeLink.click();
                        await sleep(5000);
                    } else {
                        navigateTo('https://www.tiktok.com/tiktokstudio', 'START', null);
                        return;
                    }
                    break;
                }

                default: {
                    saveState('START', null);
                    break;
                }
            }
        } catch(e) {
            log(e.message || 'Erro desconhecido', 'ERRO', '#f00');
            await sleep(5000);
        }

        await sleep(2000);
    }
})();
"""

def main() -> None:
    produtos = build_products()

    js_final = JS_TEMPLATE.replace(
        'PRODUTOS_JSON',
        json.dumps(produtos, ensure_ascii=False, indent=2)
    )

    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JS.write_text(js_final, encoding='utf-8')
    print(f'Gerado: {OUTPUT_JS}')
    print(f'Produtos incluidos: {len(produtos)}')

if __name__ == '__main__':
    main()

