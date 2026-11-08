import { CatStats } from "./drillApi";

/** Drill progress lives ONLY in this browser (localStorage). Nothing about it is sent or stored server-side
 *  except the per-category counts, which are sent with each "next card" request and not kept. */
export type Progress = { cats: CatStats; seenIds: string[]; rounds: { score: number; date: string }[] };
const KEY = "sfd.progress.v1";
const empty = (): Progress => ({ cats: {}, seenIds: [], rounds: [] });

export function loadProgress(): Progress {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...empty(), ...JSON.parse(raw) };
  } catch { /* private mode or corrupt data: start fresh */ }
  return empty();
}

export function saveProgress(p: Progress) {
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* ignore */ }
}

export function recordAnswer(p: Progress, cardId: string, category: string, correct: boolean): Progress {
  const s = p.cats[category] ?? { seen: 0, missed: 0 };
  return {
    ...p,
    cats: { ...p.cats, [category]: { seen: s.seen + 1, missed: s.missed + (correct ? 0 : 1) } },
    seenIds: [...p.seenIds, cardId].slice(-400),
  };
}

/** Categories where the user's miss rate is highest (needs >= 2 attempts). */
export function weakSpots(p: Progress, limit = 3) {
  return Object.entries(p.cats)
    .filter(([, s]) => s.seen >= 2 && s.missed > 0)
    .map(([cat, s]) => ({ cat, ...s, rate: s.missed / s.seen }))
    .sort((a, b) => b.rate - a.rate || b.missed - a.missed)
    .slice(0, limit);
}
