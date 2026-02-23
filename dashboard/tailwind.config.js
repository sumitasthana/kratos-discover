/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f1117',
        surface: '#1a1d27',
        border: '#2a2d3e',
        'text-primary': '#e2e8f0',
        'text-muted': '#64748b',
        'accent-green': '#22c55e',
        'accent-amber': '#f59e0b',
        'accent-red': '#ef4444',
        'accent-blue': '#3b82f6',
      }
    },
  },
  plugins: [],
}
