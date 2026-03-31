/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Cores principais — Roxo (base da identidade Pangeia 96)
        pangeia: {
          'lilas-claro':  '#E3D4F9',
          'lilas-medio':  '#CFB8F4',
          'roxo':         '#AE76E5',  // Roxo principal
          'roxo-medio':   '#532194',
          'roxo-profundo':'#371267',
        },
        // Cores de apoio
        apoio: {
          'laranja-claro': '#F8CA89',
          'laranja':       '#EF9837',
          'verde-claro':   '#EEFFEB',
          'verde':         '#A4D462',
          'verde-escuro':  '#609538',
          'vermelho-claro':'#FCA9AD',
          'vermelho':      '#D24C45',
          'azul-escuro':   '#3F37C9',
          'azul':          '#4896EF',
          'azul-claro':    '#4CC8F1',
          'rosa-claro':    '#F7AAD4',
          'rosa':          '#EF62A9',
          'rosa-escuro':   '#F72486',
        },
        // Neutras
        neutro: {
          'preto': '#191919',
          'cinza': '#DFDFDF',
          'branco': '#FFFFFF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 2px 12px rgba(174, 118, 229, 0.12)',
        'card-hover': '0 4px 24px rgba(174, 118, 229, 0.22)',
      },
    },
  },
  plugins: [],
}
