"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { Search, Filter, RefreshCw, Zap, ChevronDown } from "lucide-react";
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

interface DealsResponse {
  deals: Deal[];
  total: number;
  last_updated: string | null;
  categories: string[];
}

const CATEGORIES = ["All", "GPU", "CPU", "RAM", "SSD", "Motherboard", "PSU", "Cooling", "Monitor", "Other"];
const SORT_OPTIONS = ["Newest", "Oldest", "Category A-Z"];

export default function DealsPage() {
  const [data, setData] = useState<DealsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [sort, setSort] = useState("Newest");
  const [sortOpen, setSortOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [sortMenuPos, setSortMenuPos] = useState({ top: 0, left: 0, width: 144 });

  const sortButtonRef = useRef<HTMLButtonElement | null>(null);
  const PER_PAGE = 24;

  const updateSortMenuPosition = useCallback(() => {
    if (!sortButtonRef.current) return;
    const rect = sortButtonRef.current.getBoundingClientRect();
    setSortMenuPos({
      top: rect.bottom + 4,
      left: rect.right - 144,
      width: 144,
    });
  }, []);

  const fetchDeals = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (category !== "All") params.set("category", category);
      if (search) params.set("search", search);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals?${params}`);
      const json: DealsResponse = await res.json();
      setData(json);
      setPage(1);
    } catch (e) {
      console.error("Fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, [category, search]);

  useEffect(() => {
    const timer = setTimeout(fetchDeals, 400);
    return () => clearTimeout(timer);
  }, [fetchDeals]);

  useEffect(() => {
    if (!sortOpen) return;

    updateSortMenuPosition();

    const handleWindowChange = () => updateSortMenuPosition();
    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (sortButtonRef.current && target && sortButtonRef.current.contains(target)) {
        return;
      }
      setSortOpen(false);
    };

    window.addEventListener("resize", handleWindowChange);
    window.addEventListener("scroll", handleWindowChange, true);
    window.addEventListener("click", handleOutsideClick);

    return () => {
      window.removeEventListener("resize", handleWindowChange);
      window.removeEventListener("scroll", handleWindowChange, true);
      window.removeEventListener("click", handleOutsideClick);
    };
  }, [sortOpen, updateSortMenuPosition]);

  const forceRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals/refresh`, { method: "POST" });
      await fetchDeals();
    } finally {
      setRefreshing(false);
    }
  };

  const sortedDeals = [...(data?.deals ?? [])].sort((a, b) => {
    if (sort === "Newest") return new Date(b.published).getTime() - new Date(a.published).getTime();
    if (sort === "Oldest") return new Date(a.published).getTime() - new Date(b.published).getTime();
    if (sort === "Category A-Z") return a.category.localeCompare(b.category);
    return 0;
  });

  const paginated = sortedDeals.slice(0, page * PER_PAGE);
  const hasMore = paginated.length < sortedDeals.length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="animate-fade-up opacity-0" style={{ animationFillMode: "forwards" }}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="font-orbitron text-2xl font-bold text-white tracking-wider">
              DEAL <span className="text-cyber-cyan text-glow-cyan">SCANNER</span>
            </h1>
            <p className="font-mono text-xs text-cyber-muted mt-1">
              {loading ? "SCANNING..." : `${data?.total ?? 0} deals indexed across all feeds`}
            </p>
          </div>
          <button
            onClick={forceRefresh}
            disabled={refreshing}
            className="btn-cyber flex items-center gap-2 disabled:opacity-40"
          >
            <RefreshCw size={11} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "SYNCING..." : "REFRESH FEEDS"}
          </button>
        </div>
      </div>

      {/* ── Controls ────────────────────────────────────────────────── */}
      <div
        className="cyber-card rounded-none p-4 animate-fade-up opacity-0 space-y-4"
        style={{ animationDelay: "100ms", animationFillMode: "forwards" }}
      >
        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-cyber-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="SEARCH DEALS... // e.g. RTX 4070, Ryzen 7"
            className="w-full bg-cyber-dark border border-cyber-border focus:border-cyber-cyan/50 text-white font-mono text-xs placeholder:text-cyber-muted/50 py-2.5 pl-9 pr-4 outline-none transition-colors duration-200"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-cyber-muted hover:text-white transition-colors font-mono text-xs"
            >
              [CLR]
            </button>
          )}
        </div>

        {/* Filters row */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Filter size={11} className="text-cyber-muted" />
            <span className="font-mono text-[10px] text-cyber-muted tracking-widest">FILTER:</span>
          </div>

          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`font-mono text-[10px] tracking-wider px-3 py-1.5 border transition-all duration-150
                ${
                  category === cat
                    ? "border-cyber-cyan/60 text-cyber-cyan bg-cyber-cyan/10"
                    : "border-cyber-border text-cyber-muted hover:border-cyber-cyan/30 hover:text-cyber-cyan/70"
                }`}
            >
              {cat.toUpperCase()}
            </button>
          ))}

          <div className="ml-auto shrink-0">
            <button
              ref={sortButtonRef}
              onClick={(e) => {
                e.stopPropagation();
                if (!sortOpen) updateSortMenuPosition();
                setSortOpen((o) => !o);
              }}
              className="flex items-center gap-1.5 font-mono text-[10px] tracking-wider px-3 py-1.5 border border-cyber-border text-cyber-muted hover:text-cyber-cyan hover:border-cyber-cyan/30 transition-all"
            >
              SORT: {sort.toUpperCase()} <ChevronDown size={10} />
            </button>
          </div>
        </div>
      </div>

      {sortOpen && (
        <div
          className="fixed bg-cyber-card border border-cyber-border shadow-xl z-[9999]"
          style={{
            top: sortMenuPos.top,
            left: sortMenuPos.left,
            width: sortMenuPos.width,
          }}
        >
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt}
              onClick={() => {
                setSort(opt);
                setSortOpen(false);
              }}
              className={`w-full text-left font-mono text-[10px] px-3 py-2 tracking-wider transition-colors
                ${
                  sort === opt
                    ? "text-cyber-cyan bg-cyber-cyan/5"
                    : "text-cyber-muted hover:text-cyber-cyan hover:bg-cyber-cyan/5"
                }`}
            >
              {opt.toUpperCase()}
            </button>
          ))}
        </div>
      )}

      {/* ── Results count ───────────────────────────────────────────── */}
      {!loading && (
        <div className="font-mono text-xs text-cyber-muted animate-slide-in">
          <span className="text-cyber-cyan">{sortedDeals.length}</span> results
          {search && <span> for "<span className="text-white">{search}</span>"</span>}
          {category !== "All" && <span> in <span className="text-white">{category}</span></span>}
        </div>
      )}

      {/* ── Deal Grid ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {loading
          ? [...Array(12)].map((_, i) => <DealCardSkeleton key={i} />)
          : paginated.map((deal, i) => (
              <DealCard key={deal.id} {...deal} index={i % PER_PAGE} />
            ))}
      </div>

      {/* ── Empty state ─────────────────────────────────────────────── */}
      {!loading && sortedDeals.length === 0 && (
        <div className="cyber-card rounded-none p-16 text-center">
          <Zap size={40} className="text-cyber-muted mx-auto mb-4" />
          <div className="font-orbitron text-sm text-cyber-muted tracking-widest mb-2">NO_RESULTS_FOUND</div>
          <div className="font-mono text-xs text-cyber-muted">
            Try a different search term or category
          </div>
          <button
            onClick={() => {
              setSearch("");
              setCategory("All");
            }}
            className="btn-cyber mt-6 inline-block"
          >
            CLEAR FILTERS
          </button>
        </div>
      )}

      {/* ── Load more ───────────────────────────────────────────────── */}
      {hasMore && !loading && (
        <div className="text-center pt-4">
          <button
            onClick={() => setPage((p) => p + 1)}
            className="btn-cyber-green btn-cyber"
          >
            LOAD MORE // {sortedDeals.length - paginated.length} REMAINING
          </button>
        </div>
      )}

      {/* ── Footer info ─────────────────────────────────────────────── */}
      {!loading && data?.last_updated && (
        <div className="font-mono text-[10px] text-cyber-muted text-center pb-4">
          LAST_SYNC: {new Date(data.last_updated).toLocaleString()} //
          NEXT_SYNC: ~{new Date(new Date(data.last_updated).getTime() + 3600000).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}