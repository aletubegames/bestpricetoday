"use client";
import { motion } from "framer-motion";
import OfferCard from "./OfferCard";
import type { Offer } from "@/types";
import styles from "./OfferGrid.module.css";

interface Props {
  offers: Offer[];
  onCompare?: (offer: Offer) => void;
  compareSelected?: string[];
}

export default function OfferGrid({ offers, onCompare, compareSelected = [] }: Props) {
  if (!offers.length) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className={styles.empty}>
      <p style={{ fontSize: 48, marginBottom: 12 }}>🔍</p>
      <p style={{ color: "var(--muted)", fontSize: 15 }}>Nenhum resultado encontrado.</p>
      <p style={{ color: "var(--muted2)", fontSize: 13, marginTop: 6 }}>Tente um termo diferente</p>
    </motion.div>
  );

  return (
    <div className={`cq ${styles.grid}`}>
      {offers.map((offer, i) => (
        <OfferCard
          key={`${offer.provider}-${i}`}
          offer={offer}
          rank={i}
          onCompare={onCompare}
          isSelected={compareSelected.includes(offer.affiliate_url || "")}
        />
      ))}
    </div>
  );
}
