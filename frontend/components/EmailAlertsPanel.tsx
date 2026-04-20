"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { Bell, Lock, Send, ToggleLeft, ToggleRight, CheckCircle } from "lucide-react";

const ALL_CATEGORIES = ["GPU", "CPU", "RAM", "SSD", "Motherboard", "PSU", "Cooling", "Monitor", "Other"];
const DEFAULT_CATEGORIES = ["GPU", "CPU", "RAM", "SSD"];
const API = process.env.NEXT_PUBLIC_API_URL || "/api";

export default function EmailAlertsPanel() {
  const { user, token, loading: authLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [enabled, setEnabled] = useState(false);
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    if (user?.alert_config) {
      setEnabled(Boolean(user.alert_config.enabled));
      setCategories(
        user.alert_config.categories?.length ? user.alert_config.categories : DEFAULT_CATEGORIES
      );
      return;
    }

    setEnabled(false);
    setCategories(DEFAULT_CATEGORIES);
  }, [user]);

  const toggleCat = (cat: string) => {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const canSave = !saving && !!token && (!enabled || categories.length > 0);

  const save = async () => {
    if (!token || !canSave) return;

    setSaving(true);
    setSaved(false);

    try {
      const res = await fetch(`${API}/alerts/config`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled, categories }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to save");

      await refreshUser();
      setSaved(true);
      setTestResult({
        ok: true,
        msg: data.initial_alert_sent ? "Config saved. Initial alert sent." : "Config saved.",
      });
      setTimeout(() => setSaved(false), 2500);
    } catch {
      alert("Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  const sendTest = async () => {
    if (!token || !enabled) return;

    setTesting(true);
    setTestResult(null);

    try {
      const res = await fetch(`${API}/alerts/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setTestResult({ ok: res.ok, msg: res.ok ? data.message : data.detail });
    } catch {
      setTestResult({ ok: false, msg: "Network error" });
    } finally {
      setTesting(false);
      setTimeout(() => setTestResult(null), 5000);
    }
  };

  if (!authLoading && !user) {
    return (
      <div className="cyber-card rounded-none p-8 text-center border-cyber-border/50">
        <div className="mb-4">
          <Lock size={32} className="text-cyber-muted mx-auto mb-3" />
          <div className="font-orbitron text-sm text-white tracking-wider mb-1">
            EMAIL ALERTS
          </div>
          <p className="font-mono text-xs text-cyber-muted">
            Login or create an account to configure deal alerts sent directly to your inbox.
          </p>
        </div>
        <div className="flex gap-3 justify-center mt-6">
          <button onClick={() => router.push("/login")} className="btn-cyber">
            LOGIN
          </button>
          <button onClick={() => router.push("/register")} className="btn-cyber-green btn-cyber">
            REGISTER
          </button>
        </div>
      </div>
    );
  }

  if (authLoading) {
    return (
      <div className="cyber-card rounded-none p-8">
        <div className="skeleton h-4 w-32 mb-4 rounded" />
        <div className="skeleton h-24 rounded" />
      </div>
    );
  }

  return (
    <div className="cyber-card rounded-none p-5">
      <div className="flex items-center gap-2 border-b border-cyber-border pb-3 mb-5">
        <Bell size={13} className="text-cyber-cyan" />
        <span className="font-orbitron text-xs tracking-widest text-cyber-cyan">EMAIL_ALERTS</span>
      </div>

      <div
        className="flex items-center justify-between py-3 border-b border-cyber-border/40 cursor-pointer group hover:bg-cyber-cyan/3 px-1 transition-colors"
        onClick={() => setEnabled((e) => !e)}
      >
        <div>
          <div className={`font-mono text-xs transition-colors ${enabled ? "text-white" : "text-cyber-muted"}`}>
            Enable Email Alerts
          </div>
          <div className="font-mono text-[10px] text-cyber-muted/60">
            Get notified when new deals match your filters
          </div>
        </div>
        <div className={`transition-colors ${enabled ? "text-cyber-green" : "text-cyber-muted/40"}`}>
          {enabled ? <ToggleRight size={24} strokeWidth={1.5} /> : <ToggleLeft size={24} strokeWidth={1.5} />}
        </div>
      </div>

      <div className="py-4 border-b border-cyber-border/40">
        <div className="font-mono text-[10px] text-cyber-muted tracking-widest mb-3">
          ALERT_CATEGORIES // select which deal types to receive
        </div>
        <div className="flex flex-wrap gap-2">
          {ALL_CATEGORIES.map((cat) => {
            const active = categories.includes(cat);
            return (
              <button
                key={cat}
                onClick={() => toggleCat(cat)}
                disabled={!enabled}
                className={`font-mono text-[10px] tracking-wider px-3 py-1.5 border transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed
                  ${active
                    ? "border-cyber-cyan/60 text-cyber-cyan bg-cyber-cyan/10"
                    : "border-cyber-border text-cyber-muted hover:border-cyber-cyan/30"
                  }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
        {categories.length === 0 && enabled && (
          <p className="font-mono text-[10px] text-cyber-red mt-2">Select at least one category</p>
        )}
      </div>

      <div className="py-3 border-b border-cyber-border/40">
        <div className="font-mono text-[10px] text-cyber-muted space-y-1">
          <div>DELIVERY: <span className="text-white">Initial send on enable + every day at 8:00 AM</span></div>
          <div>CONTENT: <span className="text-white">Top 10 matching deals + site link</span></div>
          <div>ACCOUNT: <span className="text-white">{user?.email}</span></div>
        </div>
      </div>

      {testResult && (
        <div className={`mt-3 px-4 py-2 font-mono text-xs border ${testResult.ok
          ? "border-cyber-green/40 bg-cyber-green/5 text-cyber-green"
          : "border-cyber-red/40 bg-cyber-red/5 text-cyber-red"
        }`}>
          {testResult.ok ? "✓" : "⚠"} {testResult.msg}
        </div>
      )}

      <div className="flex gap-3 mt-5">
        <button
          onClick={save}
          disabled={!canSave}
          className={`btn-cyber flex items-center gap-2 disabled:opacity-40 ${saved ? "btn-cyber-green" : ""}`}
        >
          {saved ? <CheckCircle size={11} /> : null}
          {saving ? "SAVING..." : saved ? "SAVED ✓" : "SAVE AND SEND INITIAL ALERT"}
        </button>
        <button
          onClick={sendTest}
          disabled={testing || !enabled || !token}
          className="btn-cyber flex items-center gap-2 disabled:opacity-40"
        >
          <Send size={11} />
          {testing ? "SENDING..." : "SEND TEST ALERT"}
        </button>
      </div>
    </div>
  );
}
