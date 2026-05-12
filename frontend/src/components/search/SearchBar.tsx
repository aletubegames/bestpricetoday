"use client";
import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Search, X, Loader2 } from "lucide-react";

const SUGGESTIONS = [
  "iPhone 15 128GB",
  "Nike Air Force 42",
  "Notebook i7 16GB",
  "AirPods Pro",
  "PS5 controle",
  "Monitor 24 polegadas",
];

interface Props {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export default function SearchBar({ onSearch, isLoading }: Props) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setValue(v);
    clearTimeout(debounceRef.current);
    if (v.length >= 3) {
      debounceRef.current = setTimeout(() => onSearch(v), 600);
    }
  };

  const handleClear = () => {
    setValue("");
    onSearch("");
    inputRef.current?.focus();
  };

  const handleSuggestion = (s: string) => {
    setValue(s);
    onSearch(s);
    setFocused(false);
  };

  return (
    <div className="relative w-full">
      <motion.div
        animate={{ boxShadow: focused ? "0 0 0 2px rgba(14,165,233,0.4)" : "0 0 0 1px rgba(255,255,255,0.08)" }}
        className="flex items-center gap-3 px-4 py-3.5 rounded-2xl bg-surface-50 transition-all"
      >
        {isLoading
          ? <Loader2 size={20} className="text-brand-400 animate-spin shrink-0" />
          : <Search size={20} className="text-white/30 shrink-0" />
        }
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          placeholder="Nike Air Force tamanho 42..."
          className="flex-1 bg-transparent outline-none text-white placeholder:text-white/25 text-base"
        />
        {value && (
          <button onClick={handleClear} className="text-white/30 hover:text-white transition-colors">
            <X size={18} />
          </button>
        )}
      </motion.div>

      {/* Suggestions */}
      {focused && !value && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-full left-0 right-0 mt-2 rounded-xl bg-surface-100 border border-white/5 overflow-hidden z-50 shadow-2xl"
        >
          <p className="px-4 py-2.5 text-xs text-white/30 font-medium uppercase tracking-wider">Sugestões</p>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleSuggestion(s)}
              className="w-full text-left px-4 py-3 text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2"
            >
              <Search size={14} className="text-white/20" />
              {s}
            </button>
          ))}
        </motion.div>
      )}
    </div>
  );
}
