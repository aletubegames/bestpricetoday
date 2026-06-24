/**
 * lib/api.ts — Fonte única de verdade para a URL base da API.
 *
 * TODOS os arquivos do frontend devem importar daqui:
 *   import { API_BASE } from "@/lib/api";
 *
 * Nunca declare `process.env.NEXT_PUBLIC_API_URL || "..."` diretamente
 * em nenhuma outra página, hook ou componente.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://alessandro2090-bestpricetoday-api.hf.space";
