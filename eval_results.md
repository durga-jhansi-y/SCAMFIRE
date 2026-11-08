# Evaluation results

_Generated 2026-11-07 by `backend/evaluate.py`. Train: 400 synthetic messages (80% split, stratified by category, seed 42)._

**Read this honestly:** the synthetic data is template-generated, so the held-out split is optimistic (test messages share templates with training messages). The **hard set** (hand-written, new wording, includes legit messages that *look* scary) is the better estimate of real-world behavior, and it is small. No claim here applies to real T-Mobile traffic.


## Held-out synthetic (n=100)

| Model | Precision | Recall | F1 | Accuracy | ECE (lower=better) |
|---|---|---|---|---|---|
| Baseline (TF-IDF + LR) | 1.000 | 1.000 | 1.000 | 1.000 | 0.096 |
| Ours, uncalibrated | 1.000 | 0.948 | 0.973 | 0.970 | 0.049 |
| Ours (calibrated) | 1.000 | 0.948 | 0.973 | 0.970 | 0.054 |


Confusion matrices (scam = positive):

| Model | TN | FP | FN | TP |
|---|---|---|---|---|
| Baseline (TF-IDF + LR) | 42 | 0 | 0 | 58 |
| Ours, uncalibrated | 42 | 0 | 3 | 55 |
| Ours (calibrated) | 42 | 0 | 3 | 55 |


Per-category accuracy:

| Category | n | Baseline | Ours |
|---|---|---|---|
| bank_account_locked | 6 | 1.00 | 1.00 |
| carrier_sim_swap | 5 | 1.00 | 1.00 |
| crypto_investment | 5 | 1.00 | 1.00 |
| family_emergency | 5 | 1.00 | 1.00 |
| irs_government | 5 | 1.00 | 1.00 |
| job_offer | 5 | 1.00 | 1.00 |
| legit_2fa | 7 | 1.00 | 1.00 |
| legit_appointment | 7 | 1.00 | 1.00 |
| legit_bank_alert | 7 | 1.00 | 1.00 |
| legit_carrier | 7 | 1.00 | 1.00 |
| legit_delivery | 7 | 1.00 | 1.00 |
| legit_friend | 7 | 1.00 | 1.00 |
| package_delivery | 6 | 1.00 | 1.00 |
| prize_lottery | 5 | 1.00 | 1.00 |
| romance | 5 | 1.00 | 0.40 |
| tech_support | 5 | 1.00 | 1.00 |
| toll_fine | 6 | 1.00 | 1.00 |


**Three-way verdict** (safe if P(scam) <= 0.1, scam if >= 0.7, otherwise *unsure*): we commit on 94% of messages and are 100% accurate on those; 6 of 100 go to *unsure* (routed to the Nemotron agent). **Scams confidently called safe: 0** (baseline at 0.5 threshold: 0). Legit messages confidently called scam: 0.


Calibration (ours, calibrated): when we say P(scam) is in a bin, how often is it really a scam?

| P(scam) bin | n | Avg predicted | Actual scam rate |
|---|---|---|---|
| 0.0-0.2 | 41 | 0.05 | 0.0 |
| 0.2-0.4 | 4 | 0.35 | 0.75 |
| 0.6-0.8 | 3 | 0.75 | 1.0 |
| 0.8-1.0 | 52 | 0.98 | 1.0 |


## Hard set 1, new wording (n=24; used to guide signal lexicons, so no longer fully unseen)

| Model | Precision | Recall | F1 | Accuracy | ECE (lower=better) |
|---|---|---|---|---|---|
| Baseline (TF-IDF + LR) | 0.688 | 0.917 | 0.786 | 0.750 | 0.112 |
| Ours, uncalibrated | 0.750 | 0.500 | 0.600 | 0.667 | 0.157 |
| Ours (calibrated) | 0.750 | 0.500 | 0.600 | 0.667 | 0.152 |


Confusion matrices (scam = positive):

| Model | TN | FP | FN | TP |
|---|---|---|---|---|
| Baseline (TF-IDF + LR) | 7 | 5 | 1 | 11 |
| Ours, uncalibrated | 10 | 2 | 6 | 6 |
| Ours (calibrated) | 10 | 2 | 6 | 6 |


Per-category accuracy:

