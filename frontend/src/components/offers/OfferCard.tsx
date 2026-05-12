"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import { ExternalLink, Tag, Truck, Star, TrendingDown, AlertTriangle } from "lucide-react";
import type { Offer } from "@/types";
import { cn } from "@/lib/utils";

const PROVIDER_COLORS: Record<string, string> = {
  mercadolivre: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  amazon: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  shopee: "bg-red-500/10 text-red-400 border-red-500/20",
  kabum: "bg-green-500/10 text-green-400 border-green-500/20",
  aliexpress: "bg-red-600/10 text-red-300 border-red-600/20",
  lomadee: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  awin: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

const PROVIDER_NAMES: Record<string, string> = {
  mercadolivre: "Mercado Livre",
  amazon: "Amazon",
  shopee: "Shopee",
  kabum: "KaBuM",
  aliexpress: "AliExpress",
  lomadee: "Lomadee",
  awin: "Awin",
};

interface Props {
  offer: Offer;
  rank: number;
}

export default function OfferCard({ offer, rank }: Props) {
  const colorClass = PROVIDER_COLORS[offer.provider] || "bg-white/5 text-white/60 border-white/10";
  const providerName = PROVIDER_NAMES[offer.provider] || offer.provider;
  const scoreColor = offer.score >= 70 ? "text-green-400" : offer.score >= 40 ? "text-yellow-400" : "text-red-400";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.05 }}
      whileHover={{ y: -2 }}
      className="glass rounded-2xl p-4 flex flex-col gap-4 hover:border-white/10 transition-all cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        {offer.image_url && (
          <div className="w-16 h-16 rounded-xl overflow-hidden bg-white/5 shrink-0">
            <img src={offer.image_url} alt={offer.title} className="w-full h-full object-cover" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", colorClass)}>
              {providerName}
            </span>
            {offer.is_fake_discount && (
              <span className="flex items-center gap-1 text-xs text-orange-400">
                <AlertTriangle size={10} /> Desconto suspeito
              </span>
            )}
          </div>
          <p className="text-sm text-white/70 line-clamp-2 leading-snug">{offer.title}</p>
        </div>
      </div>

      {/* Price block */}
      <div className="flex items-end justify-between">
        <div>
          {offer.original_price && offer.original_price > offer.price && (
            <p className="text-xs text-white/30 line-through">
              R$ {offer.original_price.toFixed(2)}
            </p>
          )}
          <p className="text-2xl font-bold text-white">
            R$ <span>{offer.final_price.toFixed(2)}</span>
          </p>
          {offer.economy > 0 && (
            <p className="flex items-center gap-1 text-xs text-green-400 mt-0.5">
              <TrendingDown size={11} /> Economia de R$ {offer.economy.toFixed(2)}
            </p>
          )}
        </div>
        <div className="text-right">
          <p className={cn("text-lg font-bold", scoreColor)}>{offer.score.toFixed(0)}</p>
          <p className="text-xs text-white/30">score</p>
        </div>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2">
        {offer.shipping_free && (
          <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
            <Truck size={10} /> Frete grátis
          </span>
        )}
        {offer.discount_percent > 0 && !offer.is_fake_discount && (
          <span className="flex items-center gap-1 text-xs text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded-full border border-brand-500/20">
            <Star size={10} /> -{offer.discount_percent.toFixed(0)}%
          </span>
        )}
        {offer.coupon_code && (
          <span className="flex items-center gap-1 text-xs text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">
            <Tag size={10} /> {offer.coupon_code}
          </span>
        )}
        {offer.cashback_percent > 0 && (
          <span className="text-xs text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded-full border border-yellow-500/20">
            {offer.cashback_percent}% cashback
          </span>
        )}
      </div>

      {/* CTA */}
      <a
        href={offer.affiliate_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-all group-hover:glow-blue"
      >
        Ver oferta <ExternalLink size={14} />
      </a>
    </motion.div>
  );
}
