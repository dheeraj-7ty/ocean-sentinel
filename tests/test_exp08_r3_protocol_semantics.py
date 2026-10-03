"""EXP-08 Protocol Semantics Guardrail Tests — Phase 11-R3 Expanded Edition.

Extends tests/test_exp08_protocol_semantics.py (Phase 11-R2) with the 12 additional
guards specified in Phase 11-R3 §21.

EXECUTION_AUTHORIZED = FALSE (no inference, no training, no external data access).
"""

from __future__ import annotations

import pytest


# ===========================================================================
# ── Guard 1 (R3-NEW): Mixed DARTIS record count cannot be used as patch population
# ===========================================================================

DARTIS_TOTAL_ANNOTATION_RECORDS = 5515   # total rows in data_matrix.tab
DARTIS_OIL_PATCHES = 1365               # unique jpg_file in oc+ow subsets
DARTIS_NOOIL_PATCHES = 2290             # unique jpg_file in nc+nw subsets
DARTIS_OIL_OBJECTS = 3225               # oc+ow record count (one row per oil object)
DARTIS_NOOIL_OBJECTS = 2290             # nc+nw record count (one row per no-oil patch)
DARTIS_UNIQUE_SCENES = 1063             # unique Sentinel_IDs (post semicolon-split)


def test_total_records_not_equal_to_patch_count():
    """R3-Guard-1: 5,515 annotation records ≠ 5,515 patches."""
    # For oil subsets: multiple rows may share the same jpg_file (multi-object patches)
    # → record count (3,225) > unique oil patch count (1,365)
    assert DARTIS_OIL_OBJECTS > DARTIS_OIL_PATCHES, (
        "Oil annotation records must exceed oil patch count: "
        "multiple oil objects per patch produce multiple rows in data_matrix.tab."
    )
    # Therefore total records cannot equal total patches
    assert DARTIS_TOTAL_ANNOTATION_RECORDS != (DARTIS_OIL_PATCHES + DARTIS_NOOIL_PATCHES), (
        "5,515 annotation records ≠ 3,655 unique patches. "
        "Cannot use 5,515 as a scientific sample count."
    )


def test_correct_patch_population_denominators():
    """R3-Guard-1: Correct denominators for EXP-08 metrics."""
    assert DARTIS_OIL_PATCHES == 1365
    assert DARTIS_NOOIL_PATCHES == 2290
    assert DARTIS_OIL_PATCHES + DARTIS_NOOIL_PATCHES == 3655  # correct unique patches
    assert DARTIS_TOTAL_ANNOTATION_RECORDS == 5515             # annotation records only
    assert DARTIS_OIL_PATCHES + DARTIS_NOOIL_PATCHES < DARTIS_TOTAL_ANNOTATION_RECORDS


# ===========================================================================
# ── Guard 2 (R3-NEW): Oil-object count cannot be reported as oil-patch count
# ===========================================================================

def test_oil_object_count_not_interchangeable_with_oil_patch_count():
    """R3-Guard-2: 3,225 oil objects ≠ 1,365 oil patches."""
    assert DARTIS_OIL_OBJECTS != DARTIS_OIL_PATCHES, (
        "DARTIS contains 3,225 annotated oil objects across 1,365 oil patches. "
        "These are different entity levels and cannot be used interchangeably."
    )
    assert DARTIS_OIL_OBJECTS == 941 + 2284  # oc + ow record counts
    assert DARTIS_OIL_PATCHES == 1365        # unique jpg_files across oc+ow


def test_entity_ontology_is_consistent():
    """R3-Guard-2: Verify the entity ontology arithmetic."""
    # No-oil: 1 row = 1 patch (no object-level annotation)
    assert DARTIS_NOOIL_OBJECTS == DARTIS_NOOIL_PATCHES == 2290
    # Oil: 1 row = 1 oil object; 1 patch may contain multiple objects
    assert DARTIS_OIL_OBJECTS >= DARTIS_OIL_PATCHES  # always true: ≥1 object per oil patch
    # Record-level arithmetic
    assert DARTIS_OIL_OBJECTS + DARTIS_NOOIL_OBJECTS == DARTIS_TOTAL_ANNOTATION_RECORDS


# ===========================================================================
# ── Guard 3 (R3-NEW): Spatial-overlap result requires verified CRS semantics
# ===========================================================================

