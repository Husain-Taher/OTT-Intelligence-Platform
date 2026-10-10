"use client";

import { useState, useEffect } from "react";
import { fetchTasteUniverse, fetchTasteProfile, tuneClusterWeight, resetTasteProfile } from "@/lib/api";
import { CanonicalContent } from "@/types";
import { Orbit, Activity, Sparkles, Sliders, RefreshCw, Compass, ArrowUpRight, Play, Film, ShieldAlert } from "lucide-react";

interface TasteUniverseViewProps {
  onSelectTitle?: (content: CanonicalContent, matchPct?: number) => void;
}

export default function TasteUniverseView({ onSelectTitle }: TasteUniverseViewProps) {
  const [universe, setUniverse] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);
  const [tuning, setTuning] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [sliderVal, setSliderVal] = useState<number>(0.8);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const uData = await fetchTasteUniverse();
    const pData = await fetchTasteProfile();
    setUniverse(uData);
    setProfile(pData);
    if (uData?.clusters?.length) {
      const initial = uData.clusters[0];
      setSelectedCluster(initial);
      setSliderVal(initial.weight);
    }
  };

  const handleSelectCluster = (c: any) => {
    setSelectedCluster(c);
    setSliderVal(c.weight);
  };

  const handleTune = async (newVal: number) => {
    if (!selectedCluster) return;
    setSliderVal(newVal);
    setTuning(true);
    await tuneClusterWeight(selectedCluster.id, newVal);
    // Reload universe to reflect new coordinates & weights
    const uData = await fetchTasteUniverse();
    setUniverse(uData);
    const updated = uData?.clusters?.find((c: any) => c.id === selectedCluster.id);
    if (updated) setSelectedCluster(updated);
    setTuning(false);
  };

  const handleResetTaste = async () => {
    if (!confirm("Are you sure you want to reset your taste vector to neutral? This will clear calibrated weights.")) return;
    setResetting(true);
    await resetTasteProfile();
    await loadData();
    setResetting(false);
  };

  if (!universe || !profile) {
    return (
      <div className="flex h-64 items-center justify-center font-display text-lg italic text-ivory/50">
        <Activity className="h-6 w-6 animate-spin text-gel-400 mr-3" />
        <span>Synthesizing your taste universe…</span>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="rounded-2xl border border-brass/25 bg-surface p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Orbit className="h-4 w-4 text-gel-400" />
            <span className="text-xs font-semibold tracking-widest text-gel-300 uppercase">
              Multidimensional Topological Map & Frontier Discovery
            </span>
          </div>
          <h1 className="font-display text-3xl font-bold text-ivory">Taste Universe</h1>
          <p className="mt-2 text-sm text-ivory/65 max-w-2xl leading-relaxed">
            Your taste is not a genre filter—it is an evolving universe of narrative density, emotional resonance, and pacing. Explore your active orbits or adjust your taste gravity below.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleResetTaste}
            disabled={resetting}
            className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 px-4 py-2.5 text-xs font-medium text-rose-300 transition shadow-sm"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${resetting ? "animate-spin" : ""}`} />
            <span>Reset Gravity</span>
          </button>
        </div>
      </div>

      {/* Cluster Map & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Interactive SVG Radar Cluster Canvas */}
        <div className="lg:col-span-2 relative aspect-[4/3] rounded-2xl border border-brass/20 bg-surface-elevated overflow-hidden flex items-center justify-center p-6 shadow-xl">
          <div className="absolute inset-0 bg-[radial-gradient(#2A2320_1px,transparent_1px)] [background-size:24px_24px] opacity-40 pointer-events-none" />

          <svg className="h-full w-full max-h-[460px]" viewBox="-200 -200 400 400">
            {/* Ambient concentric rings */}
            <circle cx="0" cy="0" r="160" fill="none" stroke="rgba(243, 235, 221, 0.05)" strokeDasharray="4 4" />
            <circle cx="0" cy="0" r="110" fill="none" stroke="rgba(243, 235, 221, 0.08)" />
            <circle cx="0" cy="0" r="60" fill="none" stroke="rgba(243, 235, 221, 0.12)" />

            {/* Connecting constellations */}
            {universe.clusters.map((c: any, i: number) => {
              const next = universe.clusters[(i + 1) % universe.clusters.length];
              return (
                <line
                  key={`line_${i}`}
                  x1={c.x}
                  y1={c.y}
                  x2={next.x}
                  y2={next.y}
                  stroke="rgba(201, 162, 75, 0.3)"
                  strokeWidth="1.5"
                />
              );
            })}

            {/* Cluster Nodes */}
            {universe.clusters.map((c: any) => {
              const isSelected = selectedCluster?.id === c.id;
              const radius = 14 + (c.weight * 16);
              return (
                <g
                  key={c.id}
                  onClick={() => handleSelectCluster(c)}
                  className="cursor-pointer transition-transform duration-300 hover:scale-110"
                >
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r={radius + 8}
                    fill={c.color || "var(--gel-hex)"}
                    opacity={isSelected ? "0.35" : "0.12"}
                    className="animate-pulse"
                  />
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r={radius}
                    fill={c.color || "var(--gel-hex)"}
                    stroke={isSelected ? "#F3EBDD" : "#C9A24B"}
                    strokeWidth={isSelected ? "2.5" : "1"}
                    opacity="0.9"
                  />
                  <text
                    x={c.x}
                    y={c.y + radius + 15}
                    textAnchor="middle"
                    fill="#F3EBDD"
                    fontSize="11"
                    fontFamily="Instrument Sans, sans-serif"
                    fontWeight="600"
                    className="select-none"
                  >
                    {c.name}
                  </text>
                  <text
                    x={c.x}
                    y={c.y + 4}
                    textAnchor="middle"
                    fill="#ffffff"
                    fontSize="10"
                    fontWeight="bold"
                  >
                    {Math.round(c.weight * 100)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Selected Cluster Details & Recalibration */}
        <div className="rounded-2xl border border-brass/25 bg-surface p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold tracking-widest text-gel-300 uppercase">
                Active Cluster Node
              </span>
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-gel-400/10 text-gel-300 border border-gel-400/20">
                {selectedCluster ? `${Math.round(selectedCluster.weight * 100)}% Gravity` : "0%"}
              </span>
            </div>
            
            <h3 className="font-display text-2xl font-bold text-ivory mt-2">
              {selectedCluster ? selectedCluster.name : "Select a Cluster"}
            </h3>
            <p className="text-xs text-ivory/60 mt-1.5 leading-relaxed">
              {selectedCluster?.tagline || "Click any node on the orbital map to inspect its gravitational pull and orbiting titles."}
            </p>

            {/* Interactive Gravity Tuner */}
            {selectedCluster && (
              <div className="mt-6 rounded-xl border border-brass/20 bg-surface-elevated p-4">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-semibold text-brass-light flex items-center gap-1.5">
                    <Sliders className="h-3.5 w-3.5 text-gel-400" />
                    Adjust Node Gravity
                  </span>
                  <span className="font-bold text-ivory">{Math.round(sliderVal * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={sliderVal}
                  onChange={(e) => handleTune(parseFloat(e.target.value))}
                  className="w-full accent-gel-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-ivory/40 mt-1.5">
                  <span>Downweight (0%)</span>
                  <span>Dominant (100%)</span>
                </div>
              </div>
            )}

            {/* Dimension Breakdown */}
            <div className="mt-6 space-y-3 text-xs">
              <h4 className="text-xs font-semibold text-brass-light uppercase tracking-wider">
                Resonant Dimensions
              </h4>
              <div>
                <div className="flex justify-between text-ivory/70 mb-1">
                  <span>Slow-burn Pacing Fit</span>
                  <span className="font-bold text-gel-300">
                    {Math.round((profile?.pacing?.slow_build || 0.75) * 100)}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-surface-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gel-400 rounded-full transition-all duration-500"
                    style={{ width: `${(profile?.pacing?.slow_build || 0.75) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-ivory/70 mb-1">
                  <span>Narrative Investigation & Mystery</span>
                  <span className="font-bold text-gel-300">
                    {Math.round((profile?.narrative?.mystery || 0.85) * 100)}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-surface-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gel-400 rounded-full transition-all duration-500"
                    style={{ width: `${(profile?.narrative?.mystery || 0.85) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-brass/20 text-[11px] text-ivory/50 flex items-center justify-between">
            <span>Calibrated Interaction Events:</span>
            <span className="font-bold text-ivory/80">{universe.interaction_count}</span>
          </div>
        </div>

      </div>

      {/* Orbiting Titles for Selected Cluster */}
      {selectedCluster && selectedCluster.orbit_titles?.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Film className="h-4 w-4 text-gel-400" />
              <h3 className="font-display text-xl font-bold text-ivory">
                Titles Orbiting {selectedCluster.name}
              </h3>
            </div>
            <span className="text-xs text-ivory/50">
              Sorted by highest personal match density
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {selectedCluster.orbit_titles.map((orbit: any) => {
              const item = orbit.content;
              return (
                <div
                  key={item.content_id}
                  onClick={() => onSelectTitle && onSelectTitle(item, orbit.personal_match_percentage)}
                  className="group relative cursor-pointer overflow-hidden rounded-xl border border-brass/20 bg-surface transition-all duration-300 hover:-translate-y-1 hover:border-gel-400/50 hover:shadow-xl"
                >
                  <div className="aspect-[2/3] w-full overflow-hidden bg-surface-subtle">
                    {item.poster_path ? (
                      <img
                        src={item.poster_path}
                        alt={item.title}
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-xs text-ivory/40">No Poster</div>
                    )}
                    <div className="absolute top-2 right-2 rounded-md bg-pit/80 backdrop-blur-md px-1.5 py-0.5 text-[10px] font-bold text-gel-300 border border-brass/20">
                      {orbit.personal_match_percentage}%
                    </div>
                  </div>
                  <div className="p-3">
                    <h4 className="font-display text-xs font-semibold text-ivory truncate">{item.title}</h4>
                    <p className="text-[11px] text-ivory/50 mt-0.5 truncate">
                      {item.release_year} • {item.genres?.[0]}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* The Frontier: Expand Your Horizon */}
      {universe.frontier_titles?.length > 0 && (
        <div className="rounded-2xl border border-gel-400/30 bg-surface-elevated p-6 sm:p-8 space-y-6 shadow-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Compass className="h-4 w-4 text-gel-400" />
                <span className="text-xs font-semibold tracking-widest text-gel-300 uppercase">
                  The Frontier • Break Your Echo Chamber
                </span>
              </div>
              <h3 className="font-display text-2xl font-bold text-ivory">
                Picks Outside Your Usual Clusters
              </h3>
              <p className="text-xs text-ivory/65 max-w-2xl mt-1">
                Critically acclaimed masterpieces (8.0+ rating) from foreign genres and uncharted styles that challenge your current taste envelope.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {universe.frontier_titles.map((f: any) => {
              const item = f.content;
              return (
                <div
                  key={item.content_id}
                  onClick={() => onSelectTitle && onSelectTitle(item, f.personal_match_percentage)}
                  className="group relative cursor-pointer overflow-hidden rounded-xl border border-brass/20 bg-surface p-3 transition-all duration-300 hover:border-gel-400 hover:shadow-xl"
                >
                  <div className="aspect-video w-full overflow-hidden rounded-lg bg-surface-subtle mb-3 relative">
                    <img
                      src={item.backdrop_path || item.poster_path}
                      alt={item.title}
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute top-2 left-2 rounded bg-pit/80 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                      {item.vote_average.toFixed(1)} ★
                    </div>
                  </div>
                  <h4 className="font-display text-sm font-semibold text-ivory truncate">{item.title}</h4>
                  <p className="text-[11px] text-gel-300 font-medium mt-1 leading-snug line-clamp-2">
                    {f.discovery_reason}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
