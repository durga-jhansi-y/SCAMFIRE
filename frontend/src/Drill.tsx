import { useEffect, useRef, useState } from "react";
import { CATEGORY_NAMES, DrillCard, nextCard } from "./drillApi";
import MessageView from "./MessageView";
import { Progress, loadProgress, recordAnswer, saveProgress, weakSpots } from "./progress";

const ROUND_LEN = 8;
type Answer = { card: DrillCard; guess: "scam" | "legit"; correct: boolean };
const pct = (x: number) => Math.min(99, Math.max(1, Math.round(x * 100)));

const GENERIC_HABITS = [
  "Slow down. Scammers rely on you feeling rushed. A real problem will still be there in 10 minutes.",
  "Verify with the real company or person using a number or app you already have, never the one in the message.",
  "Never pay with gift cards, crypto or wire transfers for someone who contacted you first.",
];

function compare(a: Answer) {
  const { card, correct } = a;
  const ai = card.ai;
  const aiPct = pct(ai.confidence);
  if (ai.verdict === "unsure")
    return correct
      ? `You got it. The AI was only ${aiPct}% sure on this one. ${card.tricky ?? ""}`
      : `This one fooled you, and the AI was only ${aiPct}% sure too. ${card.tricky ?? ""}`;
  if (correct) return ai.correct ? "You and the AI both caught this one." : `You beat the AI here. It guessed wrong with ${aiPct}% confidence. ${card.tricky ?? ""}`;
  return ai.correct ? "The AI caught this one. Here's what to watch for next time." : `This fooled the AI too (${aiPct}% sure, but wrong). ${card.tricky ?? ""}`;
}

type Phase = "intro" | "card" | "feedback" | "summary";
const ROUND_KEY = "sfd.round.v1";

/** A round in progress survives a reload (this device only). */
function loadRound(): { phase: Phase; card: DrillCard; answers: Answer[]; seen: string[] } | null {
  try {
    const r = JSON.parse(localStorage.getItem(ROUND_KEY) ?? "null");
    if (r && (r.phase === "card" || r.phase === "feedback") && r.card && Array.isArray(r.answers)) return r;
  } catch { /* ignore */ }
  return null;
}