class SpatialOverlapResult:
    """Represents a computed spatial overlap result with provenance."""
    def __init__(self, value: int, denominator: int, crs_verified: bool,
                 entity_type_consistent: bool, denominator_description: str):
        self.value = value
        self.denominator = denominator
        self.crs_verified = crs_verified
        self.entity_type_consistent = entity_type_consistent
        self.denominator_description = denominator_description

    def is_scientifically_valid(self) -> bool:
        return self.crs_verified and self.entity_type_consistent

    def status(self) -> str:
        if not self.crs_verified:
            return "INVALID_CRS_UNVERIFIED"
        if not self.entity_type_consistent:
            return "INVALID_MIXED_DENOMINATOR"
        return "VALID"


def test_overlap_result_invalid_without_crs_verification():
    """R3-Guard-3: Cannot mark overlap valid without verified CRS."""
    result = SpatialOverlapResult(
        value=2468, denominator=5515,
        crs_verified=False,
        entity_type_consistent=False,
        denominator_description="mixed oil-object records and no-oil patch records",
    )
    assert not result.is_scientifically_valid()
    assert result.status() in ("INVALID_CRS_UNVERIFIED", "INVALID_MIXED_DENOMINATOR")


def test_overlap_result_invalid_with_mixed_denominator():
    """R3-Guard-3: CRS alone does not fix a mixed-entity denominator."""
    result_mixed_denom = SpatialOverlapResult(
        value=2468, denominator=5515,
        crs_verified=True,       # CRS is valid (both EPSG:4326)
        entity_type_consistent=False,  # but denominator mixes oil-objects and no-oil-patches
        denominator_description="5515 mixes 3225 oil-object records with 2290 no-oil-patch records",
    )
    assert not result_mixed_denom.is_scientifically_valid()
    assert result_mixed_denom.status() == "INVALID_MIXED_DENOMINATOR"


def test_overlap_result_valid_with_consistent_entity_and_crs():
    """R3-Guard-3: Valid when CRS is verified and entity type is consistent."""
    result_valid = SpatialOverlapResult(
        value=1234, denominator=2290,
        crs_verified=True,
        entity_type_consistent=True,
        denominator_description="2290 unique no-oil patches (unique jpg_file in nc+nw)",
    )
    assert result_valid.is_scientifically_valid()
    assert result_valid.status() == "VALID"


# ===========================================================================
# ── Guard 4 (R3-NEW): "40/40 sampled" cannot serialize as "100% of 1181 catalog scenes"
# ===========================================================================

class CDSEResolutionClaim:
    """Represents a CDSE resolution claim with its exact scope."""
    def __init__(self, resolved: int, sampled: int, catalog_size: int,
                 scope_label: str):
        self.resolved = resolved
        self.sampled = sampled
        self.catalog_size = catalog_size
        self.scope_label = scope_label  # must NOT claim full catalog if sampled < catalog_size

    def is_validly_labeled(self) -> bool:
        if self.sampled < self.catalog_size:
            # Must not claim full catalog resolution
            return "of catalog" not in self.scope_label.lower() and \
                   str(self.catalog_size) not in self.scope_label
        return True


def test_40_of_40_sampled_cannot_claim_full_catalog():
    """R3-Guard-4: 40 sampled scenes must not be reported as full-catalog resolution."""
    # Bad: claims full 1181-scene catalog
    bad_claim = CDSEResolutionClaim(
        resolved=40, sampled=40, catalog_size=1063,
        scope_label="100% of 1063 catalog Sentinel_IDs resolved",
    )
    assert not bad_claim.is_validly_labeled(), (
        "Reporting 40/40 sampled as '100% of 1063 catalog scenes' overstates the scope. "
        "The full catalog was not tested."
    )


def test_correct_cdse_claim_labels_sample_scope():
    """R3-Guard-4: Correct wording acknowledges the sample scope."""
    good_claim = CDSEResolutionClaim(
        resolved=40, sampled=40, catalog_size=1063,
        scope_label="40/40 stratified DARTIS->CDSE sampled scenes resolved",
    )
    assert good_claim.is_validly_labeled(), (
        "A properly scoped claim explicitly states '40/40 sampled' without "
        "generalizing to the full catalog."
    )


# ===========================================================================
# ── Guard 5 (R3-NEW): GRD linear representation cannot be mislabeled as σ0 dB output
# ===========================================================================

