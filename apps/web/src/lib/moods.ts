// Mood ids match services/intelligence-core/app/moods.py. Palette and copy live here
// so the room can re-light instantly without waiting on the network.
export type MoodId = "comforting" | "emotional" | "reflective" | "mystery" | "exciting" | "romance" | "strange";

export interface MoodTheme {
  id: MoodId;
  label: string;
  /** Short line shown as the room's headline when this mood is lit */
  line: string;
  /** What the user is asking for, in their words */
  ask: string;
  rgb: [number, number, number];
  hex: string;
  defaultRuntime: number;
  defaultNovelty: number;
}

export const MOODS: MoodTheme[] = [
  { id: "comforting", label: "Comforting", line: "Warm and easy tonight.", ask: "something gentle that feels like a blanket", rgb: [242, 163, 58], hex: "#F2A33A", defaultRuntime: 110, defaultNovelty: 0.3 },
  { id: "emotional", label: "Emotional", line: "Something that leaves a mark.", ask: "a story that moves me", rgb: [214, 69, 93], hex: "#D6455D", defaultRuntime: 140, defaultNovelty: 0.45 },
  { id: "reflective", label: "Reflective", line: "Big ideas to sit with.", ask: "something to think about afterwards", rgb: [94, 155, 234], hex: "#5E9BEA", defaultRuntime: 150, defaultNovelty: 0.55 },
  { id: "mystery", label: "Mystery", line: "Clues, twists, one good reveal.", ask: "a puzzle I can't solve too early", rgb: [47, 181, 176], hex: "#2FB5B0", defaultRuntime: 130, defaultNovelty: 0.5 },
  { id: "exciting", label: "Exciting", line: "Pulse up, phone down.", ask: "adrenaline and momentum", rgb: [240, 100, 47], hex: "#F0642F", defaultRuntime: 130, defaultNovelty: 0.4 },
  { id: "romance", label: "Romantic", line: "Butterflies and slow glances.", ask: "big feelings and a love story", rgb: [232, 121, 168], hex: "#E879A8", defaultRuntime: 120, defaultNovelty: 0.35 },
  { id: "strange", label: "Strange", line: "Take me somewhere odd.", ask: "a surprise I wouldn't pick myself", rgb: [155, 107, 242], hex: "#9B6BF2", defaultRuntime: 140, defaultNovelty: 0.85 },
];

export const MOOD_BY_ID: Record<string, MoodTheme> = Object.fromEntries(MOODS.map((m) => [m.id, m]));

/** House lights when no mood has been chosen: tungsten brass. */
export const HOUSE = { rgb: [201, 162, 75] as [number, number, number], hex: "#C9A24B" };

const mix = (a: number[], b: number[], t: number) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const trip = (c: number[]) => c.join(" ");

/** Applies a mood (or the house lights) to the document: Tailwind triplets + the animatable pool colour. */
export function applyMoodToDocument(mood: MoodId | null) {
  const root = document.documentElement;
  const base = mood ? MOOD_BY_ID[mood].rgb : HOUSE.rgb;
  const hex = mood ? MOOD_BY_ID[mood].hex : HOUSE.hex;
  const white = [255, 255, 255];
  const black = [0, 0, 0];
  root.style.setProperty("--g200", trip(mix(base, white, 0.6)));
  root.style.setProperty("--g300", trip(mix(base, white, 0.35)));
  root.style.setProperty("--g400", trip(mix(base, white, 0.12)));
  root.style.setProperty("--g500", trip(base));
  root.style.setProperty("--g600", trip(mix(base, black, 0.25)));
  root.style.setProperty("--g700", trip(mix(base, black, 0.5)));
  root.style.setProperty("--gel-hex", hex);
  root.dataset.mood = mood ?? "house";
}

export function greeting(date = new Date()): string {
  const h = date.getHours();
  if (h < 5) return "Late night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 21) return "Good evening";
  return "Good night";
}
