"use client";

import { useEffect, useState } from "react";
import { Clapperboard, Info, Play, X } from "lucide-react";
import MovieCard from "./MovieCard";
import MoodDimmer from "./MoodDimmer";
import { fetchDiscoveryDeck } from "@/lib/api";
import { useMood } from "@/context/MoodContext";
import { useMe } from "@/context/MeContext";
import { greeting } from "@/lib/moods";
import { CanonicalContent, DiscoveryDeck, RecommendationItem } from "@/types";

interface Props {
  onSelectTitle: (content: CanonicalContent, matchPct?: number) => void;
  onOpenStudio: () => void;
}

function Rail({ title, sub, items, onSelect, cols = "lg:grid-cols-4" }: { title: string; sub?: string; items: RecommendationItem[]; onSelect: Props["onSelectTitle"]; cols?: string }) {
  if (!items?.length) return null;
  return (
    <section>
      <h2 className="font-display text-2xl text-ivory sm:text-3xl">{title}</h2>
      {sub && <p className="mt-1 text-sm text-ivory/55">{sub}</p>}
      <div className={`mt-5 grid gap-4 sm:grid-cols-2 ${cols}`}>
        {items.map((it) => (
          <MovieCard key={it.content.content_id} item={it} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}

/** The lobby: the same catalogue, re-ordered by whichever mood is lit. */
export default function DiscoveryHomeView({ onSelectTitle, onOpenStudio }: Props) {
  const { mood, setMood, theme } = useMood();
  const { me } = useMe();
  const [deck, setDeck] = useState<DiscoveryDeck | null>(null);
  const [loading, setLoading] = useState(true);
  const [playingTrailer, setPlayingTrailer] = useState(false);

  useEffect(() => {
    let live = true;
    setLoading(true);
    fetchDiscoveryDeck(mood).then((d) => {
      if (!live) return;
      setDeck(d);
      setLoading(false);
    });
    return () => {
      live = false;
    };
  }, [mood]);

  const first = me?.display_name?.split(" ")[0];
  const learning = (me?.stats.reactions ?? 0) === 0;
  const hero = deck?.hero;

  return (
    <div className="space-y-14 pb-10">
      <section className="text-center">
        <p className="font-display text-lg italic text-ivory/60">{greeting()}{first ? `, ${first}` : ""}.</p>
        <h1 className="mt-2 font-display text-4xl font-semibold text-ivory sm:text-6xl">{theme ? theme.line : "What are we in the mood for?"}</h1>
        <div className="mt-8"><MoodDimmer variant="row" value={mood} onChange={setMood} /></div>
        {theme && (
          <button onClick={onOpenStudio} className="mt-8 inline-flex items-center gap-2 rounded-full bg-gel-500 px-7 py-3 text-sm font-semibold text-pit shadow-lg shadow-gel-500/30 hover:bg-gel-400">
            <Clapperboard className="h-4 w-4" /> Fine-tune in the Mood Studio
          </button>
        )}
      </section>

      {loading || !deck || !hero ? (
        <div className="space-y-6" aria-busy="true">
          <div className="aspect-[21/9] animate-pulse rounded-3xl bg-surface" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <div key={i} className="aspect-[4/3] animate-pulse rounded-lg bg-surface" />)}</div>
        </div>
      ) : (
        <>
          <section className="relative overflow-hidden rounded-3xl border border-brass/30 bg-surface shadow-[0_30px_100px_-40px_rgb(var(--g500)/0.6)]">
            <div className="relative aspect-[4/5] sm:aspect-[16/9] lg:aspect-[21/9]">
              <img src={hero.content.backdrop_path || hero.content.poster_path || ""} alt="" className="absolute inset-0 h-full w-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-pit via-pit/50 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 p-6 sm:p-10">
                <p className="text-sm text-gel-300">{theme ? `Tonight's top pick for a ${theme.label.toLowerCase()} mood` : learning ? "A strong place to start" : "Top pick for your taste"}</p>
                <h2 className="mt-1 font-display text-4xl font-semibold text-ivory sm:text-6xl">{hero.content.title}</h2>
                {hero.content.tagline && (
                  <p className="mt-2 font-display text-sm italic text-gel-300 sm:text-base">"{hero.content.tagline}"</p>
                )}
                <p className="mt-3 line-clamp-2 max-w-2xl text-ivory/75">{hero.content.overview}</p>
                <div className="mt-5 flex flex-wrap items-center gap-4">
                  <button onClick={() => onSelectTitle(hero.content, hero.personal_match_percentage)} className="flex items-center gap-2 rounded-full bg-gel-500 px-6 py-3 text-sm font-semibold text-pit hover:bg-gel-400">
                    <Info className="h-4 w-4" /> Why should I watch this?
                  </button>
                  {hero.content.trailer_key && (
                    <button
                      onClick={() => setPlayingTrailer(true)}
                      className="flex items-center gap-2 rounded-full border border-gel-400/60 bg-gel-500/10 px-5 py-3 text-sm font-semibold text-gel-300 hover:bg-gel-500/20"
                    >
                      <Play className="h-4 w-4 fill-current" /> Watch trailer
                    </button>
                  )}
                  {!learning && <span className="text-sm text-ivory/70">{hero.personal_match_percentage}% match</span>}
                </div>
              </div>

              {playingTrailer && hero.content.trailer_key && (
                <div className="absolute inset-0 z-30 flex flex-col bg-black">
                  <div className="flex items-center justify-between border-b border-white/10 bg-pit/90 px-4 py-2">
                    <span className="font-display text-xs text-ivory">{hero.content.title} - Official Trailer</span>
                    <button onClick={() => setPlayingTrailer(false)} className="flex items-center gap-1 text-xs text-ivory/70 hover:text-ivory">
                      <X className="h-4 w-4" /> Close
                    </button>
                  </div>
                  <iframe
                    src={`https://www.youtube-nocookie.com/embed/${hero.content.trailer_key}?autoplay=1`}
                    title={`${hero.content.title} trailer`}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    className="h-full w-full border-0"
                  />
                </div>
              )}
            </div>
          </section>

          <Rail
            title={theme ? `Playing tonight in ${theme.label.toLowerCase()}` : "Picked for you"}
            sub={theme ? theme.line : learning ? "A starting set while we learn your taste." : "Ranked by your taste so far."}
            items={deck.tonight_picks}
            onSelect={onSelectTitle}
            cols="lg:grid-cols-5"
          />
          <Rail title="From further afield" sub="Great stories from outside the usual places." items={deck.unexpected_discoveries} onSelect={onSelectTitle} />
          <Rail title="Easy watching" sub="Light on the nerves." items={deck.comfort_rail} onSelect={onSelectTitle} />
          <Rail title="Fast and loud" sub="When you want momentum." items={deck.adrenaline_rail} onSelect={onSelectTitle} />
          <Rail title="Indian cinema" items={deck.indian_cinema_rail} onSelect={onSelectTitle} cols="lg:grid-cols-3" />

          {deck.around_the_world &&
            Object.entries(deck.around_the_world).map(([region, titles]) =>
              titles.length ? (
                <Rail key={region} title={region} items={titles.map((c) => ({ content: c }) as any)} onSelect={onSelectTitle} />
              ) : null
            )}
        </>
      )}
    </div>
  );
}
