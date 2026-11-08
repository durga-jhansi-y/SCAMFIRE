export type Flag = { start: number; end: number; type: string };
export type CheckResult = {
  verdict: "scam" | "legit" | "unsure";
  p_scam: number;
  confidence: number;
  category: string | null;
  category_info: { title: string; what: string; tactic: string } | null;
  red_flags: Flag[];
  next_steps: { risk: "high" | "medium" | "low"; headline: string; steps: string[] };
  privacy: { redacted_text: string; pii_found: Record<string, number>; sent_to_llm: boolean };
  needs_agent: boolean;
};

export async function checkMessage(text: string): Promise<CheckResult> {
  const res = await fetch("/api/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("The checker is not reachable. Is the backend running?");
  return res.json();
}

export const FLAG_LABELS: Record<string, string> = {
  urgency: "Pressure to rush",
  threat: "Threat or scare",
  payment: "Asks for money",
  credential_request: "Asks for private info",
  impersonation: "Pretends to be a company",
  prize: "Too good to be true",
  too_good: "Too good to be true",
  secrecy: "Asks you to keep a secret",
  new_number: "'New number' story",
  offplatform: "Moves you to another app",
  link: "Suspicious link",
};
