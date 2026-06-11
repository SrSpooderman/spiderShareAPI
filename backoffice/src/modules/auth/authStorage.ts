const TOKEN_KEY = "spidershare.backoffice.access_token";

export const AUTH_TOKEN_CHANGED = "spidershare:auth-token-changed";

export function getStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED));
}

export function clearStoredToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED));
}