export default function Drill() {
  const [saved] = useState(loadRound);
  const [progress, setProgress] = useState<Progress>(loadProgress);
  const [phase, setPhase] = useState<Phase>(saved?.phase ?? "intro");
  const [card, setCard] = useState<DrillCard | null>(saved?.card ?? null);
  const [answers, setAnswers] = useState<Answer[]>(saved?.answers ?? []);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmErase, setConfirmErase] = useState(false);
  const topRef = useRef<HTMLHeadingElement>(null);
  const roundSeen = useRef<string[]>(saved?.seen ?? []);

  useEffect(() => { saveProgress(progress); }, [progress]);
  useEffect(() => {
    try {
      if ((phase === "card" || phase === "feedback") && card)
        localStorage.setItem(ROUND_KEY, JSON.stringify({ phase, card, answers, seen: roundSeen.current }));
      else localStorage.removeItem(ROUND_KEY);
    } catch { /* ignore */ }
  }, [phase, card, answers]);
  useEffect(() => { topRef.current?.focus(); }, [phase]);

  async function fetchCard(p: Progress) {
    setLoading(true); setError("");
    try {
      setCard(await nextCard(p.cats, [...p.seenIds, ...roundSeen.current]));
      setPhase("card");
    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }

  function start() { setAnswers([]); roundSeen.current = []; fetchCard(progress); }

  function answer(guess: "scam" | "legit") {
    if (!card) return;
    const correct = guess === card.label;
    const a: Answer = { card, guess, correct };
    roundSeen.current.push(card.id);
    setAnswers((x) => [...x, a]);
    setProgress((p) => recordAnswer(p, card.id, card.category, correct));
    setPhase("feedback");
  }

  function next() {
    if (answers.length >= ROUND_LEN) {
      const score = Math.round((answers.filter((a) => a.correct).length / answers.length) * 100);
      setProgress((p) => ({ ...p, rounds: [...p.rounds, { score, date: new Date().toISOString() }].slice(-30) }));
      setPhase("summary");
    } else fetchCard(progress);
  }

  function reset() {
    setProgress({ cats: {}, seenIds: [], rounds: [] });
    setConfirmErase(false);
  }

  const last = answers[answers.length - 1];

  // ---------- INTRO ----------
  if (phase === "intro") {
    const weak = weakSpots(progress);
    const total = Object.values(progress.cats).reduce((n, s) => n + s.seen, 0);
    return (
      <section aria-labelledby="drill-h">
        <h2 id="drill-h" ref={topRef} tabIndex={-1}>Scam Fire Drill</h2>
        <p className="lead">{ROUND_LEN} quick messages. For each one, decide: <b>scam</b> or <b>safe</b>. Then see what gave it away and how the AI did.</p>
        {weak.length > 0 ? (
          <div className="card">
            <h4>Your tricky spots</h4>
            <p className="muted">We'll show you more of these.</p>
            <ul className="weak">{weak.map((w) => <li key={w.cat}><b>{CATEGORY_NAMES[w.cat] ?? w.cat}</b>: missed {w.missed} of {w.seen}</li>)}</ul>
          </div>
        ) : (
          <div className="card"><p className="muted">{total ? "Nice start. Keep going and we'll find what trips you up." : "Play a round and we'll learn which scams trick you most, then practice those."}</p></div>
        )}
        <button className="primary" onClick={start} disabled={loading}>{loading ? "Loading…" : "Start a round"}</button>
        {error && <p role="alert" className="error">{error}</p>}
        {progress.rounds.length > 0 && <p className="recent center">Recent scores: {progress.rounds.slice(-5).map((r) => r.score).join(" · ")}</p>}
        {confirmErase ? (
          <div className="confirm-row" role="alertdialog" aria-label="Confirm erase">
            <span>Erase all practice history on this device?</span>
            <button className="danger" onClick={reset}>Yes, erase</button>
            <button className="linklike" onClick={() => setConfirmErase(false)}>Cancel</button>
          </div>
        ) : (
          <p className="muted center">Practice history stays on this device. {total > 0 && <button className="linklike" onClick={() => setConfirmErase(true)}>Erase it</button>}</p>
        )}
      </section>
    );
  }

  // ---------- SUMMARY ----------
  if (phase === "summary") {
    const right = answers.filter((a) => a.correct).length;
    const score = Math.round((right / answers.length) * 100);
    const byCat: Record<string, { seen: number; missed: number }> = {};
    answers.forEach((a) => {
      const s = (byCat[a.card.category] ??= { seen: 0, missed: 0 });
      s.seen++; if (!a.correct) s.missed++;
    });
    // habits: from missed scams (grouped by category, most misses first), then false alarms, then generic
    const missCount: Record<string, { habit: string; n: number }> = {};
    answers.filter((a) => !a.correct).forEach((a) => {
      const k = a.card.label === "scam" ? a.card.category : "false_alarm";
      (missCount[k] ??= { habit: a.card.habit, n: 0 }).n++;
    });
    const habits = Object.values(missCount).sort((a, b) => b.n - a.n).map((x) => x.habit);
    for (const g of GENERIC_HABITS) if (habits.length < 3 && !habits.includes(g)) habits.push(g);
    const missedScams = answers.filter((a) => !a.correct && a.card.label === "scam").length;
    const falseAlarms = answers.filter((a) => !a.correct && a.card.label === "legit").length;
    const aiRight = answers.filter((a) => a.card.ai.correct === true).length;
    const tier = score >= 88 ? "Scam-proof 🛡️" : score >= 63 ? "Sharp eyes 👀" : "Getting there 🌱";
    const prev = progress.rounds.slice(0, -1);
    return (
      <section aria-labelledby="sum-h">
        <h2 id="sum-h" ref={topRef} tabIndex={-1}>Round complete</h2>
        <div className="score-card">
          <div className="score-num" aria-label={`Scam Resistance Score ${score} out of 100`}>{score}</div>
          <div><b>Scam Resistance Score</b><div>{tier}</div>
            <div className="muted">{right} of {answers.length} right{prev.length ? ` · best ${Math.max(score, ...prev.map((r) => r.score))}` : ""}</div></div>
        </div>
        <div className="card">
          <p><b>You vs. the AI:</b> you got {right} right; the AI was confidently right on {aiRight} and unsure on {answers.filter((a) => a.card.ai.verdict === "unsure").length}.</p>
          {missedScams > 0 && <p>🚩 Scams that slipped past you: <b>{missedScams}</b></p>}
          {falseAlarms > 0 && <p>🔔 Real messages you flagged as scams: <b>{falseAlarms}</b></p>}
        </div>
        <div className="card">
          <h4>By type</h4>
          {Object.entries(byCat).sort((a, b) => b[1].missed - a[1].missed).map(([cat, s]) => (
            <div key={cat} className="bar-row">
              <span>{CATEGORY_NAMES[cat] ?? cat}</span>
              <div className="bar" role="img" aria-label={`${s.seen - s.missed} of ${s.seen} right`}>
                <div className="bar-ok" style={{ width: `${((s.seen - s.missed) / s.seen) * 100}%` }} />
              </div>
              <span className="bar-n">{s.seen - s.missed}/{s.seen}</span>
            </div>
          ))}
        </div>
        <div className="card steps risk-low">
          <h4>Your top 3 habits to build</h4>
          <ol>{habits.slice(0, 3).map((h, i) => <li key={i}>{h}</li>)}</ol>
        </div>
        <button className="primary" onClick={start}>Play another round</button>
        <button className="secondary" onClick={() => setPhase("intro")}>Back to start</button>
      </section>
    );
  }

  // ---------- CARD / FEEDBACK ----------
  if (!card) return null;
  const revealed = phase === "feedback" && last;
  return (
    <section aria-labelledby="q-h">
      <div className="progress-row">
        <h2 id="q-h" ref={topRef} tabIndex={-1}>Message {Math.min(answers.length + (revealed ? 0 : 1), ROUND_LEN)} of {ROUND_LEN}</h2>
        <div className="dots" aria-hidden>{Array.from({ length: ROUND_LEN }, (_, i) => <span key={i} className={i < answers.length ? (answers[i].correct ? "dot ok" : "dot bad") : "dot"} />)}</div>
      </div>
      {card.focus_reason && !revealed && <p className="focus">🎯 {card.focus_reason}</p>}

      <MessageView channel={card.channel} text={card.text} flags={revealed ? card.flags : undefined} />

      {!revealed ? (
        <>
          <p className="lead center">Is this a scam?</p>
          <div className="choices">
            <button className="choice scam" onClick={() => answer("scam")}>🚩 Scam</button>
            <button className="choice safe" onClick={() => answer("legit")}>✅ Safe</button>
          </div>
        </>
      ) : (
        <div className="result" aria-live="polite">
          <div className={`verdict ${last.correct ? "v-legit" : "v-scam"}`}>
            <span className="verdict-icon" aria-hidden>{last.correct ? "🎉" : "😬"}</span>
            <div>
              <h3>{last.correct ? "You got it!" : "Not this time"}</h3>
              <p>This one was <b>{card.label === "scam" ? `a scam${card.category_title ? ` (${card.category_title})` : ""}` : "a real message"}</b>.</p>
            </div>
          </div>
          <div className="versus">
            <div><span className="muted">You said</span><b>{last.guess === "scam" ? "Scam" : "Safe"}</b></div>
            <div><span className="muted">The AI said</span><b>{card.ai.verdict === "unsure" ? "Not sure" : card.ai.verdict === "scam" ? "Scam" : "Safe"} · {pct(card.ai.verdict === "unsure" ? card.ai.p_scam : card.ai.confidence)}%{card.ai.verdict === "unsure" ? " scam" : ""}</b></div>
          </div>
          <div className="card"><p>{compare(last)}</p></div>
          <div className="card">
            <h4>{card.label === "scam" ? "Why it's a scam" : "Why it's safe"}</h4>
            <p>{card.explanation}</p>
            {card.label === "scam" && card.flags.length > 0 && <p className="muted">The warning signs are marked in the message above.</p>}
            {card.tip && <p className="muted"><b>What to do:</b> {card.tip}</p>}
          </div>
          <div className="sticky-next">
            <button className="primary" onClick={next} disabled={loading}>{answers.length >= ROUND_LEN ? "See my score" : loading ? "Loading…" : "Next message"}</button>
          </div>
        </div>
      )}
      {error && <p role="alert" className="error">{error}</p>}
    </section>
  );
}
