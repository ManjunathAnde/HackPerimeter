/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: { DEFAULT: "#FFF8EC", dark: "#F5E9D3" },
        accent: { DEFAULT: "#F26B1D", dark: "#C9520F", soft: "#FDE3D0" },
        ink: "#111111",
      },
    },
  },
  plugins: [],
};
