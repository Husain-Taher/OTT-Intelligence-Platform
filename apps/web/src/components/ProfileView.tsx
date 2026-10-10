"use client";

import { useEffect, useState } from "react";
import { Bookmark, Trash2, AlertTriangle } from "lucide-react";
import { useMe } from "@/context/MeContext";
import { useMood } from "@/context/MoodContext";
import { fetchWatchlist, deleteMyData } from "@/lib/api";
import { MOODS, MOOD_BY_ID, MoodId } from "@/lib/moods";
import { CanonicalContent } from "@/types";

export const ARCHETYPES: Record<string, { name: string; line: string }> = {
  cerebral: { name: "The Cerebral Philosopher", line: "Big ideas, slow burns, endings you argue about." },
  comfort: { name: "The Comfort Seeker", line: "Warm stories you can relax into." },
  adrenaline: { name: "The Adrenaline Chaser", line: "Momentum first, questions later." },
  emotional: { name: "The Feeler", line: "You want to be moved, and you don't mind crying." },
  international: { name: "The Global Explorer", line: "Seoul, Paris, Mumbai: the best story wins." },
};

const MIN_REACTIONS = 3;

function ago(sqlUtc: string): string {
  const t = new Date(sqlUtc.replace(" ", "T") + "Z").getTime();
  if (Number.isNaN(t)) return "";
  const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h} hour${h === 1 ? "" : "s"} ago`;
  const d = Math.round(h / 24);
  return `${d} day${d === 1 ? "" : "s"} ago`;
}

export default function ProfileView({
  onSelectTitle,
  onTryMood,
}: {
  onSelectTitle: (c: CanonicalContent) => void;
  onTryMood: (m: MoodId) => void;
}) {
  const { me, loading, refresh } = useMe();
  const { setMood } = useMood();
  const [reel, setReel] = useState<CanonicalContent[]>([]);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    refresh();
    fetchWatchlist().then((r) => r && setReel(r.items));
  }, [refresh]);

  const handleDeleteData = async () => {
    setIsDeleting(true);
    try {
      const res = await deleteMyData();
      if (res) {
        setReel([]);
        await refresh();
        setShowConfirm(false);
      }
    } catch (e) {
      console.error("Failed to delete user data:", e);
    } finally {
      setIsDeleting(false);
    }
  };


  if (loading || !me) {
    return <div className="py-24 text-center font-display text-lg italic text-ivory/50">Pulling your ticket stub…</div>;
  }

  const arch = me.archetype ? ARCHETYPES[me.archetype] : null;
  const cal = me.calibration;
  const calText =
    cal < 20 ? "We're just getting to know you. React to a few picks and this fills in." : cal < 60 ? "Your taste is taking shape." : "We know your taste well.";

  return (
    <div className="space-y-14 pb-10">
      {/* Ticket stub */}
      <section className="ticket relative grid overflow-hidden rounded-2xl border border-brass/30 bg-surface md:grid-cols-[260px_1fr]">
        <div className="flex flex-col items-center justify-center gap-4 border-b border-dashed border-brass/30 bg-velvet-deep/50 p-8 text-center md:border-b-0 md:border-r">
          {me.picture ? (
            <img src={me.picture} alt="" referrerPolicy="no-referrer" className="h-24 w-24 rounded-full border-2 border-brass/60 object-cover" />
          ) : (
            <span className="flex h-24 w-24 items-center justify-center rounded-full border-2 border-brass/60 bg-pit font-display text-4xl text-brass-light">
              {me.display_name.slice(0, 1).toUpperCase()}
            </span>
          )}
          <div>
            <h1 className="font-display text-2xl font-semibold text-ivory">{me.display_name}</h1>
            {me.member_since && <p className="mt-1 text-xs text-ivory/50">Member since {new Date(me.member_since.replace(" ", "T") + "Z").toLocaleDateString(undefined, { month: "long", year: "numeric" })}</p>}
          </div>
          <a href="/api/auth/logout" className="text-sm text-ivory/55 underline-offset-4 hover:text-ivory hover:underline">Sign out</a>
        </div>

        <div className="space-y-7 p-8">
          <div>
            <p className="text-sm text-ivory/55">Your usual seat</p>
            <p className="font-display text-2xl text-ivory">{arch ? arch.name : "Not chosen yet"}</p>
            {arch && <p className="text-sm text-ivory/60">{arch.line}</p>}
          </div>

          <dl className="grid grid-cols-2 gap-5 sm:grid-cols-4">
            {[
              ["Titles finished", me.stats.titles_completed],
              ["Hours watched", me.stats.hours_watched],
              ["In your reel", me.stats.saved],
              ["Reactions", me.stats.reactions],
            ].map(([label, value]) => (
              <div key={label as string}>
                <dd className="font-display text-4xl font-semibold text-gel-300">{value}</dd>
                <dt className="text-sm text-ivory/55">{label}</dt>
              </div>
            ))}
          </dl>

          <div>
            <div className="flex items-baseline justify-between">
              <p className="text-sm text-ivory/75">How well we know your taste</p>
              <p className="font-display text-lg text-gel-300">{cal}%</p>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-ivory/10" role="progressbar" aria-valuenow={cal} aria-valuemin={0} aria-valuemax={100}>
              <div className="h-full rounded-full bg-gel-400 transition-all duration-1000" style={{ width: `${cal}%` }} />
            </div>
            <p className="mt-2 text-sm text-ivory/55">{calText}</p>
          </div>
        </div>
      </section>

      {/* Mood map */}
      <section>
        <h2 className="font-display text-3xl text-ivory">Your moods</h2>
        <p className="mt-1 max-w-xl text-ivory/60">What you reach for changes with how you feel. This is what we've learned for each mood.</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MOODS.map((m) => {
            const entry = me.mood_map.find((e) => e.mood === m.id);
            const remaining = Math.max(0, MIN_REACTIONS - (entry?.reactions ?? 0));
            return (
              <article key={m.id} className="relative overflow-hidden rounded-xl border bg-surface p-5" style={{ borderColor: `${m.hex}55` }}>
                <div aria-hidden className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full blur-2xl" style={{ background: `${m.hex}33` }} />
                <h3 className="relative font-display text-xl font-medium text-ivory">{m.label}</h3>
                <p className="relative mt-0.5 text-xs text-ivory/50">
                  {entry?.checkins ? `${entry.checkins} night${entry.checkins === 1 ? "" : "s"} so far` : "Not tried yet"}
                </p>
                {entry?.learned ? (
                  <div className="relative mt-4">
                    <p className="text-sm text-ivory/65">You reach for</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {entry.top_genres.map((g) => (
                        <span key={g} className="rounded-full px-3 py-1 text-sm text-ivory" style={{ background: `${m.hex}30`, border: `1px solid ${m.hex}77` }}>{g}</span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="relative mt-4">
                    <p className="text-sm text-ivory/60">
                      {entry && entry.reactions > 0
                        ? `${remaining} more reaction${remaining === 1 ? "" : "s"} and we'll start tailoring ${m.label.toLowerCase()} picks.`
                        : `Light this mood and react to what plays. After ${MIN_REACTIONS} reactions we start learning.`}
                    </p>
                    <button
                      onClick={() => { setMood(m.id); onTryMood(m.id); }}
                      className="mt-3 rounded-full border px-4 py-1.5 text-sm text-ivory transition hover:bg-ivory/5"
                      style={{ borderColor: `${m.hex}88` }}
                    >
                      Try {m.label.toLowerCase()}
                    </button>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <div className="grid gap-10 lg:grid-cols-2">
        {/* Recent nights */}
        <section>
          <h2 className="font-display text-3xl text-ivory">Recent nights</h2>
          {me.recent_checkins.length === 0 ? (
            <p className="mt-4 text-ivory/55">No nights yet. Open the Mood Studio and roll your first film.</p>
          ) : (
            <ol className="mt-5 space-y-4 border-l border-ivory/10 pl-6">
              {me.recent_checkins.map((c, i) => {
                const m = MOOD_BY_ID[c.mood];
                return (
                  <li key={i} className="relative">
                    <span aria-hidden className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full" style={{ background: m?.hex ?? "#C9A24B", boxShadow: `0 0 12px ${m?.hex ?? "#C9A24B"}` }} />
                    <p className="text-ivory">
                      <span className="font-display text-lg">{m?.label ?? c.mood}</span>
                      {c.genres.length > 0 && <span className="text-ivory/60">, leaning {c.genres.join(" and ")}</span>}
                    </p>
                    <p className="text-sm text-ivory/45">
                      {ago(c.created_at)}
                      {c.max_runtime ? `, up to ${c.max_runtime >= 240 ? "any length" : `${c.max_runtime} min`}` : ""}
                    </p>
                  </li>
                );
              })}
            </ol>
          )}
        </section>

        {/* Genres */}
        <section>
          <h2 className="font-display text-3xl text-ivory">Genres you lean toward</h2>
          {me.top_genres.length === 0 ? (
            <p className="mt-4 text-ivory/55">Nothing to show yet. Your first few reactions will start this list.</p>
          ) : (
            <ul className="mt-5 space-y-4">
              {me.top_genres.map((g) => (
                <li key={g.name}>
                  <div className="flex justify-between text-sm">
                    <span className="text-ivory/85">{g.name}</span>
                    <span className="text-ivory/45">{g.weight}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ivory/10">
                    <div className="h-full rounded-full bg-gel-400" style={{ width: `${g.weight}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* The reel */}
      <section>
        <h2 className="font-display text-3xl text-ivory">Your reel</h2>
        {reel.length === 0 ? (
          <p className="mt-4 flex items-center gap-2 text-ivory/55">
            <Bookmark className="h-4 w-4" /> Titles you save land here.
          </p>
        ) : (
          <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {reel.map((c) => (
              <button key={c.content_id} onClick={() => onSelectTitle(c)} className="group text-left">
                <div className="aspect-[2/3] overflow-hidden rounded-lg border border-brass/20 bg-surface">
                  <img src={c.poster_path || c.backdrop_path || ""} alt="" loading="lazy" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
                </div>
                <p className="mt-2 line-clamp-1 font-display text-ivory group-hover:text-gel-300">{c.title}</p>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Data & Privacy: Clear history & taste */}
      <section className="rounded-2xl border border-red-500/20 bg-velvet-deep/30 p-6 md:p-8">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="font-display text-xl text-ivory">Account History & Data</h2>
            <p className="mt-1 text-sm text-ivory/55">
              Reset your profile, delete your saved reel, reactions, and learned taste map.
            </p>
          </div>
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-red-500/40 px-4 py-2 text-sm font-medium text-red-300 transition hover:bg-red-500/10 hover:text-red-200"
            >
              <Trash2 className="h-4 w-4" />
              Delete my data
            </button>
          ) : (
            <div className="flex flex-col gap-3 rounded-xl border border-red-500/40 bg-pit/90 p-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2 text-xs text-red-300">
                <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
                <span>Are you sure? This action cannot be undone.</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleDeleteData}
                  disabled={isDeleting}
                  className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-ivory transition hover:bg-red-500 disabled:opacity-50"
                >
                  {isDeleting ? "Deleting…" : "Confirm Delete"}
                </button>
                <button
                  onClick={() => setShowConfirm(false)}
                  disabled={isDeleting}
                  className="rounded-lg border border-brass/30 px-3 py-1.5 text-xs text-ivory/70 transition hover:bg-surface hover:text-ivory"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
