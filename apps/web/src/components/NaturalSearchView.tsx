"use client";

import { useState, useEffect } from "react";
import { executeNaturalSearch, searchPeopleOnline, fetchPeopleHub, fetchCharacterVibe } from "@/lib/api";
import { CanonicalContent, RecommendationItem } from "@/types";
import { Search, Sparkles, User, Video, Clapperboard, Star, Film, ArrowRight, Play, Compass, Activity, X } from "lucide-react";
import MovieCard from "./MovieCard";

interface NaturalSearchViewProps {
  onSelectTitle: (content: CanonicalContent, matchPct?: number) => void;
}

export default function NaturalSearchView({ onSelectTitle }: NaturalSearchViewProps) {
  const [activeTab, setActiveTab] = useState<"titles" | "people" | "characters">("titles");
  const [query, setQuery] = useState("a Korean thriller with a satisfying ending");
  const [loading, setLoading] = useState(false);
  
  // Title results
  const [data, setData] = useState<any>(null);

  // People results
  const [peopleData, setPeopleData] = useState<any[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<any>(null);

  // Character Vibe modal/state
  const [characterQuery, setCharacterQuery] = useState({ actor: "", character: "", title: "" });
  const [vibeResults, setVibeResults] = useState<any>(null);
  const [vibeLoading, setVibeLoading] = useState(false);

  const sampleTitleQueries = [
    "a Korean thriller with a satisfying ending",
    "something like Dark but less confusing",
    "something emotional that will make me think",
    "90 minute mystery with atmosphere",
    "comforting movie for two people"
  ];

  const samplePeopleQueries = [
    "Christopher Nolan",
    "Denis Villeneuve",
    "Bong Joon Ho",
    "Leonardo DiCaprio",
    "Song Kang-ho",
    "Cillian Murphy"
  ];

  const sampleCharacterQueries = [
    { actor: "Cillian Murphy", character: "J. Robert Oppenheimer", title: "Oppenheimer" },
    { actor: "Song Kang-ho", character: "Ki-taek", title: "Parasite" },
    { actor: "Christian Bale", character: "Alfred Borden", title: "The Prestige" },
    { actor: "Ryan Gosling", character: "Officer K", title: "Blade Runner 2049" }
  ];

  useEffect(() => {
    if (activeTab === "people" && peopleData.length === 0) {
      loadInitialPeople();
    }
  }, [activeTab]);

  const loadInitialPeople = async () => {
    setLoading(true);
    const hub = await fetchPeopleHub();
    if (hub && (hub.directors || hub.stars)) {
      const combined = [
        ...(hub.directors || []).map((d: any) => ({ ...d, type: "director" })),
        ...(hub.stars || []).map((s: any) => ({ ...s, type: "star" }))
      ];
      setPeopleData(combined);
    }
    setLoading(false);
  };

  const handleSearch = async (overrideQ?: string) => {
    const activeQ = overrideQ || query;
    if (!activeQ.trim()) return;
    setLoading(true);

    if (activeTab === "titles") {
      const res = await executeNaturalSearch(activeQ);
      if (res) setData(res);
    } else if (activeTab === "people") {
      const res = await searchPeopleOnline(activeQ);
      if (res && res.results) {
        setPeopleData(res.results);
      }
    }
    setLoading(false);
  };

  const handleExploreCharacterVibe = async (actor: string, character?: string, title?: string) => {
    setCharacterQuery({ actor, character: character || "", title: title || "" });
    setVibeLoading(true);
    const res = await fetchCharacterVibe({
      actorName: actor,
      characterName: character,
      referenceTitle: title
    });
    setVibeResults(res);
    setVibeLoading(false);
  };

  return (
    <div className="space-y-8">
      {/* Search Header */}
      <div className="rounded-2xl border border-brass/25 bg-surface p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Search className="h-4 w-4 text-gel-400" />
              <span className="text-xs font-semibold tracking-widest text-gel-300 uppercase">
                Cinema Intelligence & People Index
              </span>
            </div>
            <h1 className="font-display text-3xl font-bold text-ivory">Search & Exploration</h1>
          </div>

          {/* Search Mode Tabs */}
          <div className="flex rounded-xl bg-surface-elevated p-1 border border-brass/20 text-xs">
            <button
              onClick={() => { setActiveTab("titles"); setQuery("a Korean thriller with a satisfying ending"); }}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 font-medium transition ${activeTab === "titles" ? "bg-gel-400/20 text-gel-300 border border-gel-400/40" : "text-ivory/60 hover:text-ivory"}`}
            >
              <Film className="h-3.5 w-3.5" />
              <span>Titles & Tone</span>
            </button>
            <button
              onClick={() => { setActiveTab("people"); setQuery("Christopher Nolan"); }}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 font-medium transition ${activeTab === "people" ? "bg-gel-400/20 text-gel-300 border border-gel-400/40" : "text-ivory/60 hover:text-ivory"}`}
            >
              <User className="h-3.5 w-3.5" />
              <span>Directors & Stars</span>
            </button>
            <button
              onClick={() => { setActiveTab("characters"); }}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 font-medium transition ${activeTab === "characters" ? "bg-gel-400/20 text-gel-300 border border-gel-400/40" : "text-ivory/60 hover:text-ivory"}`}
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Character Vibes</span>
            </button>
          </div>
        </div>

        <p className="text-sm text-ivory/65 max-w-2xl leading-relaxed">
          {activeTab === "titles" && "Search with semantic feeling, runtimes, negative filters, and thematic comparisons."}
          {activeTab === "people" && "Search visionaries and stars with their complete filmographies ordered by rating."}
          {activeTab === "characters" && "Discover films and performances sharing the exact psychological aura of specific characters."}
        </p>

        {/* Input Box for Titles & People */}
        {activeTab !== "characters" && (
          <div className="mt-6 flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder={activeTab === "titles" ? "e.g. something like Inception but more character-driven..." : "e.g. Denis Villeneuve, Song Kang-ho, Nolan..."}
                className="w-full rounded-xl border border-brass/30 bg-surface-elevated px-4 py-3 text-sm text-ivory placeholder-ivory/40 focus:border-gel-400 focus:outline-none focus:ring-1 focus:ring-gel-400"
              />
            </div>
            <button
              onClick={() => handleSearch()}
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-xl bg-velvet hover:bg-velvet-light px-6 py-3 text-sm font-semibold text-ivory border border-brass/30 shadow-lg transition-colors disabled:opacity-50"
            >
              <Search className="h-4 w-4" />
              <span>{loading ? "Searching..." : "Search"}</span>
            </button>
          </div>
        )}

        {/* Quick Suggestion Pills */}
        {activeTab === "titles" && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-ivory/50">Try:</span>
            {sampleTitleQueries.map((sample, i) => (
              <button
                key={i}
                onClick={() => { setQuery(sample); handleSearch(sample); }}
                className="rounded-lg bg-surface-elevated px-3 py-1 text-xs text-ivory/75 hover:bg-surface-subtle hover:text-ivory transition-colors border border-brass/20"
              >
                "{sample}"
              </button>
            ))}
          </div>
        )}

        {activeTab === "people" && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-ivory/50">Featured creators:</span>
            {samplePeopleQueries.map((name, i) => (
              <button
                key={i}
                onClick={() => { setQuery(name); handleSearch(name); }}
                className="rounded-lg bg-surface-elevated px-3 py-1 text-xs text-ivory/75 hover:bg-surface-subtle hover:text-ivory transition-colors border border-brass/20"
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Mode 1: Titles Results */}
      {activeTab === "titles" && (
        <div className="space-y-6">
          {data?.parsed_intent && (
            <div className="rounded-xl border border-gel-400/30 bg-surface p-5 shadow-lg">
              <div className="flex items-center gap-2 mb-3 text-xs font-bold text-gel-300 uppercase tracking-wider">
                <Sparkles className="h-4 w-4" />
                <span>Understood Structured Intent</span>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                {data.parsed_intent.mood && (
                  <span className="rounded-full bg-gel-400/15 px-3 py-1 text-gel-200 border border-gel-400/30">
                    Mood: {data.parsed_intent.mood}
                  </span>
                )}
                {data.parsed_intent.max_runtime && (
                  <span className="rounded-full bg-gel-400/15 px-3 py-1 text-gel-200 border border-gel-400/30">
                    Runtime: ≤ {data.parsed_intent.max_runtime} min
                  </span>
                )}
                {data.parsed_intent.preferred_regions?.length > 0 && (
                  <span className="rounded-full bg-brass/20 px-3 py-1 text-brass-light border border-brass/30">
                    Region: {data.parsed_intent.preferred_regions.join(", ")}
                  </span>
                )}
                {data.parsed_intent.avoid_tags?.length > 0 && (
                  <span className="rounded-full bg-velvet/40 px-3 py-1 text-rose-300 border border-velvet/50">
                    Avoid: {data.parsed_intent.avoid_tags.join(", ")}
                  </span>
                )}
              </div>
            </div>
          )}

          {data?.results && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-ivory/60">
                <span>Retrieved {data.results.length} ranked titles matching semantic profile</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {data.results.map((item: RecommendationItem) => (
                  <MovieCard
                    key={item.content.content_id}
                    item={item}
                    onSelect={(c) => onSelectTitle(c, item.personal_match_percentage)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mode 2: People Results (Directors & Stars with Headshots) */}
      {activeTab === "people" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {peopleData.map((person, idx) => (
              <div
                key={person.person_id || person.name || idx}
                className="rounded-2xl border border-brass/20 bg-surface p-5 flex flex-col justify-between shadow-xl hover:border-gel-400/50 transition-all duration-300"
              >
                <div>
                  <div className="flex items-start gap-4">
                    <div className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-full border-2 border-brass/40 bg-surface-subtle shadow-md">
                      {person.profile_path ? (
                        <img
                          src={person.profile_path}
                          alt={person.name}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs text-ivory/40">
                          <User className="h-8 w-8 text-ivory/30" />
                        </div>
                      )}
                    </div>
                    <div>
                      <span className="text-[10px] font-bold tracking-widest text-gel-300 uppercase">
                        {person.role || (person.known_for_department === "Directing" ? "Visionary Director" : "Leading Star")}
                      </span>
                      <h3 className="font-display text-lg font-bold text-ivory mt-0.5">{person.name}</h3>
                      <div className="flex items-center gap-2 mt-1 text-xs text-ivory/60">
                        <span className="flex items-center gap-1 text-amber-400 font-semibold">
                          <Star className="h-3 w-3 fill-amber-400" />
                          {person.avg_rating || "8.1"}
                        </span>
                        <span>•</span>
                        <span>{person.titles?.length || person.filmography_count || 0} acclaimed titles</span>
                      </div>
                    </div>
                  </div>

                  {/* Top filmography preview */}
                  <div className="mt-4 space-y-2 border-t border-brass/15 pt-3">
                    <span className="text-[10px] font-semibold tracking-wider text-brass-light uppercase">
                      Signature Filmography:
                    </span>
                    <div className="space-y-1.5">
                      {(person.titles || []).slice(0, 3).map((t: any) => (
                        <div
                          key={t.content_id || t.title}
                          onClick={() => onSelectTitle(t)}
                          className="flex items-center justify-between p-2 rounded-lg bg-surface-elevated hover:bg-surface-subtle cursor-pointer transition text-xs group"
                        >
                          <span className="font-medium text-ivory group-hover:text-gel-300 truncate max-w-[200px]">
                            {t.title}
                          </span>
                          <span className="text-emerald-400 font-bold">{t.vote_average?.toFixed(1)} ★</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Character Vibe Explore Trigger */}
                <div className="mt-4 pt-3 border-t border-brass/15 flex items-center justify-between">
                  <button
                    onClick={() => handleExploreCharacterVibe(person.name, person.titles?.[0]?.character, person.titles?.[0]?.title)}
                    className="flex items-center gap-1.5 text-xs font-semibold text-gel-300 hover:text-gel-200 transition"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Find Similar Character Vibes</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mode 3: Character Vibes Explorer */}
      {activeTab === "characters" && (
        <div className="space-y-8">
          <div className="rounded-2xl border border-brass/25 bg-surface p-6 shadow-xl space-y-4">
            <h3 className="font-display text-xl font-bold text-ivory flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-gel-400" />
              <span>Choose a Signature Character Archetype</span>
            </h3>
            <p className="text-xs text-ivory/65 leading-relaxed max-w-2xl">
              Select an iconic role below or enter your favorite character. The engine will match psychological weight, moral complexity, and cinematic energy.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-2">
              {sampleCharacterQueries.map((item, i) => (
                <button
                  key={i}
                  onClick={() => handleExploreCharacterVibe(item.actor, item.character, item.title)}
                  className="rounded-xl border border-brass/20 bg-surface-elevated p-3 text-left hover:border-gel-400 hover:bg-surface-subtle transition shadow-md"
                >
                  <span className="text-[10px] font-bold text-gel-300 uppercase block">{item.title}</span>
                  <div className="font-display text-sm font-bold text-ivory mt-0.5">{item.character}</div>
                  <div className="text-xs text-ivory/50 mt-1">Played by {item.actor}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Vibe Results Display */}
          {vibeLoading && (
            <div className="flex h-32 items-center justify-center font-display text-sm italic text-ivory/50">
              <Activity className="h-5 w-5 animate-spin text-gel-400 mr-2" />
              <span>Extracting character psychology and matching vibes…</span>
            </div>
          )}

          {vibeResults && !vibeLoading && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-gel-400/30 bg-surface-elevated p-6 shadow-xl">
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="h-4 w-4 text-gel-400" />
                  <span className="text-xs font-semibold tracking-widest text-gel-300 uppercase">
                    Psychological Resonance Result
                  </span>
                </div>
                <h3 className="font-display text-2xl font-bold text-ivory">
                  {vibeResults.archetype_summary}
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {vibeResults.results.map((res: any) => {
                  const item = res.content;
                  return (
                    <div
                      key={item.content_id}
                      onClick={() => onSelectTitle(item, res.personal_match_percentage)}
                      className="group cursor-pointer overflow-hidden rounded-xl border border-brass/20 bg-surface p-3 transition-all duration-300 hover:border-gel-400 hover:shadow-xl"
                    >
                      <div className="aspect-[2/3] w-full overflow-hidden rounded-lg bg-surface-subtle mb-3 relative">
                        {item.poster_path ? (
                          <img
                            src={item.poster_path}
                            alt={item.title}
                            className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
                          />
                        ) : (
                          <div className="flex h-full items-center justify-center text-xs text-ivory/40">No Poster</div>
                        )}
                        <div className="absolute top-2 right-2 rounded bg-pit/80 px-2 py-0.5 text-[10px] font-bold text-gel-300 border border-brass/20">
                          {res.personal_match_percentage}% Vibe Fit
                        </div>
                      </div>

                      <h4 className="font-display text-sm font-bold text-ivory truncate">{item.title}</h4>
                      <p className="text-[11px] text-ivory/50 mt-0.5">{item.release_year} • {item.genres?.[0]}</p>

                      <div className="mt-2.5 space-y-1">
                        {res.vibe_reasons.map((r: string, idx: number) => (
                          <div key={idx} className="text-[10px] text-gel-200/90 leading-tight flex items-start gap-1">
                            <span>•</span>
                            <span>{r}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
