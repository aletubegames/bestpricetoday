"use client";
import OfferCard from "./OfferCard";
import type { Offer } from "@/types";

export default function OfferGrid({ offers }: { offers: Offer[] }) {
  if (!offers.length) return (
    <p className="text-center text-white/30 mt-20 text-lg">Nenhum resultado encontrado.</p>
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {offers.map((offer, i) => (
        <OfferCard key={`${offer.provider}-${i}`} offer={offer} rank={i} />
      ))}
    </div>
  );
}