| Category | n | Baseline | Ours |
|---|---|---|---|
| bank_account_locked | 1 | 1.00 | 1.00 |
| carrier_sim_swap | 1 | 1.00 | 0.00 |
| crypto_investment | 1 | 0.00 | 0.00 |
| family_emergency | 2 | 1.00 | 0.50 |
| irs_government | 1 | 1.00 | 1.00 |
| job_offer | 1 | 1.00 | 0.00 |
| legit_2fa | 1 | 1.00 | 1.00 |
| legit_appointment | 3 | 0.33 | 0.67 |
| legit_bank_alert | 2 | 0.50 | 0.50 |
| legit_carrier | 1 | 1.00 | 1.00 |
| legit_delivery | 2 | 1.00 | 1.00 |
| legit_friend | 3 | 0.33 | 1.00 |
| package_delivery | 1 | 1.00 | 1.00 |
| prize_lottery | 1 | 1.00 | 1.00 |
| romance | 1 | 1.00 | 0.00 |
| tech_support | 1 | 1.00 | 0.00 |
| toll_fine | 1 | 1.00 | 1.00 |


**Three-way verdict** (safe if P(scam) <= 0.1, scam if >= 0.7, otherwise *unsure*): we commit on 46% of messages and are 91% accurate on those; 13 of 24 go to *unsure* (routed to the Nemotron agent). **Scams confidently called safe: 0** (baseline at 0.5 threshold: 1). Legit messages confidently called scam: 1.


Calibration (ours, calibrated): when we say P(scam) is in a bin, how often is it really a scam?

| P(scam) bin | n | Avg predicted | Actual scam rate |
|---|---|---|---|
| 0.0-0.2 | 11 | 0.1 | 0.36 |
| 0.2-0.4 | 4 | 0.27 | 0.25 |
| 0.4-0.6 | 3 | 0.53 | 0.67 |
| 0.8-1.0 | 6 | 0.88 | 0.83 |


## Hard set 2, fresh hold-out (n=16; written after the lexicons were frozen)

| Model | Precision | Recall | F1 | Accuracy | ECE (lower=better) |
|---|---|---|---|---|---|
| Baseline (TF-IDF + LR) | 0.800 | 1.000 | 0.889 | 0.875 | 0.166 |
| Ours, uncalibrated | 1.000 | 0.750 | 0.857 | 0.875 | 0.120 |
| Ours (calibrated) | 1.000 | 0.750 | 0.857 | 0.875 | 0.116 |


Confusion matrices (scam = positive):

| Model | TN | FP | FN | TP |
|---|---|---|---|---|
| Baseline (TF-IDF + LR) | 6 | 2 | 0 | 8 |
| Ours, uncalibrated | 8 | 0 | 2 | 6 |
| Ours (calibrated) | 8 | 0 | 2 | 6 |


Per-category accuracy:

| Category | n | Baseline | Ours |
|---|---|---|---|
| bank_account_locked | 1 | 1.00 | 1.00 |
| carrier_sim_swap | 1 | 1.00 | 1.00 |
| crypto_investment | 1 | 1.00 | 0.00 |
| family_emergency | 1 | 1.00 | 0.00 |
| irs_government | 1 | 1.00 | 1.00 |
| legit_2fa | 1 | 1.00 | 1.00 |
| legit_appointment | 2 | 1.00 | 1.00 |
| legit_bank_alert | 1 | 1.00 | 1.00 |
| legit_carrier | 1 | 1.00 | 1.00 |
| legit_delivery | 1 | 1.00 | 1.00 |
| legit_friend | 2 | 0.00 | 1.00 |
| package_delivery | 1 | 1.00 | 1.00 |
| prize_lottery | 1 | 1.00 | 1.00 |
| tech_support | 1 | 1.00 | 1.00 |


**Three-way verdict** (safe if P(scam) <= 0.1, scam if >= 0.7, otherwise *unsure*): we commit on 69% of messages and are 100% accurate on those; 5 of 16 go to *unsure* (routed to the Nemotron agent). **Scams confidently called safe: 0** (baseline at 0.5 threshold: 0). Legit messages confidently called scam: 0.


Calibration (ours, calibrated): when we say P(scam) is in a bin, how often is it really a scam?

| P(scam) bin | n | Avg predicted | Actual scam rate |
|---|---|---|---|
| 0.0-0.2 | 9 | 0.09 | 0.11 |
| 0.2-0.4 | 1 | 0.39 | 1.0 |
| 0.4-0.6 | 1 | 0.52 | 1.0 |
| 0.6-0.8 | 2 | 0.76 | 1.0 |
| 0.8-1.0 | 3 | 0.97 | 1.0 |
