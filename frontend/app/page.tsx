"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Zap,
  TrendingUp,
  RefreshCw,
  ArrowRight,
  Radio,
} from "lucide-react";
import StatWidget from "@/components/StatWidget";
import DealCard from "@/components/DealCard";
import { DealCardSkeleton } from "@/components/LoadingScreen";

interface Deal {
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
}

interface SourceStatus {
  name: string;
  deal_count: number;
  status: "LIVE" | "INACTIVE";
  uptime: "ACTIVE" | "INACTIVE";
}

interface DealsResponse {
  deals: Deal[];
  total: number;
  last_updated: string | null;
  categories: string[];
  sources: string[];
  source_statuses: SourceStatus[];
}

const CATEGORY_COLORS: Record<string, string> = {
  GPU: "text-cyber-cyan",
  CPU: "text-cyber-green",
  RAM: "text-purple-400",
  SSD: "text-yellow-400",
  Motherboard: "text-sky-400",
  PSU: "text-orange-400",
  Cooling: "text-blue-400",
  Monitor: "text-pink-400",
  Other: "text-cyber-muted",
};

export default function HomePage() {
  const [data, setData] = useState<DealsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tick, setTick] = useState(0);
  const [fetchFailed, setFetchFailed] = useState(false);

  const fetchDeals = async () => {
    try {
      setFetchFailed(false);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const json: DealsResponse = await res.json();
      setData(json);
    } catch (e) {
      console.error("Failed to fetch deals:", e);
      setFetchFailed(true);
    } finally {
      setLoading(false);
    }
  };

  const forceRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals/refresh`, {
        method: "POST",
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      await fetchDeals();
    } catch (e) {
      console.error("Failed to refresh deals:", e);
      setFetchFailed(true);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDeals();
    const interval = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const categoryBreakdown =
    data?.deals.reduce((acc: Record<string, number>, d) => {
      acc[d.category] = (acc[d.category] || 0) + 1;
      return acc;
    }, {}) ?? {};

  const displayedCategories = (data?.categories ?? []).map((cat) => ({
    name: cat,
    count: categoryBreakdown[cat] || 0,
  }));

  const recentDeals =
    [...(data?.deals ?? [])]
      .sort((a, b) => {
        const aTime = a.published ? new Date(a.published).getTime() : 0;
        const bTime = b.published ? new Date(b.published).getTime() : 0;
        return bTime - aTime;
      })
      .slice(0, 6);

  const uptime = `${String(Math.floor(tick / 3600)).padStart(2, "0")}:${String(
    Math.floor((tick % 3600) / 60)
  ).padStart(2, "0")}:${String(tick % 60).padStart(2, "0")}`;

  const feedSources = data?.sources ?? [];
  const feedStatuses = data?.source_statuses ?? [];

  const hasSync = Boolean(data?.last_updated);
  const dashboardActive = !loading && !fetchFailed && hasSync;

  const dashboardStatusLabel = dashboardActive ? "● ONLINE" : "● INACTIVE";
  const dashboardStatusClass = dashboardActive
    ? "text-cyber-green animate-pulse"
    : "text-red-400";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div className="animate-fade-up opacity-0" style={{ animationFillMode: "forwards" }}>
        <div className="flex items-center gap-2 mb-1">
          <Radio
            size={12}
            className={dashboardActive ? "text-cyber-green animate-pulse" : "text-red-400"}
          />
          <span
            className={`font-mono text-xs tracking-widest ${
              dashboardActive ? "text-cyber-green" : "text-red-400"
            }`}
          >
            LIVE DASHBOARD
          </span>
        </div>
        <h1 className="font-orbitron text-2xl sm:text-3xl font-bold text-white tracking-wider">
          SYSTEM <span className="text-cyber-cyan text-glow-cyan">OVERVIEW</span>
        </h1>
        <p className="font-mono text-xs text-cyber-muted mt-1">
          Real-time PC hardware deal aggregator | Feeds auto-refresh every 60 min
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatWidget
          label="Total Deals"
          value={loading ? "—" : data?.total ?? 0}
          sub="across all feeds"
          accent="cyan"
          index={0}
        />
        <StatWidget
          label="Categories"
          value={loading ? "—" : data?.categories?.length ?? 0}
          sub="supported"
          accent="green"
          index={1}
        />
        <StatWidget
          label="Feed Sources"
          value={loading ? "—" : feedSources.length}
          sub="RSS endpoints"
          accent="purple"
          index={2}
        />
        <StatWidget
          label="Uptime"
          value={uptime}
          sub="session active"
          accent="red"
          index={3}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div
          className="cyber-card rounded-none p-5 animate-fade-up opacity-0"
          style={{ animationDelay: "200ms", animationFillMode: "forwards" }}
        >
          <div className="flex items-center gap-2 mb-4 border-b border-cyber-border pb-3">
            <TrendingUp size={14} className="text-cyber-cyan" />
            <span className="font-orbitron text-xs tracking-widest text-cyber-cyan">
              CATEGORY_INDEX
            </span>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="skeleton h-8 rounded" />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {displayedCategories.map(({ name, count }) => {
                const pct = Math.round((count / (data?.total || 1)) * 100);
                return (
                  <div key={name} className="group cursor-pointer">
                    <div className="flex justify-between items-center mb-1">
                      <span
                        className={`font-mono text-xs ${
                          CATEGORY_COLORS[name] ?? "text-cyber-muted"
                        }`}
                      >
                        {name}
                      </span>
                      <span className="font-mono text-[10px] text-cyber-muted">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-1 bg-cyber-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-current rounded-full transition-all duration-1000"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-6 pt-3 border-t border-cyber-border">
            <div className="font-mono text-[10px] text-cyber-muted space-y-1">
              <div>
                LAST_SYNC:{" "}
                <span className={hasSync ? "text-cyber-green" : "text-red-400"}>
                  {data?.last_updated
                    ? new Date(data.last_updated).toLocaleTimeString()
                    : "PENDING"}
                </span>
              </div>
              <div>
                STATUS: <span className={dashboardStatusClass}>{dashboardStatusLabel}</span>
              </div>
            </div>
          </div>

          <button
            onClick={forceRefresh}
            disabled={refreshing}
            className="btn-cyber w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-40"
          >
            <RefreshCw size={11} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "SYNCING..." : "FORCE REFRESH"}
          </button>
        </div>

        <div className="lg:col-span-2 space-y-3">
          <div
            className="flex items-center justify-between animate-fade-up opacity-0"
            style={{ animationDelay: "300ms", animationFillMode: "forwards" }}
          >
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-cyber-cyan" />
              <span className="font-orbitron text-xs tracking-widest text-cyber-cyan">
                LATEST_DEALS
              </span>
            </div>
            <Link
              href="/deals"
              className="flex items-center gap-1 font-mono text-xs text-cyber-muted hover:text-cyber-cyan transition-colors"
            >
              VIEW ALL <ArrowRight size={11} />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {loading
              ? [...Array(6)].map((_, i) => <DealCardSkeleton key={i} />)
              : recentDeals.map((deal, i) => <DealCard key={deal.id} {...deal} index={i} />)}
          </div>

          {!loading && recentDeals.length === 0 && (
            <div className="cyber-card rounded-none p-12 text-center">
              <Zap size={32} className="text-cyber-muted mx-auto mb-3" />
              <div className="font-orbitron text-sm text-cyber-muted tracking-wider">
                NO_DEALS_CACHED
              </div>
              <div className="font-mono text-xs text-cyber-muted mt-2">
                Try forcing a refresh
              </div>
            </div>
          )}
        </div>
      </div>

      <div
        className="cyber-card rounded-none p-4 animate-fade-up opacity-0"
        style={{ animationDelay: "500ms", animationFillMode: "forwards" }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Radio size={12} className="text-cyber-cyan" />
          <span className="font-orbitron text-xs tracking-widest text-cyber-cyan">
            FEED_STATUS
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {(loading ? [] : feedStatuses).map((feed) => {
            const isLive = feed.status === "LIVE";

            return (
              <div
                key={feed.name}
                className="flex items-center justify-between border border-cyber-border px-4 py-2"
              >
                <div>
                  <div className="font-mono text-xs text-white">{feed.name}</div>
                  <div className="font-mono text-[10px] text-cyber-muted">
                    UPTIME: {feed.uptime} // DEALS: {feed.deal_count}
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isLive ? "bg-cyber-green animate-pulse" : "bg-red-400"
                    }`}
                  />
                  <span
                    className={`font-mono text-[10px] ${
                      isLive ? "text-cyber-green" : "text-red-400"
                    }`}
                  >
                    {feed.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}