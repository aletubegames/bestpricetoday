/**
 * lib/api.ts — Fonte única de verdade para a URL base da API.
 *
 * TODOS os arquivos do frontend devem importar daqui:
 *   import { API_BASE } from "@/lib/api";
 *
 * Nunca declare `process.env.NEXT_PUBLIC_API_URL || "..."` diretamente
 * em nenhuma outra página, hook ou componente.
 */
import axios from "axios";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://sacrament-subduing-confined.ngrok-free.dev";

// Necessário para evitar a página de interstitial do ngrok em produção.
// O header ngrok-skip-browser-warning instrui o ngrok a passar a requisição
// diretamente ao backend sem exibir a página de aviso HTML.
axios.defaults.headers.common["ngrok-skip-browser-warning"] = "true";

/**
 * Wrapper sobre fetch() que adiciona automaticamente os headers necessários
 * para o ngrok e outros headers comuns. Use este em vez de fetch() direto
 * para qualquer chamada ao backend.
 */
export function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  headers.set("ngrok-skip-browser-warning", "true");
  return fetch(url, { ...options, headers });
}
