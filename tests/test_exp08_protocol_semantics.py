"""EXP-08 Protocol Semantics Guardrail Tests.

Phase 11-R2 minimal targeted guards to prevent the specific design errors
identified in the Phase 11-R1 EXP-08 draft from being silently re-introduced.

These tests enforce semantic contracts, not implementation correctness.

EXECUTION_AUTHORIZED = FALSE (no inference, no training, no external data access).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Guard 1: Lookalike IoU cannot be labeled as suppression success
# ---------------------------------------------------------------------------

class LookalikeMetricLabel:
    """Simulates a metric result object that must have a correct label."""

    def __init__(self, metric_name: str, value: float):
        self.metric_name = metric_name
        self.value = value


def is_valid_lookalike_metric_label(label: str) -> bool:
    """
    A metric label is INVALID if it implies that oil-prediction overlap with
    a lookalike ground-truth region is a SUCCESS metric.

    Valid labels include: activation_rate, patch_alarm_rate, false_alarm_rate,
    bbox_intersection_rate, predicted_oil_area_fraction.

    Invalid labels: lookalike_iou, lookalike_segmentation_success,
    lookalike_detection_rate (implies detection is the goal).
    """
    label_lower = label.lower().strip()
    # These labels imply oil overlap with lookalike is GOOD — that is wrong.
    prohibited_patterns = [
        "lookalike_iou",
        "lookalike_segmentation_iou",
        "lookalike_detection_success",
        "look_alike_iou",
    ]
    for pattern in prohibited_patterns:
        if pattern in label_lower:
            return False
    return True


def test_lookalike_iou_label_is_prohibited():
    """RESEARCH-08: Oil-detector overlap with lookalike ground truth is false activation."""
    prohibited_labels = [
        "lookalike_iou",
        "lookalike_segmentation_iou",
        "look_alike_iou",
        "lookalike_detection_success",
    ]
    for label in prohibited_labels:
        assert not is_valid_lookalike_metric_label(label), (
            f"Metric label '{label}' implies lookalike overlap = success. "
            f"This is semantically inverted: high oil overlap with a lookalike region "
            f"means high false activation, NOT detection success."
        )


def test_valid_lookalike_metric_labels_pass():
    """Correct metric labels (hard-negative framing) should pass."""
    valid_labels = [
        "patch_activation_rate",
        "hard_negative_activation_rate",
        "predicted_oil_area_fraction",
        "scene_alarm_rate",
        "bbox_intersection_rate",
        "false_alarm_rate",
    ]
    for label in valid_labels:
        assert is_valid_lookalike_metric_label(label), (
            f"Metric label '{label}' should be valid but was rejected."
        )


# ---------------------------------------------------------------------------
# Guard 2: Bounding boxes cannot silently become pixel segmentation masks
# ---------------------------------------------------------------------------

class AnnotationRecord:
    """Minimal representation of a DARTIS annotation record."""

    def __init__(self, annotation_type: str, has_pixel_mask: bool):
        self.annotation_type = annotation_type  # "bounding_box" or "pixel_mask"
        self.has_pixel_mask = has_pixel_mask


def can_compute_segmentation_iou(annotation: AnnotationRecord) -> bool:
    """Segmentation IoU requires actual pixel-level ground truth."""
    return annotation.has_pixel_mask and annotation.annotation_type == "pixel_mask"


def test_dartis_bounding_boxes_cannot_produce_segmentation_iou():
    """RESEARCH-09: DARTIS bounding boxes must not be silently converted to pixel ground truth."""
    dartis_annotation = AnnotationRecord(
        annotation_type="bounding_box",
        has_pixel_mask=False,
    )
    assert not can_compute_segmentation_iou(dartis_annotation), (
        "DARTIS provides only Pascal VOC XML bounding boxes, not pixel-level masks. "
        "Computing 'segmentation IoU' against filled bounding boxes fabricates ground truth. "
        "This metric is prohibited for DARTIS."
    )


def test_pixel_mask_dataset_can_compute_segmentation_iou():
    """A dataset with actual pixel masks CAN legitimately compute segmentation IoU."""
    pixel_annotation = AnnotationRecord(
        annotation_type="pixel_mask",
        has_pixel_mask=True,
    )
    assert can_compute_segmentation_iou(pixel_annotation), (
        "A dataset with actual pixel-level segmentation masks should be able "
        "to compute segmentation IoU."
    )


# ---------------------------------------------------------------------------
# Guard 3: Unknown parent-scene independence cannot be serialized as VERIFIED
# ---------------------------------------------------------------------------

class IndependenceStatus:
    VERIFIED = "VERIFIED"
    NOT_DETERMINABLE = "NOT_DETERMINABLE"
    UNKNOWN = "UNKNOWN"
    PARTIAL = "PARTIAL"


def serialize_independence_claim(status: str, basis: str) -> dict:
    """Produce a serialized independence claim."""
    if status == IndependenceStatus.VERIFIED and not basis:
        raise ValueError(
            "Cannot serialize independence as VERIFIED without an explicit basis. "
            "Independence claims require documented evidence."
        )
    return {"status": status, "basis": basis}


def test_verified_independence_requires_basis():
    """RESEARCH-10: Cannot claim VERIFIED independence without documented evidence."""
    with pytest.raises(ValueError, match="Cannot serialize independence as VERIFIED"):
        serialize_independence_claim(
            status=IndependenceStatus.VERIFIED,
            basis="",  # No basis provided
        )


def test_not_determinable_independence_serializes_correctly():
    """NOT_DETERMINABLE independence must be preserved as-is in serialization."""
    result = serialize_independence_claim(
        status=IndependenceStatus.NOT_DETERMINABLE,
        basis="Trujillo Part I rasters carry no parent Sentinel-1 scene IDs; "
              "cross-match with DARTIS Sentinel_IDs is impossible.",
    )
    assert result["status"] == IndependenceStatus.NOT_DETERMINABLE
    assert len(result["basis"]) > 0


def test_dartis_acquisition_independence_is_not_determinable():
    """The known status for DARTIS acquisition independence relative to EXP-06 training."""
    # This is the established verified status from EXTERNAL_VALIDATION_READINESS.md §3.3
    known_status = IndependenceStatus.NOT_DETERMINABLE
    known_basis = (
        "Trujillo Part I rasters carry zero parent Sentinel-1 scene IDs; "
        "acquisition-level cross-match between DARTIS and Trujillo training tiles "
        "is not feasible from current repository artifacts."
    )
    result = serialize_independence_claim(status=known_status, basis=known_basis)
    assert result["status"] == IndependenceStatus.NOT_DETERMINABLE
    # Must not be promoted to VERIFIED without explicit forensic evidence
    assert result["status"] != IndependenceStatus.VERIFIED


# ---------------------------------------------------------------------------
# Guard 4: External object-level metrics cannot be labeled as segmentation metrics
# ---------------------------------------------------------------------------

VALID_DARTIS_METRIC_TYPES = {
    "patch_level",    # patch-level binary activation
    "object_bbox",    # bounding-box-level intersection (explicitly labeled as such)
    "area_fraction",  # predicted area fraction
    "scene_level",    # scene-level alarm rate
}

PROHIBITED_DARTIS_METRIC_TYPES = {
    "segmentation_iou",
    "segmentation_dice",
    "pixel_level_iou",
}


def validate_dartis_metric_type(metric_type: str) -> bool:
    """Check that a metric type is valid for DARTIS (no pixel ground truth)."""
    if metric_type in PROHIBITED_DARTIS_METRIC_TYPES:
        return False
    return metric_type in VALID_DARTIS_METRIC_TYPES


def test_segmentation_iou_is_prohibited_for_dartis():
    """RESEARCH-09 / RESEARCH-11: Cannot use segmentation metrics on box-annotated data."""
    assert not validate_dartis_metric_type("segmentation_iou")
    assert not validate_dartis_metric_type("segmentation_dice")
    assert not validate_dartis_metric_type("pixel_level_iou")


def test_valid_dartis_metrics_pass():
    """Correct DARTIS-compatible metric types pass validation."""
    assert validate_dartis_metric_type("patch_level")
    assert validate_dartis_metric_type("object_bbox")
    assert validate_dartis_metric_type("area_fraction")
    assert validate_dartis_metric_type("scene_level")


# ---------------------------------------------------------------------------
# Guard 5: Experiment protocol cannot use unsupported universal thresholds
# ---------------------------------------------------------------------------

class ExperimentThreshold:
    """Represents a declared success threshold in the experiment protocol."""

    def __init__(self, value: float, label: str, basis: str):
        self.value = value
        self.label = label  # "ENGINEERING_GATE" or "SCIENTIFIC_TRUTH_THRESHOLD"
        self.basis = basis


def validate_threshold_label(threshold: ExperimentThreshold) -> bool:
    """
    A threshold labeled 'SCIENTIFIC_TRUTH_THRESHOLD' without a published
    supporting basis is not permitted.
    """
    if threshold.label == "SCIENTIFIC_TRUTH_THRESHOLD":
        if not threshold.basis or len(threshold.basis.strip()) < 20:
            return False
    return True


def test_arbitrary_50pct_threshold_cannot_be_scientific_truth():
    """RESEARCH-13: 50% lookalike IoU was not a scientifically grounded threshold."""
    threshold = ExperimentThreshold(
        value=0.50,
        label="SCIENTIFIC_TRUTH_THRESHOLD",
        basis="",  # No published basis
    )
    assert not validate_threshold_label(threshold), (
        "The 50% threshold in the Phase 11-R1 draft had no scientific basis. "
        "It cannot be labeled as a SCIENTIFIC_TRUTH_THRESHOLD."
    )


def test_engineering_gate_threshold_is_always_permitted():
    """An engineering gate is explicitly permitted even without a scientific citation."""
    threshold = ExperimentThreshold(
        value=0.50,
        label="ENGINEERING_GATE",
        basis="Pragmatic implementation decision; not a universal scientific standard.",
    )
    assert validate_threshold_label(threshold), (
        "ENGINEERING_GATE labels are always permitted since they explicitly "
        "acknowledge they are implementation choices, not scientific truth."
    )


def test_scientific_threshold_with_published_basis_is_permitted():
    """A threshold with a published supporting reference is valid."""
    threshold = ExperimentThreshold(
        value=0.22,
        label="SCIENTIFIC_TRUTH_THRESHOLD",
        basis=(
            "Pre-registered acceptance gate from PHASE_5G_EXP06_HYPOTHESIS_AND_TRAINING_CONTRACT "
            "§6, locked before training and retained as the frozen operational threshold."
        ),
    )
    assert validate_threshold_label(threshold), (
        "The τ=0.22 threshold has an explicit pre-registered basis and is permitted."
    )


# ---------------------------------------------------------------------------
# Guard 6: Training population count cannot be misidentified as validation population
# ---------------------------------------------------------------------------

EXP06_KNOWN_POPULATIONS = {
    "train_standard": 13440,      # TRAIN tiles from spatial split
    "train_hard_neg_pool": 355,   # Capped severity candidate pool
    "validation_part1": 2880,     # Part I validation tiles (NOT training)
    "holdout_part3": None,        # Never accessed; count withheld
}


def get_training_tile_count() -> int:
    """Return the correct EXP-06 training tile count."""
    return EXP06_KNOWN_POPULATIONS["train_standard"]


def get_validation_tile_count() -> int:
    """Return the correct EXP-06 Part I validation tile count."""
    return EXP06_KNOWN_POPULATIONS["validation_part1"]


def test_training_count_is_not_validation_count():
    """RESEARCH-15: Training population != validation population."""
    train_count = get_training_tile_count()
    val_count = get_validation_tile_count()
    assert train_count != val_count, (
        "Training tiles (13,440 from TRAIN split) must not be confused with "
        "Part I validation tiles (2,880). These are distinct non-overlapping populations."
    )
    assert train_count == 13440
    assert val_count == 2880


def test_training_count_is_not_20_dev_scenes():
    """RESEARCH-15: The incorrect claim '20 DEV scenes = training' must be rejected."""
    incorrect_claimed_training_count = 20  # from the Phase 11-R1 draft error
    actual_training_count = get_training_tile_count()
    assert actual_training_count != incorrect_claimed_training_count, (
        "The Phase 11-R1 draft incorrectly described EXP-06 training as '20 DEV scenes'. "
        "EXP-06 was trained on 13,440 canonical TRAIN tiles (not 20 scenes). "
        "The 2,880-tile validation set is the Part I VALIDATION population, not training."
    )
