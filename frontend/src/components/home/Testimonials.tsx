"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getTestimonials, type Review } from "@/lib/mockData";

function StarRating({ count }: { count: number }) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          style={{ fontSize: 14, color: i < count ? "#f59e0b" : "#ddd" }}
        >
          ★
        </span>
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e0e0f0",
        borderRadius: 16,
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        height: "100%",
        boxSizing: "border-box",
      }}
    >
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

      <StarRating count={review.stars} />

      <p
        style={{
          fontSize: 13,
          lineHeight: 1.6,
          color: "#3a3a5c",
          margin: 0,
          fontStyle: "italic",
          flex: 1,
        }}
      >
        &ldquo;{review.text}&rdquo;
      </p>

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
    </div>
  );
}

export default function Testimonials() {
  const reviews = getTestimonials();
  const itemsPerPage = 3;
  const totalPages = Math.ceil(reviews.length / itemsPerPage);
  const [page, setPage] = useState(0);
  const [direction, setDirection] = useState(0);

  const paginate = useCallback(
    (newDirection: number) => {
      setDirection(newDirection);
      setPage((prev) => {
        const next = prev + newDirection;
        if (next < 0) return totalPages - 1;
        if (next >= totalPages) return 0;
        return next;
      });
    },
    [totalPages]
  );

  const visible = reviews.slice(
    page * itemsPerPage,
    page * itemsPerPage + itemsPerPage
  );

  return (
    <div>
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
        <p style={{ fontSize: 14, color: "rgba(26,26,46,0.5)", marginBottom: 10 }}>
          Pessoas reais economizando de verdade
        </p>
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

      {/* Carousel */}
      <div style={{ position: "relative" }}>
        {/* Nav buttons */}
        {totalPages > 1 && (
          <>
            <button
              onClick={() => paginate(-1)}
              style={{
                position: "absolute",
                left: -16,
                top: "50%",
                transform: "translateY(-50%)",
                zIndex: 2,
                width: 40,
                height: 40,
                borderRadius: "50%",
                border: "1px solid #e0e0f0",
                background: "#fff",
                fontSize: 16,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#7c3aed",
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                transition: "all .15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "#7c3aed";
                e.currentTarget.style.boxShadow = "0 4px 16px rgba(124,58,237,0.15)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "#e0e0f0";
                e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.06)";
              }}
            >
              ←
            </button>
            <button
              onClick={() => paginate(1)}
              style={{
                position: "absolute",
                right: -16,
                top: "50%",
                transform: "translateY(-50%)",
                zIndex: 2,
                width: 40,
                height: 40,
                borderRadius: "50%",
                border: "1px solid #e0e0f0",
                background: "#fff",
                fontSize: 16,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#7c3aed",
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                transition: "all .15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "#7c3aed";
                e.currentTarget.style.boxShadow = "0 4px 16px rgba(124,58,237,0.15)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "#e0e0f0";
                e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.06)";
              }}
            >
              →
            </button>
          </>
        )}

        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={page}
            custom={direction}
            initial={{ opacity: 0, x: direction > 0 ? 60 : -60 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction > 0 ? -60 : 60 }}
            transition={{ duration: 0.3 }}
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${Math.min(itemsPerPage, visible.length)}, 1fr)`,
              gap: 16,
            }}
          >
            {visible.map((review) => (
              <ReviewCard key={review.name} review={review} />
            ))}
          </motion.div>
        </AnimatePresence>

        {/* Dots */}
        {totalPages > 1 && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 8,
              marginTop: 16,
            }}
          >
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={() => {
                  setDirection(i > page ? 1 : -1);
                  setPage(i);
                }}
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  border: "none",
                  background: i === page ? "#7c3aed" : "#e0e0f0",
                  cursor: "pointer",
                  transition: "background .2s",
                }}
              />
            ))}
          </div>
        )}
      </div>

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
