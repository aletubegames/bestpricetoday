"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getTestimonials, type Review } from "@/lib/mockData";
import styles from "./Testimonials.module.css";

function StarRating({ count }: { count: number }) {
  return (
    <div className={styles.stars}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span key={i} className={`${styles.star} ${i < count ? styles.starFilled : styles.starEmpty}`}>
          ★
        </span>
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.avatar} style={{ background: review.avatarColor }}>
          {review.initials}
        </div>
        <div>
          <div className={styles.name}>{review.name}</div>
          <div className={styles.state}>{review.state}</div>
        </div>
      </div>

      <StarRating count={review.stars} />

      <p className={styles.text}>
        &ldquo;{review.text}&rdquo;
      </p>

      <div className={styles.tags}>
        <span className={styles.savingsTag}>
          💰 Economizou {review.savings}
        </span>
        <span className={styles.productTag}>
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
  const [paused, setPaused] = useState(false);

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

  // Auto-rotate a cada 5 segundos
  useEffect(() => {
    if (paused || totalPages <= 1) return;
    const timer = setInterval(() => paginate(1), 5000);
    return () => clearInterval(timer);
  }, [paginate, paused, totalPages]);

  const visible = reviews.slice(
    page * itemsPerPage,
    page * itemsPerPage + itemsPerPage
  );

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          O que dizem nossos usuários
        </h2>
        <p className={styles.subtitle}>
          Depoimentos ilustrativos de economias reais
        </p>
        <div className={styles.ratingPill}>
          <StarRating count={5} />
          <span className={styles.ratingValue}>
            4.9
          </span>
        </div>
      </div>

      {/* Carousel */}
      <div className={styles.carousel}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}>
        {/* Nav buttons */}
        {totalPages > 1 && (
          <>
            <button
              onClick={() => paginate(-1)}
              aria-label="Depoimento anterior"
              className={`${styles.navBtn} ${styles.navBtnPrev}`}
            >
              ←
            </button>
            <button
              onClick={() => paginate(1)}
              aria-label="Próximo depoimento"
              className={`${styles.navBtn} ${styles.navBtnNext}`}
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
            className={styles.grid}
            style={{ gridTemplateColumns: `repeat(${Math.min(itemsPerPage, visible.length)}, 1fr)` }}
          >
            {visible.map((review) => (
              <ReviewCard key={review.name} review={review} />
            ))}
          </motion.div>
        </AnimatePresence>

        {/* Dots */}
        {totalPages > 1 && (
          <div className={styles.dots}>
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                aria-label={`Ir para depoimento ${i + 1}`}
                onClick={() => {
                  setDirection(i > page ? 1 : -1);
                  setPage(i);
                }}
                className={`${styles.dot} ${i === page ? styles.dotActive : ""}`}
              />
            ))}
          </div>
        )}
      </div>

      <p className={styles.disclaimer}>
        * Depoimentos ilustrativos baseados em economias típicas dos usuários
      </p>
    </div>
  );
}
