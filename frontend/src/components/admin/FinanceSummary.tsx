"use client";
import React, { useEffect, useState } from "react";
import { AlertTriangle, BadgeCheck, CheckCircle, Clock, LoaderCircle, Wallet } from "lucide-react";
import { API_BASE as API, apiFetch } from "@/lib/api";
import styles from "@/app/admin/page.module.css";

interface FinanceSnapshot {
  collected_at: string | null;
  period_until: string | null;
  estimated_earnings: number | null;
  confirmed_earnings: number | null;
  clicks: number | null;
  orders: number | null;
}
interface FinanceProvider {
  provider: string;
  source: string;
  record_count: number;
  estimated_commission: number | null;
  approved_commission: number | null;
  paid_commission: number | null;
  notes: string[];
  latest_snapshot: FinanceSnapshot | null;
  historical_snapshot: FinanceSnapshot | null;
}
interface FinanceReport {
  period_days: number;
  period_start: string;
  period_end: string;
  partial: boolean;
  totals: {
    estimated_commission: number | null;
    approved_commission: number | null;
    paid_commission: number | null;
  };
  providers: FinanceProvider[];
  notes: string[];
}

const SOURCE_LABELS: Record<string, string> = {
  conversion_events: "Conversões registradas",
  affiliate_metrics_snapshots: "Relatórios do portal",
  unavailable: "Sem fonte integrada",
};

