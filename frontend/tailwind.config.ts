import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontSize: {
        base: ['17px', { lineHeight: '1.6' }],
      },
      colors: {
        'seabot-navy': {
          50:  '#e8eaf4',
          100: '#c5cae5',
          200: '#9fa8d5',
          300: '#7986c5',
          400: '#5c6bb8',
          500: '#3f51ab',
          600: '#3849a4',
          700: '#2f3f9b',
          800: '#263693',
          900: '#192383',
          950: '#0d1547',
          DEFAULT: '#0d1547',
        },
        'seabot-teal': {
          50:  '#e0f7fa',
          100: '#b2ebf2',
          200: '#80deea',
          300: '#4dd0e1',
          400: '#26c6da',
          500: '#00bcd4',
          600: '#00b2c8',
          700: '#00a5b9',
          800: '#0099ab',
          900: '#007b8e',
          DEFAULT: '#00bcd4',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'Consolas',
          'monospace',
        ],
      },
      spacing: {
        '18': '4.5rem',
        '84': '21rem',
        '88': '22rem',
      },
      animation: {
        'pulse-soft': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.2s ease-out',
        'fade-in': 'fadeIn 0.15s ease-out',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(-8px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      transitionDuration: {
        '250': '250ms',
      },
    },
  },
  plugins: [],
}

export default config
