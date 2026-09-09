# Proposed Scientific Sampling Policy — EXP02B-1

**Intervention Identifier**: `POLICY_EXP02B_HARD_NEGATIVE_3X_BALANCED`  
**Phase**: EXP02B-0 (Frozen for CAO Approval)  
**Parent Investigation**: EXP-02A False-Alarm Mitigation  
**Intervention Category**: Training Distribution Re-weighting (Single Intervention Only)  

---

## 1. Mathematical Formulation

### 1.1 Candidate Definition & Classification
Candidate mining evaluated all 13,440 training tiles using the certified canonical EXP01 teacher model (`experiments/exp01_baseline/best_model.pt`, SHA-256: `9B8BD867...`) in `model.eval()` mode with `torch.no_grad()` at frozen threshold 0.22.

Based strictly on the observed empirical TRAIN distributions (Phase 2), each training tile $i \in \{0, \dots, 13439\}$ is assigned to one of three mutually exclusive classes:

1. **`positive_spill_tile`**:
   $$\sum_{h, w} M_{i, 0, h, w} > 0$$
   - Total Tiles: **5,083** (37.82% of train split).
   - Sampling Weight: $w_{i} = w_{\text{pos}} = 1.00$.

2. **`candidate_hard_negative`**:
   $$\sum_{h, w} M_{i, 0, h, w} == 0 \quad \text{AND} \quad \text{fp\_pixel\_count}_i \ge 100 \text{ pixels}$$
   - Total Tiles: **1,605** (11.94% of train split; 19.21% of all GT-negatives).
   - **Cutoff Selection Rationale**: The 100-pixel threshold was **not** pre-specified prior to viewing data; it was selected after inspecting the empirical TRAIN distribution in Phase 2. Among the 2,599 GT-negative tiles producing false positives ($\ge 1$ px) at threshold 0.22, the distribution of `fp_pixel_count` exhibits a 25th percentile of 45 pixels, median of 168 pixels, and 75th percentile of 712 pixels. The 100-pixel cutoff was chosen as an operationally meaningful boundary to isolate **macro false-positive tiles** ($\ge 100$ FP pixels) where false alarms form coherent spatial artifacts, separating them from minor speckle noise (<100 pixels) while retaining a robust candidate pool (1,605 tiles, 61.8% of all false-positive-producing negatives) without introducing multi-parameter composite scoring.
   - Sampling Weight: $w_{i} = w_{\text{hard\_neg}} = 2.25$.

3. **`ordinary_gt_negative`**:
   $$\sum_{h, w} M_{i, 0, h, w} == 0 \quad \text{AND} \quad \text{fp\_pixel\_count}_i < 100 \text{ pixels}$$
   - Total Tiles: **6,752** (50.24% of train split; 80.79% of all GT-negatives).
   - Sampling Weight: $w_{i} = w_{\text{ord\_neg}} = 0.75$.

---

## 2. Weight Assignment & Relative Exposure

The sampling probability $p_i$ of tile $i$ under `torch.utils.data.WeightedRandomSampler(replacement=True)` is:
$$p_i = \frac{w_i}{\sum_{k=1}^{13440} w_k}$$

The weights ($w_{\text{pos}} = 1.00$, $w_{\text{hard\_neg}} = 2.25$, $w_{\text{ord\_neg}} = 0.75$) are explicit scientific intervention parameters chosen by design to achieve an intended $3.0\times$ exposure ratio of hard negatives over ordinary negatives ($w_{\text{hard\_neg}} / w_{\text{ord\_neg}} = 2.25 / 0.75 = 3.0$), informed by the observed TRAIN candidate population sizes rather than mathematically determined by the data:

| Class | Count ($N_c$) | Weight ($w_c$) | Total Weight ($\sum w$) | Expected Draws (Epoch) | Expected Exposure Share | Mean Views / Tile / Epoch |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`positive_spill_tile`** | 5,083 | 1.00 | 5083.00 | 4965.4 | **36.95%** | **0.977x** |
| **`candidate_hard_negative`** | 1,605 | 2.25 | 3611.25 | 3527.7 | **26.25%** | **2.198x** |
| **`ordinary_gt_negative`** | 6,752 | 0.75 | 5064.00 | 4946.9 | **36.81%** | **0.733x** |
| **Total** | **13,440** | — | **13758.25** | **13,440.0** | **100.00%** | **1.000x** |

### Key Scientific Design Properties:
1. **Effective Exposure Ratio**: Every hard-negative tile receives $\frac{2.198}{0.733} = \mathbf{3.00\times}$ the expected exposure of an ordinary GT-negative tile.
2. **Substantial Positive Exposure Retention**: Positive spill tiles retain **36.47%** of dry-run training exposures (expected 36.95%, nominal baseline 37.82%), which preserves substantial positive-example exposure but does NOT guarantee recall preservation. Recall preservation remains an empirical endpoint of EXP02B-1.
3. **Hard-Negative Exposure Surge**: Hard-negative tiles increase from 11.94% of the dataset to **26.25%** of all training exposures (a **2.20x** increase in total gradient signals on radar lookalikes).

---

## 3. Strict Invariance Proof

This policy alters **ONLY** the data sampling probabilities. All 16 core scientific parameters are mathematically invariant:
- Model Architecture: `ResNet34UNet` (2-channel `slice_variance_scaled`) [UNCHANGED]
- Loss Function: $0.5 \cdot \text{BCE} + 0.5 \cdot \text{SoftDice}(\text{smooth}=1.0)$ [UNCHANGED]
- Normalization: Training-derived z-score normalization [UNCHANGED]
- Optimizer: AdamW (lr=$10^{-4}$, weight_decay=$0.01$) [UNCHANGED]
- Scheduler: CosineAnnealingLR ($T_{\max}=30$, $\eta_{\min}=10^{-6}$, last_epoch=$-1$) [UNCHANGED]
- Batch Size: 8; Accumulation Steps: 1; Batches per Epoch: 1,680 [UNCHANGED]
- Train Augmentation: HFlip + VFlip + Rot90 [UNCHANGED]
- Threshold: Locked to 0.22 [UNCHANGED]
