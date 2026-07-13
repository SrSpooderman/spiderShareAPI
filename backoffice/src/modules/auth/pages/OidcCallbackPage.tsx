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

export function OidcCallbackPage() {
  const { completeOidcLogin, isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const redirectUri = `${window.location.origin}/login/oidc/callback`;

    if (!code || !state) {
      setError("No se pudo completar el login con SSO.");
      return;
    }

    completeOidcLogin(code, state, redirectUri)
      .then(() => navigate(consumeOidcReturnTo(), { replace: true }))
      .catch(() => setError("No se pudo completar el login con SSO."));
  }, [completeOidcLogin, navigate, searchParams]);

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
