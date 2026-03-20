/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        concrete: {
          50: '#f7f7f6',
          100: '#e8e8e5',
          200: '#d2d1cc',
          300: '#b4b2aa',
          400: '#928f86',
          500: '#78756c',
          600: '#625f57',
          700: '#514e48',
          800: '#45433d',
          900: '#3c3a36',
        }
      }
    }
  },
  plugins: [],
}
