"use client";

import { useState } from "react";
import { executeNaturalSearch } from "@/lib/api";
import { CanonicalContent, RecommendationItem } from "@/types";
import { Search, Sparkles, Filter, AlertCircle } from "lucide-react";
import MovieCard from "./MovieCard";

interface NaturalSearchViewProps {
  onSelectTitle: (content: CanonicalContent) => void;
}

export default function NaturalSearchView({ onSelectTitle }: NaturalSearchViewProps) {
  const [query, setQuery] = useState("a Korean thriller with a satisfying ending");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  const sampleQueries = [
    "a Korean thriller with a satisfying ending",
    "something like Dark but less confusing",
    "something emotional that will make me think",
    "90 minute mystery with atmosphere",
    "comforting movie for two people"
  ];

  const handleSearch = async (qText?: string) => {
    const activeQuery = qText || query;
    if (!activeQuery.trim()) return;
    setLoading(true);
    const res = await executeNaturalSearch(activeQuery);
    if (res) {
      setData(res);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="rounded-2xl border border-brass/25 bg-surface p-6 sm:p-8">
        <div className="flex items-center gap-2 mb-2">
          <Search className="h-4 w-4 text-gel-400" />
          <span className="text-xs font-semibold tracking-widest text-gel-300 uppercase">
            Semantic & Intent Search
          </span>
        </div>
        <h1 className="font-display text-3xl font-bold text-ivory">Natural Search</h1>
        <p className="mt-2 text-sm text-ivory/65 max-w-2xl leading-relaxed">
          Ask for cinematic qualities, emotional tones, negative constraints, and thematic comparisons rather than keywords.
        </p>

        {/* Input Box */}
        <div className="mt-6 flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="e.g. something like Inception but more character-driven..."
              className="w-full rounded-xl border border-brass/30 bg-surface-elevated px-4 py-3 text-sm text-ivory placeholder-ivory/40 focus:border-gel-400 focus:outline-none focus:ring-1 focus:ring-gel-400"
            />
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="flex items-center justify-center gap-2 rounded-xl bg-velvet hover:bg-velvet-light px-6 py-3 text-sm font-semibold text-ivory border border-brass/30 shadow-lg transition-colors disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            <span>{loading ? "Parsing..." : "Search"}</span>
          </button>
        </div>

        {/* Quick Suggestion Pills */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-ivory/50">Try asking:</span>
          {sampleQueries.map((sample, i) => (
            <button
              key={i}
              onClick={() => {
                setQuery(sample);
                handleSearch(sample);
              }}
              className="rounded-lg bg-surface-elevated px-3 py-1 text-xs text-ivory/75 hover:bg-surface-subtle hover:text-ivory transition-colors border border-brass/20"
            >
              "{sample}"
            </button>
          ))}
        </div>
      </div>

      {/* Parsed Intent Badges */}
      {data?.parsed_intent && (
        <div className="rounded-xl border border-gel-400/30 bg-surface p-5">
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
                Runtime Constraint: ≤ {data.parsed_intent.max_runtime} min
              </span>
            )}
            {data.parsed_intent.preferred_regions?.length > 0 && (
              <span className="rounded-full bg-brass/20 px-3 py-1 text-brass-light border border-brass/30">
                Region: {data.parsed_intent.preferred_regions.join(", ")}
              </span>
            )}
            {data.parsed_intent.avoid_tags?.length > 0 && (
              <span className="rounded-full bg-velvet/40 px-3 py-1 text-rose-300 border border-velvet/50">
                Negative Filter: Avoid {data.parsed_intent.avoid_tags.join(", ")}
              </span>
            )}
            {data.parsed_intent.novelty && (
              <span className="rounded-full bg-gel-400/15 px-3 py-1 text-gel-200 border border-gel-400/30">
                Novelty: {Math.round(data.parsed_intent.novelty * 100)}%
              </span>
            )}
          </div>
        </div>
      )}

      {/* Results Grid */}
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
                onSelect={onSelectTitle}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
