/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans Devanagari"', "system-ui", "sans-serif"],
        display: ['"Fraunces"', "Georgia", "serif"],
      },
      colors: {
        forest: { 50: "#f2f7f2", 100: "#e1ede1", 200: "#c3dbc5", 300: "#97c09c", 400: "#649f6d", 500: "#43814d", 600: "#31673b", 700: "#285231", 800: "#21422a", 900: "#1b3723", 950: "#0d1f13" },
        cream: { 50: "#fbfaf5", 100: "#f5f3e8", 200: "#ebe6d1" },
        sev: { safe: "#15803d", low: "#65a30d", moderate: "#ca8a04", high: "#ea580c", critical: "#dc2626" },
      },
      boxShadow: { soft: "0 1px 2px rgba(16,40,24,.04), 0 8px 24px -12px rgba(16,40,24,.12)" },
    },
  },
  plugins: [],
};
