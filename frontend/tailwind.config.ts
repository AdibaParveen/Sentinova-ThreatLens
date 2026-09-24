import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070b14",
          900: "#0b1220",
          800: "#111a2e",
          700: "#18243d",
          600: "#243354",
        },
        accent: {
          DEFAULT: "#2f6fed",
          muted: "#4c84f0",
        },
        critical: "#e5484d",
        high: "#f76808",
        medium: "#f5d90a",
        low: "#30a46c",
      },
      fontFamily: {
        sans: ["Segoe UI", "Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
