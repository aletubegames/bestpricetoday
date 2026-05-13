"use client";
import { motion } from "framer-motion";

function Sk() {
  return (
    <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div className="sk" style={{ width: 100, height: 22, borderRadius: 99 }} />
        <div className="sk" style={{ width: 60, height: 22, borderRadius: 99 }} />
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <div className="sk" style={{ width: 72, height: 72, borderRadius: 12, flexShrink: 0 }} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="sk" style={{ height: 13, width: "90%" }} />
          <div className="sk" style={{ height: 13, width: "75%" }} />
          <div className="sk" style={{ height: 13, width: "60%" }} />
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div className="sk" style={{ height: 12, width: 60 }} />
          <div className="sk" style={{ height: 36, width: 140 }} />
        </div>
        <div className="sk" style={{ width: 52, height: 52, borderRadius: 12 }} />
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <div className="sk" style={{ height: 22, width: 90, borderRadius: 99 }} />
        <div className="sk" style={{ height: 22, width: 60, borderRadius: 99 }} />
      </div>
      <div className="sk" style={{ height: 46, borderRadius: 12 }} />
    </div>
  );
}

export default function OfferSkeleton() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
      {Array.from({ length: 8 }).map((_, i) => <Sk key={i} />)}
    </motion.div>
  );
}
