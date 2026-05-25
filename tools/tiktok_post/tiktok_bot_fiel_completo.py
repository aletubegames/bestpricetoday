#!/usr/bin/env python3
"""
tiktok_bot_fiel_completo.py — Lê shopee_products.csv + shopee_videos.csv + videos/
e gera tiktok_post.user.js (Tampermonkey UserScript).

Melhorias v10:
  - Retry automático (3x) com fallback de XPath por step
  - Confirma publicação antes de marcar 'ok'
  - XPath flexível (contains) em vez de texto exato
  - Wait pós-publicar que detecta "Publicado" / "Seu vídeo" / URL / /creator-center
  - Timeout configurável por step
  - Log melhorado com contadores

Uso:
  python3 tiktok_bot_fiel_completo.py
"""

import json
from pathlib import Path

import pandas as pd

BASE = Path("/home/alessandro/bin/Git_Repo/BestPriceToday/tools/shopee_extract_mp4/")
AFILIADOS_CSV = BASE / "shopee_products.csv"
PRODUTOS_CSV = BASE / "shopee_videos.csv"
VIDEO_DIR = BASE / "videos"
OUTPUT_JS = Path("/home/alessandro/bin/Git_Repo/BestPriceToday/tools/tiktok_post/tiktok_post.user.js")


