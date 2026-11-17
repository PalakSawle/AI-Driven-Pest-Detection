import { Loader2, Mail } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Logo } from "../components/Layout";
import { ErrorBox } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

function Shell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-3xl font-semibold">{title}</h1>
          <p className="muted mt-2 text-sm">{subtitle}</p>
          <div className="mt-8">{children}</div>
          {footer && <div className="muted mt-6 text-center text-sm">{footer}</div>}
        </div>
      </div>
      <div className="relative hidden overflow-hidden bg-forest-900 lg:block">
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "radial-gradient(circle at 30% 30%, #97c09c 0, transparent 45%)" }} />
        <div className="relative flex h-full flex-col justify-end p-12 text-white">
          <blockquote className="font-display text-3xl leading-snug">"खेत की निगरानी जितनी जल्दी, नुकसान उतना कम।"</blockquote>
          <p className="mt-3 text-forest-200">Early scouting means smaller losses — and fewer sprays.</p>
        </div>
      </div>
    </div>
  );
}

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await login(email, password); nav(loc.state?.from ?? "/app", { replace: true }); } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };
  return (
    <Shell title="Welcome back" subtitle="Log in to see your scans, alerts and treatment plans." footer={<>New to AgriGuard? <Link className="font-semibold text-forest-700 dark:text-forest-300" to="/register">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        {err && <ErrorBox message={err} />}
        <div><label className="label" htmlFor="email">Email</label><input id="email" type="email" autoComplete="email" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div>
          <div className="flex justify-between"><label className="label" htmlFor="pw">Password</label><Link to="/forgot-password" className="text-xs font-semibold text-forest-700 dark:text-forest-300">Forgot?</Link></div>
          <input id="pw" type="password" autoComplete="current-password" required className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className="btn-primary w-full" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Log in</button>
      </form>
    </Shell>
  );
}

export function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ full_name: "", email: "", phone: "", password: "", language: "hinglish" });
  const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await register({ ...f, phone: f.phone || undefined }); nav("/app/profile?welcome=1", { replace: true }); } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };
  return (
    <Shell title="Create your account" subtitle="Free for farmers. Your scans stay private to you." footer={<>Already registered? <Link className="font-semibold text-forest-700 dark:text-forest-300" to="/login">Log in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        {err && <ErrorBox message={err} />}
        <div><label className="label" htmlFor="name">Full name</label><input id="name" required minLength={2} className="input" value={f.full_name} onChange={set("full_name")} /></div>
        <div><label className="label" htmlFor="remail">Email</label><input id="remail" type="email" required className="input" value={f.email} onChange={set("email")} /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label" htmlFor="phone">Phone (optional)</label><input id="phone" className="input" value={f.phone} onChange={set("phone")} /></div>
          <div><label className="label" htmlFor="lang">Language</label>
            <select id="lang" className="input" value={f.language} onChange={set("language")}><option value="hinglish">Hinglish</option><option value="hi">हिंदी</option><option value="en">English</option></select></div>
        </div>
        <div><label className="label" htmlFor="rpw">Password</label><input id="rpw" type="password" autoComplete="new-password" required minLength={8} className="input" value={f.password} onChange={set("password")} /><p className="muted mt-1 text-xs">At least 8 characters.</p></div>
        <button className="btn-primary w-full" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Create account</button>
      </form>
    </Shell>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState(""); const [done, setDone] = useState<string | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { const r = await api.post<{ message: string; dev_reset_link?: string }>("/api/auth/forgot-password", { email }); setDone(r.message); setDevLink(r.dev_reset_link ?? null); }
    catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };
  return (
    <Shell title="Reset your password" subtitle="We'll email you a link to choose a new password." footer={<Link className="font-semibold text-forest-700 dark:text-forest-300" to="/login">Back to log in</Link>}>
      {done ? (
        <div className="rounded-2xl bg-forest-50 p-5 text-sm dark:bg-white/5"><Mail className="mb-2 h-5 w-5 text-forest-600" />{done}
          {devLink && <p className="mt-3 text-xs">Development mode (no email server configured): <a className="break-all font-semibold underline" href={devLink.replace(/^https?:\/\/[^/]+/, "")}>open reset link</a></p>}
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {err && <ErrorBox message={err} />}
          <div><label className="label" htmlFor="femail">Email</label><input id="femail" type="email" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <button className="btn-primary w-full" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Send reset link</button>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [pw, setPw] = useState(""); const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await api.post("/api/auth/reset-password", { token: params.get("token"), new_password: pw }); nav("/login"); } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };
  return (
    <Shell title="Choose a new password" subtitle="Use at least 8 characters.">
      <form onSubmit={submit} className="space-y-4">
        {err && <ErrorBox message={err} />}
        <div><label className="label" htmlFor="npw">New password</label><input id="npw" type="password" minLength={8} required className="input" value={pw} onChange={(e) => setPw(e.target.value)} /></div>
        <button className="btn-primary w-full" disabled={busy || !params.get("token")}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Update password</button>
      </form>
    </Shell>
  );
}
