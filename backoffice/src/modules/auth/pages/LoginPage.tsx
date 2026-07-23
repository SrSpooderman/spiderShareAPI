import { KeyRound, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/modules/auth/AuthContext";
import { rememberOidcReturnTo } from "@/modules/auth/pages/OidcCallbackPage";

export function LoginPage() {
  const { isAuthenticated, login, startOidcLogin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [ssoError, setSsoError] = useState<string | null>(null);
  const [isSubmittingLocal, setIsSubmittingLocal] = useState(false);
  const [isStartingSso, setIsStartingSso] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleLocalLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    setIsSubmittingLocal(true);

    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch {
      setLocalError("No se pudo iniciar sesion con esas credenciales.");
    } finally {
      setIsSubmittingLocal(false);
    }
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
        <p>Acceso operativo para administracion, colas, worker y auditoria.</p>

        <button className="button primary" disabled={isStartingSso} onClick={handleSsoLogin} type="button">
          <KeyRound size={16} />
          {isStartingSso ? "Redirigiendo..." : "Continuar con SSO"}
        </button>
        {ssoError ? <p className="form-error">{ssoError}</p> : null}

        <div className="login-divider" role="separator">
          <span>o entra con usuario local</span>
        </div>

        <form className="login-local-form" onSubmit={handleLocalLogin}>
          <label className="field">
            <span>Usuario</span>
            <input
              autoComplete="username"
              name="username"
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>

          <label className="field">
            <span>Contrasena</span>
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {localError ? <p className="form-error">{localError}</p> : null}

          <button className="button ghost" disabled={isSubmittingLocal} type="submit">
            {isSubmittingLocal ? "Entrando..." : "Entrar con usuario local"}
          </button>
        </form>
      </section>
    </main>
  );
}
