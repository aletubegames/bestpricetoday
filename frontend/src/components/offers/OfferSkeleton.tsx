"use client"
import { motion } from "framer-motion"

const shimmer = `
  @keyframes shimmer {
    0% { background-position: -1000px 0 }
    100% { background-position: 1000px 0 }
  }
`

function SkeletonBlock({ w = "100%", h = 16, radius = 6 }: { w?: string | number; h?: number; radius?: number }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: radius,
      background: "linear-gradient(90deg, #f5f7ff 25%, #e0e0e0 50%, #f5f7ff 75%)",
      backgroundSize: "1000px 100%",
      animation: "shimmer 2s infinite linear",
    }} />
  )
}

export default function OfferSkeleton() {
  return (
    <>
      <style>{shimmer}</style>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
        gap: 16,
      }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <motion.div key={i}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            transition={{ delay: i * 0.05 }}
            style={{
              background: "#ffffff", border: "1px solid rgba(124,106,255,0.1)",
              borderRadius: 14, padding: 20, display: "flex", flexDirection: "column", gap: 14,
            }}
          >
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <SkeletonBlock w={80} h={80} radius={10} />
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                <SkeletonBlock h={14} />
                <SkeletonBlock w="80%" h={14} />
                <SkeletonBlock w="60%" h={14} />
              </div>
            </div>
            <SkeletonBlock h={36} />
            <div style={{ display: "flex", gap: 8 }}>
              <SkeletonBlock w="30%" h={22} radius={99} />
              <SkeletonBlock w="35%" h={22} radius={99} />
            </div>
            <SkeletonBlock h={44} radius={10} />
          </motion.div>
        ))}
      </div>
    </>
  )
}
