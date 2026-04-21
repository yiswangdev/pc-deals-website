"use client";

import Link from "next/link";
import { ExternalLink, Clock } from "lucide-react";

interface DealCardProps {
  id: string;
  title: string;
  link: string;
  source: string;
  category: string;
  published: string;
  summary?: string;
  price?: string | null;
  image?: string | null;
  product_link?: string | null;
  index?: number;
}

// Fully opaque, saturated badges — no transparency fighting the image
const CATEGORY_STYLES: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  GPU:         { bg: "bg-cyan-500",    text: "text-black",    border: "border-cyan-300",    dot: "bg-cyan-300" },
  CPU:         { bg: "bg-green-500",   text: "text-black",    border: "border-green-300",   dot: "bg-green-300" },
  RAM:         { bg: "bg-purple-500",  text: "text-white",    border: "border-purple-300",  dot: "bg-purple-300" },
  SSD:         { bg: "bg-yellow-400",  text: "text-black",    border: "border-yellow-200",  dot: "bg-yellow-200" },
  Motherboard: { bg: "bg-sky-500",     text: "text-black",    border: "border-sky-300",     dot: "bg-sky-300" },
  PSU:         { bg: "bg-orange-500",  text: "text-black",    border: "border-orange-300",  dot: "bg-orange-300" },
  Cooling:     { bg: "bg-blue-500",    text: "text-white",    border: "border-blue-300",    dot: "bg-blue-300" },
  Monitor:     { bg: "bg-pink-500",    text: "text-white",    border: "border-pink-300",    dot: "bg-pink-300" },
  Other:       { bg: "bg-slate-600",   text: "text-white",    border: "border-slate-400",   dot: "bg-slate-400" },
};

function timeAgo(dateString: string) {
  const date = new Date(dateString).getTime();
  if (Number.isNaN(date)) return "UNKNOWN";

  const diff = Math.floor((Date.now() - date) / 1000);
  if (diff < 60) return `${diff}s AGO`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m AGO`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h AGO`;
  return `${Math.floor(diff / 86400)}d AGO`;
}

function getFallbackImage(title: string, category: string) {
  const label = encodeURIComponent(category || "PC DEAL");
  const text = encodeURIComponent(title.slice(0, 42));
  return `https://placehold.co/800x500/0a0f1c/00e5ff?text=${label}%0A${text}`;
}

export default function DealCard({
  title,
  link,
  category,
  published,
  summary,
  price,
  image,
  product_link,
  index = 0,
}: DealCardProps) {
  const delay = `${Math.min(index * 60, 400)}ms`;
  const imageSrc = image || getFallbackImage(title, category);
  const style = CATEGORY_STYLES[category] ?? CATEGORY_STYLES.Other;
  const href = product_link || link;

  return (
    <Link
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="relative cyber-card rounded-none overflow-hidden block animate-fade-up opacity-0 hover:-translate-y-0.5 transition-all duration-200"
      style={{ animationDelay: delay, animationFillMode: "forwards" }}
    >
      <div className="relative w-full h-40 bg-cyber-dark border-b border-cyber-border overflow-hidden">
        <img
          src={imageSrc}
          alt={title}
          className="w-full h-full object-cover"
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(e) => {
            const target = e.currentTarget;
            const fallback = getFallbackImage(title, category);
            if (target.src !== fallback) target.src = fallback;
          }}
        />

        <div className="absolute top-2 left-2 z-10">
          <span
            className={`inline-flex items-center gap-1 px-2 py-1 font-mono text-[10px] font-bold tracking-wider border ${style.bg} ${style.text} ${style.border}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${style.dot} opacity-80`} />
            {category.toUpperCase()}
          </span>
        </div>

        {price && (
          <div className="absolute bottom-2 right-2 z-10">
            <span className="inline-flex items-center border border-cyber-green/50 bg-black/90 px-2 py-1 font-mono text-xs text-cyber-green font-bold shadow-lg">
              {price}
            </span>
          </div>
        )}
      </div>

      <div className="p-4 space-y-3">
        <div className="min-h-[48px]">
          <h3 className="font-orbitron text-sm text-white tracking-wide leading-5 line-clamp-2">
            {title}
          </h3>
        </div>

        {summary && (
          <p className="font-mono text-xs text-cyber-muted leading-5 line-clamp-3">
            {summary}
          </p>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-cyber-border">
          <div className="flex items-center gap-1.5 font-mono text-[10px] text-cyber-muted tracking-wider">
            <Clock size={10} />
            {timeAgo(published)}
          </div>

          <div className="flex items-center gap-1 font-mono text-[10px] text-cyber-cyan tracking-wider">
            OPEN <ExternalLink size={10} />
          </div>
        </div>
      </div>
    </Link>
  );
}