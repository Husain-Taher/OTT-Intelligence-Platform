"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

const KEY = "ott.curtain.seen";

/** Velvet curtains part once per browser session, right after sign-in. */
export default function Curtain() {
  const reduce = useReducedMotion();
  const [show, setShow] = useState(false);

  useEffect(() => {
    try {
      if (reduce || sessionStorage.getItem(KEY)) return;
      sessionStorage.setItem(KEY, "1");
    } catch {}
    if (!reduce) setShow(true);
  }, [reduce]);

  if (!show) return null;
  const ease = [0.7, 0, 0.2, 1] as const;
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-[70] overflow-hidden">
      <motion.div
        className="velvet absolute inset-y-0 left-0 w-1/2 origin-left"
        initial={{ scaleX: 1 }}
        animate={{ scaleX: 0.08 }}
        transition={{ duration: 1.5, ease, delay: 0.35 }}
        onAnimationComplete={() => setShow(false)}
      />
      <motion.div
        className="velvet absolute inset-y-0 right-0 w-1/2 origin-right"
        initial={{ scaleX: 1 }}
        animate={{ scaleX: 0.08 }}
        transition={{ duration: 1.5, ease, delay: 0.35 }}
      />
    </div>
  );
}
