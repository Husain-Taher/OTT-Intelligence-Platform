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
      <div className="rounded-2xl border border-white/[0.08] bg-surface p-6 sm:p-8">
        <div className="flex items-center gap-2 mb-2">
          <Search className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-bold tracking-widest text-indigo-400 uppercase">
            Semantic & Intent Search
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-white">Natural Search</h1>
        <p className="mt-1 text-sm text-slate-400 max-w-2xl leading-relaxed">
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
              className="w-full rounded-xl border border-white/10 bg-[#0E0B0A] px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:bg-indigo-500 transition-colors disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            <span>{loading ? "Parsing..." : "Search"}</span>
          </button>
        </div>

        {/* Quick Suggestion Pills */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Try asking:</span>
          {sampleQueries.map((sample, i) => (
            <button
              key={i}
              onClick={() => {
                setQuery(sample);
                handleSearch(sample);
              }}
              className="rounded-lg bg-white/[0.04] px-2.5 py-1 text-xs text-slate-300 hover:bg-white/[0.08] hover:text-white transition-colors border border-white/[0.06]"
            >
              "{sample}"
            </button>
          ))}
        </div>
      </div>

      {/* Parsed Intent Badges */}
      {data?.parsed_intent && (
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4">
          <div className="flex items-center gap-2 mb-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Understood Structured Intent</span>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            {data.parsed_intent.mood && (
              <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-indigo-300 border border-indigo-500/30">
                Mood: {data.parsed_intent.mood}
              </span>
            )}
            {data.parsed_intent.max_runtime && (
              <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-indigo-300 border border-indigo-500/30">
                Runtime Constraint: ≤ {data.parsed_intent.max_runtime} min
              </span>
            )}
            {data.parsed_intent.preferred_regions?.length > 0 && (
              <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-emerald-300 border border-emerald-500/30">
                Region: {data.parsed_intent.preferred_regions.join(", ")}
              </span>
            )}
            {data.parsed_intent.avoid_tags?.length > 0 && (
              <span className="rounded-full bg-rose-500/20 px-3 py-1 text-rose-300 border border-rose-500/30">
                Negative Filter: Avoid {data.parsed_intent.avoid_tags.join(", ")}
              </span>
            )}
            {data.parsed_intent.novelty && (
              <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-indigo-300 border border-indigo-500/30">
                Novelty: {Math.round(data.parsed_intent.novelty * 100)}%
              </span>
            )}
          </div>
        </div>
      )}

      {/* Results Grid */}
      {data?.results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
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
