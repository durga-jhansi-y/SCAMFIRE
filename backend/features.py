"""Hand-built scam signals. Each lexicon yields highlightable spans, used both as model
features and as the red-flag highlights shown in the UI."""
import re
from urllib.parse import urlparse

FLAGS = {
    "urgency": r"\b(urgent(ly)?|immediately|right away|right now|act now|asap|final (notice|attempt)|within \d+ ?(hours?|hrs?|h|minutes?)|today only|expires? (today|soon|tonight)|limited spots|only \d+ left|before it'?s too late|press 1|call (us |back )?(now|immediately)|need it in an hour|offer ends)\b",
    "threat": r"\b(suspend(ed)?|locked|closed|closure|arrest(ed)?|warrant|legal action|lawsuit|penalt(y|ies)|late fees?|seiz(e|ure)|compromised|hacked|infected|virus|overdue|unpaid|violation|criminal|service will be)\b",
    "payment": r"\b(gift ?cards?|wire( it| transfer| money)?|zelle|western union|bitcoin|usdt|ethereum|crypto(currency)?|bail money|processing fee|redelivery fee|customs fee|pay (now|a|the|just)|deposit (it|just)|send \$?\d[\d,.]*|\$\d[\d,.]*|prepaid (cards?|debit)|(play|itunes|steam|apple|target) cards?|(buy|purchase|read me).{0,25}(cards?|numbers))",
    "credential_request": r"\b(ssn|social security number|last four|pin\b|password|passcode|recovery phrase|seed phrase|card number|bank (info|details|account)|verify your (identity|account|login)|confirm your (login|identity|address|account)|account pin|remote access|send your (id|ssn))\b",
    "impersonation": r"\b(irs|internal revenue|social security administration|treasury|usps|fedex|ups|dhl|microsoft|apple support|norton|amazon|paypal|t-mobile|bank of america|chase|wells fargo|citi|fraud department|security team|ntta|military engineer)\b",
    "prize": r"\b(you'?ve? (been chosen|won)|congratulations|lucky winner|free (iphone|gift|phone)|guaranteed( \d+%)? returns?|risk[- ]free|\d{2,3}% returns?|double it|lottery)\b",
    "secrecy": r"\b(don'?t tell (anyone|mom|dad)|please don'?t tell|keep this (just )?between us|just between us|don'?t call anyone)\b",
    "offplatform": r"(telegram|whatsapp|signal app|move (this|our chat)|text me at|link in bio)",
    "too_good": r"(no (experience|interview)( needed| required)?|\$[\d,]+ ?/ ?(week|wk|hr|hour|day)|turned \$[\d,]+ into|work from home|flexible,? no|selected for a|you'?ve been selected|seem so genuine)",
    "new_number": r"\b(new number|new phone|lost my phone|phone (broke|is dead)|wrong number)\b",
}
FLAG_RE = {k: re.compile(v, re.I) for k, v in FLAGS.items()}

URL_RE = re.compile(r"(https?://\S+|\b[\w-]+(\.[\w-]+)*\.(com|net|org|info|top|xyz|click|cc|co|support|ly|link)(/\S*)?)", re.I)
SHORTENERS = ("bit.ly", "tinyurl.com", "cutt.ly", "t.co", "goo.gl", "is.gd", "ow.ly")
BAD_TLDS = (".top", ".xyz", ".click", ".cc", ".info", ".support", ".link", ".co")
TRUSTED = ("t-mobile.com", "usps.com", "ups.com", "fedex.com", "chase.com", "google.com", "amazon.com")
SAFE_PHRASES = re.compile(r"(never (share|ask|call|include)|we will never|didn'?t request this|ignore this message|no action needed|reply (c|yes|no|stop)\b|number on the back of your card|in the .{0,20}app|dial 611)", re.I)
OTP_RE = re.compile(r"\b(verification code|one-time passcode|login code|is your .{0,15}code)\b", re.I)
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[ -]?\d{3}-\d{4}\b")
# domain that contains a brand but isn't the brand's real domain (e.g. chase-secure-alert.co)
BRANDS = ("chase", "t-mobile", "usps", "irs", "paypal", "amazon", "fedex", "ups", "wellsfargo", "apple")

FEATURE_NAMES = (list(FLAGS) + ["n_links", "short_url", "bad_tld", "trusted_domain", "lookalike_domain",
                                "safe_phrases", "otp_pattern", "phone_in_text", "exclaim", "caps_ratio"])


def _domain(u):
    u = u if u.startswith("http") else "http://" + u
    return (urlparse(u).hostname or "").lower()


def find_spans(text):
    """Return [{start,end,type,text}] sorted, overlaps resolved (earlier/longer wins)."""
    spans = []
    for kind, rx in FLAG_RE.items():
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), kind))
    for m in URL_RE.finditer(text):
        d = _domain(m.group(0))
        if d.endswith(TRUSTED) and not any(b in d.split(".")[0] and not d.endswith(TRUSTED) for b in BRANDS):
            continue
        spans.append((m.start(), m.end(), "link"))
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    out, last = [], -1
    for s, e, k in spans:
        if s >= last:
            out.append({"start": s, "end": e, "type": k, "text": text[s:e]})
            last = e
    return out


def featurize(text):
    f = {k: len(rx.findall(text)) for k, rx in FLAG_RE.items()}
    urls = [m.group(0) for m in URL_RE.finditer(text)]
    doms = [_domain(u) for u in urls]
    f["n_links"] = len(urls)
    f["short_url"] = int(any(d in SHORTENERS for d in doms))
    f["bad_tld"] = int(any(d.endswith(BAD_TLDS) and not d.endswith(TRUSTED) for d in doms))
    f["trusted_domain"] = int(any(d.endswith(TRUSTED) for d in doms))
    f["lookalike_domain"] = int(any(any(b in d for b in BRANDS) and not d.endswith(TRUSTED) for d in doms))
    f["safe_phrases"] = len(SAFE_PHRASES.findall(text))
    f["otp_pattern"] = int(bool(OTP_RE.search(text)))
    f["phone_in_text"] = int(bool(PHONE_RE.search(text)))
    f["exclaim"] = text.count("!")
    letters = [c for c in text if c.isalpha()]
    f["caps_ratio"] = sum(c.isupper() for c in letters) / max(1, len(letters))
    # cap counts so one feature can't dominate
    return [min(f[n], 4) if n != "caps_ratio" else f[n] for n in FEATURE_NAMES]
