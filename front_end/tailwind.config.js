/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cream': '#fcfcfc',
        'charcoal': '#2c2c2c',
        'muted': '#999999',
        'accent': '#cfaa6f',
        assistantBg: '#ffffffff',
        assistantText: '#2c2c2c',
        userBg: '#fffaeeff',
        userText: '#2c2c2c',
      },
      fontFamily: {
        'montserrat': ['Montserrat', 'sans-serif'],
        'playfair': ['Playfair Display', 'serif'],
      },
      letterSpacing: {
        'wider': '0.1em',
        'widest': '0.15em',
      },
    },
  },
  plugins: [],
}