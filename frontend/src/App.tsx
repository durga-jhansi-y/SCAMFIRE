import { useEffect, useState } from "react";
import Check from "./Check";
import Drill from "./Drill";

type Tab = "drill" | "check";
const SIZES = [{ px: 16, label: "A", name: "Normal text" }, { px: 19, label: "A+", name: "Large text" }, { px: 22, label: "A++", name: "Extra large text" }];

function stored<T extends string | number>(key: string, ok: (v: string) => T | null, fallback: T): T {
  try { const v = localStorage.getItem(key); const r = v === null ? null : ok(v); return r ?? fallback; } catch { return fallback; }
}
function save(key: string, v: string) { try { localStorage.setItem(key, v); } catch { /* ignore */ } }

export default function App() {
  const [tab, setTabState] = useState<Tab>(() => stored<Tab>("sfd.tab", (v) => (v === "drill" ? "drill" : "check"), "check"));
  const [size, setSize] = useState<number>(() => stored<number>("sfd.size", (v) => (SIZES.some((s) => String(s.px) === v) ? Number(v) : null), 16));
  const setTab = (t: Tab) => { setTabState(t); save("sfd.tab", t); };

  // Text size scales everything (all sizes are rem-based off <html>).
  useEffect(() => { document.documentElement.style.setProperty("--fs", String(size)); save("sfd.size", String(size)); }, [size]);

  return (
    <div className="app">
      <header>
        <div className="head-row">
          <h1>🛡️ Scam Fire Drill</h1>
          <div className="sizer" role="group" aria-label="Text size">
            {SIZES.map((s) => (
              <button key={s.px} className={size === s.px ? "on" : ""} aria-pressed={size === s.px} aria-label={s.name} onClick={() => setSize(s.px)}>{s.label}</button>
            ))}
          </div>
        </div>
        <p>Practice spotting scams. Check anything suspicious.</p>
      </header>
      <nav role="tablist" aria-label="Main">
        <button role="tab" id="tab-drill" aria-controls="panel" aria-selected={tab === "drill"} className={tab === "drill" ? "on" : ""} onClick={() => setTab("drill")}>🎯 Drill</button>
        <button role="tab" id="tab-check" aria-controls="panel" aria-selected={tab === "check"} className={tab === "check" ? "on" : ""} onClick={() => setTab("check")}>🔍 Check</button>
      </nav>
      <main id="panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === "check" ? <Check /> : <Drill />}
      </main>
      <footer>Demo built with synthetic data. Never enter real account numbers.</footer>
    </div>
  );
}
