"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { UserPlus, Eye, EyeOff, Cpu } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) { setError("Passwords do not match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await register(email, password);
      router.push("/settings");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const strength = password.length === 0 ? 0 : password.length < 8 ? 1 : password.length < 12 ? 2 : 3;
  const strengthLabel = ["", "WEAK", "MODERATE", "STRONG"][strength];
  const strengthColor = ["", "text-cyber-red", "text-yellow-400", "text-cyber-green"][strength];

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div
        className="cyber-card rounded-none w-full max-w-md p-8 animate-fade-up opacity-0"
        style={{ animationFillMode: "forwards" }}
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="relative">
            <Cpu size={22} className="text-cyber-green" strokeWidth={1.5} />
            <div className="absolute inset-0 blur-sm bg-cyber-green opacity-30 rounded-full" />
          </div>
          <div>
            <h1 className="font-orbitron text-lg font-bold text-white tracking-wider">
              CREATE <span className="text-cyber-green text-glow-green">ACCOUNT</span>
            </h1>
            <p className="font-mono text-[10px] text-cyber-muted tracking-widest">REGISTER FOR DEAL ALERTS</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 border border-cyber-red/40 bg-cyber-red/5 px-4 py-2 font-mono text-xs text-cyber-red">
            ⚠ {error}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="font-mono text-[10px] text-cyber-muted tracking-widest block mb-1">EMAIL_ADDRESS</label>
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
            <div className="flex justify-between mb-1">
              <label className="font-mono text-[10px] text-cyber-muted tracking-widest">PASSWORD</label>
              {strength > 0 && (
                <span className={`font-mono text-[10px] ${strengthColor}`}>{strengthLabel}</span>
              )}
            </div>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Min. 8 characters"
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
            {/* Strength bar */}
            <div className="flex gap-1 mt-1.5">
              {[1, 2, 3].map((l) => (
                <div
                  key={l}
                  className="h-0.5 flex-1 rounded transition-all duration-300"
                  style={{
                    background: strength >= l
                      ? l === 1 ? "#ff2d55" : l === 2 ? "#ffd60a" : "#00ff88"
                      : "#0d2137",
                  }}
                />
              ))}
            </div>
          </div>

          <div>
            <label className="font-mono text-[10px] text-cyber-muted tracking-widest block mb-1">CONFIRM_PASSWORD</label>
            <input
              type={showPw ? "text" : "password"}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              placeholder="Repeat password"
              className={`w-full bg-cyber-dark border text-white font-mono text-xs placeholder:text-cyber-muted/40 py-2.5 px-3 outline-none transition-colors
                ${confirm && confirm !== password ? "border-cyber-red/60" : "border-cyber-border focus:border-cyber-cyan/50"}`}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-cyber-green btn-cyber w-full flex items-center justify-center gap-2 py-2.5 mt-2 disabled:opacity-40"
          >
            <UserPlus size={12} />
            {loading ? "CREATING ACCOUNT..." : "REGISTER"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-cyber-border text-center">
          <span className="font-mono text-[10px] text-cyber-muted">ALREADY HAVE AN ACCOUNT? </span>
          <Link href="/login" className="font-mono text-[10px] text-cyber-cyan hover:underline">
            LOGIN HERE →
          </Link>
        </div>
      </div>
    </div>
  );
}