class SentinelProductRepresentation:
    """Describes the radiometric representation of a Sentinel-1 product."""
    def __init__(self, level: str, unit: str, requires_calibration: bool):
        self.level = level         # "Level-1 GRD", "σ⁰ calibrated", etc.
        self.unit = unit           # "linear_power", "dB", "amplitude"
        self.requires_calibration = requires_calibration


def is_directly_compatible_with_exp06(rep: SentinelProductRepresentation) -> bool:
    """EXP-06 requires calibrated σ⁰ in dB (float32). GRD linear is NOT compatible."""
    return rep.unit == "dB" and not rep.requires_calibration


def test_raw_grd_linear_is_not_compatible():
    """R3-Guard-5: Raw GRD intensity (linear power) is not compatible with EXP-06."""
    cdse_raw_grd = SentinelProductRepresentation(
        level="Level-1 GRD COG",
        unit="linear_power",
        requires_calibration=True,
    )
    assert not is_directly_compatible_with_exp06(cdse_raw_grd), (
        "CDSE Level-1 GRD products store intensity in linear power, not calibrated dB. "
        "Explicit radiometric calibration (LUT application) and 10*log10 conversion "
        "are required before use with EXP-06."
    )


def test_calibrated_db_raster_is_compatible():
    """R3-Guard-5: Calibrated σ⁰ dB is compatible with EXP-06."""
    calibrated = SentinelProductRepresentation(
        level="σ⁰ calibrated",
        unit="dB",
        requires_calibration=False,
    )
    assert is_directly_compatible_with_exp06(calibrated)


# ===========================================================================
# ── Guard 6 (R3-NEW): Unknown channel mapping cannot serialize as VERIFIED
# ===========================================================================

class ChannelMappingStatus:
    VERIFIED = "VERIFIED"
    INFERRED_FROM_STATISTICS = "INFERRED_FROM_STATISTICS"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


def can_execute_exp08(channel_mapping_status: str) -> bool:
    """EXP-08 is blocked if channel mapping is not at minimum VERIFIED."""
    return channel_mapping_status == ChannelMappingStatus.VERIFIED


def test_unverified_channel_mapping_blocks_exp08():
    """R3-Guard-6: UNVERIFIED channel mapping blocks EXP-08 execution."""
    current_status = ChannelMappingStatus.UNVERIFIED
    assert not can_execute_exp08(current_status), (
        "EXP-08 inference on CDSE Route B rasters requires knowing which CDSE band "
        "maps to EXP-06 Ch0 (historically inferred as VH) and Ch1 (historically inferred as VV). "
        "The Trujillo dataset documentation explicitly states polarization_mapping = UNKNOWN. "
        "Until authoritatively verified, EXP-08 execution is blocked."
    )


def test_inferred_from_statistics_is_not_verified():
    """R3-Guard-6: Statistical inference of channel mapping is not authoritative verification."""
    assert ChannelMappingStatus.INFERRED_FROM_STATISTICS != ChannelMappingStatus.VERIFIED


def test_verified_channel_mapping_allows_exp08():
    """R3-Guard-6: Once verified, EXP-08 can proceed."""
    assert can_execute_exp08(ChannelMappingStatus.VERIFIED)


# ===========================================================================
# ── Guard 7 (R3-NEW): Internal FAR cannot be a formal equivalence test without margin
# ===========================================================================

class HypothesisTestConfig:
    def __init__(self, equivalence_margin: float | None, power: float | None,
                 test_type: str):
        self.equivalence_margin = equivalence_margin
        self.power = power
        self.test_type = test_type  # "DESCRIPTIVE" or "EQUIVALENCE_TEST"

    def is_valid_hypothesis_test(self) -> bool:
        if self.test_type == "EQUIVALENCE_TEST":
            return (
                self.equivalence_margin is not None and
                self.equivalence_margin > 0 and
                self.power is not None and
                self.power > 0
            )
        return True  # DESCRIPTIVE always valid


def test_exp08_baseline_comparison_is_descriptive_only():
    """R3-Guard-7: EXP-08 FAR comparison is descriptive, not a formal equivalence test."""
    exp08_config = HypothesisTestConfig(
        equivalence_margin=None,
        power=None,
        test_type="DESCRIPTIVE",
    )
    assert exp08_config.is_valid_hypothesis_test()


