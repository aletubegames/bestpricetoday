"use client";
import { motion } from "framer-motion";
import OfferCard from "./OfferCard";
import type { Offer } from "@/types";

export default function OfferGrid({ offers }: { offers: Offer[] }) {
  if (!offers.length) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      style={{ textAlign: "center", padding: "80px 20px" }}>
      <p style={{ fontSize: 48, marginBottom: 12 }}>🔍</p>
      <p style={{ color: "var(--muted)", fontSize: 15 }}>Nenhum resultado encontrado.</p>
      <p style={{ color: "var(--muted2)", fontSize: 13, marginTop: 6 }}>Tente um termo diferente</p>
    </motion.div>
  );

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
      {offers.map((offer, i) => <OfferCard key={`${offer.provider}-${i}`} offer={offer} rank={i} />)}
    </div>
  );
}
