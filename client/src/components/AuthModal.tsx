import React, { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { X, Lock, Mail, User as UserIcon, Loader2, Sparkles } from "lucide-react";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: "login" | "register";
}

export function AuthModal({ isOpen, onClose, initialMode = "login" }: AuthModalProps) {
  const { login, register, isLoading } = useAuth();
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Authentication failed. Please check credentials.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Dialog container */}
      <div className="relative w-full max-w-md overflow-hidden rounded-[28px] border border-line bg-white p-6 shadow-[0_24px_70px_rgba(26,31,23,.18)] sm:p-8">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-5 top-5 rounded-full p-2 text-ink/40 transition hover:bg-mist hover:text-ink"
          aria-label="Close dialog"
        >
          <X size={18} />
        </button>

        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-saffron">
          <Sparkles size={13} />
          {mode === "login" ? "Traveler Sign In" : "Join KhojAI"}
        </div>

        <h2 className="mt-2 font-display text-3xl tracking-[-0.04em] text-ink">
          {mode === "login" ? "Welcome back." : "Start your journey."}
        </h2>
        <p className="mt-1 text-xs text-ink/55">
          {mode === "login"
            ? "Access your saved itineraries, private field logs, and notes."
            : "Create an account to save offbeat routes and sync travel briefs."}
        </p>

        {/* Tab switcher */}
        <div className="mt-5 flex rounded-full bg-mist p-1">
          <button
            type="button"
            onClick={() => { setMode("login"); setError(null); }}
            className={`flex-1 rounded-full py-2 text-xs font-semibold transition ${
              mode === "login" ? "bg-white text-ink shadow-sm" : "text-ink/55 hover:text-ink"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setError(null); }}
            className={`flex-1 rounded-full py-2 text-xs font-semibold transition ${
              mode === "register" ? "bg-white text-ink shadow-sm" : "text-ink/55 hover:text-ink"
            }`}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {mode === "register" && (
            <div>
              <label className="mb-1 block text-xs font-semibold text-ink/70">Full Name</label>
              <div className="relative">
                <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink/35" size={16} />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Aarav Patel"
                  className="h-11 w-full rounded-xl border border-line bg-paper pl-10 pr-3 text-sm outline-none transition focus:border-saffron"
                />
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-semibold text-ink/70">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink/35" size={16} />
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="h-11 w-full rounded-xl border border-line bg-paper pl-10 pr-3 text-sm outline-none transition focus:border-saffron"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-ink/70">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink/35" size={16} />
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-11 w-full rounded-xl border border-line bg-paper pl-10 pr-3 text-sm outline-none transition focus:border-saffron"
              />
            </div>
            {mode === "register" && (
              <p className="mt-1 text-[10px] text-ink/40">
                Min 8 characters, with letters and numbers.
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-6 flex h-12 w-full items-center justify-center gap-2 rounded-full bg-saffron text-sm font-semibold text-white shadow-md transition hover:bg-[#b95a36] active:scale-[0.99] disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                Processing...
              </>
            ) : mode === "login" ? (
              "Sign In to KhojAI"
            ) : (
              "Create My Account"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
