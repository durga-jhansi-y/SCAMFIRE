import { Flag } from "./api";

export type DrillCard = {
  id: string;
  channel: "sms" | "email" | "voicemail";
  text: string;
  label: "scam" | "legit";
  category: string;
  category_title: string | null;
  explanation: string;
  tip: string | null;
  habit: string;
  flags: Flag[];
  ai: { verdict: "scam" | "legit" | "unsure"; p_scam: number; confidence: number; correct: boolean | null };
  tricky: string | null;
  focus_reason: string | null;
};

export type CatStats = Record<string, { seen: number; missed: number }>;

export async function nextCard(stats: CatStats, seenIds: string[]): Promise<DrillCard> {
  const res = await fetch("/api/drill/next", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stats, seen_ids: seenIds }),
  });
  if (!res.ok) throw new Error("Couldn't load a practice message. Is the backend running?");
  return res.json();
}

export const CATEGORY_NAMES: Record<string, string> = {
  bank_account_locked: "Fake bank alerts",
  package_delivery: "Fake delivery notices",
  toll_fine: "Fake tolls & fines",
  irs_government: "Government impersonation",
  tech_support: "Tech support scams",
  romance: "Romance scams",
  job_offer: "Fake job offers",
  prize_lottery: "Fake prizes",
  crypto_investment: "Crypto & investment scams",
  family_emergency: "'Hi Mom' family emergencies",
  carrier_sim_swap: "Carrier / SIM-swap scams",
  legit_2fa: "Real verification codes",
  legit_delivery: "Real delivery updates",
  legit_friend: "Messages from friends",
  legit_appointment: "Real reminders",
  legit_bank_alert: "Real bank notices",
  legit_carrier: "Real carrier notices",
};
