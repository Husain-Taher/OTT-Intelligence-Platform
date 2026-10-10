"use client";

import { useEffect, useRef, useState } from "react";
import { Clapperboard, Compass, Orbit, Search, Ticket } from "lucide-react";
import MoodDimmer from "./MoodDimmer";
import { useMood } from "@/context/MoodContext";
import { useMe } from "@/context/MeContext";

export const TABS = [
  { id: "discover", label: "Lobby", icon: Compass },
  { id: "studio", label: "Mood Studio", icon: Clapperboard },
  { id: "taste-universe", label: "Taste Universe", icon: Orbit },
  { id: "search", label: "Search", icon: Search },
  { id: "profile", label: "My Ticket", icon: Ticket },
] as const;

export default function Navigation({ activeTab, onTabChange }: { activeTab: string; onTabChange: (tab: string) => void }) {
  const { mood, setMood, theme } = useMood();
  const { me } = useMe();
  const [open, setOpen] = useState(false);
  const pop = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => pop.current && !pop.current.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-brass/20 bg-pit/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <button onClick={() => onTabChange("discover")} className="flex items-center gap-3 text-left">
            <span aria-hidden className="bulb animate-flicker" />
            <span className="font-display text-xl font-semibold tracking-tight text-ivory">OTT Intelligence</span>
          </button>

          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            {TABS.map(({ id, label, icon: Icon }) => {
              const on = activeTab === id;
              return (
                <button
                  key={id}
                  onClick={() => onTabChange(id)}
                  aria-current={on ? "page" : undefined}
                  className={`relative flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${on ? "bg-ivory/10 text-ivory" : "text-ivory/60 hover:text-ivory"}`}
                >
                  <Icon className={`h-4 w-4 ${on ? "text-gel-300" : ""}`} />
                  {label}
                </button>
              );
            })}
          </nav>

          <div className="relative flex items-center gap-3" ref={pop}>
            <button
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-haspopup="dialog"
              className="flex items-center gap-2 rounded-full border border-ivory/15 py-1.5 pl-2.5 pr-3.5 text-sm text-ivory transition hover:border-gel-400"
            >
              <span aria-hidden className="h-3 w-3 rounded-full" style={{ background: theme?.hex ?? "#C9A24B", boxShadow: `0 0 10px ${theme?.hex ?? "#C9A24B"}` }} />
              <span>{theme ? theme.label : "Set the mood"}</span>
            </button>
            {me?.picture ? (
              <button onClick={() => onTabChange("profile")} aria-label="Open your profile">
                <img src={me.picture} alt="" referrerPolicy="no-referrer" className="h-9 w-9 rounded-full border border-brass/50 object-cover" />
              </button>
            ) : null}

            {open && (
              <div role="dialog" aria-label="Change the mood" className="absolute right-0 top-12 z-50 w-[min(92vw,640px)] rounded-2xl border border-brass/30 bg-surface p-5 shadow-2xl">
                <p className="mb-3 text-center font-display text-lg italic text-ivory/80">How does it feel now?</p>
                <MoodDimmer variant="row" value={mood} onChange={(m) => { setMood(m); setOpen(false); }} />
                {mood && (
                  <button onClick={() => { setMood(null); setOpen(false); }} className="mx-auto mt-3 block text-sm text-ivory/50 underline-offset-4 hover:text-ivory hover:underline">
                    Back to house lights
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Mobile tab bar */}
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-brass/20 bg-pit/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl md:hidden">
        {TABS.map(({ id, label, icon: Icon }) => {
          const on = activeTab === id;
          return (
            <button key={id} onClick={() => onTabChange(id)} aria-current={on ? "page" : undefined} className={`flex flex-col items-center gap-1 py-2.5 text-[11px] ${on ? "text-gel-300" : "text-ivory/55"}`}>
              <Icon className="h-5 w-5" />
              {label.replace("Mood ", "").replace("Taste ", "")}
            </button>
          );
        })}
      </nav>
    </>
  );
}
