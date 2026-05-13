"use client";
import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, Loader2, ArrowRight } from "lucide-react";

const SUGGESTIONS = [
  "iPhone 16 Pro Max 256GB",
  "Nike Air Force 1 42",
  "Notebook Dell i7 16GB RAM",
  "AirPods Pro 2ª geração",
  "PS5 Slim + controle extra",
  "Monitor LG 27 4K IPS",
  "RTX 4070 Super 12GB",
  "Samsung Galaxy S24 Ultra",
];

interface Props {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export default function SearchBar({ onSearch, isLoading }: Props) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debRef = useRef<NodeJS.Timeout>();

  const submit = (v: string) => { onSearch(v); setFocused(false); };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setValue(v);
    clearTimeout(debRef.current);
    if (v.length >= 3) debRef.current = setTimeout(() => submit(v), 500);
    else if (!v) onSearch("");
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <motion.form
        onSubmit={(e) => { e.preventDefault(); if (value.length >= 2) submit(value); }}
        animate={{
          boxShadow: focused
            ? "0 0 0 2px rgba(124,106,255,0.5), 0 8px 40px rgba(124,106,255,0.15)"
            : "0 0 0 1px rgba(255,255,255,0.07)",
        }}
        style={{
          display: "flex", alignItems: "center", gap: 12,
          padding: "0 16px", height: 60,
          borderRadius: 16,
          background: "var(--s2)",
        }}
      >
        {isLoading
          ? <Loader2 size={20} style={{ color: "var(--acc)", flexShrink: 0, animation: "spin 1s linear infinite" }} />
          : <Search size={20} style={{ color: "var(--muted2)", flexShrink: 0 }} />
        }
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          placeholder="Ex: iPhone 16 Pro, Nike 42, RTX 4070..."
          style={{
            flex: 1, background: "none", border: "none", outline: "none",
            fontSize: 16, color: "var(--txt)", caretColor: "var(--acc)",
            minWidth: 0,
          }}
        />
        {value && (
          <button type="button" onClick={() => { setValue(""); onSearch(""); inputRef.current?.focus(); }}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted2)", padding: 4, borderRadius: 8, display: "flex", flexShrink: 0 }}>
            <X size={16} />
          </button>
        )}
        <button type="submit"
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "0 20px", height: 40, borderRadius: 12,
            border: "none", cursor: "pointer",
            fontSize: 14, fontWeight: 700,
            background: value ? "linear-gradient(135deg,#7c6aff,#a78bfa)" : "var(--s4)",
            color: value ? "#fff" : "var(--muted2)",
            flexShrink: 0,
            transition: "background .2s",
            whiteSpace: "nowrap",
          }}>
          Buscar <ArrowRight size={14} />
        </button>
      </motion.form>

      {/* Suggestions */}
      <AnimatePresence>
        {focused && !value && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: .98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: .98 }}
            transition={{ duration: .15 }}
            style={{
              position: "absolute", top: "calc(100% + 8px)", left: 0, right: 0,
              background: "var(--s2)", border: "1px solid var(--bd)",
              borderRadius: 16, overflow: "hidden", zIndex: 100,
              boxShadow: "0 20px 60px rgba(0,0,0,.6)",
            }}
          >
            <p style={{ padding: "12px 16px 8px", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--muted2)", borderBottom: "1px solid var(--bd)" }}>
              🔥 Em alta agora
            </p>
            {SUGGESTIONS.map((s, i) => (
              <motion.button key={s}
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .025 }}
                onClick={() => { setValue(s); submit(s); }}
                style={{
                  width: "100%", textAlign: "left", background: "none", border: "none",
                  padding: "12px 16px", cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 10,
                  fontSize: 14, color: "var(--muted)",
                  transition: "background .1s, color .1s",
                }}
                onMouseEnter={e => Object.assign(e.currentTarget.style, { background: "rgba(124,106,255,.07)", color: "var(--txt)" })}
                onMouseLeave={e => Object.assign(e.currentTarget.style, { background: "none", color: "var(--muted)" })}
              >
                <Search size={13} style={{ color: "var(--muted2)", flexShrink: 0 }} />
                {s}
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
