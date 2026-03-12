/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ag3ntwerk agent color palette
        'aw': {
          'bg': '#0f0f13',
          'surface': '#1a1a24',
          'card': '#22222e',
          'border': '#2d2d3d',
          'text': '#e4e4ef',
          'muted': '#8888a0',
          'accent': '#6366f1',
          'success': '#22c55e',
          'warning': '#f59e0b',
          'error': '#ef4444',
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
