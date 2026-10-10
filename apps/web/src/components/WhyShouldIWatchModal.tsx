"use client";

import { useState } from "react";
import { CanonicalContent } from "@/types";
import { recordUserEvent } from "@/lib/api";
import { X, Play, Bookmark, ThumbsDown, AlertOctagon, CheckCircle2, Tv, Sparkles } from "lucide-react";

interface WhyModalProps {
  content: CanonicalContent | null;
  onClose: () => void;
  onEventLogged?: () => void;
  /** Real match score for this title, when we have one. Nothing is shown otherwise. */
  matchPct?: number;
  moodLabel?: string;
}

export default function WhyShouldIWatchModal({ content, onClose, onEventLogged, matchPct, moodLabel }: WhyModalProps) {
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null);

  if (!content) return null;

  const prof = content.profile;

  const handleAction = async (eventType: string, label: string) => {
    setFeedbackStatus(`Recorded: ${label}`);
    await recordUserEvent(content.content_id, eventType);
    if (onEventLogged) onEventLogged();
    setTimeout(() => setFeedbackStatus(null), 3000);
  };

  const backdrop = content.backdrop_path || content.poster_path || "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1200&q=80";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto bg-black/85 backdrop-blur-md">
      <div className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl bg-surface border border-white/[0.12] shadow-2xl">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 flex h-9 w-9 items-center justify-center rounded-full bg-black/60 text-slate-300 hover:text-white hover:bg-black/80 backdrop-blur-sm transition-colors border border-white/10"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Hero Backdrop Section */}
        <div className="relative aspect-[21/9] w-full overflow-hidden">
          <img src={backdrop} alt={content.title} className="h-full w-full object-cover object-center" />
          <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/60 to-transparent" />
          
          <div className="absolute bottom-6 left-6 right-6">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              {matchPct !== undefined && (
                <span className="flex items-center gap-1.5 rounded-full bg-gel-500/20 px-3 py-1 text-xs font-bold text-gel-300 border border-gel-500/30">
                  <Sparkles className="h-3.5 w-3.5" />
                  {matchPct}% match{moodLabel ? ` for a ${moodLabel.toLowerCase()} night` : ""}
                </span>
              )}
              {content.runtime && (
                <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs text-slate-300">
                  {content.runtime} min
                </span>
              )}
              {content.release_year && (
                <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs text-slate-300">
                  {content.release_year}
                </span>
              )}
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">{content.title}</h2>
            {content.tagline && (
              <p className="mt-1 text-xs sm:text-sm text-slate-400 italic">"{content.tagline}"</p>
            )}

            {/* Quick Actions */}
            <div className="mt-4 flex flex-wrap items-center gap-2.5">
              <button
                onClick={() => handleAction("WATCH_COMPLETE", "Marked as Watched")}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg hover:bg-indigo-500 transition-colors"
              >
                <Play className="h-4 w-4 fill-white" />
                <span>Watch</span>
              </button>
              <button
                onClick={() => handleAction("SAVE", "Saved to List")}
                className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-white/10 transition-colors"
              >
                <Bookmark className="h-3.5 w-3.5" />
                <span>Save</span>
              </button>
              <button
                onClick={() => handleAction("DISLIKE", "Preference Calibrated (Disliked)")}
                className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-white/10 transition-colors"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
                <span>Not For Me</span>
              </button>
              <button
                onClick={() => handleAction("ABANDON", "Recorded Abandonment")}
                className="flex items-center gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-300 hover:bg-rose-500/20 transition-colors"
              >
                <AlertOctagon className="h-3.5 w-3.5" />
                <span>Abandoned</span>
              </button>
            </div>

            {feedbackStatus && (
              <div className="mt-2 text-xs font-medium text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{feedbackStatus}</span>
              </div>
            )}
          </div>
        </div>

        {/* Content Body Grid */}
        <div className="p-6 space-y-6">
          
          {/* Overview */}
          <div>
            <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Premise</h4>
            <p className="mt-1 text-sm text-slate-300 leading-relaxed">{content.overview}</p>
          </div>

          {/* Section: Why it Matches You (Mapping) */}
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
            <h4 className="text-xs font-semibold tracking-wider text-indigo-400 uppercase mb-3 flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5" />
              Why It Matches You
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                <span className="text-slate-400">Your Taste: Slow-burn pacing</span>
                <span className="font-semibold text-slate-200">Deliberate unhurried build</span>
              </div>
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                <span className="text-slate-400">Your Taste: Mystery</span>
                <span className="font-semibold text-slate-200">High investigation payoff</span>
              </div>
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                <span className="text-slate-400">Your Taste: Character depth</span>
                <span className="font-semibold text-slate-200">Morally ambiguous characters</span>
              </div>
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                <span className="text-slate-400">Your Taste: World-building</span>
                <span className="font-semibold text-slate-200">High atmosphere immersion</span>
              </div>
            </div>
          </div>

          {/* Section: Audience Reaction & Aspects */}
          {prof && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              
              {/* Audience Reaction */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
                <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3">
                  Audience Reaction Spectrum
                </h4>
                <div className="space-y-2.5">
                  {Object.entries(prof.audience_reaction).map(([k, v]) => (
                    <div key={k} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">{k}</span>
                        <span className="font-semibold text-indigo-400">{v}%</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-indigo-400"
                          style={{ width: `${v}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* What Viewers Loved vs Divided */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3">
                    What Viewers Loved
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                    <div className="flex justify-between bg-white/[0.03] p-2 rounded">
                      <span className="text-slate-400">Atmosphere</span>
                      <span className="font-semibold text-emerald-400">{prof.aspect_breakdown.atmosphere}%</span>
                    </div>
                    <div className="flex justify-between bg-white/[0.03] p-2 rounded">
                      <span className="text-slate-400">Characters</span>
                      <span className="font-semibold text-emerald-400">{prof.aspect_breakdown.characters}%</span>
                    </div>
                    <div className="flex justify-between bg-white/[0.03] p-2 rounded">
                      <span className="text-slate-400">Story</span>
                      <span className="font-semibold text-emerald-400">{prof.aspect_breakdown.story}%</span>
                    </div>
                    <div className="flex justify-between bg-white/[0.03] p-2 rounded">
                      <span className="text-slate-400">Acting</span>
                      <span className="font-semibold text-emerald-400">{prof.aspect_breakdown.acting}%</span>
                    </div>
                  </div>

                  <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-2">
                    What Divided Viewers
                  </h4>
                  <div className="flex gap-2 text-xs">
                    <span className="rounded bg-amber-500/10 px-2 py-1 text-amber-300 border border-amber-500/20">
                      Pacing: {prof.aspect_breakdown.pacing_rating}%
                    </span>
                    <span className="rounded bg-amber-500/10 px-2 py-1 text-amber-300 border border-amber-500/20">
                      Ending: {prof.aspect_breakdown.ending_satisfaction}%
                    </span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-white/[0.06] text-xs text-slate-400 italic">
                  "{prof.audience_voice_summary}"
                </div>
              </div>
            </div>
          )}

          {/* Section: Review Signals & Verified Quotes */}
          {prof && prof.highlighted_quotes.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3">
                Review Intelligence Signals
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {prof.highlighted_quotes.map((q) => (
                  <div key={q.id} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 text-xs">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-[10px] tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 uppercase">
                        {q.tag}
                      </span>
                      <span className="text-[10px] text-slate-500">{q.author}</span>
                    </div>
                    <p className="text-slate-300 italic leading-relaxed">"{q.text}"</p>
                    <div className="mt-2 text-[10px] text-slate-500">Source: {q.source}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Available Streaming Platforms */}
          <div className="flex items-center justify-between border-t border-white/[0.08] pt-4">
            <div className="flex items-center gap-2">
              <Tv className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-medium text-slate-300">Available on:</span>
            </div>
            <div className="flex items-center gap-2">
              {content.providers.length > 0 ? (
                content.providers.map((p) => (
                  <span
                    key={p.provider_id}
                    className="rounded-lg bg-surface-elevated border border-white/10 px-2.5 py-1 text-xs font-semibold text-indigo-200"
                  >
                    {p.provider_name}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500">Checking local streaming licenses...</span>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
