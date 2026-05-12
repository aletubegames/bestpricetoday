"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import SearchBar from "@/components/search/SearchBar";
import OfferGrid from "@/components/offers/OfferGrid";
import OfferSkeleton from "@/components/offers/OfferSkeleton";
import { useSearch } from "@/hooks/useSearch";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const { data, isLoading, error } = useSearch(query);

  return (
    <main className="min-h-screen bg-[#0a0a0a]">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-4 pt-20 pb-12">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-6">
            <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
            Comparando preços em tempo real
          </div>
          <h1 className="text-4xl sm:text-6xl font-bold tracking-tight mb-4 bg-gradient-to-br from-white to-white/50 bg-clip-text text-transparent">
            Menor preço do Brasil,<br />
            <span className="text-brand-400">na sua mão</span>
          </h1>
          <p className="text-white/40 text-lg max-w-md mx-auto">
            Busca automática em Mercado Livre, Amazon, Shopee, KaBuM e mais. Com cupons e cashback.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="w-full max-w-2xl"
        >
          <SearchBar onSearch={setQuery} isLoading={isLoading} />
        </motion.div>

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex gap-6 mt-8 text-white/30 text-sm"
        >
          <span>7 lojas</span>
          <span>•</span>
          <span>Cupons automáticos</span>
          <span>•</span>
          <span>Histórico de preços</span>
          <span>•</span>
          <span>Alertas grátis</span>
        </motion.div>
      </section>

      {/* Results */}
      <section className="px-4 pb-20 max-w-7xl mx-auto">
        <AnimatePresence mode="wait">
          {isLoading && <OfferSkeleton key="skeleton" />}
          {error && (
            <motion.p key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-red-400 mt-10">
              Erro ao buscar. Tente novamente.
            </motion.p>
          )}
          {data && !isLoading && (
            <motion.div key="results" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
              <div className="flex items-center justify-between mb-6">
                <p className="text-white/50 text-sm">
                  {data.total} ofertas encontradas em {data.took_ms}ms
                  {data.cached && <span className="ml-2 px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 text-xs">cache</span>}
                </p>
              </div>
              <OfferGrid offers={data.offers} />
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </main>
  );
}
