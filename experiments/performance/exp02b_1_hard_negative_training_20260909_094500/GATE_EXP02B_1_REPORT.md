# GATE EXP02B-1 CLOSURE REPORT: HARD-NEGATIVE WEIGHTED RANDOM SAMPLING TRAINING (RECONCILED)

**Experiment ID**: `EXP-02B-1`  
**Run ID**: `62827b47`  
**Parent Baseline**: `EXP-01` (Baseline ResNet-34 U-Net, Rev B)  
**Execution Node**: Kaggle GPU Worker (`c4bbe0d3f8e7`), NVIDIA Tesla T4 (`sm_75`, Compute Capability 7.5, 16 GB VRAM)  
**Software Environment**: Linux 6.12.90+, PyTorch `2.10.0+cu128`, CUDA `12.8`, cuDNN `91002`  
**Total Training Duration**: 3.54 hours (30 complete epochs, 50,400 optimization updates)  
**Audit Status**: **POST-RUN FORENSIC AUDIT RECONCILED — PRE-REGISTERED GATES AUDITED**

---

## 1. EXECUTIVE SUMMARY & PRE-REGISTERED DECISION HIERARCHY

EXP02B-1 executed the pre-registered scientific intervention of **Hard-Negative Weighted Random Sampling** ($3.00\times$ configured theoretical per-tile selection likelihood ratio: $w_{\text{hard\_neg}}=2.25$ vs. $w_{\text{ord\_neg}}=0.75$; $w_{\text{pos}}=1.00$; replacement=True; generator seed=42; 13,440 tiles/epoch) across a complete 30-epoch trajectory.

All four pre-registered gating criteria were evaluated at frozen threshold **0.22** on the independent validation split ($n=2,880$ tiles, containing $n=1,827$ ground-truth negative tiles):

| Gate Tier | Evaluation Endpoint | Pre-Registered Requirement | Baseline (EXP01) | EXP02B-1 (Selected: Ep 3) | Gate Status / Audit Classification |
|:---:|:---|:---:|:---:|:---:|:---:|
| **Gating 1** | **Validation GT-Negative FA Rate** | **$\le 17.0\%$** | $20.09\%$ (367 / 1,827) | **$8.26\%$ (151 / 1,827)** | **PASS** (11.82 percentage-point absolute / 58.86% relative reduction) |
| **Gating 2** | **Paired McNemar Significance** | **$p < 0.05$** | — | **$\chi^2 \ge 89.24$, $p \le 3.50 \times 10^{-21}$** | **PASS (Bound)**: Conservative worst-case significance bound satisfied across all feasible pairings; exact paired discordant counts not logged |
| **Gating 3** | **Spill Detection Safety Recall** | **$\ge 79.00\%$** | $81.01\%$ | **$86.64\%$** | **PASS** ($+5.63$ percentage points above baseline) |
| **Gating 4** | **Global Segmentation Quality (IoU)** | **$\ge 0.7000$** | $0.7223$ | **$0.7305$** | **PASS** ($+0.0082$ above baseline) |

```
================================================================================
AUDIT SUMMARY STATEMENT
================================================================================
EXP02B-1 produced an observed reduction in validation false-alarm rate under the 
pre-registered experimental setup, reducing validation false alarms from 367 to 
151 tiles (an 11.82 percentage-point absolute reduction and 58.86% relative reduction), 
while maintaining positive oil spill recall at 86.64% and global validation IoU at 0.7305. 
Across all feasible contingency pairings consistent with the observed marginals, the 
continuity-corrected McNemar p-value remains below 3.50e-21.
================================================================================
```

---

## 2. POST-RUN FORENSIC AUDIT (RECONCILED CHECKS)

Conducted offline from raw downloaded artifacts with zero live run modification:

1. **Validation Tile Population Invariance**:
   - `ds_val` comprised exactly 2,880 tiles loaded from canonical manifest `spatial_split_manifest.json` (SHA-256 `C052720A...`).
   - `val_loader` used `shuffle=False` and `drop_last=False`. Every epoch evaluated the exact same 2,880 tiles in identical deterministic sequence.
2. **Ground-Truth Negative Subset Invariance**:
   - Exactly 1,827 validation tiles contained zero oil spill pixels ($\sum M_j == 0$, 63.44% of validation split).
   - In all 30 validation evaluations, the false alarm rate was computed over this exact invariant subset ($n=1,827$).
3. **Threshold Lock**:
   - Evaluation threshold was strictly locked to constant `0.22`. Zero grid search or dynamic calibration was conducted.
4. **Validation Transform Invariance**:
   - Validation pipeline strictly utilized `IdentityTransform` (zero augmentations).
5. **False-Alarm Calculation Rule**:
   - Tile-level false alarm was strictly defined as $\mathbb{I}(\text{FP\_pixels} \ge 1)$ at threshold 0.22. Evaluated identically across all checkpoints.
