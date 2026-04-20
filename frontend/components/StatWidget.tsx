"use client";

interface StatWidgetProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "cyan" | "green" | "purple" | "red";
  index?: number;
}

const ACCENT_MAP = {
  cyan:   { text: "text-cyber-cyan",  border: "border-cyber-cyan/30",  bg: "bg-cyber-cyan/5"  },
  green:  { text: "text-cyber-green", border: "border-cyber-green/30", bg: "bg-cyber-green/5" },
  purple: { text: "text-purple-400",  border: "border-purple-500/30",  bg: "bg-purple-500/5"  },
  red:    { text: "text-cyber-red",   border: "border-cyber-red/30",   bg: "bg-cyber-red/5"   },
};

export default function StatWidget({ label, value, sub, accent = "cyan", index = 0 }: StatWidgetProps) {
  const a = ACCENT_MAP[accent];
  return (
    <div
      className={`cyber-card rounded-none px-5 py-4 animate-fade-up opacity-0 border ${a.border} ${a.bg}`}
      style={{ animationDelay: `${index * 100}ms`, animationFillMode: "forwards" }}
    >
      <div className="font-mono text-[10px] tracking-widest text-cyber-muted uppercase mb-1">{label}</div>
      <div className={`font-orbitron text-2xl font-bold ${a.text} text-glow-cyan leading-none mb-1`}>
        {value}
      </div>
      {sub && <div className="font-mono text-[10px] text-cyber-muted">{sub}</div>}
    </div>
  );
}
