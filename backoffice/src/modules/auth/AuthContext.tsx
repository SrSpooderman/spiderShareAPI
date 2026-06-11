import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/shared/api/httpClient";
import { AUTH_TOKEN_CHANGED, clearStoredToken, getStoredToken, storeToken } from "@/modules/auth/authStorage";

type LoginResponse = {
  access_token: string;
  token_type: string;
};

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());

  useEffect(() => {
    const syncToken = () => setToken(getStoredToken());

    window.addEventListener(AUTH_TOKEN_CHANGED, syncToken);
    window.addEventListener("storage", syncToken);

    return () => {
      window.removeEventListener(AUTH_TOKEN_CHANGED, syncToken);
      window.removeEventListener("storage", syncToken);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      async login(username, password) {
        const response = await apiRequest<LoginResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
          skipAuth: true
        });
        storeToken(response.access_token);
        setToken(response.access_token);
      },
      logout() {
        clearStoredToken();
        setToken(null);
      }
    }),
    [token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
