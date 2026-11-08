import { useState } from "react";
import { CheckResult, checkMessage } from "./api";
import Highlighted from "./Highlighted";

const SAMPLES = [
  { label: "Bank alert", text: "Chase Alert: Your account has been temporarily locked due to suspicious activity. Verify within 24 hours or it will be closed: chase-secure-alert.co/verify" },
  { label: "Hi Mom", text: "Hi Mom, this is my new number. My phone broke. Can you send $300 in Apple gift cards today? It's urgent, please don't tell Dad." },
  { label: "Real code", text: "Your T-Mobile verification code is 482913. It expires in 10 minutes. Never share this code with anyone." },
  { label: "Tricky", text: "Hey it's Jess, I dropped my phone in the lake lol this is my temp number. Can you grab me a $50 Google Play card? I'll pay you back tonight." },
];

const VERDICT = {
  scam: { icon: "⚠️", title: "This looks like a scam", cls: "v-scam" },
  unsure: { icon: "❓", title: "We're not sure", cls: "v-unsure" },
  legit: { icon: "✅", title: "This looks safe", cls: "v-legit" },
} as const;

export default function Check() {
  const [text, setText] = useState("");
  const [sent, setSent] = useState(""); // the text the result refers to (highlights use its offsets)
  const [result, setResult] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!text.trim()) return;
    setBusy(true); setError(""); setResult(null);
    try {
      const t = text.trim();
      setResult(await checkMessage(t));
      setSent(t);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const v = result ? VERDICT[result.verdict] : null;
  // Never display 0% or 100%: no detector is certain.
  const clamp = (x: number) => Math.min(99, Math.max(1, Math.round(x * 100)));
  const pct = result ? clamp(result.confidence) : 0;
  const scamPct = result ? clamp(result.p_scam) : 0;

  return (
    <section aria-labelledby="check-h">
      <h2 id="check-h">Got a suspicious message?</h2>
      <p className="lead">Paste it below. We'll tell you what we think, how sure we are, and what to do next.</p>

      <label htmlFor="msg" className="sr-only">Message to check</label>
      <textarea id="msg" value={text} onChange={(e) => setText(e.target.value)} rows={6}
        placeholder="Paste a text, email, or voicemail transcript here…" maxLength={4000} />

      <div className="chips" aria-label="Try an example">
        <span className="chips-label">Try an example:</span>
        {SAMPLES.map((s) => (
          <button key={s.label} className="chip" onClick={() => { setText(s.text); setResult(null); }}>{s.label}</button>
        ))}
      </div>

      <button className="primary" onClick={run} disabled={busy || !text.trim()}>
        {busy ? "Checking…" : "Check this message"}
      </button>
      {error && <p role="alert" className="error">{error}</p>}

      {result && v && (
        <div className="result" aria-live="polite">
          <div className={`verdict ${v.cls}`}>
            <span className="verdict-icon" aria-hidden>{v.icon}</span>
            <div>
              <h3>{v.title}</h3>
              {result.verdict === "unsure" ? (
                <p>We think there's about a <b>{scamPct}%</b> chance this is a scam. That's not enough to be sure, so please be careful.</p>
              ) : (
                <p>We're about <b>{pct}%</b> sure.{result.verdict === "legit" && " No detector is perfect, so stay alert."}</p>
              )}
              <div className="meter" role="img" aria-label={`Estimated chance this is a scam: ${scamPct}%`}>
                <div className="meter-fill" style={{ width: `${scamPct}%` }} />
              </div>
              <div className="meter-scale"><span>Safe</span><span>Scam</span></div>
            </div>
          </div>

          {result.category_info && (
            <div className="card">
              <h4>{result.category_info.title}</h4>
              <p>{result.category_info.what}</p>
              <p className="muted"><b>Their trick:</b> {result.category_info.tactic}</p>
            </div>
          )}

          {result.verdict !== "legit" && result.red_flags.length > 0 && (
            <div className="card">
              <h4>Warning signs we found</h4>
              <Highlighted text={sent} flags={result.red_flags} />
            </div>
          )}

          <div className={`card steps risk-${result.next_steps.risk}`}>
            <h4>What to do now</h4>
            <ol>{result.next_steps.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
          </div>

          <details className="card">
            <summary>What we looked at (your privacy)</summary>
            <p className="muted">Private details are removed on the server before anything else could see them. This is the version any AI helper would get:</p>
            <pre className="redacted">{result.privacy.redacted_text}</pre>
            <p className="muted">
              {Object.keys(result.privacy.pii_found).length
                ? "Removed: " + Object.entries(result.privacy.pii_found).map(([k, n]) => `${n} ${k.toLowerCase()}`).join(", ")
                : "We didn't find any private details to remove."}
              {" "}Your message is not saved.
            </p>
          </details>
        </div>
      )}
    </section>
  );
}
