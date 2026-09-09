# Pre-Registered Evaluation Endpoints, Statistical Test & Decision Hierarchy — EXP02B-1

**Investigation**: EXP-02B-1 (Hard-Negative Sampling Intervention)  
**Parent Baseline**: EXP-01 Baseline ResNet-34 U-Net (Rev B)  
**Reference Document**: `docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md`  
**Registration Status**: **FROZEN PRIOR TO ANY MODEL TRAINING**  
**Evaluation Isolation**: Validation split is strictly evaluation-only; Held-out test split is 100% frozen and untouched.  

---

## 1. Primary Evaluation Endpoint (Mathematically Defined)

### Metric: Validation GT-Negative False-Alarm Rate ($	ext{FA\_rate}_{	ext{val}}$)
$$	ext{FA\_rate}_{	ext{val}} = rac{\sum_{j \in \mathcal{V}_{	ext{neg}}} \mathbb{I}\left(\sum_{h, w} [\sigma(z_{j, h, w}) \ge 0.22] \ge 1ight)}{|\mathcal{V}_{	ext{neg}}|}$$
where:
- $\mathcal{V}_{	ext{neg}}$ is the frozen set of validation tiles containing **zero labeled oil spill pixels** ($\sum M_j == 0$).
- Total validation GT-negative tiles: $|\mathcal{V}_{	ext{neg}}| = \mathbf{1,827}$ tiles (63.44% of the 2,880 validation tiles).
- Diagnostic threshold: Locked to canonical constant **0.22**.
- $\mathbb{I}(\cdot)$ is the indicator function evaluating whether a GT-negative tile produces $\ge 1$ false-positive pixel.

### Baseline Benchmark Value (EXP02A Empirical Truth):
$$	ext{FA\_rate}_{	ext{val}}^{	ext{EXP01}} = rac{367}{1,827} = 20.0876\% pprox \mathbf{20.09\%}$$

---

## 2. Pre-Registered Paired Statistical Hypothesis Test

### Formal Statistical Protocol:
- **Unit of Analysis**: Individual validation GT-negative tile ($j \in \mathcal{V}_{	ext{neg}}$, $n = 1,827$).
- **Paired Binary Outcome**:
  - $Y_j^{	ext{EXP01}} \in \{0, 1\}$: False-alarm status of tile $j$ under canonical EXP01 baseline.
  - $Y_j^{	ext{EXP02B-1}} \in \{0, 1\}$: False-alarm status of tile $j$ under candidate EXP02B-1 intervention.
- **Statistical Procedure**: **Two-sided McNemar Test** with continuity correction on the $2 	imes 2$ paired contingency table:

$$egin{array}{c|c|c|c}
& 	ext{EXP02B-1 Negative } (Y=0) & 	ext{EXP02B-1 False Alarm } (Y=1) & 	ext{Total} \
\hline
	ext{EXP01 Negative } (Y=0) & a & c 	ext{ (new false alarms)} & 1,460 \
	ext{EXP01 False Alarm } (Y=1) & b 	ext{ (cured false alarms)} & d & 367 \
\hline
	ext{Total} & a + b & c + d & 1,827
\end{array}$$

$$\chi^2 = rac{(|b - c| - 1)^2}{b + c} \sim \chi^2(1)$$

- **Significance Level**: $lpha = \mathbf{0.05}$ (Pre-registered, two-sided, $p < 0.05$).
- **Effect Metrics**:
  - Absolute Reduction: $\Delta_{	ext{abs}} = rac{b - c}{1,827}$
  - Relative Reduction: $\Delta_{	ext{rel}} = rac{b - c}{367}$
  - 95% Confidence Interval for $\Delta_{	ext{abs}}$ using Wilson / Wald paired score interval.

---

## 3. Decision Hierarchy & Strict Success Criteria

EXP02B-1 will be declared a **SCIENTIFIC SUCCESS** if and only if **ALL FOUR** gating conditions are satisfied:

| Tier | Criterion / Endpoint | Threshold / Cutoff | Baseline (EXP01) | Rationale / Mathematical Rule |
| :---: | :--- | :---: | :---: | :--- |
| **Gating 1** | **Primary False-Alarm Rate** | **$\le 17.0\%$** | $20.09\%$ ($367/1827$) | **Stricter than 15% Relative Reduction**: $20.0876\% 	imes 0.85 = 17.0745\%$. A cutoff of $\le 17.0\%$ strictly requires at least 57 net cured tiles ($b - c \ge 57$, relative reduction $\ge 15.37\%$). |
| **Gating 2** | **Statistical Significance** | **$p < 0.05$** | — | Two-sided paired McNemar test on $n=1,827$ paired validation GT-negative tiles must confirm rejection of null hypothesis $H_0: b = c$. |
| **Gating 3** | **Spill Detection Safety Recall** | **$\ge 79.00\%$** | $81.01\%$ | Validation global positive oil spill recall ($rac{	ext{TP}}{	ext{TP}+	ext{FN}}$ at 0.22) must not degrade by more than 2.0 percentage points. |
| **Gating 4** | **Global Segmentation Quality** | **$\ge 0.7000$** | $0.7223$ | Validation global IoU ($rac{	ext{TP}}{	ext{TP}+	ext{FP}+	ext{FN}}$ at 0.22) must remain $\ge 0.7000$ (allowable margin $\le 0.0223$). |

---

## 4. Secondary Descriptive Endpoints (Non-Gating)

1. **Total False-Positive Pixel Burden on Negatives**:
   $$	ext{FP\_fraction}_{	ext{val}} = rac{\sum_{j \in \mathcal{V}_{	ext{neg}}} 	ext{FP\_pixels}_j}{1,827 	imes 262,144}$$
2. **Extensive False-Alarm Tile Rate**:
   Percentage of validation GT-negative tiles with severe false-positive footprints ($\ge 1,000$ pixels). Baseline in EXP02A: $6.32\%$.
3. **Expected Calibration Error (ECE)** on negative tiles across 10 probability bins $[0.0, 0.1), \dots, [0.9, 1.0]$.
4. **Held-Out Test Set Confirmation**:
   Conducted strictly after validation acceptance at frozen threshold 0.22. Zero threshold tuning on test.
