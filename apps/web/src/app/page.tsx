"use client";

import { useState } from "react";
import { useUser } from "@auth0/nextjs-auth0/client";
import { MoodProvider, useMood } from "@/context/MoodContext";
import { MeProvider, useMe } from "@/context/MeContext";
import Navigation from "@/components/Navigation";
import DiscoveryHomeView from "@/components/DiscoveryHomeView";
import MoodStudio from "@/components/MoodStudio";
import TasteUniverseView from "@/components/TasteUniverseView";
import NaturalSearchView from "@/components/NaturalSearchView";
import ProfileView from "@/components/ProfileView";
import WhyShouldIWatchModal from "@/components/WhyShouldIWatchModal";
import MarqueeLanding from "@/components/MarqueeLanding";
import Onboarding from "@/components/Onboarding";
import Curtain from "@/components/Curtain";
import { CanonicalContent } from "@/types";

interface Selected {
  content: CanonicalContent;
  matchPct?: number;
}

function Theater() {
  const [tab, setTab] = useState("discover");
  const [selected, setSelected] = useState<Selected | null>(null);
  const { me, loading, refresh } = useMe();
  const { theme } = useMood();

  const select = (content: CanonicalContent, matchPct?: number) => setSelected({ content, matchPct });
  const go = (t: string) => {
    setTab(t);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (!loading && me && !me.onboarded) {
    return <Onboarding onDone={() => go("studio")} />;
  }

  return (
    <>
      <Curtain />
      <Navigation activeTab={tab} onTabChange={go} />
      <main className="relative z-10 mx-auto w-full max-w-7xl flex-1 px-4 pb-32 pt-6 sm:px-6 md:pb-16 md:pt-10 lg:px-8">
        {tab === "discover" && <DiscoveryHomeView onSelectTitle={select} onOpenStudio={() => go("studio")} />}
        {tab === "studio" && <MoodStudio onSelectTitle={select} />}
        {tab === "taste-universe" && <TasteUniverseView />}
        {tab === "search" && <NaturalSearchView onSelectTitle={select} />}
        {tab === "profile" && <ProfileView onSelectTitle={select} onTryMood={() => go("studio")} />}
      </main>
      <WhyShouldIWatchModal
        content={selected?.content ?? null}
        matchPct={selected?.matchPct}
        moodLabel={theme?.label}
        onClose={() => setSelected(null)}
        onEventLogged={refresh}
      />
    </>
  );
}

export default function Home() {
  const { user, isLoading } = useUser();
  const devMode = process.env.NEXT_PUBLIC_AUTH_DISABLED === "true";

  return (
    <MoodProvider>
      <div aria-hidden className="house-light" />
      <div aria-hidden className="film-grain" />
      {isLoading ? (
        <div className="relative z-10 flex min-h-screen items-center justify-center font-display text-xl italic text-ivory/50">Dimming the lights…</div>
      ) : user ? (
        <MeProvider>
          <Theater />
        </MeProvider>
      ) : (
        <MarqueeLanding devMode={devMode} />
      )}
    </MoodProvider>
  );
}
