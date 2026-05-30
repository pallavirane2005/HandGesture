/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cyber': {
          'dark': '#0a0e1a',
          'darker': '#050810',
          'panel': '#0f1629',
          'border': '#1a2342',
          'accent': '#00f0ff',
          'accent-dim': 'rgba(0, 240, 255, 0.3)',
          'secondary': '#ff00a0',
          'success': '#00ff88',
          'warning': '#ffaa00',
          'danger': '#ff0044',
          'text': '#e0e6ed',
          'text-dim': '#6b7a99',
        }
      },
      fontFamily: {
        'mono': ['"JetBrains Mono"', 'monospace'],
        'display': ['"Orbitron"', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'scan': 'scan 4s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0, 240, 255, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(0, 240, 255, 0.6), 0 0 40px rgba(0, 240, 255, 0.2)' },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'fadeIn': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slideUp': {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [],
}