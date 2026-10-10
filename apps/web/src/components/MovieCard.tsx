"use client";

import { CanonicalContent, RecommendationItem } from "@/types";

interface MovieCardProps {
  item: RecommendationItem | { content: CanonicalContent; personal_match_percentage?: number; reasons?: string[] };
  onSelect: (content: CanonicalContent, matchPct?: number) => void;
}

const FALLBACK = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80";

export default function MovieCard({ item, onSelect }: MovieCardProps) {
  const content = item.content;
  const matchPct = "personal_match_percentage" in item ? item.personal_match_percentage : undefined;
  const reason = "reasons" in item && item.reasons && item.reasons.length > 0 ? item.reasons[0] : null;
  const imageSrc = content.backdrop_path || content.poster_path || FALLBACK;

  return (
    <button
      type="button"
      onClick={() => onSelect(content, matchPct)}
      className="group relative flex flex-col overflow-hidden rounded-lg border border-brass/15 bg-surface text-left transition duration-300 hover:-translate-y-1 hover:border-gel-400/60 hover:shadow-2xl hover:shadow-gel-500/10"
    >
      <div className="relative aspect-video w-full overflow-hidden bg-pit">
        <img
          src={imageSrc}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/20 to-transparent" />
        {matchPct !== undefined && (
          <span className="absolute right-2.5 top-2.5 rounded-full bg-pit/85 px-2.5 py-1 text-xs font-semibold text-gel-300 backdrop-blur">
            {matchPct}% match
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col justify-between p-4">
        <div>
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="line-clamp-1 font-display text-lg font-medium text-ivory transition-colors group-hover:text-gel-300">
              {content.title}
            </h3>
            {content.release_year && <span className="shrink-0 text-xs text-ivory/45">{content.release_year}</span>}
          </div>
          {reason && <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-ivory/55">{reason}</p>}
        </div>
        <div className="mt-3 flex items-center justify-between gap-2 border-t border-ivory/[0.07] pt-3 text-xs text-ivory/55">
          <span className="flex gap-3">
            {content.runtime ? <span>{content.runtime} min</span> : null}
            {content.genres[0] && <span className="text-ivory/75">{content.genres[0]}</span>}
          </span>
          {content.providers[0] && (
            <span className="rounded border border-gel-500/25 bg-gel-500/10 px-1.5 py-0.5 text-[11px] text-gel-300">
              {content.providers[0].provider_name.split(" ")[0]}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
