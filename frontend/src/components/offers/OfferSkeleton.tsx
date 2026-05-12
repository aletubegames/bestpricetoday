"use client";
import { motion } from "framer-motion";

function SkeletonCard() {
  return (
    <div className="glass rounded-2xl p-4 flex flex-col gap-4">
      <div className="flex gap-3">
        <div className="skeleton w-16 h-16 shrink-0" />
        <div className="flex-1 flex flex-col gap-2">
          <div className="skeleton h-4 w-20" />
          <div className="skeleton h-3 w-full" />
          <div className="skeleton h-3 w-3/4" />
        </div>
      </div>
      <div className="skeleton h-8 w-32" />
      <div className="flex gap-2">
        <div className="skeleton h-5 w-20" />
        <div className="skeleton h-5 w-16" />
      </div>
      <div className="skeleton h-10 w-full rounded-xl" />
    </div>
  );
}

export default function OfferSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
    >
      {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
    </motion.div>
  );
}
