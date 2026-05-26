"use client";

import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getChartData } from "@/lib/mockData";

export default function SearchesChart() {
  const data = getChartData();
  const maxVal = Math.max(...data.map((d) => d.value));
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ background: "#fff", border: "1px solid #e0e0f0", borderRadius: 16, padding: "24px 16px" }}>
      <h3
        style={{
          fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
          fontSize: 18,
          fontWeight: 800,
          color: "#1a1a2e",
          marginBottom: 4,
        }}
      >
        Buscas nos últimos 7 dias
      </h3>
      <p style={{ fontSize: 12, color: "rgba(26,26,46,0.45)", marginBottom: 20 }}>
        Quantidade de pesquisas realizadas por dia
      </p>

      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 4,
          height: 160,
        }}
      >
        {data.map((d, i) => {
          const pct = maxVal > 0 ? (d.value / maxVal) * 100 : 0;
          return (
            <div
              key={d.day}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4,
                height: "100%",
                justifyContent: "flex-end",
              }}
            >
              {/* Valor acima */}
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: "#7c3aed",
                  marginBottom: 2,
                }}
              >
                {visible ? d.value : 0}
              </span>

              {/* Barra */}
              <div
                style={{
                  width: "100%",
                  maxWidth: 48,
                  borderRadius: 8,
                  overflow: "hidden",
                  position: "relative",
                  flex: 1,
                }}
              >
                <motion.div
                  initial={{ height: 0 }}
                  animate={visible ? { height: `${pct}%` } : { height: 0 }}
                  transition={{ delay: 0.1 + i * 0.08, duration: 0.6, ease: "easeOut" }}
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    background: "linear-gradient(180deg, #a78bfa 0%, #7c3aed 100%)",
                    borderRadius: 8,
                  }}
                />
              </div>

              {/* Label abaixo */}
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 500,
                  color: "rgba(26,26,46,0.45)",
                  marginTop: 4,
                }}
              >
                {d.day}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