def test_equivalence_test_requires_margin_and_power():
    """R3-Guard-7: Cannot run equivalence test without predefined margin."""
    bad_test = HypothesisTestConfig(
        equivalence_margin=None,  # No margin defined
        power=None,
        test_type="EQUIVALENCE_TEST",
    )
    assert not bad_test.is_valid_hypothesis_test(), (
        "An equivalence test requires a pre-specified margin (δ) and a power calculation. "
        "Without these, comparing to 0.55% internal FAR is descriptive, not hypothesis testing."
    )


# ===========================================================================
# ── Guard 8 (R3-RETAINED): DARTIS bounding boxes cannot become pixel masks
# ===========================================================================

class AnnotationRecord:
    def __init__(self, annotation_type: str, has_pixel_mask: bool):
        self.annotation_type = annotation_type
        self.has_pixel_mask = has_pixel_mask


def can_compute_segmentation_iou(annotation: AnnotationRecord) -> bool:
    return annotation.has_pixel_mask and annotation.annotation_type == "pixel_mask"


def test_dartis_bounding_boxes_cannot_produce_segmentation_iou():
    """R3-Guard-8 (retained from R2): DARTIS has bounding boxes, not pixel masks."""
    dartis_annotation = AnnotationRecord(annotation_type="bounding_box", has_pixel_mask=False)
    assert not can_compute_segmentation_iou(dartis_annotation)


# ===========================================================================
# ── Guard 9 (R3-RETAINED): Lookalike activation is always false activation
# ===========================================================================

def is_valid_lookalike_metric_label(label: str) -> bool:
    label_lower = label.lower().strip()
    prohibited = ["lookalike_iou", "lookalike_segmentation_iou",
                  "lookalike_detection_success", "look_alike_iou"]
    return not any(p in label_lower for p in prohibited)


def test_lookalike_activation_framing_is_always_false_alarm():
    """R3-Guard-9 (retained from R2): Oil activation on lookalike = false activation."""
    prohibited = ["lookalike_iou", "lookalike_segmentation_iou", "look_alike_iou"]
    for label in prohibited:
        assert not is_valid_lookalike_metric_label(label)
    valid = ["patch_activation_rate", "hard_negative_activation_rate",
             "predicted_oil_area_fraction", "scene_alarm_rate"]
    for label in valid:
        assert is_valid_lookalike_metric_label(label)


# ===========================================================================
# ── Guard 10 (R3-NEW): Mixed record/patch/object denominators are rejected
# ===========================================================================

class MetricDenominator:
    """Represents a denominator used in a scientific metric."""
    VALID_TYPES = {"patch", "object", "scene", "annotation_record"}

    def __init__(self, value: int, entity_type: str, is_homogeneous: bool):
        self.value = value
        self.entity_type = entity_type  # must be a single type, not mixed
        self.is_homogeneous = is_homogeneous  # False if mixing entity types

    def is_valid_for_metric(self) -> bool:
        return (
            self.entity_type in self.VALID_TYPES and
            self.is_homogeneous and
            self.value > 0
        )


def test_mixed_denominator_5515_is_rejected():
    """R3-Guard-10: 5,515 mixes oil-object records with no-oil patch records."""
    mixed = MetricDenominator(
        value=5515,
        entity_type="mixed_object_and_patch",
        is_homogeneous=False,
    )
    assert not mixed.is_valid_for_metric(), (
        "5,515 is a mixed count of 3,225 oil-object annotation records and "
        "2,290 no-oil patch records. It cannot serve as a scientific denominator."
    )


def test_homogeneous_denominators_are_valid():
    """R3-Guard-10: Pure patch or scene denominators are valid."""
    oil_patches = MetricDenominator(value=1365, entity_type="patch", is_homogeneous=True)
    nooil_patches = MetricDenominator(value=2290, entity_type="patch", is_homogeneous=True)
    scenes = MetricDenominator(value=1063, entity_type="scene", is_homogeneous=True)
    assert oil_patches.is_valid_for_metric()
    assert nooil_patches.is_valid_for_metric()
    assert scenes.is_valid_for_metric()


# ===========================================================================
# ── Guard 11 (R3-NEW): Geographic independence cannot be inferred from institution names
# ===========================================================================

