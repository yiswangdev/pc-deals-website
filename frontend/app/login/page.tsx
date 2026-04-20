"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { LogIn, Eye, EyeOff, Cpu } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/settings");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div
        className="cyber-card rounded-none w-full max-w-md p-8 animate-fade-up opacity-0"
        style={{ animationFillMode: "forwards" }}
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="relative">
            <Cpu size={22} className="text-cyber-cyan" strokeWidth={1.5} />
            <div className="absolute inset-0 blur-sm bg-cyber-cyan opacity-30 rounded-full" />
          </div>
          <div>
            <h1 className="font-orbitron text-lg font-bold text-white tracking-wider">
              SYSTEM <span className="text-cyber-cyan text-glow-cyan">LOGIN</span>
            </h1>
            <p className="font-mono text-[10px] text-cyber-muted tracking-widest">
              AUTH_PORTAL // ENTER CREDENTIALS
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 border border-cyber-red/40 bg-cyber-red/5 px-4 py-2 font-mono text-xs text-cyber-red">
            ⚠ {error}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="font-mono text-[10px] text-cyber-muted tracking-widest block mb-1">
              EMAIL_ADDRESS
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="user@domain.com"
              className="w-full bg-cyber-dark border border-cyber-border focus:border-cyber-cyan/50 text-white font-mono text-xs placeholder:text-cyber-muted/40 py-2.5 px-3 outline-none transition-colors"
            />
          </div>

          <div>
            <label className="font-mono text-[10px] text-cyber-muted tracking-widest block mb-1">
              PASSWORD
            </label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Enter password"
                className="w-full bg-cyber-dark border border-cyber-border focus:border-cyber-cyan/50 text-white font-mono text-xs placeholder:text-cyber-muted/40 py-2.5 px-3 pr-10 outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPw((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-cyber-muted hover:text-cyber-cyan transition-colors"
              >
                {showPw ? <EyeOff size={13} /> : <Eye size={13} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-cyber w-full flex items-center justify-center gap-2 py-2.5 mt-2 disabled:opacity-40"
          >
            <LogIn size={12} />
            {loading ? "AUTHENTICATING..." : "LOGIN"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-cyber-border text-center">
          <span className="font-mono text-[10px] text-cyber-muted">NO ACCOUNT? </span>
          <Link href="/register" className="font-mono text-[10px] text-cyber-cyan hover:underline">
            REGISTER HERE →
          </Link>
        </div>
      </div>
    </div>
  );
}
