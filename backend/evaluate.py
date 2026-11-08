"""Evaluate baseline vs improved detector. Writes eval_results.md and backend/eval_results.json.

Two test sets:
  * held-out 20% of the synthetic data (same templates -> optimistic)
  * hand-written "hard set" in new wording (what we'd expect on unfamiliar messages -> honest)
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from detector import SCAM_HI, SCAM_LO, Baseline, Improved, load_hard, load_synthetic
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def ece(p, y, bins=5):
    """Expected calibration error on the P(scam) axis, plus per-bin table."""
    edges = np.linspace(0, 1, bins + 1)
    table, total = [], 0.0
    for i in range(bins):
        m = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if m.sum():
            conf, acc = p[m].mean(), y[m].mean()
            total += m.sum() / len(p) * abs(conf - acc)
            table.append((f"{edges[i]:.1f}-{edges[i+1]:.1f}", int(m.sum()), round(float(conf), 2), round(float(acc), 2)))
    return float(total), table


def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    pr, rc, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"precision": pr, "recall": rc, "f1": f1, "acc": float((pred == y).mean()),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "ece": ece(p, y)[0]}


def per_cat(df, p):
    pred = (p >= 0.5).astype(int)
    y = (df.label == "scam").astype(int).values
    out = {}
    for c, g in df.groupby("category"):
        out[c] = (float((pred[g.index] == y[g.index]).mean()), len(g))
    return out


def abstain_stats(p, y):
    """With the 'unsure' band: how often we commit, and how accurate we are when we do."""
    commit = (p >= SCAM_HI) | (p <= SCAM_LO)
    pred = (p >= 0.5).astype(int)
    acc = float((pred[commit] == y[commit]).mean()) if commit.any() else float("nan")
    return float(commit.mean()), acc, int(((p <= SCAM_LO) & (y == 1)).sum()), int(((p >= SCAM_HI) & (y == 0)).sum()), int(((p > SCAM_LO) & (p < SCAM_HI)).sum())


def fit_models(tr):
    y = (tr.label == "scam").astype(int).values
    t = tr.text.tolist()
    return (Baseline().fit(t, y),
            Improved(calibrate=False).fit(t, y, tr.category.values),
            Improved(calibrate=True).fit(t, y, tr.category.values))


def md_table(headers, rows):
    s = "| " + " | ".join(headers) + " |\n|" + "---|" * len(headers) + "\n"
    return s + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows) + "\n"


def main():
    syn = load_synthetic()
    hard = load_hard()
    tr, te = train_test_split(syn, test_size=0.2, stratify=syn.category, random_state=42)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    base, imp_raw, imp = fit_models(tr)

    hard2 = pd.read_csv(ROOT / "data" / "synthetic" / "hard_set_2.csv").fillna("")
    sets = {"Held-out synthetic (n=%d)" % len(te): te,
            "Hard set 1, new wording (n=%d; used to guide signal lexicons, so no longer fully unseen)" % len(hard): hard,
            "Hard set 2, fresh hold-out (n=%d; written after the lexicons were frozen)" % len(hard2): hard2}
    models = {"Baseline (TF-IDF + LR)": base, "Ours, uncalibrated": imp_raw, "Ours (calibrated)": imp}
    out = ["# Evaluation results\n",
           f"_Generated {date.today()} by `backend/evaluate.py`. Train: {len(tr)} synthetic messages (80% split, stratified by category, seed 42)._\n",
           "**Read this honestly:** the synthetic data is template-generated, so the held-out split is optimistic "
           "(test messages share templates with training messages). The **hard set** (hand-written, new wording, "
           "includes legit messages that *look* scary) is the better estimate of real-world behavior, and it is small. "
           "No claim here applies to real T-Mobile traffic.\n"]
    results = {}
    for sname, df in sets.items():
        y = (df.label == "scam").astype(int).values
        out.append(f"\n## {sname}\n")
        rows, cms = [], []
        results[sname] = {}
        for mname, m in models.items():
            p = m.proba(df.text.tolist())
            r = metrics(y, p)
            results[sname][mname] = {**r, "p": p.tolist()}
            rows.append([mname, f"{r['precision']:.3f}", f"{r['recall']:.3f}", f"{r['f1']:.3f}", f"{r['acc']:.3f}", f"{r['ece']:.3f}"])
            cms.append((mname, r))
        out.append(md_table(["Model", "Precision", "Recall", "F1", "Accuracy", "ECE (lower=better)"], rows))
        out.append("\nConfusion matrices (scam = positive):\n")
        out.append(md_table(["Model", "TN", "FP", "FN", "TP"], [[n, r["tn"], r["fp"], r["fn"], r["tp"]] for n, r in cms]))
        pc_b, pc_i = per_cat(df, np.array(results[sname]["Baseline (TF-IDF + LR)"]["p"])), per_cat(df, np.array(results[sname]["Ours (calibrated)"]["p"]))
        out.append("\nPer-category accuracy:\n")
        out.append(md_table(["Category", "n", "Baseline", "Ours"], [[c, pc_b[c][1], f"{pc_b[c][0]:.2f}", f"{pc_i[c][0]:.2f}"] for c in sorted(pc_b)]))
        p_i = np.array(results[sname]["Ours (calibrated)"]["p"])
        cov, acc, bad_safe, bad_scam, n_uns = abstain_stats(p_i, y)
        pb = np.array(results[sname]["Baseline (TF-IDF + LR)"]["p"])
        out.append(f"\n**Three-way verdict** (safe if P(scam) <= {SCAM_LO}, scam if >= {SCAM_HI}, otherwise *unsure*): we commit on {cov:.0%} of messages "
                   f"and are {acc:.0%} accurate on those; {n_uns} of {len(y)} go to *unsure* (routed to the Nemotron agent). "
                   f"**Scams confidently called safe: {bad_safe}** (baseline at 0.5 threshold: {int(((pb < 0.5) & (y == 1)).sum())}). "
                   f"Legit messages confidently called scam: {bad_scam}.\n")
        _, tbl = ece(p_i, y)
        out.append("\nCalibration (ours, calibrated): when we say P(scam) is in a bin, how often is it really a scam?\n")
        out.append(md_table(["P(scam) bin", "n", "Avg predicted", "Actual scam rate"], tbl))

    Path(ROOT / "eval_results.md").write_text("\n".join(out), encoding="utf-8")
    summary = {s: {m: {k: v for k, v in r.items() if k != "p"} for m, r in d.items()} for s, d in results.items()}
    Path(Path(__file__).parent / "eval_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Final production model: train on everything.
    Improved().fit(syn.text.tolist(), (syn.label == "scam").astype(int).values, syn.category.values).save()
    print("\n".join(out))


if __name__ == "__main__":
    main()
