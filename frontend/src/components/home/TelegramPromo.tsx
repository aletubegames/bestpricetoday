"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, X } from "lucide-react";
import { trackEvent, trackPixelEvent } from "@/lib/analytics";

const TG_URL = "https://t.me/bestpricetodayBr";
const DISMISS_KEY = "bpt_tg_popup_dismissed"; // localStorage (timestamp) — suprime por 7 dias
const SHOWN_KEY = "bpt_tg_popup_shown"; // sessionStorage — 1x por sessão
const SHOW_DELAY_MS = 8000;
const SCROLL_TRIGGER = 0.5;
const DISMISS_DAYS = 7;

export default function TelegramPromo() {
  const [open, setOpen] = useState(false);
  const shown = useRef(false);

  useEffect(() => {
    if (sessionStorage.getItem(SHOWN_KEY)) return;
    const dismissed = Number(localStorage.getItem(DISMISS_KEY) || 0);
    if (dismissed && Date.now() - dismissed < DISMISS_DAYS * 86400e3) return;

    const show = () => {
      if (shown.current) return;
      shown.current = true;
      sessionStorage.setItem(SHOWN_KEY, "1");
      setOpen(true);
      trackEvent("popup_show", { type: "telegram" });
    };

    const timer = setTimeout(show, SHOW_DELAY_MS);
    const onScroll = () => {
      const limit = document.documentElement.scrollHeight - window.innerHeight;
      if (limit > 0 && window.scrollY / limit >= SCROLL_TRIGGER) show();
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      clearTimeout(timer);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  const dismiss = () => {
    setOpen(false);
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    trackEvent("popup_dismiss", { type: "telegram" });
  };

  const join = () => {
    trackEvent("popup_click", { type: "telegram" });
    trackPixelEvent("Lead", { content_name: "telegram_channel", source: "site_popup" });
    setOpen(false);
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ opacity: 0, y: 24, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.97 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          role="dialog"
          aria-label="Canal de ofertas no Telegram"
          style={{
            position: "fixed",
            right: 16,
            bottom: 16,
            zIndex: 90,
            width: "min(340px, calc(100vw - 32px))",
            background: "var(--s1)",
            border: "1px solid var(--bd)",
            borderRadius: 16,
            boxShadow: "0 12px 40px rgba(26,26,46,0.16)",
            padding: 18,
          }}
        >
          <button
            onClick={dismiss}
            aria-label="Fechar"
            style={{
              position: "absolute",
              top: 10,
              right: 10,
              border: "none",
              background: "transparent",
              color: "var(--muted)",
              cursor: "pointer",
              padding: 4,
              display: "flex",
            }}
          >
            <X size={16} />
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
            <span
              style={{
                width: 42,
                height: 42,
                borderRadius: 12,
                background: "#229ed9",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                flexShrink: 0,
              }}
            >
              <Send size={20} />
            </span>
            <strong
              style={{
                fontFamily: "var(--font-syne)",
                fontSize: 16,
                fontWeight: 700,
                color: "var(--txt)",
                lineHeight: 1.25,
              }}
            >
              Ofertas direto no seu Telegram
            </strong>
          </div>

          <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.5, margin: "0 0 14px" }}>
            As melhores promoções do dia no canal — antes de esgotar. Grátis, sem spam.
          </p>

          <a
            href={TG_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={join}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              background: "#229ed9",
              color: "#fff",
              fontWeight: 700,
              fontSize: 14,
              padding: "11px 14px",
              borderRadius: 10,
              textDecoration: "none",
            }}
          >
            <Send size={15} /> Entrar no canal
          </a>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
