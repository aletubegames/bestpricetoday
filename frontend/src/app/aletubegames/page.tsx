"use client";
import { useState } from "react";
import { API_BASE as API } from "@/lib/api";

type Step = "upload" | "analyze" | "preview" | "publish" | "published";

interface VideoData {
  video_id: string;
  filename: string;
  title?: string;
  description?: string;
  hashtags?: string[];
  duration_seconds?: number;
  tiktok_video_id?: string;
  youtube_video_id?: string;
  tiktok_short_link?: string;
  youtube_short_link?: string;
}

export default function AleTubeGamesPage() {
  const [step, setStep] = useState<Step>("upload");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [video, setVideo] = useState<VideoData | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [plataformas, setPlataformas] = useState(["tiktok", "youtube"]);
  const [affiliateUrl, setAffiliateUrl] = useState("");

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Selecione um arquivo");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/api/v1/aletube/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erro no upload");
      }

      const data = await res.json();
      setVideo({
        video_id: data.video_id,
        filename: data.filename,
      });
      setStep("analyze");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!video) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API}/api/v1/aletube/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `video_id=${video.video_id}`,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erro na análise");
      }

      const data = await res.json();
      setVideo((prev) => prev ? { ...prev, ...data } : null);
      setStep("preview");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!video) return;
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("video_id", video.video_id);
    formData.append("plataformas", plataformas.join(","));
    if (affiliateUrl) {
      formData.append("affiliate_url", affiliateUrl);
    }

    try {
      const res = await fetch(`${API}/api/v1/aletube/publish`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erro na publicação");
      }

      const data = await res.json();
      setVideo((prev) => prev ? { ...prev, ...data } : null);
      setStep("published");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const S = {
    card: {
      background: "#ffffff",
      border: "1px solid rgba(108,92,231,0.2)",
      borderRadius: 14,
      padding: "24px",
      marginBottom: 20,
    } as React.CSSProperties,
    btn: (primary: boolean) => ({
      padding: "12px 24px",
      fontSize: 14,
      fontWeight: 700,
      borderRadius: 8,
      border: "none",
      cursor: "pointer",
      background: primary ? "#6c5ce7" : "#f5f7ff",
      color: primary ? "#fff" : "#1a1a2e",
      transition: "all 0.2s",
    } as React.CSSProperties),
    input: {
      width: "100%",
      padding: "12px 16px",
      fontSize: 14,
      border: "1px solid rgba(108,92,231,0.2)",
      borderRadius: 8,
      background: "#f5f7ff",
      color: "#1a1a2e",
      marginBottom: 16,
    } as React.CSSProperties,
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", padding: "40px 24px" }}>
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        {/* Header com botão de voltar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 40, gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 32, fontWeight: 900, color: "#1a1a2e", marginBottom: 8 }}>
              🎥 AleTubeGames
            </h1>
            <p style={{ fontSize: 16, color: "#6b6b8a" }}>
              Upload, análise IA e publicação automática em TikTok + YouTube
            </p>
          </div>
          <a href="/" style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "10px 16px", borderRadius: 8,
            background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)",
            color: "#7c6aff", textDecoration: "none", fontWeight: 700, fontSize: 14,
            whiteSpace: "nowrap"
          }}>
            ← Home
          </a>
        </div>

        {/* Upload Step */}
        {step === "upload" && (
          <div style={S.card}>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 20, color: "#1a1a2e" }}>
              1️⃣ Selecione seu vídeo
            </h2>
            <input
              type="file"
              accept="video/mp4,video/quicktime,video/x-msvideo"
              onChange={handleFileSelect}
              style={{ marginBottom: 16 }}
            />
            {file && (
              <p style={{ color: "#6b6b8a", marginBottom: 16 }}>
                ✅ {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
            {error && (
              <div
                style={{
                  background: "#fef2f2",
                  color: "#e74c3c",
                  padding: 12,
                  borderRadius: 8,
                  marginBottom: 16,
                  fontSize: 14,
                }}
              >
                {error}
              </div>
            )}
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              style={{
                ...S.btn(true),
                opacity: !file || loading ? 0.5 : 1,
              }}
            >
              {loading ? "Enviando..." : "Fazer Upload"}
            </button>
          </div>
        )}

        {/* Analyze Step */}
        {step === "analyze" && (
          <div style={S.card}>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 20, color: "#1a1a2e" }}>
              2️⃣ Análise IA
            </h2>
            <p style={{ color: "#6b6b8a", marginBottom: 20 }}>
              Extraindo frames e gerando metadados...
            </p>
            <button
              onClick={handleAnalyze}
              disabled={loading}
              style={{ ...S.btn(true), opacity: loading ? 0.5 : 1 }}
            >
              {loading ? "Analisando..." : "Analisar Vídeo"}
            </button>
          </div>
        )}

        {/* Preview Step */}
        {step === "preview" && video && (
          <div style={S.card}>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 20, color: "#1a1a2e" }}>
              3️⃣ Preview
            </h2>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontWeight: 700, marginBottom: 8, color: "#1a1a2e" }}>
                Título
              </label>
              <input
                type="text"
                value={video.title || ""}
                onChange={(e) => setVideo({ ...video, title: e.target.value })}
                style={S.input}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontWeight: 700, marginBottom: 8, color: "#1a1a2e" }}>
                Descrição
              </label>
              <textarea
                value={video.description || ""}
                onChange={(e) => setVideo({ ...video, description: e.target.value })}
                style={{ ...S.input, minHeight: 100 }}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontWeight: 700, marginBottom: 8, color: "#1a1a2e" }}>
                Hashtags
              </label>
              <input
                type="text"
                value={video.hashtags?.join(", ") || ""}
                onChange={(e) =>
                  setVideo({
                    ...video,
                    hashtags: e.target.value.split(",").map((h) => h.trim()),
                  })
                }
                placeholder="#aletubegames, #tech, #promo"
                style={S.input}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontWeight: 700, marginBottom: 8, color: "#1a1a2e" }}>
                Plataformas
              </label>
              <div style={{ display: "flex", gap: 16 }}>
                {["tiktok", "youtube", "telegram"].map((p) => (
                  <label key={p} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={plataformas.includes(p)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setPlataformas([...plataformas, p]);
                        } else {
                          setPlataformas(plataformas.filter((x) => x !== p));
                        }
                      }}
                    />
                    <span style={{ color: "#1a1a2e", fontWeight: 600 }}>
                      {p === "tiktok" ? "🎵 TikTok" : p === "youtube" ? "📺 YouTube" : "📱 Telegram"}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontWeight: 700, marginBottom: 8, color: "#1a1a2e" }}>
                URL de Afiliado (opcional)
              </label>
              <input
                type="url"
                value={affiliateUrl}
                onChange={(e) => setAffiliateUrl(e.target.value)}
                placeholder="https://..."
                style={S.input}
              />
            </div>

            {error && (
              <div
                style={{
                  background: "#fef2f2",
                  color: "#e74c3c",
                  padding: 12,
                  borderRadius: 8,
                  marginBottom: 16,
                  fontSize: 14,
                }}
              >
                {error}
              </div>
            )}

            <button
              onClick={handlePublish}
              disabled={loading}
              style={{ ...S.btn(true), opacity: loading ? 0.5 : 1 }}
            >
              {loading ? "Publicando..." : "Publicar Agora"}
            </button>
          </div>
        )}

        {/* Published Step */}
        {step === "published" && video && (
          <div style={S.card}>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 20, color: "#1a1a2e" }}>
              ✅ Publicado com sucesso!
            </h2>

            {video.tiktok_video_id && (
              <div style={{ marginBottom: 16, padding: 12, background: "#f0fdf4", borderRadius: 8 }}>
                <p style={{ color: "#1a1a2e", fontWeight: 700, marginBottom: 4 }}>
                  🎵 TikTok
                </p>
                <p style={{ color: "#6b6b8a", fontSize: 12 }}>
                  Video ID: {video.tiktok_video_id}
                </p>
                {video.tiktok_short_link && (
                  <a
                    href={video.tiktok_short_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#6c5ce7", textDecoration: "none", fontWeight: 600 }}
                  >
                    Ver short link →
                  </a>
                )}
              </div>
            )}

            {video.youtube_video_id && (
              <div style={{ marginBottom: 16, padding: 12, background: "#fef3f2", borderRadius: 8 }}>
                <p style={{ color: "#1a1a2e", fontWeight: 700, marginBottom: 4 }}>
                  📺 YouTube
                </p>
                <p style={{ color: "#6b6b8a", fontSize: 12 }}>
                  Video ID: {video.youtube_video_id}
                </p>
                {video.youtube_short_link && (
                  <a
                    href={video.youtube_short_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#6c5ce7", textDecoration: "none", fontWeight: 600 }}
                  >
                    Ver short link →
                  </a>
                )}
              </div>
            )}

            <button
              onClick={() => {
                setStep("upload");
                setFile(null);
                setVideo(null);
                setError(null);
              }}
              style={S.btn(false)}
            >
              Publicar outro vídeo
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
