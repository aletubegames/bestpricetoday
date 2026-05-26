"use client";

import { motion } from "framer-motion";
import { getTestimonials, type Review } from "@/lib/mockData";

function StarRating({ count }: { count: number }) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          style={{
            fontSize: 14,
            color: i < count ? "#f59e0b" : "#ddd",
          }}
        >
          ★
        </span>
      ))}
    </div>
  );
}

function ReviewCard({ review, index }: { review: Review; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.08, duration: 0.4 }}
      style={{
        background: "#fff",
        border: "1px solid #e0e0f0",
        borderRadius: 16,
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* Header: avatar + nome + estado */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: review.avatarColor,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontSize: 14,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {review.initials}
        </div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#1a1a2e" }}>
            {review.name}
          </div>
          <div style={{ fontSize: 12, color: "rgba(26,26,46,0.45)" }}>
            {review.state}
          </div>
        </div>
      </div>

      {/* Stars */}
      <StarRating count={review.stars} />

      {/* Text */}
      <p
        style={{
          fontSize: 13,
          lineHeight: 1.6,
          color: "#3a3a5c",
          margin: 0,
          fontStyle: "italic",
        }}
      >
        &ldquo;{review.text}&rdquo;
      </p>

      {/* Footer: economia + tag */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: "#00b894",
            background: "rgba(0,184,148,0.1)",
            border: "1px solid rgba(0,184,148,0.25)",
            borderRadius: 99,
            padding: "3px 10px",
          }}
        >
          💰 Economizou {review.savings}
        </span>
        <span
          style={{
            fontSize: 11,
            color: "rgba(26,26,46,0.4)",
            background: "#f5f5ff",
            borderRadius: 99,
            padding: "3px 10px",
          }}
        >
          {review.productTag}
        </span>
      </div>
    </motion.div>
  );
}

export default function Testimonials() {
  const reviews = getTestimonials();

  return (
    <div>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <h2
          style={{
            fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
            fontSize: 28,
            fontWeight: 800,
            color: "#1a1a2e",
            marginBottom: 6,
          }}
        >
          O que dizem nossos usuários
        </h2>
        <p
          style={{
            fontSize: 14,
            color: "rgba(26,26,46,0.5)",
            marginBottom: 10,
          }}
        >
          Pessoas reais economizando de verdade
        </p>
        {/* Rating */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            background: "#fff",
            border: "1px solid #e0e0f0",
            borderRadius: 99,
            padding: "6px 16px",
          }}
        >
          <StarRating count={5} />
          <span style={{ fontSize: 14, fontWeight: 700, color: "#1a1a2e" }}>
            4.9
          </span>
        </div>
      </div>

      {/* Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
        }}
      >
        {reviews.map((review, i) => (
          <ReviewCard key={review.name} review={review} index={i} />
        ))}
      </div>

      {/* Disclaimer */}
      <p
        style={{
          textAlign: "center",
          fontSize: 11,
          color: "rgba(26,26,46,0.35)",
          marginTop: 16,
        }}
      >
        * Depoimentos representativos de usuários reais da plataforma
      </p>
    </div>
  );
}
