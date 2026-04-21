"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Cpu, Zap, Activity, Settings, Menu, X, LogIn, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const links = [
  { href: "/", label: "Dashboard", icon: Activity },
  { href: "/deals", label: "Deals", icon: Zap },
  // { href: "/settings", label: "Settings", icon: Settings },
];

export default function Navbar() {
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.push("/");
    setOpen(false);
  };

  return (
    <header className="relative z-50 border-b border-cyber-border">
      <div className="absolute inset-0 bg-gradient-to-r from-cyber-dark via-cyber-black to-cyber-dark opacity-90 backdrop-blur-md" />

      <nav className="relative flex items-center justify-between px-6 py-3 max-w-7xl mx-auto">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="relative">
            <Cpu size={22} className="text-cyber-cyan animate-pulse-slow" strokeWidth={1.5} />
            <div className="absolute inset-0 blur-sm bg-cyber-cyan opacity-30 rounded-full" />
          </div>
          <span className="font-orbitron font-bold text-sm tracking-[0.2em] text-cyber-cyan text-glow-cyan animate-flicker">
            PC<span className="text-white">DEALS</span>
          </span>
          <span className="font-mono text-xs text-cyber-muted hidden sm:block">// SYS_ONLINE</span>
        </Link>

        {/* Desktop nav */}
        <ul className="hidden md:flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => {
            const active = path === href;
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={`flex items-center gap-1.5 px-4 py-2 font-orbitron text-xs tracking-widest transition-all duration-200
                    ${active
                      ? "text-cyber-cyan border border-cyber-cyan/40 bg-cyber-cyan/10 glow-cyan"
                      : "text-cyber-muted hover:text-cyber-cyan hover:border-cyber-border border border-transparent"
                    }`}
                >
                  <Icon size={13} strokeWidth={2} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Right side: status + auth (Remove comment after deployment) */}
        {/* <div className="hidden md:flex items-center gap-3">
          <div className="flex items-center gap-2 font-mono text-xs text-cyber-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-cyber-green animate-pulse inline-block" />
            FEEDS_LIVE
          </div>

          {user ? (
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 font-orbitron text-xs tracking-widest border border-cyber-border text-cyber-muted hover:text-cyber-red hover:border-cyber-red/40 transition-all duration-200"
            >
              <LogOut size={11} />
              LOGOUT
            </button>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1.5 px-3 py-1.5 font-orbitron text-xs tracking-widest border border-cyber-cyan/40 text-cyber-cyan bg-cyber-cyan/5 hover:bg-cyber-cyan/15 transition-all duration-200"
            >
              <LogIn size={11} />
              LOGIN
            </Link>
          )}
        </div> */} 

        {/* Mobile menu toggle */}
        <button
          className="md:hidden text-cyber-muted hover:text-cyber-cyan transition-colors"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {/* Mobile dropdown */}
      {open && (
        <div className="md:hidden absolute top-full left-0 right-0 z-50 border-b border-cyber-border bg-cyber-dark/95 backdrop-blur-md py-2">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-2 px-6 py-3 font-orbitron text-xs tracking-widest transition-colors
                ${path === href ? "text-cyber-cyan" : "text-cyber-muted hover:text-cyber-cyan"}`}
            >
              <Icon size={13} />
              {label}
            </Link>
          ))}

          <div className="px-6 py-3 border-t border-cyber-border/40 mt-1">
            {user ? (
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 font-orbitron text-xs tracking-widest text-cyber-muted hover:text-cyber-red transition-colors"
              >
                <LogOut size={13} />
                LOGOUT
              </button>
            ) : (
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 font-orbitron text-xs tracking-widest text-cyber-cyan"
              >
                <LogIn size={13} />
                LOGIN
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
