import {
  CanonicalContent, DiscoveryDeck, FindMyWatchResponse, MeResponse,
  MoodCatalogEntry, UserTasteVector,
} from "@/types";

/**
 * All calls go through the Next.js server (/api/ott/*), which attaches the signed-in user's
 * Auth0 access token. The browser never holds the token and never says who it is: the API
 * takes the user from the token.
 */
const BASE = "/api/ott";

let activeMood: string | null = null;
/** MoodProvider keeps this in sync so every behavioural event is tagged with the mood it happened in. */
export function setActiveMood(mood: string | null) {
  activeMood = mood;
}

export class AuthRequiredError extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    });
    if (res.status === 401) {
      if (typeof window !== "undefined") window.location.href = "/api/auth/login";
      throw new AuthRequiredError("Session expired");
    }
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof AuthRequiredError) return null;
    console.error(`API ${path} failed:`, err);
    return null;
  }
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

// ---- Discovery -------------------------------------------------------------
export const fetchDiscoveryDeck = (mood?: string | null) =>
  request<DiscoveryDeck>(`/discover${mood ? `?mood=${encodeURIComponent(mood)}` : ""}`);

export const fetchTitleDetails = (contentId: string) => request<CanonicalContent>(`/content/${contentId}`);

export const fetchCatalog = () => request<CanonicalContent[]>(`/content`);

export const fetchMoodCatalog = () => request<{ moods: MoodCatalogEntry[]; genres: string[] }>(`/moods`);

export function executeFindMyWatch(params: {
  prompt?: string;
  mood?: string;
  maxRuntime?: number;
  novelty?: number;
  genres?: string[];
  energy?: string;
  excludeIds?: string[];
}): Promise<FindMyWatchResponse | null> {
  return post<FindMyWatchResponse>("/find-my-watch", {
    prompt: params.prompt || "",
    mood: params.mood || "reflective",
    max_runtime: params.maxRuntime || 130,
    novelty: params.novelty ?? 0.6,
    genres: params.genres?.length ? params.genres : null,
    energy: params.energy || null,
    exclude_ids: params.excludeIds?.length ? params.excludeIds : null,
  });
}

export const executeNaturalSearch = (query: string) =>
  post<any>(`/search?query=${encodeURIComponent(query)}`);

// ---- Profile ---------------------------------------------------------------
export const fetchMe = () => request<MeResponse>(`/me`);
export const finishOnboarding = () => post<{ status: string }>(`/me/onboarded`);
export const chooseArchetype = (archetype: string) => post<any>(`/profile/archetype`, { archetype });

// The optional trailing user-id arguments are kept so older call sites still compile; they are ignored.
export const fetchTasteProfile = (_userId?: string) => request<UserTasteVector>(`/profile/taste`);
export const fetchTasteUniverse = (_userId?: string) => request<any>(`/profile/taste-universe`);

export const fetchWatchlist = () =>
  request<{ count: number; items: CanonicalContent[] }>(`/user/watchlist`);

export const toggleWatchlist = (contentId: string) =>
  post<{ is_saved: boolean }>(`/user/watchlist/toggle`, { content_id: contentId, mood: activeMood });

// ---- Behaviour -------------------------------------------------------------
export async function recordUserEvent(
  contentId: string,
  eventType: string,
  _userId?: string,
  metadata: Record<string, any> = {}
) {
  // "Save" is a watchlist action; the toggle endpoint logs the event and teaches the profile.
  if (eventType === "SAVE") return toggleWatchlist(contentId);
  return post<any>(`/events`, {
    user_id: "",
    content_id: contentId,
    event_type: eventType,
    metadata: { ...(activeMood ? { mood: activeMood } : {}), ...metadata },
  });
}
