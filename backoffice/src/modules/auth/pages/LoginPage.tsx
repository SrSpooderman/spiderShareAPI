import { ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

export function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-panel">
        <ShieldCheck size={32} />
        <h1>SpiderShare Backoffice</h1>
        <p>
          La autenticacion real se conectara al endpoint de login existente. De momento el
          panel arranca en modo mock para desarrollar la interfaz sin tocar el backend.
        </p>
        <Link className="button primary" to="/dashboard">
          Entrar al panel
        </Link>
      </section>
    </main>
  );
}
