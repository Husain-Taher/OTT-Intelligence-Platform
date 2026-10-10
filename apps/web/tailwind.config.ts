import type { Config } from "tailwindcss";

// The room is lit by the active mood. --g200..--g700 are "R G B" triplets set at runtime
// (see src/lib/moods.ts), so every `indigo-*` utility in the app re-tints with the mood.
const gel = (n: number) => `rgb(var(--g${n}) / <alpha-value>)`;
const gelScale = { 200: gel(200), 300: gel(300), 400: gel(400), 500: gel(500), 600: gel(600), 700: gel(700), 950: "rgb(var(--g700) / 0.35)" };

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#0E0B0A",
        indigo: gelScale,
        gel: gelScale,
        pit: "#0E0B0A",
        velvet: { DEFAULT: "#5B1220", deep: "#3A0B15", light: "#7A1A2C" },
        brass: { DEFAULT: "#C9A24B", light: "#E6C77A", dark: "#8F7030" },
        ivory: "#F3EBDD",
        surface: {
          DEFAULT: "#171210",
          elevated: "#1F1916",
          subtle: "#2A2320",
        },
      },
      fontFamily: {
        sans: ['"Instrument Sans"', "system-ui", "sans-serif"],
        display: ['"Fraunces"', "Georgia", "serif"],
      },
      keyframes: {
        chase: { "0%,100%": { opacity: "0.35" }, "50%": { opacity: "1" } },
        flicker: { "0%,100%": { opacity: "1" }, "47%": { opacity: "1" }, "50%": { opacity: "0.82" }, "53%": { opacity: "1" } },
      },
      animation: {
        chase: "chase 1.6s ease-in-out infinite",
        flicker: "flicker 4s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