function fmtMoney(v: number | null | undefined) {
  if (v === null || v === undefined) return "Não informado";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function fmtNum(v: number | null | undefined) {
  if (v === null || v === undefined) return "Não informado";
  return v.toLocaleString("pt-BR");
}
function fmtDateTime(iso: string | null | undefined) {
  if (!iso) return "Não informado";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Não informado";
  return d.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo",
  });
}
function fmtPeriod(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

function SnapshotBlock({ title, snap }: { title: string; snap: FinanceSnapshot }) {
  return (
    <div style={{ flex: "1 1 260px", minWidth: 240, border: "1px dashed var(--bd)", borderRadius: 8, padding: "8px 10px", fontSize: 11 }}>
      <div style={{ fontWeight: 700, color: "var(--muted)", marginBottom: 4 }}>{title}</div>
      <div style={{ color: "var(--muted)", marginBottom: 6 }}>Referência do portal — não somar ao período sem cobertura comprovada</div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          <tr><td style={{ padding: "2px 0", color: "var(--muted)" }}>Coletado em</td><td style={{ textAlign: "right" }}>{fmtDateTime(snap.collected_at)}</td></tr>
          <tr><td style={{ padding: "2px 0", color: "var(--muted)" }}>Período do portal</td><td style={{ textAlign: "right" }}>{snap.period_until || "Não informado"}</td></tr>
          <tr><td style={{ padding: "2px 0", color: "var(--muted)" }}>Ganhos estimados</td><td style={{ textAlign: "right" }}>{fmtMoney(snap.estimated_earnings)}</td></tr>
          <tr><td style={{ padding: "2px 0", color: "var(--muted)" }}>Ganhos confirmados</td><td style={{ textAlign: "right" }}>{fmtMoney(snap.confirmed_earnings)}</td></tr>
          <tr><td style={{ padding: "2px 0", color: "var(--muted)" }}>Cliques</td><td style={{ textAlign: "right" }}>{fmtNum(snap.clicks)}</td></tr>
          <tr><td style={{ padding: "2px 0", color: "var(--muted)" }}>Pedidos</td><td style={{ textAlign: "right" }}>{fmtNum(snap.orders)}</td></tr>
        </tbody>
      </table>
    </div>
  );
}

export default function FinanceSummary({ adminKey, days, platform }: {
  adminKey: string;
  days: number;
  platform: string;
}) {
  const [report, setReport] = useState<FinanceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const providerParam = platform !== "all" ? `&provider=${platform}` : "";
    apiFetch(`${API}/api/v1/admin/finance?days=${days}${providerParam}`, {
      cache: "no-store",
      headers: { "X-Admin-Key": adminKey },
    })
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data: FinanceReport) => { if (!cancelled) setReport(data); })
      .catch((e) => { if (!cancelled) { setReport(null); setError(e instanceof Error ? e.message : String(e)); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [adminKey, days, platform]);

  if (loading) {
    return (
      <div className={styles.card}>
        <div className={styles.cardHeader}><div className={styles.cardTitle}><Wallet size={16} /> Financeiro — comissões</div></div>
        <div className={styles.emptyState}><div className={styles.emptyStateIcon}><LoaderCircle size={22} /></div>Carregando relatório financeiro…</div>
      </div>
    );
  }
  if (error || !report) {
    return (
      <div className={styles.card}>
        <div className={styles.cardHeader}><div className={styles.cardTitle}><Wallet size={16} /> Financeiro — comissões</div></div>
        <div className={styles.emptyState}><div className={styles.emptyStateIcon}><AlertTriangle size={22} /></div>Relatório financeiro indisponível ({error || "sem dados"})</div>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}><Wallet size={16} /> Financeiro — comissões ({fmtPeriod(report.period_start)} — {fmtPeriod(report.period_end)})</div>
      </div>

      <div style={{ padding: "0 4px 12px", fontSize: 12, color: "var(--ylw)", fontWeight: 600 }}>
        Cobertura parcial. Aprovada não significa paga. Sem extrato de pagamento integrado, não é possível apurar lucro.
      </div>

      <div className={styles.kpiGrid} style={{ padding: "0 4px" }}>
        {[
          { label: "Estimadas pendentes", value: report.totals.estimated_commission, color: "var(--ylw)", icon: <Clock size={20} /> },
          { label: "Aprovadas no sistema", value: report.totals.approved_commission, color: "var(--org)", icon: <BadgeCheck size={20} /> },
          { label: "Efetivamente pagas", value: report.totals.paid_commission, color: "var(--grn)", icon: <CheckCircle size={20} /> },
        ].map((card) => (
          <div key={card.label} className={styles.kpiCard} style={{ ["--kpiColor" as string]: card.color }}>
            <div className={styles.kpiIcon}>{card.icon}</div>
            <div className={styles.kpiLabel}>{card.label}</div>
            <div className={styles.kpiValue}>{fmtMoney(card.value)}</div>
          </div>
        ))}
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Marketplace</th>
              <th className={styles.th}>Fonte</th>
              <th className={styles.th}>Registros</th>
              <th className={styles.th}>Estimadas pendentes</th>
              <th className={styles.th}>Aprovadas no sistema</th>
              <th className={styles.th}>Efetivamente pagas</th>
            </tr>
          </thead>
          <tbody>
            {report.providers.length === 0 && (
              <tr><td colSpan={6} className={styles.td} style={{ textAlign: "center", color: "var(--muted)" }}>Sem dados</td></tr>
            )}
            {report.providers.map((row) => (
              <React.Fragment key={row.provider}>
                <tr className={styles.tr}>
                  <td className={styles.td} style={{ fontWeight: 600 }}>{row.provider}</td>
                  <td className={styles.td} style={{ color: "var(--muted)" }}>{SOURCE_LABELS[row.source] || row.source}</td>
                  <td className={styles.td}>{row.record_count}</td>
                  <td className={styles.td}>{fmtMoney(row.estimated_commission)}</td>
                  <td className={styles.td}>{fmtMoney(row.approved_commission)}</td>
                  <td className={styles.td}>{fmtMoney(row.paid_commission)}</td>
                </tr>
                {(row.notes.length > 0 || row.latest_snapshot || row.historical_snapshot) && (
                  <tr className={styles.tr}>
                    <td className={styles.td} colSpan={6} style={{ paddingTop: 0 }}>
                      {row.notes.length > 0 && (
                        <ul style={{ margin: "4px 0 8px", paddingLeft: 18, fontSize: 11, color: "var(--muted)" }}>
                          {row.notes.map((n, i) => <li key={i}>{n}</li>)}
                        </ul>
                      )}
                      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                        {row.latest_snapshot && <SnapshotBlock title="Última coleta do portal" snap={row.latest_snapshot} />}
                        {row.historical_snapshot && <SnapshotBlock title="Referência histórica do portal" snap={row.historical_snapshot} />}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {report.notes.length > 0 && (
        <ul style={{ margin: "8px 4px 4px", paddingLeft: 18, fontSize: 11, color: "var(--muted)" }}>
          {report.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      )}
    </div>
  );
}
