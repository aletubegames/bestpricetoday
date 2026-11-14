#!/usr/bin/env python3
"""Watcher do Business Inbox da página Bestpricetoday — roda no alaserver.

Lê a caixa unificada (Messenger da página + comentários FB/IG), detecta
itens não lidos, grava na fila e dispara `devin -p` — o Devin responde
cordial, busca o produto no banco e manda o link /r/ (abre no link de
AFILIADO da loja).

Fluxo:
  inbox -> filtro "Não lidas" -> abre cada item -> extrai remetente/texto
  -> job JSON na fila -> devin -p -> fb_mkt_send responde como a página

Anti-detecção: xvfb-run (Chrome real), pausas humanas, kill switch se a
Meta pedir login/checkpoint.

Cron (com jitter): 3-7 */3 * * * * sleep $((RANDOM%90)) &&
  cd /home/alessandro/backend && xvfb-run -a venv/bin/python
  -m app.workers.fb_mkt_watcher >> fb_mkt_watcher.log 2>&1
"""
import hashlib, json, os, random, subprocess, sys, time

sys.path.insert(0, "/home/alessandro/backend")
from app.workers.fb_mkt_common import (
    BASE, QUEUE_DIR, h_sleep, tg_alert, load_state, save_state,
    open_browser, detect_block, pause_all, is_paused)

from playwright.sync_api import sync_playwright

ASSET = "1151428081393652"   # página Bestpricetoday
INBOX_URL = (f"https://business.facebook.com/latest/inbox/all"
             f"?asset_id={ASSET}")
DEVIN = "/home/alessandro/.local/bin/devin"
WORKDIR = "/home/alessandro/alaserver-bot"
MAX_ITEMS_PER_RUN = 6
MIN_REPLY_GAP_S = 240


FILTROS = ["Messenger", "Instagram", "WhatsApp",
           "Comentários do Facebook", "Comentários do Instagram"]


def item_id(texto):
    return hashlib.md5(texto[:160].encode()).hexdigest()[:12]


def sidebar_badges(page):
    """Filtros laterais com badge numérico = não lidos.
    Retorna [{'filtro', 'count'}]."""
    return page.evaluate("""(filtros) => {
      const out=[];
      for(const nome of filtros){
        const els=[...document.querySelectorAll('span,div,a')]
          .filter(e=>e.textContent.trim()===nome);
        for(const el of els){
          let box=el.parentElement;
          for(let i=0;i<4&&box;i++){
            const badge=[...box.querySelectorAll('span,div')]
              .find(b=>/^\\d{1,3}$/.test(b.textContent.trim()));
            if(badge){out.push({filtro:nome,count:badge.textContent.trim()});
                      i=9;break}
            box=box.parentElement;
          }
          if(out.length&&out[out.length-1].filtro===nome) break;
        }
      }
      return out;
    }""", FILTROS)


def click_filtro(page, nome):
    return page.evaluate("""(nome) => {
      const el=[...document.querySelectorAll('span,div,a')]
        .find(e=>e.textContent.trim()===nome);
      if(!el) return 'nf';
      let t=el;
      for(let i=0;i<8&&t;i++){
        if(t.tagName==='A'||t.getAttribute('role')==='link'
           ||t.getAttribute('role')==='button'||t.onclick){
          t.click();return 'clicked '+i}
        t=t.parentElement}
      el.click(); return 'span clicked';
    }""", nome)


def read_panel(page):
    """Lê a página após clicar no filtro — pega o body inteiro.
    O Devin separa o conteúdo da conversa do ruído do menu."""
    return page.evaluate("""() => {
      const lines=(document.body.innerText||'').split('\\n')
        .map(s=>s.trim()).filter(Boolean);
      return {name:'', tail:lines.slice(-70)};
    }""")


