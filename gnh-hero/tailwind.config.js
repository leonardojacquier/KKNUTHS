/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './ventas/index.html', './institucional/index.html', './src/**/*.ts'],
  theme: {
    extend: {
      colors: {
        navy:   '#0F172A',   // base / fundo do hero
        navy2:  '#0D1626',   // navy mais escuro p/ vinheta e gradientes
        orange: '#F26D21',   // acento / CTA / detalhe do título
        ink:    '#0A0E1A',
        paper:  '#F5F6F8',   // seções claras pós-hero
        slate:  '#5B6472',
      },
      fontFamily: {
        display: ['"Satoshi"', 'sans-serif'],
        body: ['"General Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
