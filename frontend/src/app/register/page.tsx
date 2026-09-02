"use client";

import { Stamp } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register, user } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace("/analyze");
  }, [user, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await register(email, password, fullName);
      router.push("/analyze");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create your account.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[var(--color-ink)] px-6 text-[var(--color-paper)]">
      <div className="w-full max-w-sm">
        <Link href="/" className="mb-8 flex items-center justify-center gap-2">
          <Stamp size={22} className="text-[var(--color-signal)]" />
          <span className="font-display text-xl font-semibold">Verafide</span>
        </Link>
        <div className="bg-grain card p-8">
          <h1 className="font-display text-2xl font-semibold">Open a case</h1>
          <p className="mt-1 text-sm text-[var(--color-slate)]">Create your desk account — free, no credit card.</p>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <Field label="Name" type="text" value={fullName} onChange={setFullName} placeholder="Jamie Reyes" required={false} />
            <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="you@newsroom.com" />
            <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" />
            {error && <p className="text-sm text-[var(--color-flagged)]">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-md bg-[var(--color-signal)] py-2.5 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.01] disabled:opacity-60"
            >
              {busy ? "Creating account…" : "Create account"}
            </button>
          </form>
        </div>
        <p className="mt-6 text-center text-sm text-[var(--color-slate)]">
          Already have a desk?{" "}
          <Link href="/login" className="font-medium text-[var(--color-signal)]">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  placeholder,
  required = true,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="mb-1.5 block font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">{label}</label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-signal)]"
      />
    </div>
  );
}
