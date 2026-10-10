# OTT Intelligence Platform

> **Global Entertainment Discovery, Personalization & Content Intelligence System**

---

## 1. System Overview

The **OTT Intelligence Platform** transforms entertainment discovery from generic popularity carousels into **Preference Intelligence**. Rather than answering *"What movies are similar to this movie?"*, it answers:

> *"Given everything this person has watched, skipped, searched for, enjoyed, disliked, reviewed, and abandoned, what are the experiences they are most likely to want right now?"*

---

## 2. Quickstart

Sign-in uses Auth0. See [`docs/UPGRADE_NOTES.md`](docs/UPGRADE_NOTES.md) for setup, the mood system, and what changed.

- Web app: http://localhost:3000 (`apps/web`, `npm run dev`)
- API docs: http://localhost:8000/docs (`services/intelligence-core`, `uvicorn app.main:app --port 8000`)

---

## 3. Architecture & Implemented Capabilities

### A. Live TMDB Content Ingestion
- Real-time adapter querying TMDB with API key integration.
- Deep metadata enrichment: genres, keywords, directors, writers, primary cast, release dates, runtimes, and flatrate streaming providers (Netflix, Amazon Prime Video, Disney+, Apple TV+, etc.).
- Pre-seeded flagship international catalog spanning US, South Korea, Japan, France, Germany, and India.

### B. Aspect-Based Review & 20-D Emotion Intelligence
- **20-Dimensional Emotion Spectrum**: `AWE`, `WONDER`, `JOY`, `COMFORT`, `NOSTALGIA`, `TENSION`, `SUSPENSE`, `FEAR`, `ANXIETY`, `SADNESS`, `GRIEF`, `HOPE`, `INSPIRATION`, `ROMANCE`, `CURIOSITY`, `CONFUSION`, `FRUSTRATION`, `SATISFACTION`, `REFLECTION`, `MOTIVATION`.
- **Narrative Profiling**: `complexity`, `mystery`, `philosophical_depth`, `character_driven`, `plot_driven`.
- **Pacing Index**: `slow_build`, `medium`, `fast`.
- **Review Signals & Quote Provenance**: Extracting verified review quotes tagged with `EMOTIONAL IMPACT`, `PACING OBSERVATION`, `CHARACTER RELATIONSHIP`, and `VISUAL ATMOSPHERE`.

### C. Dynamic User Taste Vector & Preference Engine
- Maintains a continuously evolving vector reflecting:
  - Genre affinities
  - Narrative complexity preferences
  - Emotional payoff resonance
  - Pacing tolerance (e.g. slow-burn build vs kinetic action)
  - Cross-cultural / international affinity
- **Behavioral Signal Weighting**:
  - `WATCH_COMPLETE`: +1.0
  - `REWATCH`: +1.4
  - `LIKE`: +0.9
  - `SAVE`: +0.7
  - `ABANDON`: -0.7 (updates `abandoned_patterns` such as slow openings)
  - `DISLIKE`: -1.3

### D. Multi-Stage Recommendation & Diverse Ranking
- **Candidate Generation**: Semantic Intent Match, Content-based Taste Matching, Knowledge Graph Connections, and Cross-Cultural Exploration.
- **Learned Ranking**: Combines personal match, intent alignment, quality signals, and exploration index.
- **Diversity Penalty**: Prevents over-concentration of same genre or country in top recommendations.

### E. Signature Experiences
1. **"FIND MY WATCH" Cockpit (Section 80)**:
   - Natural language input: *"I have 2 hours. I want something emotional but not depressing. A mystery with great visuals, preferably not American..."*
   - Interactive sliders for runtime constraints, dominant moods, and novelty exploration.
   - **YOUR PERFECT WINDOW** readout with visual attribute meters (`Emotional Depth`, `Mystery Level`, `Narrative Complexity`, `Visual Atmosphere`, `Novelty Quotient`) and transparent contrastive reasoning (*"Why this one?"*).
2. **"Why Should I Watch This?" Inspector Modal (Section 26-28)**:
   - Full backdrop overlay, personal match %, side-by-side taste mapping (*Your Taste* $\rightarrow$ *Content*), audience reaction spectrum, what viewers loved vs divided, verified review excerpts, and streaming availability.
   - Interactive feedback buttons (`Watch Now`, `Save`, `Not For Me`, `Abandoned`) that calibrate the live taste profile.
3. **Taste Universe (Section 33)**:
   - Interactive SVG constellation radar mapping cluster nodes (`Sci-Fi & Cosmos`, `Deep Mystery`, `Atmospheric Slow Burn`, `Korean Thrillers`, `Character Complexity`, `Awe & Wonder`).
4. **Natural Intent Search (Section 34)**:
   - Free-form search with automatic extraction of runtime constraints, negative filters, mood, and regions.
