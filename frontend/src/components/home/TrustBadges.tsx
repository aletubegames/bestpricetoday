"use client";
import { IconShieldCheck, IconRefresh, IconLockCheck, IconInfoCircle } from "@tabler/icons-react";

interface Badge {
  icon: React.ReactNode;
  text: string;
  iconColor: string;
}

const BADGES: Badge[] = [
  { icon: <IconLockCheck size={22} stroke={1.5} />, text: "SSL seguro", iconColor: "#00b894" },
  { icon: <IconRefresh size={22} stroke={1.5} />, text: "Preços em tempo real", iconColor: "#f97316" },
  { icon: <IconShieldCheck size={22} stroke={1.5} />, text: "Compra protegida pela garantia da plataforma oficial", iconColor: "#00b894" },
  { icon: <IconInfoCircle size={22} stroke={1.5} />, text: "Afiliado — preço não muda", iconColor: "#6b6b8a" },
];

export default function TrustBadges() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
      {BADGES.map((badge) => (
        <div key={badge.text} style={{
          display: "flex", alignItems: "center", gap: 10,
          background: "#fff", border: "1px solid #e0e0f0", borderRadius: 14, padding: "14px 16px",
        }}>
          <span style={{ color: badge.iconColor, flexShrink: 0, display: "flex" }}>{badge.icon}</span>
          <span style={{ fontSize: 13, fontWeight: 500, color: "#3a3a5c", lineHeight: 1.4 }}>
            {badge.text}
          </span>
        </div>
      ))}
    </div>
  );
}
