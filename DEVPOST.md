## Inspiration

Most scam tools do one thing: they tell you "scam" or "not scam" after the message has already landed. But the people who lose the most money are often the ones least able to judge that answer: grandparents who get a "Hi Mom, new number" text, or anyone rushed by a fake bank alert. A verdict alone doesn't change what they do next, and it doesn't make them harder to fool next time.

T-Mobile's challenge asked for scam protection "in ways we haven't thought of yet" and said detection should be a core piece, not the whole product. So we built **Scam Fire Drill**: like a fire drill, you practice *before* the emergency, and when a real suspicious message arrives, you get a clear answer, an honest confidence level, and concrete next steps.

## What it does

**Drill mode (practice)**
- Realistic messages shown as a text, email, or voicemail transcript. You choose **Scam** or **Safe**.
- After each answer: the truth, the red flags highlighted *inside the message*, and the AI's confidence shown next to yours ("You and the AI both caught this one" or "The AI was only 62% sure; here's why it's tricky").
- It adapts: categories you miss come up more often.
- Each round ends with a **Scam Resistance Score**, a per-category breakdown, and your top 3 habits to build.

**Check mode (real-time protection)**
- Paste a suspicious message and get a verdict (**scam / safe / unsure**), calibrated confidence, the scam category, highlighted warning signs, and clear next steps (for example, "Call your bank using the number on your card, not this one. Forward it to 7726 (SPAM)").

**Privacy by design**
- Personal details (phones, emails, names, card/account numbers, addresses) are stripped locally *before* anything could reach an LLM, and you can see the redacted version.
- Pasted messages are never stored. Drill progress lives only in your browser.

## How we built it

- **Backend:** Python + FastAPI. **Frontend:** React + Vite + TypeScript, mobile-first, with a text-size control and large tap targets for accessibility.
- **Data:** T-Mobile's dataset wasn't available to us, so we wrote a generator for ~500 labeled synthetic messages (60% scam / 40% legit) across 11 scam types (bank, delivery, toll, IRS, tech support, romance, job, prize, crypto, family emergency, SIM swap) plus legit messages, including near-misses like real fraud alerts and a friend asking for $20. We also hand-wrote two small "hard" sets in new wording to test generalization.
- **Detector:** a TF-IDF + logistic-regression **baseline**, and an improved detector that blends a text model with a signals-only model (urgency, payment requests, impersonation, look-alike domains, shortened links, credential requests, and more), then calibrates the output so probabilities mean what they say.
- **Honest verdicts:** the detector can answer "unsure". It only calls something safe when it is very sure, because telling someone a scam is safe is the worst mistake.
- **Nemotron agent (NVIDIA track):** a multi-step tool-calling agent over NVIDIA's OpenAI-compatible API, with tools `redact_pii`, `classify`, `lookup_taxonomy`, `explain_red_flags`, `recommend_next_steps`, `generate_drill`, and `get_user_weak_spots`. In Check mode it plans redact → classify → (if unsure) analyze deeper → map to taxonomy → explain and give next steps. In Drill mode it writes *new* practice messages aimed at the user's weak spots. A "How I decided" panel shows each step. *(Status at submission: the agent and its tests are implemented; live connection to Nemotron is being finalized.)*
- **Agent privacy guards:** the model never sees the raw message, only the redacted version. A guard blocks any LLM request that still contains an email, SSN, card number, or phone number. The agent can only *raise* an "unsure" verdict to "scam"; it can never turn one into a confident "safe".

## How we measure accuracy

We report precision, recall, F1, confusion matrices, per-category accuracy, and calibration for baseline vs. ours. For calibration we use expected calibration error:

$$\mathrm{ECE}=\sum_{b=1}^{B}\frac{n_b}{N}\,\bigl|\,\mathrm{acc}(b)-\mathrm{conf}(b)\,\bigr|$$

Lower is better: when we say "80%", it should be right about 80% of the time.

| Test set | Baseline F1 | Ours F1 | ECE (baseline → ours) |
|---|---|---|---|
| Held-out synthetic (n=100) | 1.000 | 0.973 | 0.096 → 0.054 |
| Fresh hard set (n=16, new wording) | 0.889 | 0.857 | 0.166 → 0.116 |

On the fresh hard set our precision is **1.00 vs. 0.80** (the baseline wrongly flagged 2 real messages), and across all test sets we **never confidently called a scam "safe"**. We did not beat the baseline on raw F1, and we say so.

## Challenges we ran into

- **Synthetic data makes easy tests.** The baseline scored a perfect 1.000 on the random split because test messages share templates with training ones. That number is meaningless, so we added hand-written hard sets and report them separately.
- **Our first "improved" detector was worse on unfamiliar wording.** It under-called scams that had no obvious cue words. Rather than hide this, we changed the product behavior: an asymmetric "unsure" zone that favors caution.
- **Honest drill confidence.** The detector was trained on the same messages shown in the game, so its confidence would look inflated. We precompute out-of-fold predictions so every card is scored by a model that never saw it.
- **Tricky near-misses.** A scam asking for a gift card and a real friend asking for $20 look almost identical on the surface. Some messages are genuinely ambiguous, and the right answer is "unsure, verify another way."
- **Practical hurdles:** a Windows dev-server reload bug, PowerShell script restrictions, and keeping redaction aggressive without wrecking the signals the detector needs.

## What we learned

- Calibration and the willingness to say "unsure" matter more to trust than a single accuracy number.
- Privacy is a design constraint, not a feature to add later: enforcing it in code (guards, redaction before the model, a visible "what was sent" view) is more convincing than promising it.
- For people who aren't technical, the **next step** matters more than the label.

## What's next

- Evaluate on T-Mobile's real data and taxonomy, and on real scam messages (everything here is synthetic).
- Finish the live Nemotron agent evaluation, including how much the agent's judgment improves "unsure" cases.
- Trusted Circle: with consent, alert a chosen family member when a high-risk message arrives.
- "Turn this into a drill": convert a real scam you received into a training card, with personal details removed.
