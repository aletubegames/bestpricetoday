"use client";
import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, Loader2 } from "lucide-react";
import { useTrendingSearches } from "@/hooks/useTrendingSearches";
import styles from "./SearchBar.module.css";

interface Props {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export default function SearchBar({ onSearch, isLoading }: Props) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debRef = useRef<NodeJS.Timeout>();
  const { data: trendingData } = useTrendingSearches(12);
  const suggestions = trendingData?.items ?? [];

  const submit = (v: string) => { onSearch(v); setFocused(false); };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setValue(v);
    clearTimeout(debRef.current);
    if (v.length >= 3) debRef.current = setTimeout(() => submit(v), 500);
    else if (!v) onSearch("");
  };

  return (
    <div className={styles.root}>
      <motion.form
        className={styles.form}
        onSubmit={(e) => { e.preventDefault(); if (value.length >= 2) submit(value); }}
        animate={{
          boxShadow: focused
            ? "0 0 0 2px rgba(124,106,255,0.5), 0 8px 40px rgba(124,106,255,0.15)"
            : "0 0 0 1px rgba(108,92,231,0.15)",
        }}
      >
        {isLoading
          ? <Loader2 size={20} className={`${styles.icon} ${styles.spinner}`} />
          : <Search size={20} className={styles.icon} />
        }
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          placeholder="Ex: iPhone 16 Pro, Nike 42, RTX 4070..."
          className={styles.input}
        />
        {value && (
          <button type="button" aria-label="Limpar busca" onClick={() => { setValue(""); onSearch(""); inputRef.current?.focus(); }}
            className={styles.clearBtn}>
            <X size={18} />
          </button>
        )}
      </motion.form>

      {/* Suggestions */}
      <AnimatePresence>
        {focused && !value && suggestions.length > 0 && (
          <motion.div
            className={styles.suggestions}
            initial={{ opacity: 0, y: -8, scale: .98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: .98 }}
            transition={{ duration: .15 }}
          >
            <p className={styles.suggestionsTitle}>
              🔥 Em alta agora
            </p>
            {suggestions.map((item, i) => (
              <motion.button key={item.query}
                className={styles.suggestionItem}
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .025 }}
                onClick={() => { setValue(item.query); submit(item.query); }}
              >
                <Search size={13} style={{ color: "var(--muted2)", flexShrink: 0 }} />
                {item.query}
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
