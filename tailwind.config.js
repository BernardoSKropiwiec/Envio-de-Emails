/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./Templates/*"],
  theme: {
    extend: {
      fontFamily: {
        barcode: ['"Libre Barcode 39 Extended Text"', 'serif'],
        sigmar: ['Sigmar'],
        archivo: ['Archivo Black'],
        slab: ['Alfa Slab One']
      }
    },
  },
  plugins: [],
}
