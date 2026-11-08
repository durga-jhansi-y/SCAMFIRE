"""Nemotron agent: a multi-step, tool-calling loop (NVIDIA's OpenAI-compatible API).

PRIVACY DESIGN
  * The model never receives the raw message. Tools read the raw text from server memory and return only
    derived data; every string handed back to the model is passed through the local redactor first.
  * `classify` refuses to run until `redact_pii` has run (the plan order is enforced in code, not just prompted).
  * Before every LLM request a guard re-scans the whole payload and BLOCKS the call if an email, SSN, card
    number or phone number is still present.
  * The exact payload of the final request is returned to the UI ("egress") so the user can see what was sent.

SAFETY / HONESTY
  * The agent may only RAISE an 'unsure' verdict to 'scam'. It can never turn a detector 'unsure' or 'scam' into a
    confident 'safe', because a wrong 'safe' is the most harmful error.
  * Without NVIDIA_API_KEY + NEMOTRON_MODEL the same tools run in a fixed local order and the response is labelled
    mode='local'. It is never presented as an LLM result.
"""
import json
import os
import random
import re
import uuid

from dotenv import load_dotenv

from detector import ROOT, SCAM_HI, SCAM_LO, load_model
from features import find_spans
from guidance import HABITS, LEGIT_WHY, TAXONOMY, next_steps
from redact import redact_pii

load_dotenv(ROOT / ".env")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MAX_STEPS = 8
BLOCK_LABELS = {"EMAIL", "SSN", "CARD", "PHONE"}
ALL_CATEGORIES = list(TAXONOMY) + list(LEGIT_WHY)

FLAG_LABELS = {
    "urgency": "Pressure to rush", "threat": "Threat or scare", "payment": "Asks for money / gift cards / crypto",
    "credential_request": "Asks for private info", "impersonation": "Pretends to be a trusted company",
    "prize": "Too good to be true", "too_good": "Too good to be true", "secrecy": "Asks for secrecy",
    "new_number": "'New number' story", "offplatform": "Moves you to another app", "link": "Suspicious link",
}
FLAG_WHY = {
    "urgency": "Scammers rush you so you don't stop and think.",
    "threat": "Fear makes people act before checking.",
    "payment": "Gift cards, crypto and wires are hard to get back. Real companies rarely ask for them.",
    "credential_request": "Real companies don't ask for PINs, passwords or full SSNs by message.",
    "impersonation": "Scammers borrow the name of a company or agency you trust.",
    "prize": "Unexpected prizes and huge returns are bait.",
    "too_good": "Offers that are too good to be true usually are.",
    "secrecy": "Scammers isolate you so no one can warn you.",
    "new_number": "'New number' is a common opener to impersonate family.",
    "offplatform": "Moving to a private chat avoids the platform's scam protection.",
    "link": "Look-alike or shortened links lead to fake sign-in pages.",
}

_model = None


def detector():
    global _model
    if _model is None:
        _model = load_model()
    return _model


def status():
    key, model = os.getenv("NVIDIA_API_KEY"), os.getenv("NEMOTRON_MODEL")
    return {"configured": bool(key and model), "has_key": bool(key), "has_model": bool(model), "model": model or None}


class PrivacyBlock(Exception):
    pass


def guard(payload: str):
    _, counts = redact_pii(payload)
    bad = BLOCK_LABELS & set(counts)
    if bad:
        raise PrivacyBlock(f"Blocked: unredacted {', '.join(sorted(bad))} found in LLM payload")


def scrub(obj):
    """Redact every string in a JSON-able structure."""
    if isinstance(obj, str):
        return redact_pii(obj)[0]
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    return obj


class Ctx:
    def __init__(self, raw="", stats=None, client=None, model=None):
        self.raw, self.stats, self.client, self.model = raw, stats or {}, client, model
        self.redacted_done = False
        self.analysis = None
        self.generated = None


# ------------------------------------------------------------------ tools
def t_redact_pii(ctx, text=None):
    red, counts = redact_pii(ctx.raw)
    ctx.redacted_done = True
    return {"redacted_text": red, "removed": counts}


