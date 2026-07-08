"use client";

import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import styles from "./SearchesChart.module.css";

export interface ChartDay {
  day: string;
  value: number;
}

interface Props {
  data: ChartDay[];
}

export default function SearchesChart({ data }: Props) {
  const maxVal = Math.max(...data.map((d) => d.value), 1);
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
    <div ref={ref} className={styles.root}>
      <h3 className={styles.title}>
        Buscas nos últimos 7 dias
      </h3>
      <p className={styles.subtitle}>
        Quantidade de pesquisas realizadas por dia
      </p>

      <div className={styles.chart}>
        {data.map((d, i) => {
          const pct = maxVal > 0 ? (d.value / maxVal) * 100 : 0;
          return (
            <div key={d.day} className={styles.column}>
              <span className={styles.value}>{d.value}</span>
              <div className={styles.barWrap}>
                <motion.div
                  initial={{ height: 0 }}
                  animate={visible ? { height: `${pct}%` } : { height: 0 }}
                  transition={{ delay: 0.1 + i * 0.08, duration: 0.6, ease: "easeOut" }}
                  className={styles.bar}
                />
              </div>
              <span className={styles.label}>{d.day}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
