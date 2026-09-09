# ADR 005: Resumed Training Infrastructure Qualification & Scientific Separation

**Status**: APPROVED / CLOSED  
**Date**: September 2026  
**Author**: Implementation Engineer (under CAO Architectural Authority)  
**Phase**: Gate 4.3C-C / EXP02B-0  
**Context**: Cloud Execution Qualification under Kaggle 12-Hour Limits  

---

## 1. Context & Problem Statement

Training the full 30-epoch Ocean Sentinel baseline (`EXP-01`) on Kaggle GPU hardware requires approximately 4.5 to 5.0 hours of compute. In production and iterative development, platform timeouts (12-hour session limits), transient machine preemptions, and unexpected local or cloud shutdowns introduce a fundamental operational requirement: the training pipeline must support reliable, lossless multi-epoch checkpoint resumption.

Prior to Gate 4.3C, resuming an interrupted run was vulnerable to two primary defects:
1. **Cosine Annealing Scheduler Desynchronization**: Standard re-instantiation of `torch.optim.lr_scheduler.CosineAnnealingLR` with remaining epochs resets $T_{\max}$, corrupting the learning rate trajectory and decaying LR prematurely.
2. **Cumulative Optimizer Accounting Drift**: Session step counters reset to zero, obfuscating the actual training exposure and causing logging discrepancies across segmented sessions.

Gate 4.3C-C was commissioned to qualify and prove lossless resumed training on Kaggle GPU hardware over a single controlled epoch transition (Epoch 1 $\to$ Epoch 2).

---

## 2. Decision & Architectural Implementation

### 2.1 Pure State Restoration Contract
To ensure exact mathematical continuity of the learning rate schedule without altering scientific parameters:
- The learning rate scheduler state is restored exclusively via `scheduler.load_state_dict(checkpoint["scheduler_state_dict"])`.
- The scheduler retains its full 30-epoch horizon ($T_{\max}=30$) across all session boundaries.
- Under CosineAnnealingLR, the mathematical learning rate at Epoch 2 ($t=2$) is guaranteed to follow:
  $$\eta_t = \eta_{\min} + \frac{1}{2}(\eta_{\max} - \eta_{\min})\left(1 + \cos\left(\frac{t\pi}{T_{\max}}\right)\right) \approx 9.892\times 10^{-5}$$
  rather than dropping to the terminal minimum learning rate $\eta_{\min} = 10^{-6}$.

### 2.2 Cumulative Step Accounting
- The runner tracks `prior_optimizer_steps` (read from checkpoint), `successful_optimizer_updates` (executed in current session), and `cumulative_optimizer_updates` ($=\text{prior} + \text{session}$).
- Physical checkpoint inspection confirms that 100% of AdamW optimizer parameter states (150/150 tensors) track identical step counts ($3360.0$ at Epoch 2).

### 2.3 Best Model State Preservation
- Resuming into an isolated output directory preserves the prior best model checkpoint from the resume seed when the resumed epoch does not achieve a superior validation metric.
- Both `best_model.pt` checkpoints (seed vs resumed) are bitwise identical (SHA-256: `65ECF4415897644878E9BAA1A3230430250C5DDF3F66150F0DBE723ABAD983F4`).

### 2.4 Execution-Only `--stop-after-epoch` Control
- An execution-only flag `--stop-after-epoch` was introduced in `scripts/train_exp01.py` allowing deterministic termination after any target epoch without changing `--epochs 30`.

---

## 3. Strict Boundary: Infrastructure vs. Scientific Configuration

All modifications implemented for Gate 4.3C-C are strictly categorized as **Execution Infrastructure and Fault-Tolerance Plumbing**. 

They:
1. **DO NOT** alter the scientific model architecture (`ResNet34UNet`).
2. **DO NOT** alter the loss formulation ($0.5 \cdot \text{BCE} + 0.5 \cdot \text{SoftDice}$).
3. **DO NOT** alter the dataset spatial partition (`spatial_split_manifest.json`, seed 42).
4. **DO NOT** alter optimizer hyperparameters ($\text{lr}=10^{-4}$, $\text{weight\_decay}=0.01$).
5. **DO NOT** alter train-time data augmentation (HFlip + VFlip + Rot90).
6. **DO NOT** alter evaluation thresholds ($0.22$).

### Initial State Rule for Subsequent Scientific Experiments
Gate 4.3C-C checkpoints (`latest_checkpoint.pt`, `best_model.pt`, `final_model.pt` from C-C4) are qualification artifacts only. All subsequent scientific training experiments (including `EXP02B-1`) must initialize from the canonical EXP01 initial state (certified ImageNet pretrained weights `torchvision://resnet34`, SHA-256: `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F`), and **NEVER** from a C-C checkpoint.
