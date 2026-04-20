/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          black: "#020408",
          dark: "#070d14",
          card: "#0a1628",
          border: "#0d2137",
          cyan: "#00e5ff",
          green: "#00ff88",
          purple: "#7c3aed",
          red: "#ff2d55",
          yellow: "#ffd60a",
          muted: "#4a6880",
        },
      },
      fontFamily: {
        orbitron: ["Orbitron", "monospace"],
        mono: ["Share Tech Mono", "monospace"],
        body: ["Exo 2", "sans-serif"],
      },
      animation: {
        "scan": "scan 4s linear infinite",
        "pulse-cyan": "pulseCyan 2s ease-in-out infinite",
        "flicker": "flicker 6s linear infinite",
        "matrix-fall": "matrixFall 8s linear infinite",
        "border-glow": "borderGlow 2s ease-in-out infinite",
        "fade-up": "fadeUp 0.6s ease-out forwards",
        "slide-in": "slideIn 0.4s ease-out forwards",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        pulseCyan: {
          "0%, 100%": { boxShadow: "0 0 5px #00e5ff44, 0 0 20px #00e5ff22" },
          "50%": { boxShadow: "0 0 20px #00e5ff88, 0 0 60px #00e5ff44" },
        },
        flicker: {
          "0%, 95%, 100%": { opacity: "1" },
          "96%": { opacity: "0.7" },
          "97%": { opacity: "1" },
          "98%": { opacity: "0.5" },
          "99%": { opacity: "1" },
        },
        borderGlow: {
          "0%, 100%": { borderColor: "#00e5ff44" },
          "50%": { borderColor: "#00e5ffaa" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
      backdropBlur: { xs: "2px" },
    },
  },
  plugins: [],
};