def t_classify(ctx, text=None):
    if not ctx.redacted_done:
        return {"error": "Call redact_pii first. The plan is: redact, then classify."}
    a = detector().analyze(ctx.raw)
    ctx.analysis = a
    return {"verdict": a["verdict"], "p_scam": a["p_scam"], "category": a["category"],
            "category_confidence": a["category_confidence"],
            "needs_deeper_analysis": a["verdict"] == "unsure",
            "note": "p_scam is calibrated. 'unsure' means 0.10 < p_scam < 0.70."}


def t_explain_red_flags(ctx, text=None):
    spans = find_spans(ctx.raw)
    out = [{"type": s["type"], "label": FLAG_LABELS.get(s["type"], s["type"]), "snippet": s["text"][:60],
            "why_it_matters": FLAG_WHY.get(s["type"], "")} for s in spans[:8]]
    return scrub({"red_flags": out, "count": len(spans),
                  "note": "No red-flag signals found." if not spans else "Weigh these against what a legitimate sender would do."})


def t_lookup_taxonomy(ctx, category=None):
    if category in TAXONOMY:
        t = TAXONOMY[category]
        return {"category": category, "title": t["title"], "what": t["what"], "tactic": t["tactic"], "habit": HABITS.get(category)}
    if category in LEGIT_WHY:
        return {"category": category, "title": "Legitimate message type", "why_it_is_safe": LEGIT_WHY[category]}
    return {"error": f"Unknown category. Valid: {', '.join(ALL_CATEGORIES)}"}


def t_recommend_next_steps(ctx, category=None, risk="medium"):
    v, conf = {"high": ("scam", 0.95), "medium": ("scam", 0.6), "low": ("legit", 0.95)}.get(risk, ("unsure", 0.5))
    ns = next_steps(category or "", v, conf)
    return {"risk": ns["risk"], "headline": ns["headline"], "steps": ns["steps"]}


def t_get_user_weak_spots(ctx):
    rows = [{"category": c, "seen": s.get("seen", 0), "missed": s.get("missed", 0),
             "miss_rate": round(s.get("missed", 0) / max(1, s.get("seen", 0)), 2)}
            for c, s in ctx.stats.items() if s.get("seen", 0) >= 1]
    rows.sort(key=lambda r: (-r["miss_rate"], -r["missed"]))
    if not rows:
        pool = random.sample(list(TAXONOMY), 3)
        return {"weak_spots": [], "note": "No history yet. Suggested starter categories.", "suggested": pool}
    return {"weak_spots": rows[:4]}


GEN_SYSTEM = (
    "You write FAKE practice messages for a scam-awareness training game. Use only fictional details: phone numbers "
    "like (555) 010-0123, made-up names, and made-up look-alike web addresses. Reply with ONLY a JSON object: "
    '{"channel": "sms" | "email" | "voicemail", "text": "..."}. For a scam category, write a realistic scam of that type. '
    "For a legit_* category, write a genuine, harmless message of that type. Under 450 characters. Email text starts with "
    "'Subject: '. Voicemail text is a transcript."
)
DIFF = {"easy": "Make the warning signs obvious.", "medium": "Include a few warning signs, not all.",
        "hard": "Make it subtle: few obvious red flags, believable tone. For legit categories, make it LOOK a little "
                "alarming (urgency or a link) while still being genuinely safe."}


