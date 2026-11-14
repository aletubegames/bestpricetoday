#!/usr/bin/env python3
"""Watcher do inbox do Facebook/Marketplace — roda no alaserver via cron.

Detecta conversas não lidas (incl. Marketplace), grava na fila e dispara
`devin -p` (CLI no alaserver) que responde cordial + link /r/ de afiliado.

Anti-detecção:
- jitter aleatório na largada (o cron já tem, mas reforço aqui)
- Chromium real no Xvfb (headless=False), UA Chrome desktop
- pausas humanas entre ações
- se a Meta pedir login/checkpoint: pausa tudo e alerta no Telegram
  (nunca tenta burlar — é o que derruba conta)

Uso: DISPLAY=:99 venv/bin/python -m app.workers.fb_mkt_watcher
"""
import hashlib, json, os, random, subprocess, sys, time

sys.path.insert(0, "/home/alessandro/backend")
from app.workers.fb_mkt_common import (
    BASE, QUEUE_DIR, h_sleep, tg_alert, load_state, save_state,
    open_browser, detect_block, pause_all, is_paused)

from playwright.sync_api import sync_playwright

INBOX_URL = "https://www.messenger.com/"
DEVIN = "/home/alessandro/.local/bin/devin"
WORKDIR = "/home/alessandro/alaserver-bot"
MAX_THREADS_PER_RUN = 6          # não varrer tudo de uma vez
MIN_REPLY_GAP_S = 240            # não responde a mesma conversa <4min seguido


def conv_id_from_url(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]


def collect_threads(page):
    """Extrai threads da inbox: [{url, title, preview, unread}]."""
    page.goto(INBOX_URL, timeout=60000)
    h_sleep(6, 10)
    # marcação de conversas não lidas no messenger web muda bastante;
    # usamos heurística por aria-label + texto em negrito (font-weight)
    return page.evaluate("""() => {
      const out = [];
      const items = document.querySelectorAll('[role="row"], a[href*="/t/"]');
      for (const el of items) {
        const a = el.tagName === 'A' ? el : el.querySelector('a[href*="/t/"]');
        if (!a) continue;
        const txt = (el.innerText || a.innerText || '').trim();
        if (!txt) continue;
        const bold = [...el.querySelectorAll('*')].some(n =>
          parseInt(getComputedStyle(n).fontWeight) >= 600 && n.innerText);
        const unread = bold
          || /unread|não lida|nao lida/i.test(el.getAttribute('aria-label') || '');
        out.push({url: a.href, text: txt.slice(0, 400), unread});
      }
      const seen = new Set();
      return out.filter(t => !seen.has(t.url) && seen.add(t.url));
    }""")


def read_thread(page, url):
    """Abre a conversa e extrai {name, item_title, messages[]}."""
    page.goto(url, timeout=60000)
    h_sleep(4, 7)
    return page.evaluate("""() => {
      const body = document.body.innerText || '';
      // mensagens: bolhas têm role/estrutura variável — pego os últimos
      // blocos de texto da área principal
      const main = document.querySelector('[role="main"]') || document.body;
      const lines = (main.innerText || '').split('\\n')
        .map(s => s.trim()).filter(Boolean);
      // nome da conversa = primeiro heading
      const h = main.querySelector('h1,h2,[dir="auto"]');
      return {
        name: h ? h.innerText.trim().slice(0, 80) : '',
        item_title: '',            // preenchido por heurística abaixo
        tail: lines.slice(-40),    // últimas 40 linhas do chat
      };
    }""")


def trigger_devin(job):
    os.makedirs(QUEUE_DIR, exist_ok=True)
    fname = f"{int(time.time())}_{job['conv_id']}.json"
    fpath = os.path.join(QUEUE_DIR, fname)
    with open(fpath, "w") as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    prompt = f"""Atendimento Facebook Marketplace — responda o cliente.

Leia o arquivo {fpath} (JSON com nome do cliente, url da conversa e
últimas mensagens). Depois:

1. Identifique o produto citado (título do anúncio / contexto das msgs).
2. Consulte o Postgres local: psql -h 127.0.0.1 -U bestpricetoday
   -d bestpricetoday, tabela affiliate_products (busque por título
   aproximado com ILIKE, pegue price, affiliate_url, product_url).
3. Crie o link curto rastreado:
   curl -s -X POST https://api.alaserver.com.br/api/v1/links/create
     -H 'Content-Type: application/json' -d
     '{{"affiliate_url":"<affiliate_url>","provider":"<provider>",
        "product_title":"<titulo>","price":<preco>,
        "source":"fb_marketplace","campaign":"mkt_bot"}}'
   O campo "url" retornado (…/r/CODE) é o link de compra — ele abre
   direto no link de AFILIADO da loja.
4. Responda o cliente com:
   venv/bin/python -m app.workers.fb_mkt_send "<conv_url>" "<resposta>"
   (cwd=/home/alessandro/backend, DISPLAY=:99 — só UMA resposta curta)

REGRAS de tom: português BR, cordial e breve (2-4 linhas), como vendedor
humano. Responda o que perguntou (preço/disponibilidade/frete). Sempre
feche com o link de compra. NÃO prometa o que não sabe (frete/garantia =
"verifica no anúncio da loja"). NUNCA envie link sem ter criado o /r/.
Se a conversa não for sobre produto (spam, saudação solta), NÃO responda —
apenas apague o arquivo da fila. Ao terminar, apague o arquivo da fila."""
    try:
        subprocess.run(
            [DEVIN, "--respect-workspace-trust", "false",
             "--permission-mode", "smart", "--model", "swe-2-max",
             "-c", "-p", prompt],
            cwd=WORKDIR, timeout=900,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        tg_alert("⏱ FB MKT: devin timeout respondendo "
                 + job.get("name", "?"))
    except Exception as e:
        tg_alert(f"⚠️ FB MKT: falha ao disparar devin — {e}")


def main():
    if is_paused():
        print("pausado (checkpoint anterior) — saída silenciosa")
        return
    h_sleep(2, 20)  # jitter extra além do cron
    st = load_state()
    with sync_playwright() as p:
        ctx, page = open_browser(p)
        try:
            threads = collect_threads(page)
            block = detect_block(page)
            if block:
                pause_all(block)
                tg_alert("🚫 FB MKT PAUSADO — Meta pediu " + block
                         + ". Reautenticar sessão e apagar .fb_mkt_paused")
                return
            unread = [t for t in threads if t.get("unread")]
            print(f"threads={len(threads)} unread={len(unread)}")
            for t in unread[:MAX_THREADS_PER_RUN]:
                cid = conv_id_from_url(t["url"])
                last_seen = st["seen"].get(cid, 0)
                last_reply = st["replied"].get(cid, 0)
                if time.time() - last_reply < MIN_REPLY_GAP_S:
                    continue
                if time.time() - last_seen < 60:
                    continue  # já processado nessa janela
                info = read_thread(page, t["url"])
                block = detect_block(page)
                if block:
                    pause_all(block)
                    tg_alert("🚫 FB MKT PAUSADO — " + block)
                    return
                job = {
                    "conv_id": cid, "conv_url": t["url"],
                    "name": info.get("name") or t["text"].split("\n")[0],
                    "thread_preview": t["text"],
                    "tail": info.get("tail", []),
                    "ts": int(time.time()),
                }
                st["seen"][cid] = int(time.time())
                st["replied"][cid] = int(time.time())
                save_state(st)
                trigger_devin(job)
                h_sleep(15, 60)  # pausa humana entre conversas
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
