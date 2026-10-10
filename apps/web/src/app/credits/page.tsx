import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Credits & Attributions | OTT Intelligence",
  description: "Data attributions and API credits for OTT Intelligence Platform.",
};

export default function CreditsPage() {
  return (
    <div className="min-h-screen bg-pit text-ivory px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl space-y-10">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-ivory/60 hover:text-ivory transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Theatre
        </Link>

        <header className="border-b border-brass/20 pb-6">
          <h1 className="font-display text-4xl font-semibold text-ivory">Credits & Data Attributions</h1>
          <p className="mt-2 text-sm text-ivory/60">
            Transparency, licensing, and third-party data providers that power the OTT Intelligence Platform.
          </p>
        </header>

        {/* TMDB Attribution Section */}
        <section className="rounded-2xl border border-brass/30 bg-surface p-8 space-y-6">
          <div className="flex items-center gap-6">
            <img
              src="https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg"
              alt="The Movie Database (TMDB)"
              className="h-16 w-16 object-contain shrink-0"
            />
            <div>
              <h2 className="font-display text-2xl font-semibold text-ivory">The Movie Database (TMDB)</h2>
              <p className="mt-1 text-xs text-gel-300">Film Metadata, Imagery, Trailers & Cast Intelligence</p>
            </div>
          </div>

          <div className="rounded-xl border border-brass/20 bg-velvet-deep/40 p-4 text-sm leading-relaxed text-ivory/80">
            <p className="font-medium">
              "This product uses the TMDB API but is not endorsed or certified by TMDB."
            </p>
          </div>

          <p className="text-sm text-ivory/70 leading-relaxed">
            All film overviews, original titles, high-resolution posters, backdrop imagery, official trailers,
            cast filmographies, and streaming availability indicators are made possible through the TMDB API under
            non-commercial educational and research fair use terms.
          </p>
        </section>

        {/* IMDb Non-Commercial Datasets */}
        <section className="rounded-2xl border border-brass/30 bg-surface p-8 space-y-4">
          <h2 className="font-display text-2xl font-semibold text-ivory">IMDb Non-Commercial Datasets</h2>
          <p className="text-sm text-ivory/70 leading-relaxed">
            Ratings consensus, masterpiece classifications, and principal filmography indices reference subsets of the
            IMDb Non-Commercial Datasets for scholarly analysis, algorithmic personalization research, and UX evaluation studies.
          </p>
        </section>

        {/* Open-Source Project & Academic Notice */}
        <section className="rounded-2xl border border-brass/20 bg-surface/50 p-6 text-xs text-ivory/50 space-y-2">
          <p>
            OTT Intelligence is an academic, non-commercial prototype created for studying mood-aware recommendation
            algorithms and cinematic UI interaction design.
          </p>
          <p>
            All trademarks, logos, and registered brand names remain the property of their respective owners.
          </p>
        </section>
      </div>
    </div>
  );
}
