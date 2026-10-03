"""EXP-07-P0-C22-A.2: Zero-Step End-to-End Preflight Rehearsal.

Executes the actual future EXP07_DIAG01 execution path end-to-end up to and including
the first forward-pass and loss calculation boundary, then STOPS before any backward pass
or optimizer update.

Governance:
- ZERO TRAINING
- ZERO BACKWARD PASS
- ZERO OPTIMIZER STEP
- ZERO SCHEDULER STEP
- ZERO KAGGLE CALLS
- ZERO HOLDOUT ACCESS
- ZERO PART-III ACCESS
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image
import rasterio
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, Sampler

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ocean_sentinel.ml.exp07_reference import ResNet18UNet
from ocean_sentinel.ml.exp07_fingerprint import (
    assert_dataset_lineage_hashes,
    assert_loss_weight_vector_contract,
    assert_quarantine_firewall,
    capture_rng_snapshot,
    fingerprint_model_state_dict,
    restore_rng_snapshot,
    verify_runtime_initialization_parity,
    CANONICAL_HISTORICAL_C16_LITERALS,
    UNIFORM_TREATMENT_LITERALS,
    FREEZE_SPEC_SHA256,
    PHYSICAL_MANIFEST_SHA256,
    PARTITION_MANIFEST_SHA256,
    PARENT_CLUSTER_MANIFEST_SHA256,
    TAXONOMY_SPEC_SHA256,
    WEIGHT_PROVENANCE_SHA256,
)

# Constants from C15 / C19 / C21 protocol
TRAIN_LOG1P_MEAN = 4.424158
TRAIN_LOG1P_STD = 0.469261
IGNORE_INDEX = -100

DENSE_CLASSES = [
    "BG", "AF", "BS", "LWA", "MCC", "OF",
    "POW", "RF", "WS", "Eddy", "IWs", "HM"
]

SOURCE_LABEL_TO_DENSE = {
    0: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5,
    7: 6, 8: 7, 10: 8, 11: 9, 12: 10, 13: 11,
}

HOLDOUT_ACCESS_COUNT = 0
PART_III_ACCESS_COUNT = 0


def update_run_state(phase: str, last_action: str, current_step: str, next_action: str, status: str = "IN_PROGRESS") -> None:
    telemetry_path = REPO_ROOT / "scratch" / "exp07_p0_c22a2_run_state.json"
    if telemetry_path.exists():
        state = json.loads(telemetry_path.read_text(encoding="utf-8"))
    else:
        state = {"task_id": "EXP-07-P0-C22-A.2", "artifacts_created": [], "artifacts_modified": []}

    state.update({
        "phase": phase,
        "status": status,
        "last_updated_at": time.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "last_successful_action": last_action,
        "current_step": current_step,
        "next_action": next_action,
        "holdout_access": (HOLDOUT_ACCESS_COUNT > 0),
        "part_iii_access": (PART_III_ACCESS_COUNT > 0),
        "training_started": False,
        "kaggle_started": False,
        "active_processes": 0,
    })
    telemetry_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def preprocess_sar_image(raw_image: np.ndarray, mean: float = TRAIN_LOG1P_MEAN, std: float = TRAIN_LOG1P_STD) -> Tuple[np.ndarray, np.ndarray]:
    if raw_image.ndim == 2:
        raw_image = raw_image[np.newaxis, :, :]
    validity_mask = (raw_image > 0).astype(bool)
    log1p_img = np.log1p(np.maximum(raw_image, 0.0, dtype=np.float32))
    standardized = (log1p_img - mean) / std
    standardized[~validity_mask] = 0.0
    return standardized.astype(np.float32), validity_mask


def remap_source_mask_to_dense(source_mask: np.ndarray, validity_mask: np.ndarray | None = None) -> np.ndarray:
    if source_mask.ndim == 3 and source_mask.shape[0] == 1:
        source_mask = source_mask[0]
    dense_mask = np.full(source_mask.shape, IGNORE_INDEX, dtype=np.int64)
    for src_id, dense_idx in SOURCE_LABEL_TO_DENSE.items():
        dense_mask[source_mask == src_id] = dense_idx
    if validity_mask is not None:
        v_mask_2d = validity_mask[0] if (validity_mask.ndim == 3 and validity_mask.shape[0] == 1) else validity_mask
        dense_mask[~v_mask_2d] = IGNORE_INDEX
    return dense_mask


class OPS02Dataset(Dataset):
    def __init__(self, manifest_data: dict, partition: str = "TRAIN"):
        super().__init__()
        global HOLDOUT_ACCESS_COUNT
        self.partition = partition.upper()
        if self.partition == "HOLDOUT":
            HOLDOUT_ACCESS_COUNT += 1
            raise PermissionError("HARD FIREWALL: HOLDOUT partition is strictly barred from training ingestion!")

        self.samples = [s for s in manifest_data["samples"] if s["partition"] == self.partition]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int):
        global HOLDOUT_ACCESS_COUNT
        sample = self.samples[idx]
        if sample["partition"] == "HOLDOUT":
            HOLDOUT_ACCESS_COUNT += 1
            raise PermissionError("HARD FIREWALL: Attempted to load HOLDOUT sample!")

        img_path = REPO_ROOT / sample["derived_image_path"]
        mask_path = REPO_ROOT / sample["derived_mask_path"]

        with rasterio.open(img_path) as src:
            raw_image = src.read(1).astype(np.float32)

        norm_image, validity_mask = preprocess_sar_image(raw_image)
        raw_mask = np.array(Image.open(mask_path), dtype=np.int64)
        target = remap_source_mask_to_dense(raw_mask, validity_mask=validity_mask)

        return (
            torch.from_numpy(norm_image).float(),
            torch.from_numpy(target).long(),
            torch.from_numpy(validity_mask).bool(),
            sample["sample_id"],
            sample["cluster_id"]
        )


class CandidateFWeightedSampler(Sampler):
    def __init__(self, weights: np.ndarray, num_samples: int = 72, seed: int = 42):
        super().__init__()
        self.weights = torch.as_tensor(weights, dtype=torch.double)
        self.num_samples = num_samples
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int):
        self.epoch = epoch

    def get_indices(self) -> List[int]:
        g = torch.Generator()
        g.manual_seed(self.seed + self.epoch * 1000)
        indices = torch.multinomial(self.weights, self.num_samples, replacement=True, generator=g)
        return indices.tolist()

    def __iter__(self):
        return iter(self.get_indices())

    def __len__(self):
        return self.num_samples


def compute_sampler_weights(train_samples: List[dict]) -> np.ndarray:
    parent_counts = {}
    for s in train_samples:
        parent_counts[s["cluster_id"]] = parent_counts.get(s["cluster_id"], 0) + 1
    w_parent = np.array([1.0 / parent_counts[s["cluster_id"]] for s in train_samples], dtype=np.float64)
    w_parent /= w_parent.sum()

    presence_scores = []
    for s in train_samples:
        fg_classes = [c for c in s["canonical_dense_class_ids_present"] if c > 0]
        score = sum(1.0 / math.sqrt(max(1, len([x for x in train_samples if c in x["canonical_dense_class_ids_present"]]))) for c in fg_classes)
        presence_scores.append(max(0.1, score))
    w_presence = np.array(presence_scores, dtype=np.float64)
    w_presence /= w_presence.sum()

    w_hybrid = 0.70 * w_parent + 0.30 * w_presence
    w_hybrid /= w_hybrid.sum()
    return w_hybrid


def tensor_checksum(t: torch.Tensor) -> str:
    arr = t.detach().cpu().numpy()
    return hashlib.sha256(arr.tobytes()).hexdigest().upper()


def run_zero_step_preflight_rehearsal() -> Dict[str, Any]:
    print("=" * 80)
    print("EXP-07-P0-C22-A.2: ZERO-STEP END-TO-END PREFLIGHT REHEARSAL")
    print("=" * 80)

    # 1. AUDIT & STATIC CONTRACT CHECK
    update_run_state("AUDIT", "INITIALIZING_AUDIT", "PART_B_DEPENDENCY_HASHING", "VERIFY_DEPENDENCIES")
    lineage_hashes = assert_dataset_lineage_hashes(REPO_ROOT)
    print(f"Lineage Hashes: Verified {len(lineage_hashes)} specifications.")

    # Canonical Weight Serialization
    update_run_state("STATIC_CONTRACT_CHECK", "VERIFYING_WEIGHT_SERIALIZATION", "PART_C_CANONICAL_SERIALIZATION", "VERIFY_VECTORS")
    ctrl_compact_bytes = json.dumps(CANONICAL_HISTORICAL_C16_LITERALS, separators=(',', ':')).encode('utf-8')
    treat_compact_bytes = json.dumps(UNIFORM_TREATMENT_LITERALS, separators=(',', ':')).encode('utf-8')
    ctrl_formatted_bytes = json.dumps(CANONICAL_HISTORICAL_C16_LITERALS).encode('utf-8')
    treat_formatted_bytes = json.dumps(UNIFORM_TREATMENT_LITERALS).encode('utf-8')

    ctrl_compact_sha256 = hashlib.sha256(ctrl_compact_bytes).hexdigest().upper()
    treat_compact_sha256 = hashlib.sha256(treat_compact_bytes).hexdigest().upper()
    ctrl_formatted_sha256 = hashlib.sha256(ctrl_formatted_bytes).hexdigest().upper()
    treat_formatted_sha256 = hashlib.sha256(treat_formatted_bytes).hexdigest().upper()

    t_ctrl = torch.tensor(CANONICAL_HISTORICAL_C16_LITERALS, dtype=torch.float32)
    t_treat = torch.tensor(UNIFORM_TREATMENT_LITERALS, dtype=torch.float32)
    assert_loss_weight_vector_contract(t_ctrl, t_treat)
    print(f"Canonical Control Compact JSON SHA256:   {ctrl_compact_sha256}")
    print(f"Canonical Treatment Compact JSON SHA256: {treat_compact_sha256}")
    print(f"Canonical Control Formatted JSON SHA256: {ctrl_formatted_sha256}")
    print(f"Canonical Treatment Formatted JSON SHA256: {treat_formatted_sha256}")

    # 2. INITIAL MODEL IDENTITY & REPOSITORY ARTIFACT VERIFICATION
    update_run_state("ARTIFACT_DISCOVERY", "VERIFYING_INITIAL_MODEL_STATE", "PART_D_INITIAL_MODEL_IDENTITY", "LOAD_INITIAL_STATE")
    init_model_path = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"
    if not init_model_path.exists():
        raise FileNotFoundError(f"Initial model state artifact missing: {init_model_path}")

    init_model_bytes = init_model_path.read_bytes()
    init_model_sha256 = hashlib.sha256(init_model_bytes).hexdigest().upper()
    loaded_sd = torch.load(init_model_path, map_location="cpu")

    # Instantiate model to verify structure
    probe_model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    probe_model.load_state_dict(loaded_sd, strict=True)

    trainable_params = sum(p.numel() for p in probe_model.parameters() if p.requires_grad)
    buffers = list(probe_model.named_buffers())
    float_buf = sum(b.numel() for _, b in buffers if b.dtype in (torch.float32, torch.float64))
    int_buf = sum(b.numel() for _, b in buffers if b.dtype in (torch.int64, torch.int32, torch.int16, torch.int8, torch.uint8))
    total_elements = sum(v.numel() for v in loaded_sd.values())
    bn_count = sum(1 for m in probe_model.modules() if isinstance(m, nn.BatchNorm2d))

    assert trainable_params == 14310860, f"Trainable params mismatch: {trainable_params}"
    assert (float_buf + int_buf) == 11806, f"Buffer count mismatch: {float_buf + int_buf}"
    assert total_elements == 14322666, f"Total state elements mismatch: {total_elements}"
    assert bn_count == 30, f"BatchNorm count mismatch: {bn_count}"
    print(f"Initial Model State SHA256: {init_model_sha256} (14,310,860 params, 30 BN layers verified)")

    # 3. CONTROL AND TREATMENT PIPELINE CONSTRUCTION
    update_run_state("CONTROL_CONSTRUCTION", "CONSTRUCTING_CONTROL_OBJECTS", "PART_E_CONTROL_CONSTRUCTION", "CONSTRUCT_TREATMENT")
    # Set canonical base seed 42
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    initial_rng_snapshot = capture_rng_snapshot()

    # Model Control
    model_control = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    model_control.load_state_dict(loaded_sd, strict=True)
    model_control.train()

    # Model Treatment
    update_run_state("TREATMENT_CONSTRUCTION", "CONSTRUCTING_TREATMENT_OBJECTS", "PART_E_TREATMENT_CONSTRUCTION", "ASSERT_PARITY")
    model_treatment = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    model_treatment.load_state_dict(loaded_sd, strict=True)
    model_treatment.train()

    # Assert Initial Model State Parity
    update_run_state("INITIAL_STATE_PARITY", "CHECKING_MODEL_STATE_PARITY", "PART_E_STATE_PARITY", "CHECK_RNG")
    fp_model_c = fingerprint_model_state_dict(model_control.state_dict())
    fp_model_t = fingerprint_model_state_dict(model_treatment.state_dict())
    assert fp_model_c == fp_model_t, f"Pre-epoch 0 model state mismatch: {fp_model_c} vs {fp_model_t}"

    # Load Dataset Manifest
    update_run_state("DATA_PARITY", "LOADING_TRAIN_DATASET", "PART_F_FIRST_BATCH_PARITY", "PREPARE_SAMPLER")
    manifest_path = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    train_dataset = OPS02Dataset(manifest_data, partition="TRAIN")
    assert len(train_dataset) == 132, f"Expected 132 TRAIN samples, got {len(train_dataset)}"

    # Candidate F Hybrid Sampler Schedule Parity
    update_run_state("SCHEDULE_PARITY", "VERIFYING_SAMPLER_SCHEDULES", "PART_J_SAMPLER_REHEARSAL", "CHECK_BATCH_PARITY")
    sampler_weights = compute_sampler_weights(train_dataset.samples)
    sampler_c = CandidateFWeightedSampler(sampler_weights, num_samples=72, seed=42)
    sampler_t = CandidateFWeightedSampler(sampler_weights, num_samples=72, seed=42)

    indices_c = sampler_c.get_indices()
    indices_t = sampler_t.get_indices()
    assert indices_c == indices_t, f"Sampler schedule mismatch between control and treatment!"
    sampler_schedule_sha256 = hashlib.sha256(json.dumps(indices_c).encode('utf-8')).hexdigest().upper()
    print(f"Precomputed Sampler Schedule (72 draws) SHA256: {sampler_schedule_sha256}")

    # DataLoader Construction (batch_size=8, shuffle=False)
    loader_c = DataLoader(train_dataset, batch_size=8, sampler=sampler_c, num_workers=0)
    loader_t = DataLoader(train_dataset, batch_size=8, sampler=sampler_t, num_workers=0)

    # 4. FIRST BATCH PARITY REHEARSAL
    update_run_state("FIRST_BATCH_PARITY", "EXTRACTING_FIRST_BATCH", "PART_F_BATCH_EXTRACTION", "ASSERT_BATCH_CHECKSUMS")
    batch_c = next(iter(loader_c))
    batch_t = next(iter(loader_t))

    imgs_c, targets_c, valids_c, sample_ids_c, clusters_c = batch_c
    imgs_t, targets_t, valids_t, sample_ids_t, clusters_t = batch_t

    # Invariants verification on first batch
    assert imgs_c.shape == (8, 1, 256, 256), f"Image shape mismatch: {imgs_c.shape}"
    assert imgs_c.dtype == torch.float32, f"Image dtype mismatch: {imgs_c.dtype}"
    assert targets_c.shape == (8, 256, 256), f"Target shape mismatch: {targets_c.shape}"
    assert targets_c.dtype == torch.int64, f"Target dtype mismatch: {targets_c.dtype}"
    assert valids_c.shape == (8, 1, 256, 256), f"Validity shape mismatch: {valids_c.shape}"
    assert valids_c.dtype == torch.bool, f"Validity dtype mismatch: {valids_c.dtype}"

    # Parity assertions between control and treatment first batch
    assert torch.equal(imgs_c, imgs_t), "Input image tensor disparity between control and treatment!"
    assert torch.equal(targets_c, targets_t), "Target tensor disparity between control and treatment!"
    assert torch.equal(valids_c, valids_t), "Validity mask disparity between control and treatment!"
    assert list(sample_ids_c) == list(sample_ids_t), "Sample ID list disparity between control and treatment!"
    assert list(clusters_c) == list(clusters_t), "Parent cluster list disparity between control and treatment!"

    img_chk = tensor_checksum(imgs_c)
    target_chk = tensor_checksum(targets_c)
    valid_chk = tensor_checksum(valids_c)

    print("First Batch Verified:")
    print(f"  Input Tensor Checksum:  {img_chk}")
    print(f"  Target Tensor Checksum: {target_chk}")
    print(f"  Valid Mask Checksum:    {valid_chk}")
    print(f"  Batch Sample IDs:       {list(sample_ids_c)}")

    # 5. BATCHNORM PRE-FORWARD PARITY
    update_run_state("FIRST_FORWARD_PASS", "VERIFYING_PRE_FORWARD_BN_PARITY", "PART_G_BATCHNORM_PARITY", "RUN_FORWARD_PASS")
    bn_c_modules = [m for m in model_control.modules() if isinstance(m, nn.BatchNorm2d)]
    bn_t_modules = [m for m in model_treatment.modules() if isinstance(m, nn.BatchNorm2d)]
    assert len(bn_c_modules) == 30 and len(bn_t_modules) == 30

    for idx, (bn_c, bn_t) in enumerate(zip(bn_c_modules, bn_t_modules)):
        assert torch.equal(bn_c.running_mean, bn_t.running_mean), f"BN layer {idx} running_mean pre-forward mismatch!"
        assert torch.equal(bn_c.running_var, bn_t.running_var), f"BN layer {idx} running_var pre-forward mismatch!"
        assert torch.equal(bn_c.weight, bn_t.weight), f"BN layer {idx} affine weight pre-forward mismatch!"
        assert torch.equal(bn_c.bias, bn_t.bias), f"BN layer {idx} affine bias pre-forward mismatch!"
        assert bn_c.num_batches_tracked == bn_t.num_batches_tracked, f"BN layer {idx} num_batches_tracked pre-forward mismatch!"

    # 6. FIRST FORWARD PASS & LOSS CONTRACT
    logits_c = model_control(imgs_c)
    logits_t = model_treatment(imgs_t)

    assert logits_c.shape == (8, 12, 256, 256), f"Logits shape mismatch: {logits_c.shape}"
    assert torch.equal(logits_c, logits_t), "Logits disparity between control and treatment under identical initialization!"
    logits_chk = tensor_checksum(logits_c)
    print(f"Forward Pass Output Verified (Logits Checksum: {logits_chk})")

    # Loss Calculation
    criterion_c = nn.CrossEntropyLoss(weight=t_ctrl, ignore_index=IGNORE_INDEX, reduction="mean")
    criterion_t = nn.CrossEntropyLoss(weight=t_treat, ignore_index=IGNORE_INDEX, reduction="mean")

    loss_c = criterion_c(logits_c, targets_c)
    loss_t = criterion_t(logits_t, targets_t)

    assert torch.isfinite(loss_c), f"Control loss is non-finite: {loss_c}"
    assert torch.isfinite(loss_t), f"Treatment loss is non-finite: {loss_t}"
    assert not torch.isnan(loss_c), "Control loss is NaN!"
    assert not torch.isnan(loss_t), "Treatment loss is NaN!"

    val_loss_c = float(loss_c.item())
    val_loss_t = float(loss_t.item())
    delta_loss = val_loss_t - val_loss_c

    print(f"Batch 0 Loss Calculated:")
    print(f"  Control Loss:   {val_loss_c:.6f}")
    print(f"  Treatment Loss: {val_loss_t:.6f}")
    print(f"  Delta Loss:     {delta_loss:+.6f}")
    print("SUCCESS: Preflight halted at forward pass boundary. ZERO backward calls. ZERO optimizer steps.")

    # 7. FIREWALL REHEARSAL
    update_run_state("FIREWALL_CHECK", "TESTING_QUARANTINE_FIREWALL", "PART_K_FIREWALL_REHEARSAL", "COMPLETE_PREFLIGHT")
    assert HOLDOUT_ACCESS_COUNT == 0, f"HOLDOUT partition was accessed {HOLDOUT_ACCESS_COUNT} times!"
    assert PART_III_ACCESS_COUNT == 0, f"Part-III partition was accessed {PART_III_ACCESS_COUNT} times!"
    assert_quarantine_firewall(["data/ops02/train/tile_001.tif", "data/ops02/dev/tile_002.png"])

    # Compile authoritative rehearsal audit
    rehearsal_audit = {
        "audit_metadata": {
            "audit_id": "OPS02_C22A2_ZERO_STEP_PREFLIGHT_v1",
            "task_id": "EXP-07-P0-C22-A.2",
            "executed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "PREFLIGHT_PASSED_ZERO_STEP_VERIFIED",
            "epistemic_standard": "LEVEL_5_MACHINE_VERIFIABLE_OPERATIONAL_GOVERNANCE"
        },
        "authoritative_experiment_structure": {
            "total_controlled_dimensions": 20,
            "independent_variable": {
                "name": "CLASS_LOSS_WEIGHT_VECTOR",
                "control_vector_compact_json_sha256": ctrl_compact_sha256,
                "treatment_vector_compact_json_sha256": treat_compact_sha256,
                "control_vector_formatted_json_sha256": ctrl_formatted_sha256,
                "treatment_vector_formatted_json_sha256": treat_formatted_sha256,
                "control_vector_sha256": ctrl_compact_sha256,
                "treatment_vector_sha256": treat_compact_sha256,
                "vector_length": 12
            },
            "scientific_experimental_invariants": [
                "INV-01: Dataset Specification (OPS02_v1.0.1_FROZEN)",
                "INV-02: Partition Allocation (132 TRAIN / 40 DEV / 40 HOLDOUT)",
                "INV-04: Physical Image Representation (GeoTIFF float32 single-band VV SAR, 256x256)",
                "INV-05: Preprocessing Transformation (np.log1p, valid DN > 0, nodata = 0.0)",
                "INV-06: Radiometric Normalization (mu=4.424158, sigma=0.469261)",
                "INV-07: Taxonomy & Index Ordering (12 dense classes 0..11)",
                "INV-08: Excluded Source Labels (3, 9, 14 mapped to ignore_index=-100)",
                "INV-09: Neural Network Architecture (ResNet18-UNet, 14,310,860 parameters, 30 BN layers)",
                "INV-10: Pretrained Backbone Identity (ResNet18_Weights.IMAGENET1K_V1)",
                "INV-11: Optimization Algorithm (AdamW, beta1=0.9, beta2=0.999, eps=1e-8)",
                "INV-12: Base Learning Rate (0.0005)",
                "INV-13: Weight Decay (0.01 applied to 2D conv/linear weights only)",
                "INV-14: Learning Rate Schedule (LinearWarmupCosineAnnealingLR, T_max=30, T_warmup=3, eta_min=1e-6)",
                "INV-15: Batch Dynamics & Accumulation (physical batch=8, accumulation=2, effective batch=16)",
                "INV-16: Sampler Strategy (Candidate F Hybrid, 72 draws per epoch)",
                "INV-17: Random Seed Configuration (Base seed 42, epoch formula 42 + epoch * 1000)",
                "INV-18: Data Augmentation (Disabled / deterministic loaders)",
                "INV-19: Benchmark Metric & Stopping Rule (dev_mIoU_phenomena, patience=10, min_epoch=15)"
            ],
            "execution_governance_invariants": [
                "INV-03: Partition Firewall Boundaries (Zero HOLDOUT / Zero Part-III access)"
            ]
        },
        "dependency_lineage_hashes": lineage_hashes,
        "initial_model_identity": {
            "initial_model_state_path": "data/ops02/initial_model_state.pt",
            "initial_model_state_sha256": init_model_sha256,
            "trainable_parameters": trainable_params,
            "buffer_count": float_buf + int_buf,
            "total_state_elements": total_elements,
            "batchnorm_2d_layers": bn_count,
            "strict_load_verified": True,
            "pretrained_backbone_file_hash": "NOT_LOCALLY_VERIFIED",
            "pretrained_backbone_reason": "resnet18-f37072fd.pth not in local torch hub cache; zero network downloads permitted under governance"
        },
        "parity_fingerprints": {
            "control_model_state_sha256": fp_model_c,
            "treatment_model_state_sha256": fp_model_t,
            "sampler_schedule_72_draws_sha256": sampler_schedule_sha256,
            "first_batch_sample_ids": list(sample_ids_c),
            "first_batch_input_tensor_checksum": img_chk,
            "first_batch_target_tensor_checksum": target_chk,
            "first_batch_validity_mask_checksum": valid_chk,
            "first_batch_logits_checksum": logits_chk,
            "batchnorm_pre_forward_equality": True,
            "logits_bitwise_equality": True
        },
        "first_forward_loss_results": {
            "control_loss_batch_0": val_loss_c,
            "treatment_loss_batch_0": val_loss_t,
            "delta_loss_batch_0": delta_loss,
            "finite_loss_verified": True,
            "backward_executed": False,
            "optimizer_step_executed": False,
            "scheduler_step_executed": False
        },
        "firewall_compliance": {
            "holdout_access_count": HOLDOUT_ACCESS_COUNT,
            "part_iii_access_count": PART_III_ACCESS_COUNT,
            "quarantine_firewall_verified": True
        },
        "readiness_verdict": "READY_FOR_USER_AUTHORIZATION"
    }

    audit_out_path = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a2_zero_step_preflight_v1.json"
    audit_out_path.write_text(json.dumps(rehearsal_audit, indent=2), encoding="utf-8")
    print(f"Saved Authoritative Audit: {audit_out_path}")

    update_run_state("COMPLETE", "ZERO_STEP_PREFLIGHT_VERIFIED", "PART_Q_READINESS_DECISION", "AWAIT_USER_AUTHORIZATION", status="SUCCESS")
    return rehearsal_audit


if __name__ == "__main__":
    run_zero_step_preflight_rehearsal()