class IndependenceClaim:
    """Represents a statistical independence claim with its basis."""
    def __init__(self, claim_type: str, basis: str):
        self.claim_type = claim_type
        self.basis = basis

    def is_valid(self) -> bool:
        # Institution-name basis alone is never valid for independence
        institution_keywords = ["institution", "different lab", "different team",
                                "different country", "separate organization"]
        basis_lower = self.basis.lower()
        if any(kw in basis_lower for kw in institution_keywords) and \
           "spatial" not in basis_lower and "acquisition" not in basis_lower:
            return False
        return True


def test_institution_based_independence_claim_is_invalid():
    """R3-Guard-11: Different institutions do not imply statistical independence."""
    bad_claim = IndependenceClaim(
        claim_type="statistical_independence",
        basis="Processed by different institutions: IPICYT (Mexico) vs DLR/DMI (Germany)",
    )
    assert not bad_claim.is_valid(), (
        "Institutional separation does not imply statistical independence. "
        "Trujillo and DARTIS both contain Eastern Mediterranean patches. "
        "Spatial/acquisition co-location must be checked directly."
    )


def test_geographic_verified_independence_is_valid():
    """R3-Guard-11: Verified spatial separation is a valid basis."""
    good_claim = IndependenceClaim(
        claim_type="zero_spatial_footprint_overlap",
        basis=(
            "Verified by direct geographic bounding box intersection: "
            "zero spatial footprint overlap between patch A and any patch in dataset B."
        ),
    )
    assert good_claim.is_valid()


# ===========================================================================
# ── Guard 12 (R3-NEW): EXP-08 must remain blocked while channel mapping is UNKNOWN
# ===========================================================================

MATERIAL_PREREQUISITES = {
    "channel_mapping": "UNVERIFIED",         # Trujillo polarization_mapping = UNKNOWN
    "cdse_radiometric_processing": "UNVERIFIED",  # GRD calibration chain not verified
    "dartis_entity_ontology": "VERIFIED",    # Forensically established this phase
    "spatial_geometry_crs": "VERIFIED",      # Both datasets EPSG:4326 confirmed
    "cdse_resolution_scope": "40_of_1063",   # Only 40/1063 tested
}


def exp08_execution_gate_passes(prerequisites: dict) -> bool:
    """Return True only if ALL material prerequisites are resolved."""
    blocking_statuses = {"UNVERIFIED", "UNKNOWN", "NOT_DETERMINABLE"}
    for key, status in prerequisites.items():
        if status in blocking_statuses:
            return False
    return True


def test_exp08_blocked_by_unverified_channel_mapping():
    """R3-Guard-12: EXP-08 execution gate fails while channel mapping is UNVERIFIED."""
    assert not exp08_execution_gate_passes(MATERIAL_PREREQUISITES), (
        "EXP-08 execution cannot proceed while 'channel_mapping' is UNVERIFIED. "
        "The physical polarization mapping (which band = VH, which = VV) must be "
        "authoritatively confirmed before CDSE Route B rasters can be fed to EXP-06."
    )


def test_exp08_passes_when_all_prerequisites_resolved():
    """R3-Guard-12: EXP-08 gate passes only with all prerequisites resolved."""
    resolved_prerequisites = {
        "channel_mapping": "VERIFIED",
        "cdse_radiometric_processing": "VERIFIED",
        "dartis_entity_ontology": "VERIFIED",
        "spatial_geometry_crs": "VERIFIED",
        "cdse_resolution_scope": "VERIFIED_40_OF_40_SAMPLED",
    }
    assert exp08_execution_gate_passes(resolved_prerequisites)


# ===========================================================================
# ── Guards retained from Phase 11-R2 (abbreviated)
# ===========================================================================

def test_verified_independence_requires_basis():
    """Retained R2: VERIFIED independence requires documented evidence."""
    # Cannot call independence VERIFIED without basis
    def serialize_independence(status: str, basis: str) -> dict:
        if status == "VERIFIED" and not basis:
            raise ValueError("Cannot serialize independence as VERIFIED without basis.")
        return {"status": status, "basis": basis}

    with pytest.raises(ValueError):
        serialize_independence("VERIFIED", "")


def test_training_count_is_not_20_dev_scenes():
    """Retained R2: Training tiles = 13,440, not 20 DEV scenes."""
    EXP06_TRAIN_TILES = 13440
    EXP06_VAL_TILES = 2880
    assert EXP06_TRAIN_TILES == 13440
    assert EXP06_VAL_TILES == 2880
    assert EXP06_TRAIN_TILES != 20
