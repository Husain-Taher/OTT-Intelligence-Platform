"use client";

import { useState, useEffect } from "react";
import { fetchTasteUniverse, fetchTasteProfile } from "@/lib/api";
import { Orbit, Compass, Sparkles, Activity } from "lucide-react";

export default function TasteUniverseView() {
  const [universe, setUniverse] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const uData = await fetchTasteUniverse("default_user");
    const pData = await fetchTasteProfile("default_user");
    setUniverse(uData);
    setProfile(pData);
    if (uData?.clusters?.length) {
      setSelectedCluster(uData.clusters[0]);
    }
  };

  if (!universe || !profile) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <Activity className="h-6 w-6 animate-spin text-indigo-400 mr-2" />
        <span>Synthesizing Taste Universe...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="rounded-2xl border border-white/[0.08] bg-surface p-6 sm:p-8">
        <div className="flex items-center gap-2 mb-2">
          <Orbit className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-bold tracking-widest text-indigo-400 uppercase">
            Private Multidimensional Taste Map
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-white">Taste Universe</h1>
        <p className="mt-1 text-sm text-slate-400 max-w-2xl leading-relaxed">
          Your entertainment taste is not a genre tag—it is a live cluster topology across pacing, thematic resonance, emotional payoff, and cultural origins.
        </p>
      </div>

      {/* Cluster Map & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Interactive SVG Radar Cluster Canvas */}
        <div className="lg:col-span-2 relative aspect-[4/3] rounded-2xl border border-white/[0.08] bg-[#07080C] overflow-hidden flex items-center justify-center p-6">
          <div className="absolute inset-0 bg-[radial-gradient(#1f2438_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />

          <svg className="h-full w-full max-h-[460px]" viewBox="-200 -200 400 400">
            {/* Ambient concentric rings */}
            <circle cx="0" cy="0" r="160" fill="none" stroke="rgba(255,255,255,0.04)" strokeDasharray="4 4" />
            <circle cx="0" cy="0" r="110" fill="none" stroke="rgba(255,255,255,0.06)" />
            <circle cx="0" cy="0" r="60" fill="none" stroke="rgba(255,255,255,0.08)" />

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
                  stroke="rgba(99, 102, 241, 0.2)"
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
                    fill={c.color}
                    opacity={isSelected ? "0.3" : "0.1"}
                    className="animate-pulse"
                  />
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r={radius}
                    fill={c.color}
                    stroke="#ffffff"
                    strokeWidth={isSelected ? "2.5" : "0.5"}
                    opacity="0.9"
                  />
                  <text
                    x={c.x}
                    y={c.y + radius + 14}
                    textAnchor="middle"
                    fill="#F1F5F9"
                    fontSize="11"
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
        <div className="rounded-2xl border border-white/[0.08] bg-surface p-6 flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold tracking-widest text-indigo-400 uppercase">
              Active Cluster Node
            </span>
            <h3 className="text-xl font-bold text-white mt-1">
              {selectedCluster ? selectedCluster.name : "Select a Cluster"}
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              This node reflects continuous implicit and explicit feedback. Higher density indicates stronger narrative resonance.
            </p>

            {/* Dimensional vector breakdown */}
            <div className="mt-6 space-y-3">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Live Dimension Weights
              </h4>
              
              <div className="space-y-2 text-xs">
                <div>
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span>Cluster Affinity Weight</span>
                    <span className="font-bold text-indigo-400">
                      {selectedCluster ? Math.round(selectedCluster.weight * 100) : 0}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${selectedCluster ? selectedCluster.weight * 100 : 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span>Pacing Affinity (Slow-burn)</span>
                    <span className="font-bold text-indigo-400">
                      {Math.round((profile?.pacing?.slow_build || 0.75) * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${(profile?.pacing?.slow_build || 0.75) * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span>International Discovery Affinity</span>
                    <span className="font-bold text-indigo-400">
                      {Math.round((profile?.international?.KR || 0.82) * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${(profile?.international?.KR || 0.82) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/[0.08] text-[11px] text-slate-500 flex items-center justify-between">
            <span>Calibrated Interaction Count:</span>
            <span className="font-bold text-slate-300">{profile.interaction_count} events</span>
          </div>
        </div>

      </div>
    </div>
  );
}
