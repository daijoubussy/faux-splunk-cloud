/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        splunk: {
          green: '#65A637',
          black: '#000000',
          gray: '#3C444D',
          'light-gray': '#F2F4F5',
        },
      },
    },
  },
  plugins: [],
}
