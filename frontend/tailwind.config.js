/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: { ink: 'var(--ink)', canvas: 'var(--canvas)', lime: '#c9f36b', mist: 'var(--mist)' },
      boxShadow: { card: '0 12px 30px rgba(32, 33, 30, 0.08)' },
    },
  },
  plugins: [],
}