def t_generate_drill(ctx, category=None, difficulty="medium"):
    if category not in ALL_CATEGORIES:
        return {"error": f"Unknown category. Valid: {', '.join(ALL_CATEGORIES)}"}
    if difficulty not in DIFF:
        difficulty = "medium"
    title = TAXONOMY[category]["title"] if category in TAXONOMY else LEGIT_WHY[category][:0] + category.replace("legit_", "legitimate ")
    user = f"Category: {category} ({title}). Difficulty: {difficulty}. {DIFF[difficulty]}"
    guard(GEN_SYSTEM + user)
    resp = ctx.client.chat.completions.create(
        model=ctx.model, temperature=0.8, max_tokens=500,
        messages=[{"role": "system", "content": GEN_SYSTEM}, {"role": "user", "content": user}])
    data = _json_from(resp.choices[0].message.content or "")
    text = (data or {}).get("text", "")
    ch = (data or {}).get("channel", "sms")
    if not isinstance(text, str) or len(text) < 15:
        return {"error": "Model did not return a usable message. Try again."}
    ctx.generated = {"text": text.strip()[:600], "channel": ch if ch in ("sms", "email", "voicemail") else "sms",
                     "category": category, "difficulty": difficulty}
    return {"ok": True, "preview": ctx.generated["text"][:80] + "…", "channel": ctx.generated["channel"]}


TOOLS = {
    "redact_pii": t_redact_pii, "classify": t_classify, "explain_red_flags": t_explain_red_flags,
    "lookup_taxonomy": t_lookup_taxonomy, "recommend_next_steps": t_recommend_next_steps,
    "generate_drill": t_generate_drill, "get_user_weak_spots": t_get_user_weak_spots,
}


def _fn(name, desc, props=None, req=None):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props or {}, "required": req or []}}}


