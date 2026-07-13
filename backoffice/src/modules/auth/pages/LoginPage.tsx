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
  const [error, setError] = useState<string | null>(null);
  const [ssoError, setSsoError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isStartingSso, setIsStartingSso] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch {
      setError("No se pudo iniciar sesion con esas credenciales.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSsoLogin() {
    setSsoError(null);
    setIsStartingSso(true);
    rememberOidcReturnTo(from);

    try {
      await startOidcLogin(`${window.location.origin}/login/oidc/callback`);
    } catch {
      setSsoError("No se pudo iniciar el login con SSO.");
      setIsStartingSso(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={handleSubmit}>
        <ShieldCheck size={32} />
        <h1>SpiderShare Backoffice</h1>
        <p>Acceso operativo para administracion, colas, worker y auditoria.</p>

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

        {error ? <p className="form-error">{error}</p> : null}

        <button className="button primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Entrando..." : "Entrar al panel"}
        </button>

        <button className="button ghost" disabled={isStartingSso} onClick={handleSsoLogin} type="button">
          <KeyRound size={16} />
          {isStartingSso ? "Redirigiendo..." : "Entrar con SSO"}
        </button>
        {ssoError ? <p className="form-error">{ssoError}</p> : null}
      </form>
    </main>
  );
}
