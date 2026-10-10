"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import MoodDimmer from "./MoodDimmer";
import { MOOD_BY_ID, MoodId } from "@/lib/moods";
import { useMood } from "@/context/MoodContext";

const BULBS = 28;

/** Signed-out front of house. The dimmer works here too, so the first thing a visitor does is change the room. */
export default function MarqueeLanding({ devMode = false }: { devMode?: boolean }) {
  const { mood, setMood, theme } = useMood();
  const [hint, setHint] = useState(false);

  const pick = (m: MoodId) => {
    setMood(m);
    setHint(true);
  };

  return (
    <main className="relative z-10 mx-auto flex min-h-screen w-full max-w-5xl flex-col items-center justify-center px-5 py-14 text-center">
      {/* Marquee frame */}
      <div className="relative w-full max-w-3xl rounded-[28px] border border-brass/50 bg-surface/80 px-6 pb-10 pt-12 shadow-[0_0_80px_-10px_rgb(var(--g500)/0.45)] backdrop-blur-sm sm:px-12">
        {[0, 1].map((row) => (
          <div key={row} aria-hidden className={`absolute inset-x-6 flex justify-between ${row === 0 ? "top-3" : "bottom-3"}`}>
            {Array.from({ length: BULBS }).map((_, i) => (
              <span key={i} className="bulb animate-chase" style={{ animationDelay: `${((i + row * 7) % 8) * 0.2}s` }} />
            ))}
          </div>
        ))}

        <p className="font-display text-sm italic text-brass-light">OTT Intelligence presents</p>
        <h1 className="mt-3 font-display text-5xl font-semibold leading-[1.02] tracking-tight text-ivory sm:text-7xl">
          Tell us how
          <br />
          tonight feels.
        </h1>
        <p className="mx-auto mt-6 max-w-md text-base leading-relaxed text-ivory/70">
          Set the lights to your mood and we pick what plays. Every pick you react to teaches us what you love in each mood.
        </p>

        <div className="mt-10">
          <MoodDimmer value={mood} onChange={pick} />
          <div className="mt-6 h-12">
            <AnimatePresence mode="wait">
              <motion.p
                key={theme?.id ?? "none"}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="font-display text-xl italic text-ivory/85"
              >
                {theme ? `${theme.line} We'd look for ${theme.ask}.` : "Pick a light to begin."}
              </motion.p>
            </AnimatePresence>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <a
            href="/api/auth/login"
            className="rounded-full bg-gel-500 px-8 py-3.5 text-sm font-semibold text-pit shadow-lg shadow-gel-500/30 transition hover:bg-gel-400 hover:shadow-gel-400/40"
          >
            {hint && theme ? `Take your seat for ${theme.label.toLowerCase()}` : "Take your seat"}
          </a>
          <a
            href="/api/auth/signup"
            className="rounded-full border border-ivory/20 px-7 py-3.5 text-sm font-medium text-ivory/85 transition hover:border-ivory/50 hover:text-ivory"
          >
            Create a free profile
          </a>
        </div>
        {devMode && <p className="mt-6 text-xs text-ivory/40">Local dev mode: sign-in is bypassed.</p>}
      </div>

      <p className="mt-8 max-w-md text-sm text-ivory/45">
        Sign-in is handled by Auth0. We never see your password. Your mood history belongs to your profile only.
      </p>
    </main>
  );
}
