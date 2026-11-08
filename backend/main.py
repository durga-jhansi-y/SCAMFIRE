"""Scam Fire Drill API. Privacy: pasted messages are processed in memory and never written to disk
or logged. Only the locally-redacted version may ever be sent to the LLM (milestone 5)."""
import json
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from detector import load_model
from drill import get_pool, pick_next
from guidance import TAXONOMY, next_steps
from redact import redact_pii

app = FastAPI(title="Scam Fire Drill", docs_url="/api/docs", openapi_url="/api/openapi.json")
_model = None


def model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


class CheckIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@app.on_event("startup")
def warm():
    get_pool()  # builds/loads the drill pool so the first card is instant


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/check")
def check(body: CheckIn):
    text = body.text.strip()
    redacted, pii_counts = redact_pii(text)
    r = model().analyze(text)
    verdict = r["verdict"]
    steps = next_steps(r["category"], verdict, r["confidence"])
    cat = TAXONOMY.get(r["category"])
    # Highlights are offsets only: the client already holds the text, so we never echo it back.
    flags = [] if verdict == "legit" else [{"start": f["start"], "end": f["end"], "type": f["type"]} for f in r["red_flags"]]
    return {
        "verdict": verdict,
        "p_scam": r["p_scam"],
        "confidence": r["confidence"],
        "category": r["category"] if verdict != "legit" else None,
        "category_info": {"title": cat["title"], "what": cat["what"], "tactic": cat["tactic"]} if cat and verdict != "legit" else None,
        "red_flags": flags,
        "next_steps": steps,
        "privacy": {"redacted_text": redacted, "pii_found": pii_counts, "sent_to_llm": False},
        "needs_agent": r["needs_agent"],
    }


class DrillIn(BaseModel):
    stats: dict = Field(default_factory=dict)  # {category: {seen, missed}} kept in the browser
    seen_ids: list[str] = Field(default_factory=list, max_length=2000)


@app.post("/api/drill/next")
def drill_next(body: DrillIn):
    return pick_next(body.stats, body.seen_ids)


@app.get("/api/eval")
def eval_summary():
    p = Path(__file__).parent / "eval_results.json"
    return json.loads(p.read_text()) if p.exists() else {}
