"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Heart, ThumbsDown, SkipForward } from "lucide-react";
import MoodDimmer from "./MoodDimmer";
import { ARCHETYPES } from "./ProfileView";
import { useMood } from "@/context/MoodContext";
import { useMe } from "@/context/MeContext";
import { chooseArchetype, fetchCatalog, finishOnboarding, recordUserEvent } from "@/lib/api";
import { CanonicalContent } from "@/types";
import { MoodId } from "@/lib/moods";

const REEL_SIZE = 8;

/** Three quick steps that give a new profile its first real signal, so the first pick isn't a guess. */
export default function Onboarding({ onDone }: { onDone: () => void }) {
  const { mood, setMood } = useMood();
  const { refresh } = useMe();
  const [step, setStep] = useState<0 | 1 | 2>(0);
  const [seat, setSeat] = useState<string | null>(null);
  const [reel, setReel] = useState<CanonicalContent[]>([]);
  const [idx, setIdx] = useState(0);
  const [reacted, setReacted] = useState(0);

  useEffect(() => {
    fetchCatalog().then((items) => {
      if (!items) return;
      // Prioritize iconic, high-recognition titles with substantial reviews across diverse genres
      const sortedByAcclaim = [...items]
        .filter((i) => i.backdrop_path && (i.vote_count ?? 0) >= 3000)
        .sort((a, b) => {
          // Bayesian popularity score: (v/(v+1000))*r + (1000/(v+1000))*7.5
          const scoreA = ((a.vote_count / (a.vote_count + 1000)) * a.vote_average) + ((1000 / (a.vote_count + 1000)) * 7.5);
          const scoreB = ((b.vote_count / (b.vote_count + 1000)) * b.vote_average) + ((1000 / (b.vote_count + 1000)) * 7.5);
          return scoreB - scoreA;
        });

      const seen = new Set<string>();
      const picks: CanonicalContent[] = [];
      for (const it of sortedByAcclaim) {
        const g = it.genres[0] ?? "Other";
        if (!seen.has(g)) {
          seen.add(g);
          picks.push(it);
        }
        if (picks.length === REEL_SIZE) break;
      }

      // Fallback if catalog was smaller than REEL_SIZE
      if (picks.length < REEL_SIZE) {
        for (const it of sortedByAcclaim) {
          if (!picks.some((p) => p.content_id === it.content_id)) {
            picks.push(it);
          }
          if (picks.length === REEL_SIZE) break;
        }
      }
      setReel(picks);
    });
  }, []);

  const current = reel[idx];

  const finishReel = () => setStep(2);
  const react = async (type: "LIKE" | "DISLIKE" | null) => {
    if (type && current) {
      setReacted((n) => n + 1);
      // Not tied to a mood: this is taste, not a night out
      recordUserEvent(current.content_id, type, undefined, { mood: null });
    }
    if (idx + 1 >= reel.length) finishReel();
    else setIdx(idx + 1);
  };

  const pickSeat = async (id: string) => {
    setSeat(id);
    await chooseArchetype(id);
    setStep(1);
  };

  const done = async () => {
    await finishOnboarding();
    await refresh();
    onDone();
  };

  const fade = { initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -10 }, transition: { duration: 0.35 } };
  const skipAll = (
    <button onClick={done} className="text-sm text-ivory/45 underline-offset-4 hover:text-ivory hover:underline">
      Skip setup
    </button>
  );

  return (
    <div className="fixed inset-0 z-[65] overflow-y-auto bg-pit">
      <div aria-hidden className="house-light" />
      <div className="relative z-10 mx-auto flex min-h-full max-w-4xl flex-col px-5 py-10">
        <div className="flex items-center justify-between text-sm text-ivory/50">
          <span>Step {step + 1} of 3</span>
          {skipAll}
        </div>

        <div className="flex flex-1 items-center">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div key="seat" {...fade} className="w-full">
                <h1 className="text-center font-display text-4xl font-semibold text-ivory sm:text-5xl">Where do you usually sit?</h1>
                <p className="mx-auto mt-3 max-w-md text-center text-ivory/60">Pick the ticket closest to you. It sets your starting taste, and your reactions will refine it.</p>
                <div className="mt-10 grid gap-4 sm:grid-cols-2">
                  {Object.entries(ARCHETYPES).map(([id, a]) => (
                    <button
                      key={id}
                      onClick={() => pickSeat(id)}
                      aria-pressed={seat === id}
                      className="ticket rounded-xl border border-brass/30 bg-surface p-6 text-left transition hover:-translate-y-0.5 hover:border-gel-400"
                    >
                      <span className="font-display text-xl text-ivory">{a.name}</span>
                      <span className="mt-1 block text-sm text-ivory/60">{a.line}</span>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div key="reel" {...fade} className="mx-auto w-full max-w-xl text-center">
                <h1 className="font-display text-4xl font-semibold text-ivory sm:text-5xl">Quick reel</h1>
                <p className="mt-3 text-ivory/60">React to {REEL_SIZE} titles. Skip any you haven't seen.</p>
                {current ? (
                  <>
                    <div className="mt-8 overflow-hidden rounded-2xl border border-brass/30 bg-surface">
                      <AnimatePresence mode="wait">
                        <motion.div key={current.content_id} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.25 }}>
                          <img src={current.backdrop_path || current.poster_path || ""} alt="" className="aspect-video w-full object-cover" />
                          <div className="p-5 text-left">
                            <h2 className="font-display text-2xl text-ivory">{current.title}</h2>
                            <p className="text-sm text-ivory/55">{[current.release_year, current.genres.slice(0, 2).join(", ")].filter(Boolean).join(", ")}</p>
                          </div>
                        </motion.div>
                      </AnimatePresence>
                    </div>
                    <div className="mt-6 flex items-center justify-center gap-3">
                      <button onClick={() => react("DISLIKE")} className="flex items-center gap-2 rounded-full border border-ivory/20 px-5 py-3 text-ivory hover:border-ivory/50"><ThumbsDown className="h-4 w-4" /> Not for me</button>
                      <button onClick={() => react(null)} className="flex items-center gap-2 rounded-full px-4 py-3 text-ivory/60 hover:text-ivory"><SkipForward className="h-4 w-4" /> Haven't seen it</button>
                      <button onClick={() => react("LIKE")} className="flex items-center gap-2 rounded-full bg-gel-500 px-6 py-3 font-semibold text-pit hover:bg-gel-400"><Heart className="h-4 w-4" /> Love it</button>
                    </div>
                    <p className="mt-4 text-sm text-ivory/45">{idx + 1} of {reel.length}</p>
                  </>
                ) : (
                  <p className="mt-10 text-ivory/50">Loading the reel…</p>
                )}
              </motion.div>
            )}

            {step === 2 && (
              <motion.div key="mood" {...fade} className="w-full text-center">
                <h1 className="font-display text-4xl font-semibold text-ivory sm:text-5xl">Now, how does tonight feel?</h1>
                <p className="mx-auto mt-3 max-w-md text-ivory/60">
                  {reacted > 0 ? `Thanks, that's ${reacted} reaction${reacted === 1 ? "" : "s"} to start from. ` : ""}Pick a light. You can change it any time from the top bar.
                </p>
                <div className="mt-10"><MoodDimmer value={mood} onChange={(m: MoodId) => setMood(m)} /></div>
                <button
                  onClick={done}
                  disabled={!mood}
                  className="mt-10 rounded-full bg-gel-500 px-10 py-4 text-base font-semibold text-pit shadow-xl shadow-gel-500/30 transition hover:bg-gel-400 disabled:opacity-40"
                >
                  Open the Mood Studio
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
