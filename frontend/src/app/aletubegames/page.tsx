"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { API_BASE as API } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AccountStatus {
  connected: boolean;
  username?: string;
  avatar?: string;
  token_status?: "ok" | "expiring" | "expired";
}

interface AccountsStatus {
  tiktok: AccountStatus;
  youtube: AccountStatus;
  instagram: AccountStatus;
  facebook: AccountStatus;
}

interface VideoInfo {
  id: string;
  filename: string;
  size: number;
  duration?: number;
  resolution?: string;
  fps?: number;
}

interface PlatformMeta {
  title?: string;
  description?: string;
  caption?: string;
  hashtags?: string[];
  bio_note?: string;
  end_screen_note?: string;
}

interface AnalyzeResult {
  video_id: string;
  platform_metadata: {
    tiktok?: PlatformMeta;
    youtube?: PlatformMeta;
    instagram?: PlatformMeta;
    facebook?: PlatformMeta;
  };
}

interface PublishResult {
  tiktok?: { success: boolean; url?: string; error?: string };
  youtube?: { success: boolean; url?: string; error?: string };
  instagram?: { success: boolean; url?: string; error?: string };
  facebook?: { success: boolean; url?: string; error?: string };
}

interface HistoryVideo {
  id: string;
  title?: string;
  created_at?: string;
  platforms?: string[];
  status?: string;
  clicks?: number;
  conversions?: number;
}

type Tab = "accounts" | "publish" | "history";
type PublishStep = 1 | 2 | 3 | 4;
type PlatformKey = "tiktok" | "youtube" | "instagram" | "facebook";

const PLATFORMS: { key: PlatformKey; label: string; color: string; icon: string }[] = [
  { key: "tiktok", label: "TikTok", color: "#ff0050", icon: "🎵" },
  { key: "youtube", label: "YouTube", color: "#ff0000", icon: "▶️" },
  { key: "instagram", label: "Instagram", color: "#e1306c", icon: "📷" },
  { key: "facebook", label: "Facebook", color: "#1877f2", icon: "👥" },
];

