import { KeyRound, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/modules/auth/AuthContext";
import { rememberOidcReturnTo } from "@/modules/auth/pages/OidcCallbackPage";

export function LoginPage() {
  const { isAuthenticated, startOidcLogin } = useAuth();
  const location = useLocation();
  const [ssoError, setSsoError] = useState<string | null>(null);
  const [isStartingSso, setIsStartingSso] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleSsoLogin() {
    setSsoError(null);
    setIsStartingSso(true);
    rememberOidcReturnTo(from);

    try {
      await startOidcLogin(new URL(from, window.location.origin).toString());
    } catch {
      setSsoError("No se pudo iniciar el login con SSO.");
      setIsStartingSso(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <ShieldCheck size={32} />
        <h1>SpiderShare Backoffice</h1>
        <p>Acceso operativo mediante SSO corporativo.</p>

        <button className="button primary" disabled={isStartingSso} onClick={handleSsoLogin} type="button">
          <KeyRound size={16} />
          {isStartingSso ? "Redirigiendo..." : "Continuar con SSO"}
        </button>
        {ssoError ? <p className="form-error">{ssoError}</p> : null}
      </section>
    </main>
  );
}
