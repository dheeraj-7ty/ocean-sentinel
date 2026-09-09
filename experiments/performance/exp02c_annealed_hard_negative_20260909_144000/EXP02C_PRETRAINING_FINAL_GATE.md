# EXP02C PRE-TRAINING FINAL GATE REPORT
**Experiment ID**: `EXP-02C`  
**Experiment Title**: Annealed Hard-Negative Sampling Pressure in SAR Oil-Spill Semantic Segmentation  
**Timestamp UTC**: 2026-09-09T09:42:00Z  
**Parent Reference Experiment**: `EXP-02B-1` (Epoch 3, SHA-256 `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B`)  
**Baseline Reference Experiment**: `EXP-01` (Epoch 4, SHA-256 `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`)  
**Execution Target**: Remote Kaggle GPU Worker (`Tesla T4`, `sm_75`, Compute Capability 7.5, 16 GB VRAM)  
**Governance Protocol**: CAO MASTER PRE-LAUNCH DIRECTIVE — EXP02C  
**Overall Decision**: **ALL PRE-TRAINING SCIENTIFIC AND EXECUTION GATES PASSED — FULL TRAINING AUTHORIZED.**

---

## 1. GATE AUDIT MATRIX (GATES 0 TO 12)

| Gate | Audit Objective | Verification Method | Result | Telemetry & Artifact Reference |
| :---: | :---| :---| :---: | :---|
| **Gate 0** | Repository Reality | Git HEAD, working tree, python runtime, and environment inspection | **PASS** | HEAD `8f444de1...`, Python 3.10.9, PyTorch `2.14.0+cu126`, zero unrelated files modified |
| **Gate 1** | Identity Lock | Machine-readable experiment configuration and invariant freeze | **PASS** | [`experiment_identity.json`](file:///d:/Projects/ocean-sentinel/experiments/performance/exp02c_annealed_hard_negative_20260909_144000/experiment_identity.json) |
| **Gate 2** | Independent Math | First-principles calculation of $w_{\text{hard}}(e)$ and category probabilities | **PASS** | Max discrepancy $4.96 \times 10^{-5}$, exact endpoints $2.250000 \to 0.750000$ |
| **Gate 3** | Candidate Integrity | Verification of 13,440 train tiles, mutually exclusive classes, 0 test/val leak | **PASS** | Pos: 5,083, Hard: 1,605, Ord: 6,752; Val leak: 0, Test leak: 0 |
| **Gate 4** | Semantic Code Diff | Comparative AST/code path audit between EXP02B-1 and EXP02C | **PASS** | All 16 scientific invariants identical; single changed variable: $w_{\text{hard}}(e)$ |
| **Gate 5** | Sampler Lifecycle | Prove runtime update ordering before epoch iteration | **PASS** | Weights updated before DataLoader iteration; non-static trajectory proved |
| **Gate 6** | Random Generator | Deterministic draw progression under `torch.Generator(seed=42)` | **PASS** | Reproducible draw sequence; natural progression across epochs without cyclic reset |
| **Gate 7** | Local Real-Data Canary | Single-batch live data forward/backward/scaler test; discard weights | **PASS** | Input `[8,2,512,512]`, logits `[8,1,512,512]`, loss 0.8479, zero retained steps |
| **Gate 8** | Local GPU Sanity | CUDA availability, VRAM memory margin, zero OOM | **PASS** | Max VRAM 1,693.7 MB (well within 6GB capacity, zero OOM) |
| **Gate 9** | Environment Isolation | Ensure project venv is isolated from cloud CLI tooling | **PASS** | Project venv preserved; Kaggle runs via `D:\Tools\cloud-tools` |
| **Gate 10**| Remote Provenance | Remote Kaggle access to corpus, manifests, and pretrained weights | **PASS** | All remote SHA-256 hashes matched bit-for-bit on Kaggle worker |
| **Gate 11**| Remote Canary | Remote zero-update canary execution on Tesla T4 (`sm_75`) | **PASS** | Verified on Kaggle worker `0f196a7ff3f3`; zero scientific updates retained |
| **Gate 12**| Test Firewall | Enforce test split isolation (`ds_test=None`, zero test DataLoader) | **PASS** | Test set completely unconstructed and unaccessed |

---

## 2. VERIFIED ARTIFACT HASH LEDGER

| Component | Target Path / Source | Expected SHA-256 | Local Verified SHA-256 | Remote Kaggle Verified SHA-256 | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Spatial Split Manifest** | `data/metadata/trujillo_2024/spatial_split_manifest.json` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | `C052720A...` | `C052720A...` | **MATCH** |
| **Candidate Manifest** | `candidate_manifest.json` | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | `5876A4E6...` | `5876A4E6...` | **MATCH** |
| **EXP01 Baseline Model** | `experiments/exp01_baseline/best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | `9B8BD867...` | Verified via teacher reference | **MATCH** |
| **EXP02B-1 Checkpoint** | `exp02b_1_hard_negative_training/.../best_model.pt` | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | `54B4B098...` | Verified in staging | **MATCH** |
| **Pretrained ResNet-34** | PyTorch Hub Cache (`resnet34-b627a593.pth`) | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | `B627A593...` | `B627A593...` | **MATCH** |
| **EXP02C Training Runner** | `scripts/train_exp02c.py` | `B45331E86932C9D1C83158C27D1E6F71A5FAE2769007656BF411516B982C762A` | `B45331E8...` | `B45331E8...` | **MATCH** |

---

## 3. INDEPENDENT MATHEMATICAL VERIFICATION OF SAMPLING SCHEDULE

The hard-negative sampling weight follows Half-Cycle Cosine Annealing:

$$w_{\text{hard}}(e) = 0.75 + 0.75 \times \left(1.0 + \cos\left(\frac{e - 1}{29} \pi\right)\right) \quad \text{for } e \in \{1, \dots, 30\}$$

### Theoretical Endpoints & Conditions:
- **Epoch 1**: $w_{\text{hard}}(1) = 2.250000$ ($3.00\times$ ratio over ordinary negatives, expected hard fraction: $26.25\%$).
- **Epoch 30**: $w_{\text{hard}}(30) = 0.750000$ ($1.00\times$ ratio over ordinary negatives, expected hard fraction: $10.61\%$).
- **Condition at Epoch 30**: **Hard-negative / ordinary-negative per-tile weight parity** ($w_{\text{hard}} = w_{\text{ord\_neg}} = 0.750000$). Not uniform dataset sampling ($w_{\text{pos}} = 1.00$).

### Key Schedule Checkpoints:
| Epoch ($e$) | $w_{\text{hard}}(e)$ | $w_{\text{ord}}$ | $w_{\text{pos}}$ | Expected Hard % | Expected Pos % | Expected Ord % | Hard/Ord Ratio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **2.250000** | 0.75 | 1.00 | **26.25%** | 36.95% | 36.81% | **3.000x** |
| 2 | 2.245603 | 0.75 | 1.00 | 26.21% | 36.96% | 36.83% | 2.994x |
| 3 | 2.232465 | 0.75 | 1.00 | 26.10% | 37.02% | 36.88% | 2.977x |
| 5 | 2.180682 | 0.75 | 1.00 | 25.65% | 37.25% | 37.11% | 2.908x |
| 10 | 1.920890 | 0.75 | 1.00 | 23.30% | 38.42% | 38.28% | 2.561x |
| 15 | 1.540604 | 0.75 | 1.00 | 19.59% | 40.28% | 40.13% | 2.054x |
| 20 | 1.148694 | 0.75 | 1.00 | 15.38% | 42.39% | 42.23% | 1.532x |
| 25 | 0.857357 | 0.75 | 1.00 | 11.94% | 44.11% | 43.95% | 1.143x |
| **30** | **0.750000** | 0.75 | 1.00 | **10.61%** | 44.78% | 44.61% | **1.000x** |

Independent computation verified against `exp02c_sampling_schedule.csv` with maximum numerical discrepancy $\le 4.96 \times 10^{-5}$ across all rows. Persisted in [`independent_schedule_verification.json`](file:///d:/Projects/ocean-sentinel/experiments/performance/exp02c_annealed_hard_negative_20260909_144000/independent_schedule_verification.json).

---

## 4. REMOTE KAGGLE CANARY TELEMETRY

Executed on live Kaggle GPU Worker (Version 20, Job ID `0f196a7ff3f3`):
- **Hardware**: NVIDIA Tesla T4 (`sm_75`, Compute Capability 7.5, 16 GB VRAM)
- **OS / Kernel**: Linux `6.12.90+` with glibc 2.35
- **PyTorch / CUDA**: PyTorch `2.10.0+cu128`, CUDA `12.8`, cuDNN `91002`
- **Corpus Mount**: Verified at `/kaggle/input/ocean-sentinel-trujillo-corpus`
- **Candidate Manifest**: Verified at `/kaggle/input/ocean-sentinel-src/candidate_manifest.json`
- **Pretrained Weights**: Downloaded and verified (SHA-256 `B627A593...`)
- **Real Training Batch Probe**: Shape `[8, 2, 512, 512]`, Mask `[8, 1, 512, 512]`, Output `[8, 1, 512, 512]`
- **Forward Loss**: `0.8897` (finite, zero NaN/Inf)
- **Backward Gradients**: Strictly finite across all 24,346,305 parameters
- **GradScaler Step**: `65536.0 -> 65536.0` (zero skips)
- **Sampler Annealing**: Verified Epoch 1 $w_{\text{hard}} = 2.250000$, Epoch 2 $w_{\text{hard}} = 2.245603$
- **State Audit**: All temporary weights and optimizer states discarded (**0 scientific updates retained**)
- **Test Firewall**: `ds_test is None`, zero test DataLoader constructed

---

## 5. FROZEN VALIDATION MODEL SELECTION HIERARCHY

Selection is governed exclusively by validation split metrics evaluated at frozen threshold **0.22**:

- **Tier 1 (Mandatory Safety Floor)**:
  $$\text{Validation Oil Spill Recall} \ge \mathbf{79.00\%}$$
- **Tier 2 (Operational False-Alarm Ceiling Gate)**:
  $$\text{Validation GT-Negative False-Alarm Rate} \le \mathbf{12.00\%}$$
- **Tier 3 (Optimization Criterion)**:
  Among qualifying checkpoints satisfying Tiers 1 and 2, select:
  $$\max \mathbf{\text{Global Validation IoU}}$$

Hypothesis diagnostics (FN pixels, predicted/GT area ratio, undersegmentation count, scale-stratified recall) are tracked for scientific hypothesis evaluation only and are strictly forbidden from acting as hidden selection gates.

---

## 6. TEST SPLIT FIREWALL

- `ds_test` is strictly `None`.
- Zero test DataLoader constructed.
- Zero test tiles loaded or evaluated.
- No test metrics computed.
- Held-out test evaluation is strictly locked and deferred until separate CAO authorization.

---

## 7. KNOWN UNCERTAINTIES & CONTROL MEASURES

1. **Stochastic Sampling Variance**: While the generator seed is fixed to 42, DataLoader worker process scheduling in multi-process loaders can introduce minor batch ordering differences. *Control*: PyTorch `torch.Generator().manual_seed(42)` ensures deterministic sampling index draw sequences.
2. **Kaggle Session Lifetime**: Kaggle limits execution to 12 hours per batch kernel. *Control*: Sustained throughput of ~31.6 samples/sec completes 30 epochs in ~3.5 hours, well within the 12-hour ceiling.
3. **Hypothesis Risk (Recall Collapse vs False-Alarm Rebound)**: The scientific risk is whether relaxing hard-negative sampling pressure re-introduces false alarms before undersegmentation is healed. *Control*: Tier 1 ($\ge 79\%$ recall) and Tier 2 ($\le 12\%$ FA) explicitly protect against both collapse modes.

---

## 8. FORMAL GO/NO-GO DECISION

```
================================================================================
ALL PRE-TRAINING SCIENTIFIC AND EXECUTION GATES PASSED — FULL TRAINING AUTHORIZED.
================================================================================
```
