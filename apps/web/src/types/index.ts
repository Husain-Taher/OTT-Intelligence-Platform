export interface StreamingProvider {
  provider_id: number;
  provider_name: string;
  logo_path: string | null;
  type: string;
}

export interface ReviewQuote {
  id: string;
  text: string;
  aspect: string;
  sentiment: string;
  tag: string;
  source: string;
  author: string;
  confidence: number;
}

export interface AspectBreakdown {
  atmosphere: number;
  characters: number;
  story: number;
  acting: number;
  music: number;
  pacing_rating: number;
  ending_satisfaction: number;
}

export interface ContentProfile {
  narrative_complexity: number;
  mystery: number;
  philosophical_depth: number;
  character_driven: number;
  plot_driven: number;
  pacing: {
    slow_build: number;
    medium: number;
    fast: number;
  };
  emotions: Record<string, number>;
  audience_reaction: Record<string, number>;
  aspect_breakdown: AspectBreakdown;
  highlighted_quotes: ReviewQuote[];
  audience_voice_summary: string;
}

export interface CanonicalContent {
  content_id: string;
  tmdb_id: number;
  title: string;
  original_title?: string;
  content_type: string;
  release_date?: string;
  release_year?: number;
  runtime?: number;
  genres: string[];
  keywords: string[];
  overview: string;
  tagline?: string;
  original_language: string;
  origin_countries: string[];
  directors: string[];
  writers: string[];
  cast: string[];
  vote_average: number;
  vote_count: number;
  poster_path?: string;
  backdrop_path?: string;
  trailer_key?: string | null;
  providers: StreamingProvider[];
  profile?: ContentProfile;
}

export interface RecommendationItem {
  content: CanonicalContent;
  score: number;
  personal_match_percentage: number;
  match_breakdown: Record<string, number>;
  reasons: string[];
  differences_from_usual: string[];
  contrasting_note?: string;
}

export interface UserTasteVector {
  user_id: string;
  genres: Record<string, number>;
  narrative: Record<string, number>;
  emotions: Record<string, number>;
  pacing: Record<string, number>;
  international: Record<string, number>;
  preferred_directors: Record<string, number>;
  abandoned_patterns: Record<string, number>;
  interaction_count: number;
}

export interface FindMyWatchResponse {
  hero: RecommendationItem;
  window_metrics: {
    emotional_depth: number;
    mystery_level: number;
    narrative_complexity: number;
    visual_atmosphere: number;
    novelty_quotient: number;
  };
  runtime_formatted: string;
  runners_up: RecommendationItem[];
}

// ---- Mood, profile and identity -------------------------------------------------

export interface MoodCatalogEntry {
  id: string;
  label: string;
  tagline: string;
  energy: string;
  genres: string[];
}

export interface MoodMapEntry {
  mood: string;
  checkins: number;
  reactions: number;
  top_genres: string[];
  learned: boolean;
}

export interface MoodCheckin {
  mood: string;
  genres: string[];
  energy: string | null;
  max_runtime: number | null;
  novelty: number | null;
  created_at: string;
}

export interface MeResponse {
  user_id: string;
  display_name: string;
  email: string | null;
  picture: string | null;
  archetype: string | null;
  onboarded: boolean;
  member_since: string | null;
  stats: { titles_completed: number; hours_watched: number; likes: number; saved: number; reactions: number };
  calibration: number;
  top_genres: { name: string; weight: number }[];
  top_directors: string[];
  mood_map: MoodMapEntry[];
  recent_checkins: MoodCheckin[];
}

export interface DiscoveryDeck {
  mood: string | null;
  hero: RecommendationItem;
  tonight_picks: RecommendationItem[];
  unexpected_discoveries: RecommendationItem[];
  comfort_rail: RecommendationItem[];
  adrenaline_rail: RecommendationItem[];
  indian_cinema_rail: RecommendationItem[];
  around_the_world: Record<string, CanonicalContent[]>;
  total_catalog_size: number;
}
