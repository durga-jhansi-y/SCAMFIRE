"""Baseline (TF-IDF + LR) and improved (TF-IDF + hand-built scam signals, calibrated) detectors.

The improved detector returns an honest verdict: "scam", "legit", or "unsure". Unsure cases set
needs_agent=True so the Nemotron agent (milestone 5) can take a deeper look.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from features import featurize, find_spans

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(__file__).resolve().parent / "models" / "detector.joblib"
BLEND = 0.5  # weight on the text model vs the signals-only model
# Asymmetric on purpose: telling someone a scam is 'safe' is the worst error, so we only say
# 'legit' when very sure. Everything in between is 'unsure'.
SCAM_HI, SCAM_LO = 0.70, 0.10


def load_synthetic():
    return pd.read_csv(ROOT / "data" / "synthetic" / "messages.csv").fillna("")


def load_hard():
    return pd.read_csv(ROOT / "data" / "synthetic" / "hard_set.csv").fillna("")


class Baseline:
    """Plain TF-IDF + logistic regression: the thing we have to beat."""

    def fit(self, texts, y):
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)
        self.clf = LogisticRegression(max_iter=2000, C=4)
        self.clf.fit(self.vec.fit_transform(texts), y)
        return self

    def proba(self, texts):
        return self.clf.predict_proba(self.vec.transform(texts))[:, 1]


class Improved:
    def __init__(self, calibrate=True):
        self.calibrate = calibrate

    def _X(self, texts, fit=False):
        F = np.array([featurize(t) for t in texts], dtype=float)
        if fit:
            self.word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)
            self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=3, max_features=20000)
            self.scaler = StandardScaler().fit(F)
            W, C = self.word.fit_transform(texts), self.char.fit_transform(texts)
        else:
            W, C = self.word.transform(texts), self.char.transform(texts)
        # hand features are up-weighted so they matter when wording is unfamiliar
        self._F = self.scaler.transform(F)
        return hstack([W, C * 0.6, csr_matrix(self._F * 0.5)]).tocsr()

    def fit(self, texts, y, cats):
        X = self._X(texts, fit=True)
        base = LogisticRegression(max_iter=3000, C=1.0)
        self.clf = CalibratedClassifierCV(base, method="sigmoid", cv=5) if self.calibrate else base
        self.clf.fit(X, y)
        self.cat_clf = LogisticRegression(max_iter=3000, C=4).fit(X, cats)
        # Signals-only model: sees urgency/link/payment/etc. but not the words, so it keeps working
        # when a scammer rewords the message. Blended with the text model.
        Fs = self.scaler.transform(np.array([featurize(t) for t in texts], dtype=float))
        fb = LogisticRegression(max_iter=3000, C=0.5)
        self.feat_clf = CalibratedClassifierCV(fb, method="sigmoid", cv=5) if self.calibrate else fb
        self.feat_clf.fit(Fs, y)
        return self

    def _blend(self, texts):
        X = self._X(texts)
        p_text = self.clf.predict_proba(X)[:, 1]
        p_sig = self.feat_clf.predict_proba(self._F)[:, 1]
        return X, BLEND * p_text + (1 - BLEND) * p_sig

    def proba(self, texts):
        return self._blend(texts)[1]

    def analyze(self, text):
        X, pb = self._blend([text])
        p = float(pb[0])
        cp = self.cat_clf.predict_proba(X)[0]
        order = np.argsort(cp)[::-1]
        if p >= SCAM_HI:
            verdict, conf = "scam", p
        elif p <= SCAM_LO:
            verdict, conf = "legit", 1 - p
        else:
            verdict, conf = "unsure", max(p, 1 - p)
        # category: best-ranked category consistent with the verdict
        cats = self.cat_clf.classes_
        pick = [c for c in cats[order] if (c.startswith("legit_") == (verdict == "legit"))] or list(cats[order])
        category = pick[0] if verdict != "unsure" else cats[order[0]]
        return {
            "p_scam": round(p, 4), "verdict": verdict, "confidence": round(float(conf), 4),
            "category": category, "category_confidence": round(float(cp[list(cats).index(category)]), 4),
            "red_flags": find_spans(text), "needs_agent": verdict == "unsure",
        }

    def save(self, path=MODEL_PATH):
        path.parent.mkdir(exist_ok=True)
        joblib.dump(self, path)


def load_model():
    return joblib.load(MODEL_PATH)


if __name__ == "__main__":
    df = load_synthetic()
    m = Improved().fit(df.text.tolist(), (df.label == "scam").astype(int).values, df.category.values)
    m.save()
    print("trained on", len(df), "messages ->", MODEL_PATH)
