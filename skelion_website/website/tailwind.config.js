/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          dark: '#050811',
          card: 'rgba(13, 19, 33, 0.65)',
          border: 'rgba(255, 255, 255, 0.12)',
          cyan: '#00f2fe',
          blue: '#4facfe',
          violet: '#7f00ff',
          emerald: '#00f5a0',
          amber: '#ffb300',
        }
      },
      backdropBlur: {
        xs: '2px',
        glass: '16px',
        deep: '24px',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glass-glow': '0 0 25px rgba(0, 242, 254, 0.25)',
        'glass-inset': 'inset 0 1px 1px 0 rgba(255, 255, 255, 0.15)',
      }
    },
  },
  plugins: [],
}
