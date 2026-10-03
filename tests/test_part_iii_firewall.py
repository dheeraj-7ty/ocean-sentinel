"""Unit tests verifying the scientific firewall protecting Trujillo Part III isolation."""

import pytest
from pathlib import Path
from ocean_sentinel.ingestion.firewall import (
    PartIIIFirewallViolationError,
    assert_no_part_iii_leakage,
    is_protected_part_iii_path,
    is_protected_part_iii_identifier,
    validate_manifest_against_firewall,
)
from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName, TileManifestEntry, PatchManifestEntry


def test_is_protected_part_iii_path():
    assert is_protected_part_iii_path("data/raw/external_validation/trujillo_part_iii/Images/Oil/00000.tif")
    assert is_protected_part_iii_path("D:\\Projects\\ocean-sentinel\\data\\raw\\external_validation\\trujillo_part_iii\\Mask\\Lookalike\\00010_segmentation.tif")
    assert is_protected_part_iii_path("experiments/DATASET_MANIFEST_TRUJILLO_PART_III.json")
    assert is_protected_part_iii_path("scratch/trujillo_part_iii_pairing.json")
    assert is_protected_part_iii_path("experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_a/Oil_00001.npz")
    assert not is_protected_part_iii_path("data/raw/trujillo_2024/images/Oil/00000.tif")
    assert not is_protected_part_iii_path("data/raw/trujillo_2024/masks/Mask_oil/00000.tif")


def test_is_protected_part_iii_identifier():
    assert is_protected_part_iii_identifier("Oil_00000")
    assert is_protected_part_iii_identifier("No oil_00045")
    assert is_protected_part_iii_identifier("Lookalike_00149")
    assert not is_protected_part_iii_identifier("00000")
    assert not is_protected_part_iii_identifier("00932")


def test_assert_no_part_iii_leakage_raises():
    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(["data/raw/external_validation/trujillo_part_iii/Images/Oil/00001.tif"])

    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(["Oil_00050"])


def test_dataset_firewall_blocks_part_iii_root(tmp_path):
    manifest = DatasetManifest(
        dataset_name="trujillo_2024_part_i",
        source_archive="dummy",
        zenodo_record="10900078",
        audit_report_path="dummy",
        radiometric_unit="dB",
        polarization_mapping="UNKNOWN",
        split_seed=42,
        split_strategy="dummy",
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        tile_height=512,
        tile_width=512,
        tile_stride_y=512,
        tile_stride_x=512,
        tiles_per_patch=16,
        patches=[],
        tiles=[],
        split_summaries=[],
        normalization_stats=None,
    )
    with pytest.raises(PartIIIFirewallViolationError):
        TrujilloTileDataset(
            manifest=manifest,
            split=SplitName.TRAIN,
            normalize=False,
            data_root="data/raw/external_validation/trujillo_part_iii",
        )


def test_manifest_identity_firewall():
    manifest_part_iii = DatasetManifest(
        dataset_name="trujillo_part_iii",
        source_archive="dummy",
        zenodo_record="10900078",
        audit_report_path="dummy",
        radiometric_unit="dB",
        polarization_mapping="UNKNOWN",
        split_seed=42,
        split_strategy="dummy",
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        tile_height=512,
        tile_width=512,
        tile_stride_y=512,
        tile_stride_x=512,
        tiles_per_patch=16,
        patches=[],
        tiles=[],
        split_summaries=[],
        normalization_stats=None,
    )
    with pytest.raises(PartIIIFirewallViolationError, match="dataset_name='trujillo_part_iii'"):
        validate_manifest_against_firewall(manifest_part_iii, context="PartIIITest")


def test_content_hash_blocks_renamed_part_iii_file(tmp_path):
    # Test that copying a protected Part III raster to an unindexed name still fails closed
    part_iii_source = Path("data/raw/external_validation/trujillo_part_iii/extracted/Images/Oil/00000.tif")
    if part_iii_source.is_file():
        # Copy to an innocuous temporary name with zero path or stem markers
        cloned_target = tmp_path / "innocent_ocean_patch_001.tif"
        cloned_target.write_bytes(part_iii_source.read_bytes())

        # Path and identifier checks pass because path doesn't contain markers
        assert not is_protected_part_iii_path(cloned_target)
        assert not is_protected_part_iii_identifier("innocent_ocean_patch_001")

        # But content hash check MUST intercept and raise PartIIIFirewallViolationError
        with pytest.raises(PartIIIFirewallViolationError, match="Protected Part III content hash detected"):
            assert_no_part_iii_leakage([cloned_target], context="RenamedContentAttack")