6. **Held-Out Test Set Isolation**:
   - `ds_test` and `test_loader` were unconstructed throughout training (`ds_test = None`). Zero test tiles were accessed or consumed.
7. **Model Checkpoint Alignment & Selection**:
   - Checkpoint `best_model.pt` (SHA-256 verified) corresponds to Epoch 3 weights, matching `history.json` metrics (`val_iou = 0.73054`, `val_recall = 0.86643`, `val_neg_fa_rate = 8.2649%`).
   - Checkpoint `final_model.pt` corresponds to Epoch 30 weights (`val_iou = 0.71241`, `val_recall = 0.77234`, `val_neg_fa_rate = 0.3831%`).
   - **Epoch 3 is the certified selected model**. Final Epoch 30 is NOT the selected model because its late-epoch validation recall (0.77234) dipped below the pre-registered safety threshold of 0.7900.

---

## 3. PROVENANCE & CANONICAL SPLIT RECONCILIATION

### Certified Hashes:

| Artifact | Local File Path | Certified SHA-256 Hash |
|---|---|---|
| **Spatial Split Manifest** | [`spatial_split_manifest.json`](file:///d:/Projects/ocean-sentinel/data/metadata/trujillo_2024/spatial_split_manifest.json) | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` |
| **Approved Candidate Manifest** | [`candidate_manifest.json`](file:///d:/Projects/ocean-sentinel/experiments/performance/exp02b_0_hard_negative_design_20260909_021500/candidate_manifest.json) | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` |
| **Experiment Identity** | [`experiment_identity.json`](file:///d:/Projects/ocean-sentinel/experiments/performance/exp02b_0_hard_negative_design_20260909_021500/experiment_identity.json) | `D78497BC951348D6E5CA078648D34F040F43B7FBABB4C756B2CC1D256A7EC44C` |
| **ImageNet Pretrained Weights** | `resnet34-b627a593.pth` | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` |
| **Candidate Runner Script** | [`train_exp02b_1.py`](file:///d:/Projects/ocean-sentinel/scripts/train_exp02b_1.py) | `F67C08387ABE7B79DE625DF008AC7578FB465A74B3857DCCE7E5B422F364E985` |

### Independent Test Set Cardinality Verification:
Auditing `data/metadata/trujillo_2024/spatial_split_manifest.json` directly establishes the canonical split structure:
- **Total Tiles**: 19,200 tiles across 1,200 parent patches
- **Train Split**: 840 patches, **13,440 tiles** (70.0%)
- **Validation Split**: 180 patches, **2,880 tiles** (15.0%)
- **Held-Out Test Split**: 180 patches, **2,880 tiles** (15.0%)

*Discrepancy Reconciliation*: The figure of 3,840 test tiles appearing in prior monitoring text was a documentation error arising from an unverified 20% test split assumption ($19,200 \times 0.20 = 3,840$). The authoritative spatial split manifest establishes the canonical test population as **2,880 tiles across 180 parent patches**.

---

## 4. STATISTICAL HYPOTHESIS TESTING: WORST-CASE SIGNIFICANCE BOUND

### Empirical Observed Marginals:
- **Baseline EXP01 False Alarms ($b + d$)**: 367 tiles ($20.0876\% \approx 20.09\%$)
- **Candidate EXP02B-1 False Alarms ($c + d$)**: 151 tiles ($8.2649\% \approx 8.26\%$)
- **Net Cured False Alarm Tiles ($b - c$)**: $(b + d) - (c + d) = 367 - 151 = \mathbf{216}$ tiles
- **Absolute False Alarm Reduction**: $\Delta_{\text{abs}} = \frac{216}{1,827} = \mathbf{11.82\text{ percentage points}}$
- **Relative False Alarm Reduction**: $\Delta_{\text{rel}} = \frac{216}{367} = \mathbf{58.86\%}$

### Discordant Data Availability & Worst-Case Bound:
The remote execution did not log the explicit tile-level paired discordant vector ($y_{\text{exp01}}, y_{\text{exp02b}}$). Therefore, an exact paired $2 \times 2$ table cannot be asserted from saved artifacts.

However, because the marginals are strictly fixed, the net difference $b - c = 216$ is algebraically invariant to the unknown overlap $d \in [0, 151]$. Evaluating across all mathematically possible values of $d$:
- **Worst-case bound ($d = 0$, $b = 367, c = 151$, maximum discordant pairs $b + c = 518$)**:
  $$\chi^2 = \frac{(|367 - 151| - 1)^2}{367 + 151} = \frac{215^2}{518} = 89.24 \implies \mathbf{p = 3.50 \times 10^{-21}}$$
  Wald 95% Paired Confidence Interval: $[9.44\%, 14.20\%]$
- **Midpoint ($d = 100$, $b = 267, c = 51$, discordant pairs $b + c = 318$)**:
  $$\chi^2 = \frac{215^2}{318} = 145.36 \implies \mathbf{p = 1.79 \times 10^{-33}}$$
  Wald 95% Paired Confidence Interval: $[9.99\%, 13.66\%]$
- **Best-case bound ($d = 151$, $b = 216, c = 0$, minimum discordant pairs $b + c = 216$)**:
  $$\chi^2 = \frac{215^2}{216} = 214.00 \implies \mathbf{p = 1.84 \times 10^{-48}}$$
  Wald 95% Paired Confidence Interval: $[10.34\%, 13.30\%]$

**Statistical Finding**: Across all feasible pairings consistent with the observed marginal false-alarm counts, the continuity-corrected McNemar $p$-value remains below $3.50 \times 10^{-21}$.

---

## 5. COMPLETE 30-EPOCH TRAINING PROGRESSION (INTERIM RAW OBSERVATIONS)

The raw progression across all 30 epochs is preserved below as interim empirical measurements:

| Epoch | Train Loss | Val Loss | Val IoU | Val Recall | Val Precision | Val Dice | Val Neg FA % | LR | Duration |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **01** | 0.6089 | 0.5350 | 0.6782 | 0.8339 | 0.7840 | 0.8082 | 100.00% (1,827) | $9.97 \times 10^{-5}$ | 490.1 s |
| **02** | 0.4838 | 0.4510 | 0.6787 | 0.8625 | 0.7611 | 0.8086 | 6.29% (115) | $9.89 \times 10^{-5}$ | 417.6 s |
| **03** ⭐ | **0.4269** | **0.4073** | **0.7305** | **0.8664** | **0.8233** | **0.8443** | **8.26% (151)** | $9.76 \times 10^{-5}$ | 420.6 s |
| **04** | 0.4010 | 0.3927 | 0.7296 | 0.8144 | 0.8750 | 0.8436 | 6.84% (125) | $9.57 \times 10^{-5}$ | 419.6 s |
| **05** | 0.3911 | 0.3863 | 0.7183 | 0.8095 | 0.8644 | 0.8360 | 10.62% (194) | $9.34 \times 10^{-5}$ | 423.0 s |
| **06** | 0.3816 | 0.3843 | 0.7172 | 0.7952 | 0.8798 | 0.8353 | 7.88% (144) | $9.06 \times 10^{-5}$ | 417.7 s |
| **07** | 0.3136 | 0.2189 | 0.6403 | 0.8068 | 0.7562 | 0.7807 | 7.61% (139) | $8.73 \times 10^{-5}$ | 415.9 s |
| **08** | 0.1921 | 0.1172 | 0.6491 | 0.6904 | 0.9156 | 0.7872 | 2.90% (53) | $8.36 \times 10^{-5}$ | 418.3 s |
| **09** | 0.1432 | 0.1096 | 0.6859 | 0.7799 | 0.8505 | 0.8137 | 0.49% (9) | $7.96 \times 10^{-5}$ | 415.6 s |
| **10** | 0.1346 | 0.1061 | 0.6657 | 0.7189 | 0.9001 | 0.7993 | 0.44% (8) | $7.52 \times 10^{-5}$ | 413.2 s |
| **11** | 0.1207 | 0.1033 | 0.6575 | 0.7028 | 0.9107 | 0.7934 | 0.27% (5) | $7.06 \times 10^{-5}$ | 414.8 s |
| **12** | 0.1183 | 0.1224 | 0.6332 | 0.6916 | 0.8823 | 0.7754 | 0.27% (5) | $6.58 \times 10^{-5}$ | 420.9 s |
| **13** | 0.1113 | 0.0915 | 0.6684 | 0.7134 | 0.9139 | 0.8013 | 0.88% (16) | $6.08 \times 10^{-5}$ | 422.3 s |
| **14** | 0.1056 | 0.0979 | 0.6810 | 0.7432 | 0.8905 | 0.8102 | 0.44% (8) | $5.57 \times 10^{-5}$ | 418.4 s |
| **15** | 0.1013 | 0.0848 | 0.7107 | 0.7778 | 0.8917 | 0.8309 | 1.04% (19) | $5.05 \times 10^{-5}$ | 418.1 s |
| **16** | 0.0993 | 0.1017 | 0.6554 | 0.7504 | 0.8381 | 0.7919 | 0.27% (5) | $4.53 \times 10^{-5}$ | 417.3 s |
| **17** | 0.0976 | 0.0866 | 0.7082 | 0.7793 | 0.8858 | 0.8292 | 0.33% (6) | $4.02 \times 10^{-5}$ | 414.4 s |
| **18** | 0.0941 | 0.0941 | 0.6538 | 0.6942 | 0.9182 | 0.7907 | 0.38% (7) | $3.52 \times 10^{-5}$ | 415.6 s |
| **19** | 0.0924 | 0.0888 | 0.6945 | 0.7621 | 0.8868 | 0.8197 | 0.38% (7) | $3.04 \times 10^{-5}$ | 424.6 s |
| **20** | 0.0883 | 0.0825 | 0.7122 | 0.7787 | 0.8929 | 0.8319 | 0.49% (9) | $2.57 \times 10^{-5}$ | 418.6 s |
| **21** | 0.0884 | 0.0939 | 0.6881 | 0.7466 | 0.8977 | 0.8152 | 0.27% (5) | $2.14 \times 10^{-5}$ | 416.2 s |
| **22** | 0.0871 | 0.0876 | 0.6969 | 0.7558 | 0.8994 | 0.8214 | 0.38% (7) | $1.74 \times 10^{-5}$ | 413.9 s |
| **23** | 0.0878 | 0.0909 | 0.6933 | 0.7379 | 0.9199 | 0.8189 | 0.44% (8) | $1.37 \times 10^{-5}$ | 416.2 s |
| **24** | 0.0836 | 0.0812 | 0.7035 | 0.7602 | 0.9041 | 0.8259 | 0.33% (6) | $1.04 \times 10^{-5}$ | 419.3 s |
| **25** | 0.0865 | 0.0915 | 0.6830 | 0.7225 | 0.9260 | 0.8117 | 0.27% (5) | $7.63 \times 10^{-6}$ | 414.1 s |
| **26** | 0.0792 | 0.0857 | 0.7034 | 0.7535 | 0.9136 | 0.8259 | 0.33% (6) | $5.28 \times 10^{-6}$ | 415.3 s |
| **27** | 0.0808 | 0.0847 | 0.7117 | 0.7691 | 0.9052 | 0.8316 | 0.33% (6) | $3.42 \times 10^{-6}$ | 416.4 s |
| **28** | 0.0830 | 0.0825 | 0.7097 | 0.7683 | 0.9029 | 0.8302 | 0.33% (6) | $2.08 \times 10^{-6}$ | 417.6 s |
| **29** | 0.0799 | 0.0808 | 0.7158 | 0.7837 | 0.8921 | 0.8344 | 0.44% (8) | $1.27 \times 10^{-6}$ | 413.3 s |
| **30** | 0.0804 | 0.0813 | 0.7124 | 0.7723 | 0.9018 | 0.8321 | 0.38% (7) | $1.00 \times 10^{-6}$ | 416.1 s |

**Optimization Stability Note**:
19 AMP GradScaler skips occurred across 50,400 update attempts, a 0.038% skip rate.

---

## 6. MODEL COMPARISON SUMMARY

| Dimension | EXP-01 Baseline | EXP-02B-1 (Final: Ep 30) | EXP-02B-1 (Selected: Ep 3) | Evaluation Rule |
|---|:---:|:---:|:---:|:---:|
| **Checkpoint Path** | `experiments/exp01_baseline/best_model.pt` | `.../final_model.pt` | `.../best_model.pt` | Certified weights |
| **Validation Global IoU** | $0.7223$ | $0.7124$ | **$0.7305$** | $\ge 0.7000$ Required |
| **Validation Recall** | $81.01\%$ | $77.23\%$ | **$86.64\%$** | $\ge 79.00\%$ Required |
| **Validation GT-Neg FA Rate** | $20.09\%$ ($367$ tiles) | $0.38\%$ ($7$ tiles) | **$8.26\%$ ($151$ tiles)** | $\le 17.00\%$ Required |
| **Net Cured Negative Tiles** | 0 (Reference) | $+360$ tiles | **$+216$ tiles** | $\ge 57$ Required |
| **Relative FA Reduction** | $0.0\%$ | $98.09\%$ | **$58.86\%$** | $\ge 15.37\%$ Required |
| **Gating Status** | Reference Baseline | Gating 3 Fail (Recall $<79\%$) | **ALL 4 GATES PASSED** | Best Checkpoint Policy |

---

## 7. RECOMMENDATION FOR HELD-OUT TEST EVALUATION

1. **Gate EXP02B-1 Validation Acceptance**: The validation evidence confirms that candidate model `best_model.pt` (Epoch 3) satisfies Gating 1 ($\le 17.0\%$), Gating 3 ($\ge 79.0\%$), Gating 4 ($\ge 0.7000$), and the worst-case significance bound for Gating 2 ($p < 3.50 \times 10^{-21}$).
2. **Readiness for Held-Out Test Evaluation**: The experiment is scientifically and methodologically ready for a single-pass held-out test evaluation on the canonical **2,880 test tiles** at locked threshold **0.22** once formally authorized by the CAO.
3. **Audit Isolation Confirmation**: Zero test tiles were constructed, loaded, or accessed during this training or audit phase.
