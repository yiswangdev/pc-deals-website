import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "PCDeals // Real-Time Component Tracker",
  description: "Aggregate PC hardware deals from Reddit, Slickdeals, and more.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {/* Circuit board background */}
          <div className="circuit-bg" aria-hidden="true" />

          {/* Animated scan line */}
          <div className="scanline" aria-hidden="true" />

          {/* App shell */}
          <div className="relative z-10 min-h-screen flex flex-col">
            <Navbar />
            <main className="flex-1">{children}</main>

            {/* Footer */}
            <footer className="border-t border-cyber-border py-4 px-6 text-center">
              <span className="font-mono text-xs text-cyber-muted tracking-widest">
                PCDEALS_SYS // v1.0.0 // FEEDS: LIVE // {new Date().getFullYear()}
              </span>
            </footer>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}