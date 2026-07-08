"use client";
import { IconShieldCheck, IconRefresh, IconLockCheck, IconInfoCircle } from "@tabler/icons-react";
import styles from "./TrustBadges.module.css";

interface Badge {
  icon: React.ReactNode;
  text: string;
  iconColor: string;
}

const BADGES: Badge[] = [
  { icon: <IconLockCheck size={22} stroke={1.5} />, text: "SSL seguro", iconColor: "#00b894" },
  { icon: <IconRefresh size={22} stroke={1.5} />, text: "Preços em tempo real", iconColor: "#f97316" },
  { icon: <IconShieldCheck size={22} stroke={1.5} />, text: "Histórico de preços — fugimos de promoção fake", iconColor: "#7c3aed" },
  { icon: <IconInfoCircle size={22} stroke={1.5} />, text: "Link de afiliado — você paga o mesmo, sem taxa extra", iconColor: "#1a1a2e" },
];

export default function TrustBadges() {
  return (
    <div className={styles.grid}>
      {BADGES.map((badge) => (
        <div key={badge.text} className={styles.badge}>
          <span className={styles.icon} style={{ color: badge.iconColor }}>{badge.icon}</span>
          <span className={styles.text}>
            {badge.text}
          </span>
        </div>
      ))}
    </div>
  );
}