const PLATFORM_NOTES: Record<PlatformKey, string> = {
  tiktok: "Requer aprovação Content Posting API",
  youtube: "OAuth Google — funciona imediatamente após configurar client_id",
  instagram: "Requer app Facebook aprovado + conta Business/Creator",
  facebook: "Requer app Facebook aprovado + conta Business/Creator",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getAuthHeaders(adminKey?: string | null, useAdminKey?: boolean): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("bpt_token") : null;
  if (useAdminKey && adminKey) {
    return { "X-Admin-Key": adminKey };
  }
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AleTubeGamesPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("accounts");

  // Auth
  const [adminKey, setAdminKey] = useState<string | null>(null);

  // Accounts
  const [accounts, setAccounts] = useState<AccountsStatus | null>(null);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<PlatformKey | null>(null);

  // Publish
  const [publishStep, setPublishStep] = useState<PublishStep>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResult | null>(null);
  const [editedMeta, setEditedMeta] = useState<Record<PlatformKey, PlatformMeta>>({
    tiktok: {}, youtube: {}, instagram: {}, facebook: {},
  });
  const [metaTab, setMetaTab] = useState<PlatformKey>("tiktok");
  const [selectedPlatforms, setSelectedPlatforms] = useState<Record<PlatformKey, boolean>>({
    tiktok: false, youtube: false, instagram: false, facebook: false,
  });
  const [affiliateUrl, setAffiliateUrl] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null);

  // History
  const [history, setHistory] = useState<HistoryVideo[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Auth guard ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const user = typeof window !== "undefined" ? localStorage.getItem("bpt_user") : null;
    if (!user) { router.push("/login"); return; }
    try {
      const parsed = JSON.parse(user);
      if (!parsed?.is_admin) { router.push("/"); return; }
    } catch {
      router.push("/login");
      return;
    }
    const key = localStorage.getItem("admin_key");
    setAdminKey(key);
  }, [router]);

  // ── Initial load ────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchAccounts();
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchAccounts() {
    setAccountsLoading(true);
    setAccountsError(null);
    try {
      const res = await fetch(`${API}/api/v1/aletube/accounts/status`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: AccountsStatus = await res.json();
      setAccounts(data);
      // Pre-select connected platforms
      setSelectedPlatforms({
        tiktok: !!data.tiktok?.connected,
        youtube: !!data.youtube?.connected,
        instagram: !!data.instagram?.connected,
        facebook: !!data.facebook?.connected,
      });
    } catch (e: unknown) {
      setAccountsError(e instanceof Error ? e.message : "Erro ao carregar contas");
    } finally {
      setAccountsLoading(false);
    }
  }

  async function fetchHistory() {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await fetch(`${API}/api/v1/aletube/videos`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setHistory(Array.isArray(data) ? data : data.videos ?? []);
    } catch (e: unknown) {
      setHistoryError(e instanceof Error ? e.message : "Erro ao carregar histórico");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleConnect(platform: PlatformKey) {
    console.log(`[handleConnect] platform=${platform}, API=${API}`);
    try {
      let url: string;
      if (platform === "tiktok") {
        const headers = getAuthHeaders(adminKey, true);
        console.log(`[handleConnect] tiktok headers:`, JSON.stringify(headers));
        const res = await fetch(`${API}/api/v1/tiktok/auth/admin`, { headers });
        console.log(`[handleConnect] tiktok res.status=${res.status}`);
        const data = await res.json();
        console.log(`[handleConnect] tiktok data:`, JSON.stringify(data));
        url = data.auth_url;
      } else if (platform === "youtube") {
        const headers = getAuthHeaders();
        console.log(`[handleConnect] youtube headers:`, JSON.stringify(headers));
        const res = await fetch(`${API}/api/v1/aletube/auth/youtube`, { headers });
        console.log(`[handleConnect] youtube res.status=${res.status}`);
        const text = await res.text();
        console.log(`[handleConnect] youtube res.text:`, text);
        const data = JSON.parse(text);
        url = data.auth_url;
      } else if (platform === "facebook" || platform === "instagram") {
        const headers = getAuthHeaders();
        const res = await fetch(`${API}/api/v1/aletube/auth/facebook`, { headers });
        console.log(`[handleConnect] fb/ig res.status=${res.status}`);
        const data = await res.json();
        url = data.auth_url;
      } else {
        return;
      }
      if (url) {
        console.log(`[handleConnect] opening URL: ${url}`);
        window.open(url, "_blank");
      } else {
        console.error(`[handleConnect] NO auth_url in response for ${platform}`);
        alert(`Erro: auth_url não retornada para ${platform}`);
      }
    } catch (e: unknown) {
      console.error(`[handleConnect] error:`, e);
      alert(`Erro ao obter URL de auth: ${e instanceof Error ? e.message : e}`);
    }
  }

  async function handleDisconnect(platform: PlatformKey) {
    if (!confirm(`Desconectar ${platform}?`)) return;
    setDisconnecting(platform);
    try {
      const res = await fetch(`${API}/api/v1/aletube/accounts/${platform}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchAccounts();
    } catch (e: unknown) {
      alert(`Erro ao desconectar: ${e instanceof Error ? e.message : e}`);
    } finally {
      setDisconnecting(null);
    }
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      const form = new FormData();
      form.append("file", selectedFile);
      const res = await fetch(`${API}/api/v1/aletube/upload`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: form,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setVideoInfo({
        id: data.video_id ?? data.id,
        filename: selectedFile.name,
        size: selectedFile.size,
        duration: data.duration,
        resolution: data.resolution,
        fps: data.fps,
      });
      setPublishStep(2);
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "Erro no upload");
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyze() {
    if (!videoInfo) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const form = new FormData();
      form.append("video_id", videoInfo.id);
      const res = await fetch(`${API}/api/v1/aletube/analyze`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: form,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: AnalyzeResult = await res.json();
      setAnalyzeResult(data);
      // Seed editable meta from analysis
      const meta: Record<PlatformKey, PlatformMeta> = {
        tiktok: { ...data.platform_metadata?.tiktok },
        youtube: { ...data.platform_metadata?.youtube },
        instagram: { ...data.platform_metadata?.instagram },
        facebook: { ...data.platform_metadata?.facebook },
      };
      setEditedMeta(meta);
      setPublishStep(3);
    } catch (e: unknown) {
      setAnalyzeError(e instanceof Error ? e.message : "Erro na análise");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handlePublish() {
    if (!videoInfo || !analyzeResult) return;
    setPublishing(true);
    setPublishError(null);
    try {
      const form = new FormData();
      form.append("video_id", analyzeResult.video_id);
      const plats = (Object.keys(selectedPlatforms) as PlatformKey[]).filter(p => selectedPlatforms[p]);
      form.append("plataformas", plats.join(","));
      if (affiliateUrl) form.append("affiliate_url", affiliateUrl);

      const buildMeta = (p: PlatformKey) => {
        const m = editedMeta[p];
        return JSON.stringify({
          title: m.title ?? "",
          description: m.description ?? m.caption ?? "",
          caption: m.caption ?? m.description ?? "",
          hashtags: typeof m.hashtags === "string"
            ? (m.hashtags as string).split(",").map((h: string) => h.trim()).filter(Boolean)
            : m.hashtags ?? [],
        });
      };

      form.append("tiktok_meta", buildMeta("tiktok"));
      form.append("youtube_meta", buildMeta("youtube"));
      form.append("instagram_meta", buildMeta("instagram"));
      form.append("facebook_meta", buildMeta("facebook"));

      const res = await fetch(`${API}/api/v1/aletube/publish`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: form,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: PublishResult = await res.json();
      setPublishResult(data);
      setPublishStep(4);
      fetchHistory();
    } catch (e: unknown) {
      setPublishError(e instanceof Error ? e.message : "Erro na publicação");
    } finally {
      setPublishing(false);
    }
  }

  function resetPublish() {
    setPublishStep(1);
    setSelectedFile(null);
    setVideoInfo(null);
    setAnalyzeResult(null);
    setEditedMeta({ tiktok: {}, youtube: {}, instagram: {}, facebook: {} });
    setAffiliateUrl("");
    setPublishResult(null);
    setUploadError(null);
    setAnalyzeError(null);
    setPublishError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function updateMeta(platform: PlatformKey, field: keyof PlatformMeta, value: string) {
    setEditedMeta(prev => ({
      ...prev,
      [platform]: { ...prev[platform], [field]: value },
    }));
  }

  // ── Styles ──────────────────────────────────────────────────────────────────
  const s = {
    page: {
      minHeight: "100vh",
      background: "#f0f4ff",
      fontFamily: "'Segoe UI', sans-serif",
      padding: "0 0 60px 0",
    } as React.CSSProperties,
    header: {
      background: "linear-gradient(135deg, #7c6aff 0%, #a78bfa 100%)",
      padding: "24px 32px 16px",
      color: "#fff",
    } as React.CSSProperties,
    headerTop: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 4,
    } as React.CSSProperties,
    title: { fontSize: 26, fontWeight: 700, margin: 0 } as React.CSSProperties,
    subtitle: { margin: "4px 0 16px", opacity: 0.85, fontSize: 14 } as React.CSSProperties,
    navBtns: { display: "flex", gap: 8 } as React.CSSProperties,
    navBtn: {
      background: "rgba(255,255,255,0.15)",
      border: "1px solid rgba(255,255,255,0.3)",
      borderRadius: 8,
      color: "#fff",
      padding: "6px 14px",
      cursor: "pointer",
      fontSize: 13,
    } as React.CSSProperties,
    tabs: {
      display: "flex",
      gap: 0,
      background: "rgba(255,255,255,0.15)",
      borderRadius: 10,
      padding: 4,
      width: "fit-content",
    } as React.CSSProperties,
    tab: (active: boolean): React.CSSProperties => ({
      padding: "8px 20px",
      borderRadius: 8,
      border: "none",
      cursor: "pointer",
      fontWeight: active ? 600 : 400,
      fontSize: 14,
      background: active ? "#fff" : "transparent",
      color: active ? "#7c6aff" : "#fff",
      transition: "all 0.2s",
    }),
    body: { padding: "24px 32px", maxWidth: 900, margin: "0 auto" } as React.CSSProperties,
    card: {
      background: "#fff",
      borderRadius: 12,
      border: "1px solid rgba(108,92,231,0.2)",
      padding: 20,
      marginBottom: 16,
    } as React.CSSProperties,
    grid4: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
      gap: 16,
    } as React.CSSProperties,
    badge: (connected: boolean): React.CSSProperties => ({
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: 20,
      fontSize: 12,
      fontWeight: 600,
      background: connected ? "#d1fae5" : "#f3f4f6",
      color: connected ? "#059669" : "#6b7280",
      marginBottom: 8,
    }),
    tokenBadge: (status: string): React.CSSProperties => ({
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 20,
      fontSize: 11,
      background: status === "ok" ? "#d1fae5" : status === "expiring" ? "#fef3c7" : "#fee2e2",
      color: status === "ok" ? "#059669" : status === "expiring" ? "#d97706" : "#dc2626",
      marginLeft: 6,
    }),
    btn: (color: string = "#7c6aff"): React.CSSProperties => ({
      background: color,
      color: "#fff",
      border: "none",
      borderRadius: 8,
      padding: "8px 16px",
      cursor: "pointer",
      fontWeight: 600,
      fontSize: 13,
    }),
    btnOutline: (color: string = "#7c6aff"): React.CSSProperties => ({
      background: "transparent",
      color: color,
      border: `1px solid ${color}`,
      borderRadius: 8,
      padding: "8px 16px",
      cursor: "pointer",
      fontWeight: 600,
      fontSize: 13,
    }),
    input: {
      width: "100%",
      padding: "8px 12px",
      borderRadius: 8,
      border: "1px solid rgba(108,92,231,0.3)",
      fontSize: 13,
      outline: "none",
      boxSizing: "border-box",
    } as React.CSSProperties,
    textarea: {
      width: "100%",
      padding: "8px 12px",
      borderRadius: 8,
      border: "1px solid rgba(108,92,231,0.3)",
      fontSize: 13,
      outline: "none",
      resize: "vertical",
      minHeight: 80,
      boxSizing: "border-box",
    } as React.CSSProperties,
    label: { fontSize: 12, fontWeight: 600, color: "#555", marginBottom: 4, display: "block" } as React.CSSProperties,
    note: (color: string = "#fef3c7"): React.CSSProperties => ({
      background: color,
      borderRadius: 8,
      padding: "10px 14px",
      fontSize: 12,
      color: "#92400e",
      marginBottom: 12,
    }),
    stepIndicator: {
      display: "flex",
      gap: 8,
      marginBottom: 20,
      alignItems: "center",
    } as React.CSSProperties,
    step: (active: boolean, done: boolean): React.CSSProperties => ({
      width: 28,
      height: 28,
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontWeight: 700,
      fontSize: 13,
      background: done ? "#00e5a0" : active ? "#7c6aff" : "#e5e7eb",
      color: done || active ? "#fff" : "#9ca3af",
    }),
    stepLine: {
      flex: 1,
      height: 2,
      background: "#e5e7eb",
    } as React.CSSProperties,
    error: {
      background: "#fee2e2",
      color: "#dc2626",
      padding: "10px 14px",
      borderRadius: 8,
      fontSize: 13,
      marginBottom: 12,
    } as React.CSSProperties,
    innerTabs: {
      display: "flex",
      gap: 4,
      marginBottom: 16,
      borderBottom: "2px solid #e5e7eb",
    } as React.CSSProperties,
    innerTab: (active: boolean, color: string): React.CSSProperties => ({
      padding: "8px 16px",
      border: "none",
      background: "none",
      cursor: "pointer",
      fontWeight: active ? 700 : 400,
      color: active ? color : "#6b7280",
      borderBottom: active ? `2px solid ${color}` : "2px solid transparent",
      marginBottom: -2,
      fontSize: 14,
    }),
    statRow: {
      display: "flex",
      gap: 16,
      marginBottom: 12,
      flexWrap: "wrap" as const,
    } as React.CSSProperties,
    stat: {
      background: "#f9fafb",
      borderRadius: 8,
      padding: "8px 16px",
      fontSize: 13,
      color: "#374151",
    } as React.CSSProperties,
    tableRow: (even: boolean): React.CSSProperties => ({
      display: "grid",
      gridTemplateColumns: "40px 1fr 100px 120px 80px 60px 70px",
      gap: 8,
      padding: "10px 12px",
      background: even ? "#f9fafb" : "#fff",
      alignItems: "center",
      fontSize: 13,
      borderBottom: "1px solid #f0f0f0",
    }),
    tableHeader: {
      display: "grid",
      gridTemplateColumns: "40px 1fr 100px 120px 80px 60px 70px",
      gap: 8,
      padding: "8px 12px",
      background: "#f3f4f6",
      fontWeight: 700,
      fontSize: 12,
      color: "#6b7280",
      borderRadius: "8px 8px 0 0",
    } as React.CSSProperties,
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerTop}>
          <h1 style={s.title}>🎥 AleTubeGames</h1>
          <div style={s.navBtns}>
            <button style={s.navBtn} onClick={() => router.push("/")}>← Home</button>
            <button style={s.navBtn} onClick={() => router.push("/dashboard")}>📊 Dashboard</button>
          </div>
        </div>
        <p style={s.subtitle}>Upload, análise e publicação multi-plataforma</p>
        <div style={s.tabs}>
          {(["accounts", "publish", "history"] as Tab[]).map(t => (
            <button key={t} style={s.tab(activeTab === t)} onClick={() => setActiveTab(t)}>
              {t === "accounts" ? "Contas" : t === "publish" ? "Publicar" : "Histórico"}
            </button>
          ))}
        </div>
      </div>

      <div style={s.body}>

        {/* ── Aba Contas ── */}
        {activeTab === "accounts" && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, color: "#1f2937" }}>Plataformas Conectadas</h2>
              <button style={s.btn()} onClick={fetchAccounts}>🔄 Atualizar</button>
            </div>
            {accountsLoading && <p style={{ color: "#6b7280" }}>Carregando...</p>}
            {accountsError && <div style={s.error}>Erro: {accountsError}</div>}
            {accounts && (
              <div style={s.grid4}>
                {PLATFORMS.map(({ key, label, color, icon }) => {
                  const acc = accounts[key];
                  return (
                    <div key={key} style={{ ...s.card, borderTop: `3px solid ${color}` }}>
                      <div style={{ fontSize: 24, marginBottom: 6 }}>{icon}</div>
                      <div style={{ fontWeight: 700, fontSize: 15, color: "#1f2937", marginBottom: 6 }}>{label}</div>
                      <span style={s.badge(acc.connected)}>
                        {acc.connected ? "✅ Conectado" : "⚪ Não conectado"}
                      </span>
                      {acc.connected && acc.token_status && (
                        <span style={s.tokenBadge(acc.token_status)}>
                          {acc.token_status === "ok" ? "Token OK" : acc.token_status === "expiring" ? "⚠ Expirando" : "❌ Expirado"}
                        </span>
                      )}
                      {acc.connected && acc.username && (
                        <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>@{acc.username}</div>
                      )}
                      <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 12, lineHeight: 1.4 }}>
                        {PLATFORM_NOTES[key]}
                      </div>
                      {acc.connected ? (
                        <button
                          style={s.btnOutline("#f43f5e")}
                          onClick={() => handleDisconnect(key)}
                          disabled={disconnecting === key}
                        >
                          {disconnecting === key ? "..." : "Desconectar"}
                        </button>
                      ) : (
                        <button style={s.btn(color)} onClick={() => handleConnect(key)}>
                          Conectar
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* ── Aba Publicar ── */}
        {activeTab === "publish" && (
          <>
            <h2 style={{ margin: "0 0 16px", fontSize: 18, color: "#1f2937" }}>Publicar Vídeo</h2>

            {/* Step indicator */}
            <div style={s.stepIndicator}>
              {[1, 2, 3, 4].map((n, i) => (
                <>
                  <div key={n} style={s.step(publishStep === n, publishStep > n)}>
                    {publishStep > n ? "✓" : n}
                  </div>
                  {i < 3 && <div style={s.stepLine} />}
                </>
              ))}
            </div>
            <div style={{ display: "flex", justifyContent: "space-around", marginBottom: 20, fontSize: 12, color: "#6b7280" }}>
              <span>Upload</span><span>Análise</span><span>Editar</span><span>Resultado</span>
            </div>

            {/* Step 1 — Upload */}
            {publishStep === 1 && (
              <div style={s.card}>
                <h3 style={{ margin: "0 0 16px", fontSize: 16 }}>1. Selecionar Vídeo</h3>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".mp4,.mov,.avi,.mkv"
                  style={{ marginBottom: 12, display: "block" }}
                  onChange={e => setSelectedFile(e.target.files?.[0] ?? null)}
                />
                {selectedFile && (
                  <div style={{ ...s.stat, marginBottom: 12 }}>
                    📁 <strong>{selectedFile.name}</strong> — {formatBytes(selectedFile.size)}
                  </div>
                )}
                {uploadError && <div style={s.error}>{uploadError}</div>}
                <button
                  style={s.btn()}
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                >
                  {uploading ? "Fazendo upload..." : "Fazer Upload"}
                </button>
              </div>
            )}

            {/* Step 2 — Análise */}
            {publishStep === 2 && videoInfo && (
              <div style={s.card}>
                <h3 style={{ margin: "0 0 16px", fontSize: 16 }}>2. Analisar Vídeo</h3>
                <div style={s.statRow}>
                  <div style={s.stat}>📁 {videoInfo.filename}</div>
                  <div style={s.stat}>💾 {formatBytes(videoInfo.size)}</div>
                  {videoInfo.duration && <div style={s.stat}>⏱ {videoInfo.duration}s</div>}
                  {videoInfo.resolution && <div style={s.stat}>📐 {videoInfo.resolution}</div>}
                  {videoInfo.fps && <div style={s.stat}>🎞 {videoInfo.fps} fps</div>}
                </div>
                {analyzeError && <div style={s.error}>{analyzeError}</div>}
                {analyzing && (
                  <div style={{ ...s.note(), color: "#7c6aff", background: "#ede9fe" }}>
                    ⏳ Gerando conteúdo para cada plataforma...
                  </div>
                )}
                <div style={{ display: "flex", gap: 8 }}>
                  <button style={s.btnOutline()} onClick={() => setPublishStep(1)}>← Voltar</button>
                  <button style={s.btn()} onClick={handleAnalyze} disabled={analyzing}>
                    {analyzing ? "Analisando..." : "Analisar com IA"}
                  </button>
                </div>
              </div>
            )}

            {/* Step 3 — Editar */}
            {publishStep === 3 && analyzeResult && (
              <div style={s.card}>
                <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>3. Editar Conteúdo por Plataforma</h3>

                {/* Platform tabs */}
                <div style={s.innerTabs}>
                  {PLATFORMS.map(({ key, label, color }) => (
                    <button
                      key={key}
                      style={s.innerTab(metaTab === key, color)}
                      onClick={() => setMetaTab(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {PLATFORMS.map(({ key }) => {
                  if (metaTab !== key) return null;
                  const m = editedMeta[key];
                  return (
                    <div key={key}>
                      {m.bio_note && (
                        <div style={s.note()}>
                          💡 <strong>Bio:</strong> {m.bio_note}
                        </div>
                      )}
                      {key === "youtube" && (m as PlatformMeta & { end_screen_note?: string }).end_screen_note && (
                        <div style={s.note()}>
                          🎬 <strong>End Screen:</strong> {(m as PlatformMeta & { end_screen_note?: string }).end_screen_note}
                        </div>
                      )}
                      <div style={{ marginBottom: 12 }}>
                        <label style={s.label}>Título</label>
                        <input
                          style={s.input}
                          value={m.title ?? ""}
                          onChange={e => updateMeta(key, "title", e.target.value)}
                        />
                      </div>
                      {(key === "tiktok" || key === "instagram") ? (
                        <div style={{ marginBottom: 12 }}>
                          <label style={s.label}>Caption</label>
                          <textarea
                            style={s.textarea}
                            value={m.caption ?? m.description ?? ""}
                            onChange={e => updateMeta(key, "caption", e.target.value)}
                          />
                        </div>
                      ) : (
                        <div style={{ marginBottom: 12 }}>
                          <label style={s.label}>Descrição</label>
                          <textarea
                            style={s.textarea}
                            value={m.description ?? m.caption ?? ""}
                            onChange={e => updateMeta(key, "description", e.target.value)}
                          />
                        </div>
                      )}
                      <div style={{ marginBottom: 12 }}>
                        <label style={s.label}>Hashtags (separadas por vírgula)</label>
                        <input
                          style={s.input}
                          value={Array.isArray(m.hashtags) ? m.hashtags.join(", ") : (m.hashtags ?? "")}
                          onChange={e => updateMeta(key, "hashtags", e.target.value)}
                        />
                      </div>
                    </div>
                  );
                })}

                {/* Affiliate URL */}
                <div style={{ marginTop: 16, marginBottom: 16 }}>
                  <label style={s.label}>URL de Afiliado (opcional)</label>
                  <input
                    style={s.input}
                    placeholder="https://..."
                    value={affiliateUrl}
                    onChange={e => setAffiliateUrl(e.target.value)}
                  />
                </div>

                {/* Platform checkboxes */}
                <div style={{ marginBottom: 16 }}>
                  <label style={s.label}>Publicar em:</label>
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                    {PLATFORMS.map(({ key, label, color }) => {
                      const connected = accounts?.[key]?.connected ?? false;
                      return (
                        <label key={key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: connected ? "pointer" : "not-allowed", opacity: connected ? 1 : 0.5 }}>
                          <input
                            type="checkbox"
                            checked={selectedPlatforms[key]}
                            disabled={!connected}
                            onChange={e => setSelectedPlatforms(prev => ({ ...prev, [key]: e.target.checked }))}
                            style={{ accentColor: color }}
                          />
                          <span style={{ color, fontWeight: 600 }}>{label}</span>
                          {!connected && <span style={{ fontSize: 11, color: "#9ca3af" }}>(não conectado)</span>}
                        </label>
                      );
                    })}
                  </div>
                </div>

                {publishError && <div style={s.error}>{publishError}</div>}

                <div style={{ display: "flex", gap: 8 }}>
                  <button style={s.btnOutline()} onClick={() => setPublishStep(2)}>← Voltar</button>
                  <button
                    style={s.btn("#00e5a0")}
                    onClick={handlePublish}
                    disabled={publishing || !Object.values(selectedPlatforms).some(Boolean)}
                  >
                    {publishing ? "Publicando..." : "🚀 Publicar Agora"}
                  </button>
                </div>
              </div>
            )}

            {/* Step 4 — Resultado */}
            {publishStep === 4 && publishResult && (
              <div style={s.card}>
                <h3 style={{ margin: "0 0 16px", fontSize: 16 }}>4. Resultado da Publicação</h3>
                {PLATFORMS.map(({ key, label, color }) => {
                  const r = publishResult[key];
                  if (!r) return null;
                  return (
                    <div key={key} style={{
                      padding: "12px 16px",
                      borderRadius: 8,
                      marginBottom: 10,
                      background: r.success ? "#d1fae5" : "#fee2e2",
                      borderLeft: `4px solid ${r.success ? "#00e5a0" : "#f43f5e"}`,
                    }}>
                      <strong style={{ color }}>{label}</strong>
                      {r.success ? (
                        <span style={{ color: "#059669", marginLeft: 8 }}>
                          ✅ Publicado
                          {r.url && <> — <a href={r.url} target="_blank" rel="noreferrer" style={{ color: "#7c6aff" }}>Ver post</a></>}
                        </span>
                      ) : (
                        <span style={{ color: "#dc2626", marginLeft: 8 }}>
                          ❌ Erro: {r.error ?? "Desconhecido"}
                        </span>
                      )}
                    </div>
                  );
                })}
                <button style={{ ...s.btn(), marginTop: 16 }} onClick={resetPublish}>
                  + Publicar outro vídeo
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Aba Histórico ── */}
        {activeTab === "history" && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, color: "#1f2937" }}>Histórico de Publicações</h2>
              <button style={s.btn()} onClick={fetchHistory}>🔄 Atualizar</button>
            </div>
            {historyLoading && <p style={{ color: "#6b7280" }}>Carregando...</p>}
            {historyError && <div style={s.error}>{historyError}</div>}
            {!historyLoading && !historyError && (
              <div style={{ ...s.card, padding: 0, overflow: "hidden" }}>
                <div style={s.tableHeader}>
                  <span>#</span>
                  <span>Título</span>
                  <span>Data</span>
                  <span>Plataformas</span>
                  <span>Status</span>
                  <span>Cliques</span>
                  <span>Conversões</span>
                </div>
                {history.length === 0 ? (
                  <div style={{ padding: "24px", textAlign: "center", color: "#9ca3af", fontSize: 14 }}>
                    Nenhum vídeo publicado ainda.
                  </div>
                ) : (
                  history.map((v, i) => (
                    <div key={v.id} style={s.tableRow(i % 2 === 0)}>
                      <div style={{
                        width: 32,
                        height: 32,
                        background: "#e5e7eb",
                        borderRadius: 4,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 10,
                        color: "#9ca3af",
                      }}>▶</div>
                      <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {v.title ?? v.id}
                      </div>
                      <div style={{ color: "#6b7280", fontSize: 12 }}>
                        {v.created_at ? new Date(v.created_at).toLocaleDateString("pt-BR") : "—"}
                      </div>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {(v.platforms ?? []).map(p => {
                          const pl = PLATFORMS.find(x => x.key === p);
                          return pl ? (
                            <span key={p} style={{
                              fontSize: 10,
                              background: pl.color,
                              color: "#fff",
                              borderRadius: 4,
                              padding: "1px 6px",
                              fontWeight: 600,
                            }}>{pl.label}</span>
                          ) : null;
                        })}
                      </div>
                      <div>
                        <span style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 20,
                          background: v.status === "published" ? "#d1fae5" : v.status === "failed" ? "#fee2e2" : "#fef3c7",
                          color: v.status === "published" ? "#059669" : v.status === "failed" ? "#dc2626" : "#d97706",
                        }}>
                          {v.status ?? "—"}
                        </span>
                      </div>
                      <div style={{ textAlign: "center" }}>{v.clicks ?? 0}</div>
                      <div style={{ textAlign: "center" }}>{v.conversions ?? 0}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
