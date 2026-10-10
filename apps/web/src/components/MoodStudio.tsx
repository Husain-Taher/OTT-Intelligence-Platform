"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Bookmark, BookmarkCheck, Clapperboard, Heart, RefreshCw, Info, ThumbsUp, ThumbsDown } from "lucide-react";
import MoodDimmer from "./MoodDimmer";
import MovieCard from "./MovieCard";
import { useMood } from "@/context/MoodContext";
import { useMe } from "@/context/MeContext";
import { executeFindMyWatch, fetchMoodCatalog, recordUserEvent, toggleWatchlist, submitPickFeedback } from "@/lib/api";
import { CanonicalContent, FindMyWatchResponse, MoodCatalogEntry } from "@/types";

type Phase = "setup" | "rolling" | "shown";

const RUNTIMES = [
  { label: "90 min", value: 95 },
  { label: "2 hours", value: 125 },
  { label: "2½ hours", value: 155 },
  { label: "No limit", value: 240 },
];

const METRICS: { key: keyof FindMyWatchResponse["window_metrics"]; label: string }[] = [
  { key: "emotional_depth", label: "Emotional depth" },
  { key: "mystery_level", label: "Mystery" },
  { key: "narrative_complexity", label: "Story complexity" },
  { key: "visual_atmosphere", label: "Atmosphere" },
  { key: "novelty_quotient", label: "Newness to you" },
];

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function MoodStudio({ onSelectTitle }: { onSelectTitle: (c: CanonicalContent, matchPct?: number) => void }) {
  const { mood, setMood, theme } = useMood();
  const { refresh } = useMe();
  const reduce = useReducedMotion();

  const [catalog, setCatalog] = useState<{ moods: MoodCatalogEntry[]; genres: string[] } | null>(null);
  const [genres, setGenres] = useState<string[]>([]);
  const [showAllGenres, setShowAllGenres] = useState(false);
  const [runtime, setRuntime] = useState(125);
  const [novelty, setNovelty] = useState(0.5);
  const [prompt, setPrompt] = useState("");

  const [phase, setPhase] = useState<Phase>("setup");
  const [result, setResult] = useState<FindMyWatchResponse | null>(null);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const [liked, setLiked] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMoodCatalog().then(setCatalog);
  }, []);

  // New mood: reset the refinements to that mood's sensible defaults.
  useEffect(() => {
    if (!theme) return;
    setGenres([]);
    setShowAllGenres(false);
    setRuntime(RUNTIMES.reduce((a, b) => (Math.abs(b.value - theme.defaultRuntime) < Math.abs(a.value - theme.defaultRuntime) ? b : a)).value);
    setNovelty(theme.defaultNovelty);
    setPhase((p) => (p === "rolling" ? p : "setup"));
    setExcluded([]);
    setResult(null);
    setFeedbackGiven(null);
  }, [theme?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const suggested = useMemo(() => catalog?.moods.find((m) => m.id === mood)?.genres ?? [], [catalog, mood]);
  const otherGenres = useMemo(() => (catalog?.genres ?? []).filter((g) => !suggested.includes(g)), [catalog, suggested]);

  const flash = (text: string) => {
    setNote(text);
    setTimeout(() => setNote(null), 3500);
  };

  const roll = async (another = false) => {
    if (!mood) return;
    const ex = another && result ? [...excluded, result.hero.content.content_id] : [];
    setPhase("rolling");
    setError(null);
    const [res] = await Promise.all([
      executeFindMyWatch({ mood, prompt, maxRuntime: runtime, novelty, genres, excludeIds: ex }),
      wait(reduce ? 200 : 2300),
    ]);
    if (!res) {
      setError("We couldn't reach the recommendation service. Check that the API is running, then try again.");
      setPhase("setup");
      return;
    }
    setResult(res);
    setExcluded(ex);
    setSaved(false);
    setLiked(false);
    setFeedbackGiven(null);
    setPhase("shown");
    if (!another) refresh(); // the check-in now appears on the profile
    requestAnimationFrame(() => stageRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }));
  };

  const hero = result?.hero;

  const onSave = async () => {
    if (!hero) return;
    const res = await toggleWatchlist(hero.content.content_id);
    if (res) {
      setSaved(res.is_saved);
      flash(res.is_saved ? "Saved to your reel." : "Removed from your reel.");
      refresh();
    }
  };

  const onLike = async () => {
    if (!hero || liked || !theme) return;
    setLiked(true);
    await recordUserEvent(hero.content.content_id, "LIKE");
    flash(`Noted. ${hero.content.genres.slice(0, 2).join(" and ")} counts toward your ${theme.label.toLowerCase()} nights.`);
    refresh();
  };

  const onFeedback = async (matched: number) => {
    if (!hero || !mood || feedbackGiven !== null) return;
    setFeedbackGiven(matched);
    await submitPickFeedback(mood, hero.content.content_id, matched);
    flash(matched === 1 ? "Thank you! Glad this fit your mood." : "Thank you! We'll calibrate for better fits.");
  };

  return (
    <div className="space-y-12 pb-10">
      {/* The rig */}
      <section className="text-center">
        <h1 className="font-display text-4xl font-semibold leading-tight text-ivory sm:text-6xl">
          {theme ? theme.line : "How does tonight feel?"}
        </h1>
        <p className="mx-auto mt-3 max-w-lg text-ivory/60">
          {theme ? `We'll look for ${theme.ask}.` : "Switch on a light. The room, and your picks, follow."}
        </p>
        <div className="mt-10">
          <MoodDimmer value={mood} onChange={(m) => setMood(m)} />
        </div>
      </section>

      {/* Refine */}
      {theme && phase !== "shown" && (
        <motion.section
          key={theme.id}
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mx-auto grid max-w-4xl gap-8 rounded-2xl border border-brass/20 bg-surface/70 p-6 backdrop-blur sm:p-8 md:grid-cols-2"
        >
          <div>
            <h2 className="font-display text-xl text-ivory">Lean toward a genre</h2>
            <p className="mt-1 text-sm text-ivory/55">Optional. Leave empty to let your mood decide.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {[...suggested, ...(showAllGenres ? otherGenres : [])].map((g) => {
                const on = genres.includes(g);
                return (
                  <button
                    key={g}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setGenres((cur) => (on ? cur.filter((x) => x !== g) : [...cur, g]))}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
                      on ? "border-gel-400 bg-gel-500/20 text-ivory" : "border-ivory/15 text-ivory/70 hover:border-ivory/40 hover:text-ivory"
                    }`}
                  >
                    {g}
                  </button>
                );
              })}
              {otherGenres.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowAllGenres((v) => !v)}
                  className="rounded-full px-3 py-1.5 text-sm text-gel-300 underline-offset-4 hover:underline"
                >
                  {showAllGenres ? "Fewer genres" : "More genres"}
                </button>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <h2 className="font-display text-xl text-ivory">How long do you have?</h2>
              <div className="mt-3 grid grid-cols-4 gap-2">
                {RUNTIMES.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    aria-pressed={runtime === r.value}
                    onClick={() => setRuntime(r.value)}
                    className={`rounded-lg border px-2 py-2 text-sm transition ${
                      runtime === r.value ? "border-gel-400 bg-gel-500/20 text-ivory" : "border-ivory/15 text-ivory/70 hover:border-ivory/40"
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <h2 className="font-display text-xl text-ivory">Play it safe or surprise me?</h2>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={novelty}
                onChange={(e) => setNovelty(parseFloat(e.target.value))}
                aria-label="Familiar to adventurous"
                className="mt-4 w-full accent-gel-500"
              />
              <div className="mt-1 flex justify-between text-xs text-ivory/50">
                <span>Familiar</span>
                <span>Adventurous</span>
              </div>
            </div>
          </div>

          <div className="md:col-span-2">
            <label htmlFor="studio-prompt" className="font-display text-xl text-ivory">
              Anything else?
            </label>
            <input
              id="studio-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && roll()}
              placeholder="Nothing too sad, preferably not American"
              className="mt-3 w-full rounded-lg border border-ivory/15 bg-pit/70 px-4 py-3 text-ivory placeholder:text-ivory/35 focus:border-gel-400 focus:outline-none"
            />
          </div>

          <div className="flex flex-col items-center gap-3 md:col-span-2">
            <button
              type="button"
              onClick={() => roll()}
              className="flex items-center gap-2 rounded-full bg-gel-500 px-10 py-4 text-base font-semibold text-pit shadow-xl shadow-gel-500/30 transition hover:bg-gel-400"
            >
              <Clapperboard className="h-5 w-5" />
              Roll the film
            </button>
            {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
          </div>
        </motion.section>
      )}

      {!theme && phase === "setup" && (
        <p className="text-center font-display text-lg italic text-ivory/45">No light on yet. Pick one above.</p>
      )}

      {/* The feature */}
      <div ref={stageRef} className="scroll-mt-24">
        {phase === "shown" && result && hero && theme && (
          <motion.section
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="space-y-10"
          >
            <div className="relative overflow-hidden rounded-3xl border border-brass/30 bg-surface shadow-[0_30px_120px_-30px_rgb(var(--g500)/0.5)]">
              <div className="relative aspect-[4/5] w-full sm:aspect-[16/9] lg:aspect-[21/9]">
                <motion.img
                  src={hero.content.backdrop_path || hero.content.poster_path || ""}
                  alt=""
                  initial={reduce ? false : { scale: 1.12 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 2.2, ease: "easeOut" }}
                  className="absolute inset-0 h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-pit via-pit/55 to-pit/10" />
                {/* Letterbox bars retract once */}
                {!reduce && (
                  <>
                    <motion.div className="absolute inset-x-0 top-0 bg-black" initial={{ height: "18%" }} animate={{ height: "0%" }} transition={{ duration: 1.1, delay: 0.25, ease: "easeInOut" }} />
                    <motion.div className="absolute inset-x-0 bottom-0 bg-black" initial={{ height: "18%" }} animate={{ height: "0%" }} transition={{ duration: 1.1, delay: 0.25, ease: "easeInOut" }} />
                  </>
                )}

                <div className="absolute inset-x-0 bottom-0 flex flex-col gap-6 p-6 sm:p-10 lg:flex-row lg:items-end lg:justify-between">
                  <div className="max-w-2xl">
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ivory/75">
                      {hero.content.release_year && <span>{hero.content.release_year}</span>}
                      {result.runtime_formatted && <span>{result.runtime_formatted}</span>}
                      {hero.content.genres.slice(0, 3).map((g) => <span key={g}>{g}</span>)}
                    </div>
                    <h2 className="mt-2 font-display text-4xl font-semibold leading-none text-ivory sm:text-6xl">{hero.content.title}</h2>
                    <p className="mt-4 line-clamp-3 max-w-xl text-sm leading-relaxed text-ivory/75 sm:text-base">{hero.content.overview}</p>
                  </div>
                  <div className="shrink-0 text-left lg:text-right">
                    <div className="font-display text-6xl font-semibold text-gel-300 sm:text-7xl">{hero.personal_match_percentage}%</div>
                    <div className="text-sm text-ivory/65">match for a {theme.label.toLowerCase()} night</div>
                  </div>
                </div>
              </div>

              <div className="grid gap-8 border-t border-ivory/10 p-6 sm:p-10 lg:grid-cols-[1.2fr_1fr]">
                <div>
                  <h3 className="font-display text-xl text-ivory">Why this one</h3>
                  <ul className="mt-3 space-y-2.5 text-ivory/80">
                    {hero.reasons.slice(0, 3).map((r, i) => (
                      <li key={i} className="flex gap-3 leading-relaxed">
                        <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gel-400" />
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                  {hero.contrasting_note && <p className="mt-4 font-display text-base italic text-ivory/60">{hero.contrasting_note}</p>}
                </div>
                <div>
                  <h3 className="font-display text-xl text-ivory">How tonight reads</h3>
                  <dl className="mt-3 space-y-2.5">
                    {METRICS.map((m) => (
                      <div key={m.key}>
                        <div className="flex justify-between text-sm">
                          <dt className="text-ivory/70">{m.label}</dt>
                          <dd className="text-ivory/50">{result.window_metrics[m.key]}</dd>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ivory/10">
                          <motion.div
                            className="h-full rounded-full bg-gel-400"
                            initial={{ width: 0 }}
                            animate={{ width: `${result.window_metrics[m.key]}%` }}
                            transition={{ duration: 0.9, ease: "easeOut" }}
                          />
                        </div>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 border-t border-ivory/10 p-6 sm:px-10">
                <button onClick={() => onSelectTitle(hero.content, hero.personal_match_percentage)} className="flex items-center gap-2 rounded-full bg-gel-500 px-6 py-3 text-sm font-semibold text-pit hover:bg-gel-400">
                  <Info className="h-4 w-4" /> Why should I watch this?
                </button>
                <button onClick={onLike} disabled={liked} className="flex items-center gap-2 rounded-full border border-ivory/20 px-5 py-3 text-sm text-ivory hover:border-gel-400 disabled:border-gel-400/50 disabled:text-gel-300">
                  <Heart className={`h-4 w-4 ${liked ? "fill-current" : ""}`} /> {liked ? "Counted for this mood" : "This fits tonight"}
                </button>
                <button onClick={onSave} className="flex items-center gap-2 rounded-full border border-ivory/20 px-5 py-3 text-sm text-ivory hover:border-gel-400">
                  {saved ? <BookmarkCheck className="h-4 w-4 text-gel-300" /> : <Bookmark className="h-4 w-4" />} {saved ? "In your reel" : "Save for later"}
                </button>
                <button onClick={() => roll(true)} className="flex items-center gap-2 rounded-full px-5 py-3 text-sm text-ivory/75 hover:text-ivory">
                  <RefreshCw className="h-4 w-4" /> Show me another
                </button>
                <button onClick={() => setPhase("setup")} className="ml-auto text-sm text-gel-300 underline-offset-4 hover:underline">
                  Adjust the mood
                </button>
              </div>

              {/* Study feedback question */}
              <div className="flex flex-wrap items-center justify-between gap-4 border-t border-dashed border-ivory/10 bg-surface-elevated/40 px-6 py-3 sm:px-10">
                <span className="text-xs text-ivory/70">
                  Did this match your {theme.label.toLowerCase()} mood?
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onFeedback(1)}
                    disabled={feedbackGiven !== null}
                    className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs transition border ${
                      feedbackGiven === 1
                        ? "bg-gel-500/20 border-gel-400 text-gel-300 font-semibold"
                        : "border-ivory/15 text-ivory/70 hover:border-gel-400 hover:text-ivory disabled:opacity-40"
                    }`}
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                    <span>Yes</span>
                  </button>
                  <button
                    onClick={() => onFeedback(0)}
                    disabled={feedbackGiven !== null}
                    className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs transition border ${
                      feedbackGiven === 0
                        ? "bg-rose-500/20 border-rose-400 text-rose-300 font-semibold"
                        : "border-ivory/15 text-ivory/70 hover:border-rose-400 hover:text-ivory disabled:opacity-40"
                    }`}
                  >
                    <ThumbsDown className="h-3.5 w-3.5" />
                    <span>No</span>
                  </button>
                </div>
              </div>
            </div>

            {result.runners_up.length > 0 && (
              <div>
                <h3 className="font-display text-2xl text-ivory">Intermission picks</h3>
                <p className="mt-1 text-sm text-ivory/55">If tonight's feature isn't it, these were next in line.</p>
                <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {result.runners_up.map((r) => (
                    <MovieCard key={r.content.content_id} item={r} onSelect={onSelectTitle} />
                  ))}
                </div>
              </div>
            )}
          </motion.section>
        )}
      </div>

      {/* Projector leader */}
      <AnimatePresence>{phase === "rolling" && !reduce && <Leader label={theme?.label ?? ""} />}</AnimatePresence>

      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex justify-center px-4 md:bottom-8">
        <AnimatePresence>
          {note && (
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-full border border-gel-400/40 bg-pit/95 px-5 py-3 text-sm text-ivory shadow-xl backdrop-blur"
            >
              {note}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/** Old-film countdown while the recommendation is found. */
function Leader({ label }: { label: string }) {
  const [n, setN] = useState(3);
  useEffect(() => {
    const t = setInterval(() => setN((v) => (v > 1 ? v - 1 : v)), 650);
    return () => clearInterval(t);
  }, []);
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      role="status"
      aria-label="Finding tonight's feature"
      className="fixed inset-0 z-[65] flex flex-col items-center justify-center bg-pit"
    >
      <div className="relative flex h-64 w-64 items-center justify-center rounded-full border-2 border-ivory/30 sm:h-80 sm:w-80">
        <div aria-hidden className="absolute inset-3 rounded-full border border-ivory/20" />
        <div aria-hidden className="absolute inset-x-0 top-1/2 h-px bg-ivory/20" />
        <div aria-hidden className="absolute inset-y-0 left-1/2 w-px bg-ivory/20" />
        <motion.div
          aria-hidden
          className="absolute inset-0 rounded-full"
          style={{ background: "conic-gradient(from 0deg, rgb(var(--g500) / 0.5), transparent 28%)" }}
          animate={{ rotate: 360 }}
          transition={{ duration: 0.65, ease: "linear", repeat: Infinity }}
        />
        <AnimatePresence mode="wait">
          <motion.span
            key={n}
            initial={{ scale: 1.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="relative font-display text-9xl font-semibold text-ivory"
          >
            {n}
          </motion.span>
        </AnimatePresence>
      </div>
      <p className="mt-8 font-display text-xl italic text-ivory/70">Finding your {label.toLowerCase()} feature</p>
    </motion.div>
  );
}
