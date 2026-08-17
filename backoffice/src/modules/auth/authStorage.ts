const TOKEN_KEY = "spidershare.backoffice.access_token";
const REFRESH_TOKEN_KEY = "spidershare.backoffice.refresh_token";
const USER_KEY = "spidershare.backoffice.user";

export const AUTH_TOKEN_CHANGED = "spidershare:auth-token-changed";

export function getStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED));
}

export function getStoredRefreshToken(): string | null {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function storeRefreshToken(token: string): void {
  window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED));
}

export function getStoredUser<T>(): T | null {
  const rawUser = window.localStorage.getItem(USER_KEY);
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as T;
  } catch {
    return null;
  }
}

export function storeUser(user: unknown): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED));
}

export function clearStoredToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED));
}
