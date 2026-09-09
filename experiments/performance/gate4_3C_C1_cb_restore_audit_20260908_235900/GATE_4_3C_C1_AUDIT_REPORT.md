# Gate 4.3C-C1: C-B Restore-Mechanics Qualification Report
## Forensic Reconstruction & Restoration Mechanics Audit

---

### Executive Summary

| Parameter | Value |
| :--- | :--- |
| **Phase** | **Gate 4.3C-C1 (Restore-Mechanics Qualification)** |
| **Target Checkpoint** | `experiments/performance/gate4_3C_B_one_epoch_pilot_20260908_220700/kernel_output/latest_checkpoint.pt` |
| **Checkpoint SHA-256** | `3B68BA80D6EE14E61066F25EC01CA3D7B70BF09C7C4F9963127A2223B6F05B9B` |
| **Size** | `292,470,251` bytes |
| **Outcome** | **CLEAN PASS (13/13 Checks Passed)** |
| **Status for Continuation** | **NON-CANONICAL (T_max=1). Authorized for restore audit ONLY. NEVER to be used for continuation training.** |

---

### Audit Verification Matrix

| Check ID | Component / Property | Expected | Observed | Status |
| :--- | :--- | :--- | :--- | :--- |
| **CHK-01** | File Size | `292,470,251` bytes | `292,470,251` bytes | **PASS** |
| **CHK-02** | Cryptographic SHA-256 | `3B68BA80D6EE...` | `3B68BA80D6EE...` | **PASS** |
| **CHK-03** | `checkpoint_integrity.json` Match | `latest_epoch=1`, exact SHA | Matched bitwise | **PASS** |
| **CHK-04** | Required Canonical Keys (14/14) | 14 canonical keys | 14 present, 0 missing | **PASS** |
| **CHK-05** | Model State Restoration | 288 tensors, 24,346,305 params | 0 missing, 0 unexpected keys | **PASS** |
| **CHK-06** | Optimizer State Restoration | 150 tracked tensors @ step 1680.0 | All 150 params at step 1680.0 | **PASS** |
| **CHK-07** | Scheduler State Forensic Audit | Audit confirmation of non-canonicality | $T_{\max}=1$, `last_epoch=1`, `_last_lr=[1e-06]` | **PASS** |
| **CHK-08** | AMP Scaler State | `scale=65536.0`, tracker=1680 | `scale=65536.0`, tracker=1680 | **PASS** |
| **CHK-09** | Epoch Derivation | `epoch=1` $\to$ `start_epoch=2` | `start_epoch=2` derived cleanly | **PASS** |
| **CHK-10** | History Restoration | Length 1, `val_iou=0.66277` | 1 record restored | **PASS** |
| **CHK-11** | Best-State Sentinel Reconciliation | `-1.0` and `0` reconciled to history | Reconciled to `best_val_iou=0.66277`, `best_epoch=1` | **PASS** |
| **CHK-12** | Manifest Fingerprint | Valid SHA-256 present | `C052720A954C2E7A...` intact | **PASS** |
| **CHK-13** | Output Dir Isolation Guard | Collision raises error | Guard triggered on path collision | **PASS** |

---

### Scientific Integrity Ruling
1. **Restore Mechanics**: The Ocean Sentinel restore pipeline correctly parses, unpickles, and restores all model, optimizer, scaler, and training state dictionaries from the C-B checkpoint across process boundaries.
2. **Continuation Disqualification**: Because the C-B checkpoint holds $T_{\max}=1$ and $\text{lr}=10^{-6}$, it **cannot** serve as the canonical EXP01 resume seed. Checkpoint surgery is prohibited.
3. **Transition to Phase C-C2**: Phase C-C2 will now proceed to generate the true canonical epoch-1 seed under $T_{\max}=30$.
