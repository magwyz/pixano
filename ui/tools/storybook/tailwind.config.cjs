/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["../../components/**/*.{html, js, svelte, ts}", "./stories/**/*.{html,js,svelte,ts}"],
  darkMode: "media", // or 'class'
  theme: {
    extend: {
      fontFamily: {
        "DM Sans": ["DM Sans", "sans-serif"],
        Montserrat: ["Montserrat", "sans-serif"],
      },
      colors: {
        main: "#771E5F",
        secondary: "#872f6e",
      },
    },
  },
  plugins: [],
};
