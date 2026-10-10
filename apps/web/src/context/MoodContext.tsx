"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { MOOD_BY_ID, MoodId, MoodTheme, applyMoodToDocument } from "@/lib/moods";
import { setActiveMood } from "@/lib/api";

interface MoodContextValue {
  mood: MoodId | null;
  theme: MoodTheme | null;
  setMood: (mood: MoodId | null) => void;
}

const MoodContext = createContext<MoodContextValue>({ mood: null, theme: null, setMood: () => {} });
const KEY = "ott.mood";

/** The mood is the room's lighting: changing it re-tints the whole app and tags every event the user generates. */
export function MoodProvider({ children }: { children: React.ReactNode }) {
  const [mood, setMoodState] = useState<MoodId | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved && MOOD_BY_ID[saved]) setMoodState(saved as MoodId);
    } catch {}
  }, []);

  useEffect(() => {
    applyMoodToDocument(mood);
    setActiveMood(mood);
    try {
      if (mood) localStorage.setItem(KEY, mood);
      else localStorage.removeItem(KEY);
    } catch {}
  }, [mood]);

  const setMood = useCallback((m: MoodId | null) => setMoodState(m), []);
  const value = useMemo(() => ({ mood, theme: mood ? MOOD_BY_ID[mood] : null, setMood }), [mood, setMood]);
  return <MoodContext.Provider value={value}>{children}</MoodContext.Provider>;
}

export const useMood = () => useContext(MoodContext);
