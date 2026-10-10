"use client";

import { useState, useEffect } from "react";
import { fetchTasteUniverse, fetchTasteProfile } from "@/lib/api";
import { Orbit, Activity, Compass, Sparkles } from "lucide-react";

export default function TasteUniverseView() {
  const [universe, setUniverse] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const uData = await fetchTasteUniverse();
    const pData = await fetchTasteProfile();
    setUniverse(uData);
    setProfile(pData);
    if (uData?.clusters?.length) {
      setSelectedCluster(uData.clusters[0]);
    }
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
    <div className="space-y-8">
      {/* Header */}
      <div className="rounded-2xl border border-brass/25 bg-surface p-6 sm:p-8">
        <div className="flex items-center gap-2 mb-2">
          <Orbit className="h-4 w-4 text-gel-400" />
          <span className="text-xs font-semibold tracking-widest text-gel-300 uppercase">
            Private Multidimensional Taste Map
          </span>
        </div>
        <h1 className="font-display text-3xl font-bold text-ivory">Taste Universe</h1>
        <p className="mt-2 text-sm text-ivory/65 max-w-2xl leading-relaxed">
          Your entertainment taste is not a genre tag—it is a live cluster topology across pacing, thematic resonance, emotional payoff, and cultural origins.
        </p>
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
                  onClick={() => setSelectedCluster(c)}
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

        {/* Selected Cluster Details */}
        <div className="rounded-2xl border border-brass/25 bg-surface p-6 flex flex-col justify-between shadow-lg">
          <div>
            <span className="text-[10px] font-bold tracking-widest text-gel-300 uppercase">
              Active Cluster Node
            </span>
            <h3 className="font-display text-2xl font-bold text-ivory mt-1">
              {selectedCluster ? selectedCluster.name : "Select a Cluster"}
            </h3>
            <p className="text-xs text-ivory/60 mt-2 leading-relaxed">
              This node reflects continuous implicit and explicit feedback. Higher density indicates stronger narrative resonance.
            </p>

            {/* Dimensional vector breakdown */}
            <div className="mt-6 space-y-4">
              <h4 className="text-xs font-semibold text-brass-light uppercase tracking-wider">
                Live Dimension Weights
              </h4>
              
              <div className="space-y-3 text-xs">
                <div>
                  <div className="flex justify-between text-ivory/70 mb-1">
                    <span>Cluster Affinity Weight</span>
                    <span className="font-bold text-gel-300">
                      {selectedCluster ? Math.round(selectedCluster.weight * 100) : 0}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-surface-subtle rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gel-400 rounded-full transition-all duration-500"
                      style={{ width: `${selectedCluster ? selectedCluster.weight * 100 : 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-ivory/70 mb-1">
                    <span>Pacing Affinity (Slow-burn)</span>
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
                    <span>International Discovery Affinity</span>
                    <span className="font-bold text-gel-300">
                      {Math.round((profile?.international?.KR || 0.82) * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-surface-subtle rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gel-400 rounded-full transition-all duration-500"
                      style={{ width: `${(profile?.international?.KR || 0.82) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-brass/20 text-[11px] text-ivory/50 flex items-center justify-between">
            <span>Calibrated Interaction Count:</span>
            <span className="font-bold text-ivory/80">{profile.interaction_count} events</span>
          </div>
        </div>

      </div>
    </div>
  );
}
