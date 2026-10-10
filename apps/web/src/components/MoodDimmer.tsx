"use client";

import { MOODS, MoodId } from "@/lib/moods";

interface MoodDimmerProps {
  value: MoodId | null;
  onChange: (mood: MoodId) => void;
  /** "arc" hangs the lights on a curved rig (desktop hero); "row" is a compact strip */
  variant?: "arc" | "row";
}

/**
 * Seven stage lights, each with a colour gel. Switching one on re-lights the whole room.
 * Behaves as a radio group: arrow keys move between lights, Enter/Space selects.
 */
export default function MoodDimmer({ value, onChange, variant = "arc" }: MoodDimmerProps) {
  const arc = variant === "arc";

  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      onChange(MOODS[(i + 1) % MOODS.length].id);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      onChange(MOODS[(i - 1 + MOODS.length) % MOODS.length].id);
    }
  };

  return (
    <div className="relative">
      {arc && <div aria-hidden className="pointer-events-none absolute inset-x-6 top-0 hidden h-px bg-gradient-to-r from-transparent via-brass/50 to-transparent md:block" />}
      <div
        role="radiogroup"
        aria-label="How are you feeling tonight?"
        className={`scroll-snap-row flex gap-3 overflow-x-auto px-2 pb-2 pt-1 md:justify-center md:gap-5 md:overflow-visible ${arc ? "md:pb-[72px] md:pt-0" : ""}`}
      >
        {MOODS.map((m, i) => {
          const on = value === m.id;
          const dim = value !== null && !on;
          const drop = arc ? Math.pow(i - 3, 2) * 7 : 0; // curve the rig
          return (
            <button
              key={m.id}
              role="radio"
              aria-checked={on}
              tabIndex={on || (value === null && i === 0) ? 0 : -1}
              onKeyDown={(e) => onKey(e, i)}
              onClick={() => onChange(m.id)}
              style={{ transform: `translateY(${drop}px)` }}
              className="group relative flex shrink-0 flex-col items-center text-center transition-transform duration-500 focus-visible:outline-offset-8"
            >
              {/* hanger */}
              <span aria-hidden className="mb-1 hidden h-5 w-px bg-gradient-to-b from-transparent to-brass/60 md:block" />
              {/* lens */}
              <span
                aria-hidden
                className="relative flex h-16 w-16 items-center justify-center rounded-full border border-brass/40 bg-pit transition-all duration-500 sm:h-[72px] sm:w-[72px]"
                style={{
                  boxShadow: on ? `0 0 0 3px ${m.hex}55, 0 0 46px 6px ${m.hex}88` : "inset 0 0 14px rgba(0,0,0,.8)",
                }}
              >
                <span
                  className="h-[78%] w-[78%] rounded-full transition-all duration-500 group-hover:scale-105"
                  style={{
                    background: `radial-gradient(circle at 35% 30%, ${m.hex}ff, ${m.hex}aa 45%, ${m.hex}44 100%)`,
                    opacity: on ? 1 : dim ? 0.32 : 0.62,
                    filter: on ? "saturate(1.15)" : "saturate(.8)",
                  }}
                />
              </span>
              <span
                className={`mt-2.5 font-display text-[15px] italic leading-none transition-colors duration-300 ${
                  on ? "text-ivory" : "text-ivory/55 group-hover:text-ivory/85"
                }`}
              >
                {m.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
