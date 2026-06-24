/**
 * Decodifica o payload de um JWT e checa se está expirado.
 * Retorna true se o token é inválido/expirado, false se ainda válido.
 */
export function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return false; // sem expiração = não expira
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}
