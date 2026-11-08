"""Local PII redaction. Runs BEFORE any text can reach an LLM. Regex + cue-word heuristics,
no network, no model. Honest limits: it can miss unusual names/addresses, so the UI shows the
redacted text to the user and the agent only ever sees that version."""
import re

_NAME = r"[A-Z][a-z]{1,15}(?: [A-Z][a-z]{1,15})?"
# (label, compiled regex, group to replace or 0 for whole match). Order matters: specific first.
RULES = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), 0),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b"), 0),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)"), 0),
    ("ACCOUNT", re.compile(r"\b(?:account|acct|a/c|routing)[^\d\n]{0,15}(\d{6,})", re.I), 1),
    ("ACCOUNT", re.compile(r"\bending (?:in )?(\d{4})\b", re.I), 1),
    ("CODE", re.compile(r"\b(?:code|passcode|pin)(?: is|:)?\s*(\d{4,8})\b", re.I), 1),
    ("CODE", re.compile(r"\b(?:G-)(\d{6})\b"), 1),
    ("ADDRESS", re.compile(r"\b\d{1,5} [A-Z][\w.]*(?: [A-Z][\w.]*){0,3} (?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Ct|Court|Way)\b\.?"), 0),
    ("ZIP", re.compile(r"(?<![\d$,.])\b\d{5}(?:-\d{4})?\b(?!\d|[,.]\d|%)"), 0),
    # Names: only after cues (greeting, "this is", "it's", signature). Avoids redacting brands/places.
    ("NAME", re.compile(r"\b(?:Hi|Hello|Hey|Dear|Thanks|Thank you),? (" + _NAME + r")"), 1),
    ("NAME", re.compile(r"\b(?:[Tt]his is|[Ii]t'?s|[Mm]y name is|[Ii]'m|[Ii] am) (" + _NAME + r")(?=[,.!\s]|$)"), 1),
    ("NAME", re.compile(r"(?m)^[-–—] ?(" + _NAME + r")\s*$"), 1),
]
# words that look like names after "this is"/"I'm" but aren't
NOT_NAMES = {"The", "Your", "Our", "Not", "Sorry", "Going", "Calling", "Here", "Just", "Now", "From", "Apple", "Microsoft",
             "Mom", "Dad", "Grandma", "Grandpa", "Officer", "Social Security", "Internal Revenue", "Norton", "Chase", "Uber"}


def redact_pii(text: str):
    """Return (redacted_text, counts) e.g. ("Call [PHONE]", {"PHONE": 1})."""
    spans = []  # (start, end, label)
    for label, rx, grp in RULES:
        for m in rx.finditer(text):
            s, e = m.span(grp)
            if label == "NAME" and m.group(grp).split()[0] in NOT_NAMES:
                continue
            if label == "CARD" and len(re.sub(r"\D", "", m.group(0))) < 13:
                continue
            spans.append((s, e, label))
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    kept, last = [], -1
    for s, e, label in spans:
        if s >= last:
            kept.append((s, e, label))
            last = e
    out, pos, counts = [], 0, {}
    for s, e, label in kept:
        out.append(text[pos:s])
        out.append(f"[{label}]")
        counts[label] = counts.get(label, 0) + 1
        pos = e
    out.append(text[pos:])
    return "".join(out), counts


if __name__ == "__main__":
    demo = ("Hi Maria, this is Carlos. Call me at (972) 555-0142 or email carlos@example.com. "
            "Card 4111 1111 1111 1111, account number 88213344, SSN 123-45-6789. I live at 412 Oak Street, Dallas 75080. "
            "Your code is 482913. Pay $149.99 at bit.ly/3xK9aQ")
    print(redact_pii(demo))
