import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/shared/api/httpClient";
import {
  AUTH_TOKEN_CHANGED,
  clearStoredToken,
  getStoredToken,
  getStoredUser,
  storeToken,
  storeUser
} from "@/modules/auth/authStorage";
import { UserRole } from "@/shared/types/backoffice";

type AuthUser = {
  id: string;
  username: string;
  role: UserRole;
};

type LoginResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

type OidcAuthorizeResponse = {
  authorization_url: string;
  state: string;
};

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  login: (username: string, password: string) => Promise<void>;
  startOidcLogin: (returnTo: string) => Promise<void>;
  completeOidcLogin: (code: string, state: string, redirectUri: string) => Promise<void>;
  completeOidcRedirect: (accessToken: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser<AuthUser>());

  useEffect(() => {
    const syncToken = () => {
      setToken(getStoredToken());
      setUser(getStoredUser<AuthUser>());
    };

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
      user,
      isAuthenticated: Boolean(token),
      isSuperAdmin: user?.role === "super_admin",
      async login(username, password) {
        const response = await apiRequest<LoginResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
          skipAuth: true
        });
        storeToken(response.access_token);
        storeUser(response.user);
        setToken(response.access_token);
        setUser(response.user);
      },
      async startOidcLogin(returnTo) {
        const response = await apiRequest<OidcAuthorizeResponse>(
          `/auth/oidc/authorize?return_to=${encodeURIComponent(returnTo)}`,
          { skipAuth: true }
        );
        window.location.assign(response.authorization_url);
      },
      async completeOidcLogin(code, state, redirectUri) {
        const response = await apiRequest<LoginResponse>("/auth/oidc/callback", {
          method: "POST",
          body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
          skipAuth: true
        });
        storeToken(response.access_token);
        storeUser(response.user);
        setToken(response.access_token);
        setUser(response.user);
      },
      async completeOidcRedirect(accessToken) {
        storeToken(accessToken);
        setToken(accessToken);

        try {
          const currentUser = await apiRequest<AuthUser>("/auth/me");
          storeUser(currentUser);
          setUser(currentUser);
        } catch (error) {
          clearStoredToken();
          setToken(null);
          setUser(null);
          throw error;
        }
      },
      logout() {
        clearStoredToken();
        setToken(null);
        setUser(null);
      }
    }),
    [token, user]
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
