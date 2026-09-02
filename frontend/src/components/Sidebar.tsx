"use client";

import { BarChart3, History, LogOut, ScanSearch, Stamp, Upload, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/analyze", label: "Analyze", icon: ScanSearch },
  { href: "/history", label: "Case History", icon: History },
  { href: "/batch", label: "Batch Review", icon: Upload },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <>
      {open && (
        <button
          aria-label="Close menu"
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed z-40 flex h-dvh w-64 shrink-0 flex-col border-r border-[var(--color-line)] bg-[var(--color-ink-soft)] transition-transform md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-6 py-6">
          <Link href="/analyze" className="flex items-center gap-2">
            <Stamp size={22} className="text-[var(--color-signal)]" />
            <span className="font-display text-xl font-semibold tracking-tight">Verafide</span>
          </Link>
          <button className="text-[var(--color-slate)] md:hidden" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-[var(--color-signal)]/15 text-[var(--color-signal)]"
                    : "text-[var(--color-slate)] hover:bg-white/5 hover:text-[var(--color-paper)]"
                }`}
              >
                <Icon size={17} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="rule mx-3 px-3 py-4">
          <p className="truncate text-sm font-medium">{user?.full_name || user?.email}</p>
          <p className="truncate font-mono text-xs text-[var(--color-slate)]">{user?.email}</p>
          <button
            onClick={handleLogout}
            className="mt-3 flex items-center gap-2 text-xs font-medium text-[var(--color-slate)] transition-colors hover:text-[var(--color-flagged)]"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
