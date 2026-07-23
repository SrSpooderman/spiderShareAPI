import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "@/modules/auth/AuthContext";

const OIDC_RETURN_TO_KEY = "spidershare_oidc_return_to";

export function rememberOidcReturnTo(path: string) {
  sessionStorage.setItem(OIDC_RETURN_TO_KEY, path);
}

function consumeOidcReturnTo() {
  const path = sessionStorage.getItem(OIDC_RETURN_TO_KEY) ?? "/dashboard";
  sessionStorage.removeItem(OIDC_RETURN_TO_KEY);
  return path;
}

function safeReturnTo(path: string | null) {
  if (!path) {
    return "/dashboard";
  }

  try {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin) {
      return "/dashboard";
    }

    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return "/dashboard";
  }
}

export function OidcCallbackPage() {
  const { completeOidcLogin, completeOidcRedirect, isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (accessToken) {
      completeOidcRedirect(accessToken)
        .then(() => navigate(safeReturnTo(searchParams.get("return_to") ?? consumeOidcReturnTo()), { replace: true }))
        .catch(() => setError("No se pudo completar el login con SSO."));
      return;
    }

    if (!code || !state) {
      setError("No se pudo completar el login con SSO.");
      return;
    }

    completeOidcLogin(code, state)
      .then(() => navigate(consumeOidcReturnTo(), { replace: true }))
      .catch(() => setError("No se pudo completar el login con SSO."));
  }, [completeOidcLogin, completeOidcRedirect, navigate, searchParams]);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <h1>SpiderShare Backoffice</h1>
        <p>{error ?? "Completando login con SSO..."}</p>
      </section>
    </main>
  );
}
