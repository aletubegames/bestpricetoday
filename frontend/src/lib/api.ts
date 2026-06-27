/**
 * lib/api.ts — Fonte única de verdade para URLs base do frontend.
 *
 * TODOS os arquivos do frontend devem importar daqui:
 *   import { API_BASE, SITE_BASE } from "@/lib/api";
 *
 * Nunca declare `process.env.NEXT_PUBLIC_API_URL || "..."` diretamente
 * em nenhuma outra página, hook ou componente.
 */
import axios from "axios";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://api.alaserver.com.br:9443";

/** URL pública do site (para canonical, redirects, OpenGraph) */
export const SITE_BASE =
  process.env.NEXT_PUBLIC_SITE_URL ||
  "https://bestpricetoday.alaserver.com.br:9443";

/**
 * Wrapper sobre fetch() que adiciona headers comuns.
 * Use este em vez de fetch() direto para qualquer chamada ao backend.
 */
export function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  return fetch(url, options);
}