def trigger_devin(job):
    os.makedirs(QUEUE_DIR, exist_ok=True)
    fname = f"{int(time.time())}_{job['item_id']}.json"
    fpath = os.path.join(QUEUE_DIR, fname)
    with open(fpath, "w") as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    prompt = f"""Atendimento Caixa de Entrada Bestpricetoday — responda o cliente.

Leia {fpath} (JSON: nome, preview e últimas linhas da conversa/comentário).

1. Identifique o produto do contexto (título do post/anúncio/msgs).
2. Consulte Postgres: psql -h 127.0.0.1 -U bestpricetoday -d bestpricetoday
   Tabela affiliate_products — ILIKE pelo título; pegue price,
   affiliate_url, provider, id.
3. Crie o link curto rastreado (abre no AFILIADO da loja):
   curl -s -X POST https://api.alaserver.com.br/api/v1/links/create
     -H 'Content-Type: application/json' -d
     '{{"affiliate_url":"<affiliate_url>","provider":"<provider>",
        "product_title":"<titulo>","price":<preco>,
        "source":"fb_inbox","campaign":"inbox_bot"}}'
   Use o campo "url" (…/r/CODE) como link de compra.
4. Responda no inbox com:
   cd /home/alessandro/backend && xvfb-run -a venv/bin/python
     -m app.workers.fb_mkt_send "<filtro>" "<resposta>"
   O filtro é o campo "filtro" do JSON (ex: "Comentários do Facebook").

TOM: português BR, cordial, claro, 2-4 linhas, como um vendedor humano.
Responda a dúvida (preço/disponibilidade/como comprar) e feche com o link.
Frete/garantia/prazo = "confirma no anúncio da loja".

IDENTIDADE (regras duras — NUNCA viole):
- Se perguntarem quem somos/como funciona: "Trabalhamos como afiliados
  das lojas — Mercado Livre, Amazon, Shopee e outras. A gente garimpa
  os melhores preços e te passa o link direto da loja com o desconto."
- NUNCA diga que é bot, IA, automação, sistema ou robô — em hipótese
  nenhuma, mesmo se insistirem.
- NUNCA diga onde você está nem quem opera (sem nome, cidade, empresa).
- NÃO prometa o que não sabe. NUNCA responda sem ter criado o link /r/.

Se for spam/propaganda de outra loja ou não for sobre produto, NÃO
responda — só apague o arquivo da fila. Ao terminar, apague o arquivo."""
    try:
        subprocess.run(
            [DEVIN, "--respect-workspace-trust", "false",
             "--permission-mode", "dangerous", "--model", "swe-2-max",
             "-c", "-p", prompt],
            cwd=WORKDIR, timeout=900,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        tg_alert("⏱ FB INBOX: devin timeout — " + job.get("name", "?"))
    except Exception as e:
        tg_alert(f"⚠️ FB INBOX: falha ao disparar devin — {e}")


def main():
    if is_paused():
        print("pausado — saída silenciosa")
        return
    h_sleep(2, 20)
    st = load_state()
    with sync_playwright() as p:
        ctx, page = open_browser(p)
        try:
            page.goto(INBOX_URL, timeout=60000)
            h_sleep(8, 12)
            block = detect_block(page)
            if block:
                pause_all(block)
                tg_alert("🚫 FB INBOX PAUSADO — " + block
                         + ". Reautenticar e apagar .fb_mkt_paused")
                return
            badges = sidebar_badges(page)
            print("badges:", badges)
            for b in badges[:MAX_ITEMS_PER_RUN]:
                click_filtro(page, b["filtro"])
                h_sleep(5, 8)
                info = read_panel(page)
                block = detect_block(page)
                if block:
                    pause_all(block)
                    tg_alert("🚫 FB INBOX PAUSADO — " + block)
                    return
                txt = "\n".join(info.get("tail", []))
                iid = item_id(txt)
                if time.time() - st["replied"].get(iid, 0) < MIN_REPLY_GAP_S:
                    continue
                job = {
                    "item_id": iid, "filtro": b["filtro"],
                    "name": info.get("name", ""),
                    "tail": info.get("tail", []),
                    "ts": int(time.time()),
                }
                st["replied"][iid] = int(time.time())
                save_state(st)
                trigger_devin(job)
                h_sleep(15, 60)
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
