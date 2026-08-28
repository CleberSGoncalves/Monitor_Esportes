/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        premium: {
          dark: "#0f172a",
          card: "#1e293b",
          highlight: "#38bdf8",
          text: "#f1f5f9",
          muted: "#94a3b8"
        }
      }
    },
  },
  plugins: [],
}
