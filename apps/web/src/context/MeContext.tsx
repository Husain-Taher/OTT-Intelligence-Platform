"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { fetchMe } from "@/lib/api";
import { MeResponse } from "@/types";

interface MeContextValue {
  me: MeResponse | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const MeContext = createContext<MeContextValue>({ me: null, loading: true, refresh: async () => {} });

export function MeProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const data = await fetchMe();
    if (data) setMe(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return <MeContext.Provider value={{ me, loading, refresh }}>{children}</MeContext.Provider>;
}

export const useMe = () => useContext(MeContext);