def read_csv_auto(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as f:
        first = f.readline()
    sep = "\t" if "\t" in first else ","
    return pd.read_csv(path, sep=sep, dtype=str).rename(columns=lambda c: str(c).strip())


def pick_col(df: pd.DataFrame, *needles: str):
    for col in df.columns:
        low = str(col).lower()
        if any(n.lower() in low for n in needles):
            return col
    return None


def get_col(row: pd.Series, *names: str, default: str = "") -> str:
    for name in names:
        for key in row.index:
            if str(key).lower().strip() == str(name).lower().strip():
                val = row[key]
                if pd.isna(val):
                    continue
                val = str(val).strip()
                if val and val.lower() != "nan":
                    return val
    return default


def make_caption(row: pd.Series) -> str:
    nome = get_col(row, "nome", "item name", "name")[:80]
    preco = get_col(row, "preco", "price")
    orig = get_col(row, "preco_original")
    desc = get_col(row, "desconto_pct")

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

    offer_col = pick_col(df_af, "offer")
    if not offer_col:
        raise ValueError("Nao achei coluna com offer em shopee_products.csv")

    df_af["slug"] = (
        df_af[offer_col]
        .astype(str)
        .str.strip()
        .str.split("/")
        .str[-1]
    )

    # ── Fonte de slugs: shopee_videos.csv OU pasta videos/ ────
    VIDEO_DIR.mkdir(exist_ok=True)
    mp4_slugs = {f.stem for f in VIDEO_DIR.glob("*.mp4")}
    print(f"  Videos na pasta: {len(mp4_slugs)}")

    csv_slugs: set[str] = set()
    if PRODUTOS_CSV.exists():
        try:
            df_pr = read_csv_auto(PRODUTOS_CSV)
            if "slug" in df_pr.columns:
                csv_slugs = set(df_pr["slug"].dropna().str.strip())
            elif len(df_pr.columns) > 0:
                csv_slugs = set(df_pr.iloc[:, 0].dropna().str.strip())
        except Exception:
            pass

    # Usa união: slugs do CSV de vídeos + slugs dos MP4
    video_slugs = csv_slugs | mp4_slugs
    print(f"  Slugs do CSV: {len(csv_slugs)} | Slugs MP4: {len(mp4_slugs)} | Uniao: {len(video_slugs)}")

    if not video_slugs:
        print("  AVISO: nenhum slug de video encontrado. Usando todos os afiliados.")
        video_slugs = set(df_af["slug"].dropna().str.strip())

    df = df_af[df_af["slug"].isin(video_slugs)].copy()

    # Enriqueciona com dados do CSV de vídeos se disponível
    if csv_slugs:
        try:
            df_pr = read_csv_auto(PRODUTOS_CSV)
            slug_col_pr = "slug" if "slug" in df_pr.columns else df_pr.columns[0]
            df = df.merge(df_pr, left_on="slug", right_on=slug_col_pr, how="left")
        except Exception:
            pass

    produtos = []
    for _, row in df.iterrows():
        slug = str(row["slug"]).strip()
        produtos.append({
            "slug": slug,
            "video": f"{slug}.mp4",
            "offer_link": str(row[offer_col]).strip(),
            "caption": make_caption(row),
        })

    return produtos


JS_TEMPLATE = r"""// ==UserScript==
// @name         Bot TikTok Fiel v10
// @namespace    http://tampermonkey.net/
// @version      10.0
// @description  Bot TikTok com retry, confirmacao de publicacao, XPath flexivel
// @author       Alessandro
// @match        https://www.tiktok.com/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(async () => {
    if (window.__tt_bot_running__) return;
    window.__tt_bot_running__ = true;

    const PK = 'tt_progress';
    const SK = 'tt_state';
    const LISTA = __PRODUTOS_JSON__;
    const MAX_RETRIES = 3;

    const readLocal = (k, fb) => { try { const r = localStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } };
    const readSession = (k, fb) => { try { const r = sessionStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } };

    let progress = readLocal(PK, {});
    let state = readSession(SK, { current: { step: 'START', slug: null, retries: 0 }, history: [], future: [] });

    const saveState = (step, slug = state.current.slug, pushToHistory = true) => {
        if (pushToHistory && (state.history.length === 0 || state.history[state.history.length - 1].step !== state.current.step)) {
            state.history.push({ ...state.current });
            state.future = [];
        }
        state.current = { step, slug, retries: 0 };
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
        if (m) { m.innerText = msg; m.style.color = color; }
        console.log('[BOT]', status, '-', msg);
    };

    // ── XPath com múltiplos fallbacks ──────────────────────────
    const waitAnyXP = async (xpaths, timeout = 15000) => {
        const deadline = Date.now() + timeout;
        while (Date.now() < deadline) {
            for (const xp of xpaths) {
                try {
                    const el = document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (el && el.isConnected) return el;
                } catch (e) {}
            }
            await sleep(1000);
        }
        return null;
    };

    // ── Safe paste em contenteditable ──────────────────────────
    const safePaste = async (el, text) => {
        el.focus();
        el.click();
        await sleep(500);
        try {
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            const ev = new ClipboardEvent('paste', {
                bubbles: true, cancelable: true,
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
            bubbles: true, cancelable: true,
            inputType: 'insertText', data: text
        }));
        await sleep(1000);
    };

    // ── Detectar produto na página ─────────────────────────────
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
                for (const p of LISTA) {
                    if (txt.includes(p.slug)) return p;
                }
            }
        } catch (e) {}
        return null;
    };

    // ── Painel UI ──────────────────────────────────────────────
    if (!document.getElementById('bot-panel')) {
        const panel = document.createElement('div');
        panel.id = 'bot-panel';
        panel.style = 'position:fixed;top:10px;right:10px;z-index:999999;background:rgba(0,0,0,0.9);color:#0f0;padding:15px;border:1px solid #ff0050;font-family:monospace;width:340px;border-radius:8px;box-shadow:0 0 10px #ff0050;';
        panel.innerHTML = `
            <h4 style="color:#ff0050;margin:0">BOT TIKTOK v10</h4>
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

    // ── Loop principal ─────────────────────────────────────────
    while (true) {
        state = readSession(SK, { current: { step: 'START', slug: null, retries: 0 }, history: [], future: [] });

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

                // ── START ────────────────────────────────────────
                case 'START': {
                    if (!location.pathname.includes('/upload')) {
                        navigateTo(
                            'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                            'AGUARDAR_VIDEO', null
                        );
                        return;
                    }
                    saveState('AGUARDAR_VIDEO', null, false);
                    await sleep(2000);
                    break;
                }

                // ── AGUARDAR_VIDEO ──────────────────────────────
                case 'AGUARDAR_VIDEO': {
                    const btnSel = await waitAnyXP([
                        '//*[@data-e2e="select_video_button"]',
                        '//button[contains(@aria-label,"elecionar")]',
                        '//button[contains(@aria-label,"elect")]',
                        '//span[contains(text(),"Selecionar")]/ancestor::button',
                    ], 15000);
                    if (!btnSel) throw new Error('Botao Selecionar Video nao encontrado');

                    log('Escolha o video na janela do Windows', 'AGUARDANDO USUARIO', '#0ff');
                    btnSel.click();

                    const campoTexto = await waitAnyXP([
                        '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                        '//div[@contenteditable="true"]',
                    ], 300000);
                    if (!campoTexto) throw new Error('Timeout: nenhum video selecionado');

                    log('Video detectado! Aguardando tela estabilizar...', 'AGUARDANDO', '#ff0');
                    await sleep(10000);

                    let produto = detectarProduto();
                    if (!produto) {
                        log('Nao identifiquei o video. Clique no produto correto:', 'ESCOLHA', '#ff0');
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
                        log(`Aviso: "${produto.slug}" ja foi postado.`, 'AVISO', '#ff0');
                    }

                    log(`Produto: ${produto.slug}`, 'IDENTIFICADO', '#0f0');
                    logProduto(produto);
                    saveState('POSTAR', produto.slug, true);
                    await sleep(1000);
                    break;
                }

                // ── POSTAR (com retry) ──────────────────────────
                case 'POSTAR': {
                    if (!produtoAtual) throw new Error('Produto nao identificado. Reinicie.');

                    let publicado = false;

                    for (let tentativa = 1; tentativa <= MAX_RETRIES && !publicado; tentativa++) {
                        if (tentativa > 1) {
                            log(`Retry ${tentativa}/${MAX_RETRIES}...`, 'RETRY', '#ff0');
                            await sleep(3000);
                        }

                        try {
                            const descBox = await waitAnyXP([
                                '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                                '//div[@contenteditable="true"]',
                            ], 30000);
                            if (!descBox) throw new Error('Campo de legenda nao encontrado');

                            log(`Preenchendo legenda (tentativa ${tentativa})...`, 'AGUARDANDO', '#ff0');
                            await safePaste(descBox, produtoAtual.caption);
                            await sleep(4000);

                            if ((descBox.textContent || '').trim().length < 5) {
                                throw new Error('Legenda ficou vazia');
                            }

                            // fechar dialog se aparecer
                            try {
                                for (const xp of [
                                    '//*[@id=":rbv:"]/div[1]/div/svg',
                                    '//div[starts-with(@id,":r")]/div[1]/div/svg',
                                    '//div[@role="dialog"]//svg',
                                ]) {
                                    const svg = document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                    if (svg) {
                                        const btn = svg.closest('button') || svg.closest('div[role="button"]') || svg.parentElement;
                                        if (btn) { btn.click(); await sleep(2000); }
                                        break;
                                    }
                                }
                            } catch (e) {}

                            const btnPub = await waitAnyXP([
                                '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[6]/div/button[1]',
                                '//button[contains(., "Publicar")]',
                                '//button[contains(., "Post")]',
                            ], 10000);
                            if (!btnPub) throw new Error('Botao Publicar nao encontrado');

                            btnPub.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            await sleep(2000);

                            log('Publicando video...', 'PUBLICANDO', '#0f0');
                            btnPub.click();

                            // ── Confirmar publicação ────────────
                            log('Aguardando confirmacao de publicacao...', 'CONFIRMANDO', '#ff0');
                            const confirmado = await new Promise(resolve => {
                                const deadline = Date.now() + 60000;
                                const check = setInterval(async () => {
                                    const url = location.href;
                                    const body = document.body.innerText;

                                    // sinais de sucesso
                                    if (
                                        url.includes('/creator-center') ||
                                        url.includes('/content') ||
                                        body.includes('Seu vídeo foi publicado') ||
                                        body.includes('Seu video foi publicado') ||
                                        body.includes('Publicado') ||
                                        body.includes('Your video has been posted')
                                    ) {
                                        clearInterval(check);
                                        resolve(true);
                                        return;
                                    }

                                    if (Date.now() > deadline) {
                                        clearInterval(check);
                                        resolve(false);
                                    }
                                }, 2000);
                            });

                            if (confirmado) {
                                log('Publicacao confirmada!', 'OK', '#0f0');
                                progress[produtoAtual.slug] = 'ok';
                                saveProgress();
                                publicado = true;
                            } else {
                                log('Timeout confirmando publicacao', 'TIMEOUT', '#f90');
                            }

                        } catch (stepErr) {
                            log(`Erro tentativa ${tentativa}: ${stepErr.message}`, 'ERRO', '#f00');
                        }
                    }

                    if (!publicado) {
                        throw new Error(`Falha ao publicar após ${MAX_RETRIES} tentativas`);
                    }

                    await sleep(5000);
                    saveState('IR_COMENTARIOS', produtoAtual.slug, true);
                    break;
                }

                // ── IR_COMENTARIOS ──────────────────────────────
                case 'IR_COMENTARIOS': {
                    log('Abrindo comentarios...', 'COMENTARIOS', '#0ff');

                    await sleep(3000);

                    const comentariosBtn = await waitAnyXP([
                        '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[2]/div/div/div[2]/div[2]/div[1]/div/div[3]/div/div/div[3]/div/div/div',
                    ], 20000);

                    if (comentariosBtn) {
                        log('Clicando no icone de comentarios...', 'COMENTARIOS', '#0ff');
                        comentariosBtn.click();
                        await sleep(4000);
                    } else {
                        log('Botao comentarios nao encontrado', 'AVISO', '#ff0');
                    }

                    saveState('ENVIAR_LINK', produtoAtual.slug, true);
                    break;
                }

                // ── ENVIAR_LINK ─────────────────────────────────
                case 'ENVIAR_LINK': {
                    if (!produtoAtual) throw new Error('Produto perdido');

                    log('Enviando link afiliado...', 'LINK', '#ff0');

                    const campoComentario = await waitAnyXP([
                        '//div[@contenteditable="true"]',
                        '//textarea',
                    ], 20000);

                    if (!campoComentario) {
                        throw new Error('Campo comentario nao encontrado');
                    }

                    await safePaste(campoComentario, produtoAtual.offer_link);
                    await sleep(600);

                    const enviarBtn = await waitAnyXP([
                        '//*[@id="root"]/div/div/div[2]/div[2]/div/div[2]/div[1]/div[2]/div[3]/div/div/button',
                        '//button[contains(@class,"css-")]//svg[contains(@viewBox,"0 0 48 48")]/ancestor::button',
                        '//button[@type="submit"]',
                        '//div[@role="button"][contains(., "Postar")]',
                    ], 10000);

                    if (enviarBtn) {
                        enviarBtn.click();
                        await sleep(3000);
                    }

                    log('Postagem finalizada!', 'OK', '#0f0');
                    saveState('START', null, true);
                    await sleep(5000);

                    navigateTo(
                        'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                        'AGUARDAR_VIDEO', null
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
})();"""


def main() -> None:
    produtos = build_products()
    js = JS_TEMPLATE.replace("__PRODUTOS_JSON__", json.dumps(produtos, ensure_ascii=False, indent=2))
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JS.write_text(js, encoding="utf-8")
    print(f"Gerado: {OUTPUT_JS}")
    print(f"Produtos: {len(produtos)}")


if __name__ == "__main__":
    main()