_TEXT = {"text": {"type": "string", "description": "Always pass 'message'. The loaded message is used."}}
SCHEMAS = {
    "redact_pii": _fn("redact_pii", "Strip personal data (names, phones, emails, account numbers, addresses) from the loaded message and return the redacted text. ALWAYS call first.", _TEXT),
    "classify": _fn("classify", "Run the local calibrated detector on the loaded message. Returns verdict (scam/legit/unsure), p_scam and category.", _TEXT),
    "explain_red_flags": _fn("explain_red_flags", "List the warning-sign phrases found in the loaded message, each with why it matters.", _TEXT),
    "lookup_taxonomy": _fn("lookup_taxonomy", "Look up a scam category in the taxonomy: what it is and the scammer's tactic.", {"category": {"type": "string"}}, ["category"]),
    "recommend_next_steps": _fn("recommend_next_steps", "Get concrete next steps for a category and risk level.", {"category": {"type": "string"}, "risk": {"type": "string", "enum": ["high", "medium", "low"]}}, ["category", "risk"]),
    "generate_drill": _fn("generate_drill", "Write ONE new fake practice message for a category at a difficulty.", {"category": {"type": "string"}, "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]}}, ["category", "difficulty"]),
    "get_user_weak_spots": _fn("get_user_weak_spots", "Get the categories this user misses most often (from their on-device history)."),
}
CHECK_TOOLS = ["redact_pii", "classify", "explain_red_flags", "lookup_taxonomy", "recommend_next_steps"]
DRILL_TOOLS = ["get_user_weak_spots", "lookup_taxonomy", "generate_drill"]

CHECK_SYSTEM = (
    "You are a scam-analysis agent protecting an ordinary person. A message has been loaded; you CANNOT see it directly. "
    "Use tools in this order: 1) redact_pii. 2) classify. 3) If the verdict is 'unsure' (needs_deeper_analysis true), call "
    "explain_red_flags and reason about whether a legitimate sender would do these things. 4) lookup_taxonomy for the likely "
    "category. 5) recommend_next_steps. Then reply with ONLY JSON: "
    '{"verdict": "scam|legit|unsure", "confidence": 0.0-1.0, "category": "<category>", "explanation": "<max 60 words, plain '
    'language for a non-technical adult, no jargon, never certain>", "reasoning": "<one sentence on what decided it>"}. '
    "Never repeat personal data. Never claim certainty. If evidence is mixed, say unsure."
)
DRILL_SYSTEM = (
    "You personalise a scam-awareness drill. Plan: 1) get_user_weak_spots. 2) lookup_taxonomy for the weakest category. "
    "3) generate_drill for that category; choose 'medium' for a category with a high miss rate, 'hard' for one the user rarely "
    "misses, 'easy' if they've missed it every time. Then reply with the single word DONE."
)


def _json_from(s):
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def summarize(tool, args, res):
    if "error" in res:
        return f"Error: {res['error']}"
    if tool == "redact_pii":
        n = sum(res["removed"].values())
        return f"Removed {n} private detail(s): " + (", ".join(f"{v} {k.lower()}" for k, v in res["removed"].items()) or "none")
    if tool == "classify":
        return f"Detector: {res['verdict']} (P(scam) {res['p_scam']:.0%}), category {res['category']}"
    if tool == "explain_red_flags":
        return f"{res['count']} warning sign(s): " + ", ".join(sorted({f['label'] for f in res['red_flags']})) if res["count"] else "No warning signs found"
    if tool == "lookup_taxonomy":
        return res.get("title", "")
    if tool == "recommend_next_steps":
        return f"{len(res['steps'])} steps ({res['risk']} risk)"
    if tool == "get_user_weak_spots":
        return ("Weakest: " + ", ".join(f"{w['category']} ({w['missed']}/{w['seen']} missed)" for w in res["weak_spots"][:3])) if res["weak_spots"] else "No history yet"
    if tool == "generate_drill":
        return f"Wrote a new {res.get('channel', '')} message"
    return ""


def _loop(ctx, system, user, tool_names):
    """Generic tool-calling loop. Returns (final_text, trace, egress)."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    schemas = [SCHEMAS[n] for n in tool_names]
    trace, final = [], ""
    for _ in range(MAX_STEPS):
        guard(json.dumps(messages))
        resp = ctx.client.chat.completions.create(model=ctx.model, messages=messages, tools=schemas,
                                                  tool_choice="auto", temperature=0.2, max_tokens=700)
        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        entry = {"role": "assistant", "content": msg.content or ""}
        if calls:
            entry["tool_calls"] = [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments or "{}"}} for c in calls]
        messages.append(entry)
        if msg.content and calls:
            trace.append({"kind": "thought", "text": scrub(msg.content)[:300]})
        if not calls:
            final = msg.content or ""
            break
        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except Exception:
                args = {}
            if name not in tool_names:
                res = {"error": f"Unknown tool {name}"}
            else:
                try:
                    res = TOOLS[name](ctx, **{k: v for k, v in args.items() if k in ("category", "difficulty", "risk", "text")})
                except PrivacyBlock:
                    raise
                except Exception as e:  # tool errors go back to the model, not the user
                    res = {"error": f"{type(e).__name__}"}
            res = scrub(res)
            shown = {k: v for k, v in args.items() if k != "text"}
            trace.append({"kind": "tool", "tool": name, "args": shown, "summary": summarize(name, args, res), "ok": "error" not in res, "source": "nemotron"})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(res)})
    egress = [{"role": m["role"], "content": (m.get("content") or "")[:1200] if m["role"] != "assistant" or m.get("content") else "[tool call]"} for m in messages if m["role"] != "system"]
    return final, trace, egress


# ------------------------------------------------------------------ check
def _client():
    from openai import OpenAI
    return OpenAI(base_url=BASE_URL, api_key=os.getenv("NVIDIA_API_KEY"), timeout=45)


def combine(local, agent):
    """Agent can only raise 'unsure' -> 'scam'. It never creates a confident 'safe'."""
    base = {"verdict": local["verdict"], "p_scam": local["p_scam"], "confidence": local["confidence"], "category": local["category"], "changed": False}
    if local["verdict"] != "unsure" or not agent:
        return base
    v, conf = agent.get("verdict"), float(agent.get("confidence") or 0.5)
    conf = min(max(conf, 0.0), 1.0)
    p_agent = 0.5 + 0.4 * conf if v == "scam" else 0.5 - 0.4 * conf if v == "legit" else 0.5
    p = 0.5 * local["p_scam"] + 0.5 * p_agent
    if p >= SCAM_HI and agent.get("category") in TAXONOMY:
        return {"verdict": "scam", "p_scam": round(p, 4), "confidence": round(p, 4), "category": agent["category"], "changed": True}
    return {**base, "p_scam": round(p, 4)}


def _finish(local, raw_text, final, mode, trace, egress, error=None):
    agent = _json_from(final) if final else None
    comb = combine(local, agent)
    cat = comb["category"]
    info = TAXONOMY.get(cat) if comb["verdict"] != "legit" else None
    return {
        "mode": mode, "error": error, "trace": trace, "egress": egress,
        "explanation": (agent or {}).get("explanation"), "reasoning": (agent or {}).get("reasoning"),
        "agent_verdict": (agent or {}).get("verdict"),
        "adjusted": {**comb, "category_info": {"title": info["title"], "what": info["what"], "tactic": info["tactic"]} if info else None,
                     "next_steps": next_steps(cat, comb["verdict"], comb["confidence"])},
    }


def _local_plan(ctx):
    """Same tools, fixed order, no LLM. Labelled as local so it is never mistaken for Nemotron."""
    trace = []

    def run(name, **kw):
        res = scrub(TOOLS[name](ctx, **kw))
        trace.append({"kind": "tool", "tool": name, "args": kw, "summary": summarize(name, kw, res), "ok": "error" not in res, "source": "local"})
        return res
    run("redact_pii")
    c = run("classify")
    if c["verdict"] == "unsure":
        run("explain_red_flags")
    run("lookup_taxonomy", category=c["category"])
    run("recommend_next_steps", category=c["category"], risk="high" if c["verdict"] == "scam" else "low" if c["verdict"] == "legit" else "medium")
    return trace


def run_check(raw: str, client=None, model=None):
    ctx = Ctx(raw=raw, client=client, model=model)
    local = detector().analyze(raw)
    st = status()
    if client is None and st["configured"]:
        client, model = _client(), st["model"]
        ctx.client, ctx.model = client, model
    if client is None:
        trace = _local_plan(ctx)
        return _finish(local, raw, "", "local", trace, [], None)
    try:
        final, trace, egress = _loop(ctx, CHECK_SYSTEM, "A message is loaded as 'message'. Analyze it using your tools.", CHECK_TOOLS)
        return _finish(local, raw, final, "nemotron", trace, egress)
    except PrivacyBlock as e:
        trace = _local_plan(Ctx(raw=raw))
        return _finish(local, raw, "", "local", trace, [], str(e))
    except Exception as e:
        trace = _local_plan(Ctx(raw=raw))
        return _finish(local, raw, "", "local", trace, [], f"Couldn't use Nemotron ({type(e).__name__}); showing the local pipeline instead.")


# ------------------------------------------------------------------ drill
def run_drill(stats, client=None, model=None):
    st = status()
    if client is None:
        if not st["configured"]:
            return {"available": False}
        client, model = _client(), st["model"]
    ctx = Ctx(stats=stats, client=client, model=model)
    try:
        _, trace, egress = _loop(ctx, DRILL_SYSTEM, "Create the next personalised practice message for this user.", DRILL_TOOLS)
    except Exception as e:
        return {"available": True, "card": None, "error": f"{type(e).__name__}"}
    g = ctx.generated
    if not g:
        return {"available": True, "card": None, "trace": trace, "error": "The agent did not produce a message."}
    from drill import public_card  # local import: drill imports detector, avoid cycles at module load
    is_scam = g["category"] in TAXONOMY
    p = detector().analyze(g["text"])["p_scam"]
    card = {"id": "gen-" + uuid.uuid4().hex[:8], "channel": g["channel"], "text": g["text"], "label": "scam" if is_scam else "legit",
            "category": g["category"], "flags": [{"start": s["start"], "end": s["end"], "type": s["type"]} for s in find_spans(g["text"])] if is_scam else [],
            "p_scam": p, "source": "nemotron"}
    out = public_card(card)
    out.update({"generated": True, "difficulty": g["difficulty"], "trace": trace})
    return {"available": True, "card": out, "trace": trace}
