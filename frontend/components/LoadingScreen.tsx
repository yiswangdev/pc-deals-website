"use client";

export function DealCardSkeleton() {
  return (
    <div className="cyber-card rounded-none p-5 opacity-60">
      <div className="flex items-start gap-3 mb-3">
        <div className="skeleton w-8 h-8 rounded" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-3 w-3/4 rounded" />
          <div className="skeleton h-3 w-1/2 rounded" />
        </div>
      </div>
      <div className="skeleton h-2 w-full rounded mb-2" />
      <div className="skeleton h-2 w-5/6 rounded mb-4" />
      <div className="flex gap-2">
        <div className="skeleton h-5 w-16 rounded" />
        <div className="skeleton h-5 w-20 rounded" />
      </div>
    </div>
  );
}

export function LoadingScreen() {
  return (
    <div className="fixed inset-0 z-[9999] bg-cyber-black flex flex-col items-center justify-center">
      <div className="circuit-bg opacity-30" />

      <div className="relative z-10 flex flex-col items-center gap-8">
        {/* Animated logo */}
        <div className="relative">
          <div className="w-16 h-16 border-2 border-cyber-cyan/30 rounded-full animate-spin" style={{ animationDuration: "3s" }} />
          <div className="absolute inset-2 border border-cyber-cyan/60 rounded-full animate-spin" style={{ animationDuration: "1.5s", animationDirection: "reverse" }} />
          <div className="absolute inset-4 bg-cyber-cyan/10 rounded-full animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-cyber-cyan font-orbitron text-xs font-bold">PC</span>
          </div>
        </div>

        <div className="font-orbitron text-cyber-cyan text-glow-cyan tracking-[0.3em] text-lg animate-flicker">
          PCDEALS
        </div>

        {/* Boot sequence */}
        <div className="font-mono text-xs text-cyber-muted space-y-1 text-left w-64">
          {[
            "INITIALIZING FEED PARSER...",
            "CONNECTING TO RSS ENDPOINTS...",
            "LOADING DEAL INDEX...",
            "SYSTEM READY",
          ].map((line, i) => (
            <div
              key={line}
              className="animate-fade-up opacity-0"
              style={{ animationDelay: `${i * 400}ms`, animationFillMode: "forwards" }}
            >
              <span className="text-cyber-green">›</span> {line}
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div className="w-64 h-px bg-cyber-border relative overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 bg-cyber-cyan"
            style={{ animation: "progressFill 1.8s ease-out forwards" }}
          />
        </div>
      </div>

      <style>{`
        @keyframes progressFill {
          0% { width: 0%; }
          100% { width: 100%; }
        }
      `}</style>
    </div>
  );
}
