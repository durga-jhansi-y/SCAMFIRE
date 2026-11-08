"""Drill mode: card pool, honest out-of-fold AI confidence, and adaptive card selection.

Progress lives in the browser. The server is stateless: the client sends its per-category stats and
the ids it has already seen, and we pick the next card.

Every card's AI confidence is OUT-OF-FOLD: the synthetic cards are scored by a model trained on the
other folds, and the hand-written hard-set cards by a model trained only on synthetic data. So the
detector never gets credit for having memorized the card it's being compared against.
"""
import hashlib
import json
import random
import threading
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold

from detector import SCAM_HI, SCAM_LO, ROOT, Improved, load_hard, load_synthetic
from features import find_spans
from guidance import FALSE_ALARM_HABIT, HABITS, LEGIT_WHY, TAXONOMY
import pandas as pd

CACHE = Path(__file__).resolve().parent / "models" / "drill_pool.json"
_lock = threading.Lock()
_pool = None


def _verdict(p):
    return "scam" if p >= SCAM_HI else "legit" if p <= SCAM_LO else "unsure"


def _spans_from_column(text, red_flags):
    """Generator red_flags are 'type:span' pairs; locate each span in the text."""
    out, used = [], 0
    for item in [x for x in str(red_flags).split(" || ") if x]:
        kind, _, span = item.partition(":")
        i = text.find(span, 0)
        if i >= 0 and not any(not (i + len(span) <= s["start"] or i >= s["end"]) for s in out):
            out.append({"start": i, "end": i + len(span), "type": kind})
    return sorted(out, key=lambda s: s["start"])


def _signature():
    h = hashlib.md5()
    for n in ("messages.csv", "hard_set.csv", "hard_set_2.csv"):
        h.update((ROOT / "data" / "synthetic" / n).read_bytes())
    h.update((Path(__file__).parent / "features.py").read_bytes())
    return h.hexdigest()


def _build():
    syn = load_synthetic()
    hard = pd.concat([load_hard(), pd.read_csv(ROOT / "data" / "synthetic" / "hard_set_2.csv").fillna("")], ignore_index=True)
    y = (syn.label == "scam").astype(int).values
    texts = syn.text.tolist()
    oof = np.zeros(len(syn))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(texts, syn.category):
        m = Improved().fit([texts[i] for i in tr], y[tr], syn.category.values[tr])
        oof[te] = m.proba([texts[i] for i in te])
    full = Improved().fit(texts, y, syn.category.values)
    hp = full.proba(hard.text.tolist())

    cards = []
    for df, probs, src in ((syn, oof, "synthetic"), (hard, hp, "hard")):
        for i, r in df.reset_index(drop=True).iterrows():
            spans = _spans_from_column(r.text, r.red_flags) if r.red_flags else (
                [{"start": s["start"], "end": s["end"], "type": s["type"]} for s in find_spans(r.text)] if r.label == "scam" else [])
            cards.append({"id": r.id, "channel": r.channel, "text": r.text, "label": r.label, "category": r.category,
                          "flags": spans, "p_scam": round(float(probs[i]), 4), "source": src})
    return cards


def get_pool():
    global _pool
    with _lock:
        if _pool is not None:
            return _pool
        sig = _signature()
        if CACHE.exists():
            d = json.loads(CACHE.read_text(encoding="utf-8"))
            if d.get("sig") == sig:
                _pool = d["cards"]
                return _pool
        cards = _build()
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps({"sig": sig, "cards": cards}), encoding="utf-8")
        _pool = cards
        return _pool


def _ai_block(card):
    """What the detector thought, plus a plain-language comparison line material."""
    p = card["p_scam"]
    v = _verdict(p)
    truth_scam = card["label"] == "scam"
    conf = p if v == "scam" else (1 - p) if v == "legit" else max(p, 1 - p)
    ai_right = (v == "scam") == truth_scam if v != "unsure" else None
    return {"verdict": v, "p_scam": p, "confidence": conf, "correct": ai_right}


def _tricky(card, ai):
    """Why this card is hard, in plain words, for when the AI was unsure or wrong."""
    scam = card["label"] == "scam"
    if scam:
        kinds = {f["type"] for f in card["flags"]}
        if "link" not in kinds and not ({"threat", "urgency"} & kinds):
            return "It has no suspicious link and no obvious threat, so it leans on trust and a believable story instead."
        return "Its wording is different from the scams we've seen most, so the warning signs are easier to miss."
    return ("It has some pressure or money talk, which scams use too. But nothing in it pushes you to click, pay or share a "
            "secret code with a stranger.")


def public_card(card):
    ai = _ai_block(card)
    scam = card["label"] == "scam"
    cat = card["category"]
    info = TAXONOMY.get(cat)
    return {
        "id": card["id"], "channel": card["channel"], "text": card["text"], "label": card["label"], "category": cat,
        "category_title": info["title"] if info else None,
        "explanation": info["what"] if scam and info else LEGIT_WHY.get(cat, ""),
        "tip": info["steps"][0] if scam and info else None,
        "habit": HABITS.get(cat) if scam else FALSE_ALARM_HABIT,
        "flags": card["flags"] if scam else [],
        "ai": ai,
        "tricky": _tricky(card, ai) if ai["verdict"] == "unsure" or ai["correct"] is False else None,
    }


def pick_next(stats, seen_ids, rng=random):
    """Adaptive: weight each category by how often THIS user has missed it, then pick an unseen card."""
    pool = get_pool()
    seen = set(seen_ids)
    by_cat = {}
    for c in pool:
        by_cat.setdefault(c["category"], []).append(c)
    weights, reasons = {}, {}
    for cat, cards in by_cat.items():
        fresh = [c for c in cards if c["id"] not in seen]
        if not fresh:
            continue
        s = stats.get(cat, {})
        n, miss = s.get("seen", 0), s.get("missed", 0)
        rate = (miss + 0.25) / (n + 1)
        weights[cat] = 1 + 12 * rate * rate  # squared: repeated misses pull hard, unseen stays modest
        if n >= 2 and miss / n >= 0.5:
            reasons[cat] = f"You've missed {miss} of {n} in this group, so here's more practice."
    if not weights:  # exhausted everything: start over
        return pick_next(stats, [], rng)
    cat = rng.choices(list(weights), weights=list(weights.values()))[0]
    # within a category, prefer hard-set cards once the user has basics down? keep it simple: random unseen
    card = rng.choice([c for c in by_cat[cat] if c["id"] not in seen])
    out = public_card(card)
    out["focus_reason"] = reasons.get(cat)
    return out
