import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "PCSeekers // Real-Time Component Tracker",
  description: "Aggregate PC hardware deals from Slickdeals, Micro Center, and more.",
  icons: {
    icon: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="circuit-bg" aria-hidden="true" />
          <div className="scanline" aria-hidden="true" />

          <div className="relative z-10 min-h-screen flex flex-col">
            <Navbar />
            <main className="flex-1">{children}</main>

            <footer className="border-t border-cyber-border py-4 px-6 text-center">
              <span className="font-mono text-xs text-cyber-muted tracking-widest">
                PCSeekers // v1.0.0 // FEEDS: LIVE // {new Date().getFullYear()}
              </span>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}