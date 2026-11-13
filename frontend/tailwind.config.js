/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Palette and type from design/mockup
      colors: {
        cream: { DEFAULT: "#EBE6DF", dark: "#DDD5CA" },
        paper: "#F4F1EB",
        note: "#F5EFB0",
        accent: { DEFAULT: "#C9622B", dark: "#A44D1E", soft: "#F2D8C6" },
        ink: "#1E2527",
      },
      fontFamily: {
        sans: ["Archivo", "system-ui", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
