"""Unit tests for DARTIS -> CDSE cross-validation components.

Verifies prefix extraction, metadata parsing, stratification sampling,
and result classification without making live network calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.verify_dartis_cdse import (
    MatchClassification,
    ValidationRecord,
    extract_canonical_prefix,
    parse_dartis_metadata,
    select_stratified_sample,
)

METADATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "metadata"
    / "yang_singha_2025"
    / "data_matrix.tab"
)


class TestDartisCrossValidationHelpers:
    """Unit tests for offline cross-validation logic."""

    def test_extract_canonical_prefix_safe(self) -> None:
        raw_id = (
            "S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_"
            "014295_01A97E_39B8.SAFE"
        )
        expected = (
            "S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E"
        )
        assert extract_canonical_prefix(raw_id) == expected

    def test_extract_canonical_prefix_cog(self) -> None:
        raw_id = (
            "S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_"
            "014295_01A97E_2DFF_COG"
        )
        expected = (
            "S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E"
        )
        assert extract_canonical_prefix(raw_id) == expected

    def test_extract_canonical_prefix_short(self) -> None:
        short_id = "S1A_INVALID"
        assert extract_canonical_prefix(short_id) == "S1A_INVALID"

    @pytest.mark.skipif(not METADATA_PATH.exists(), reason="DARTIS metadata table not acquired")
    def test_parse_dartis_metadata(self) -> None:
        clean_cols, rows = parse_dartis_metadata(METADATA_PATH)

        assert "Sentinel_ID" in clean_cols
        assert "subset" in clean_cols
        assert "start_time" in clean_cols
        assert "patch_ul_lon" in clean_cols
        assert len(rows) == 5515

        first = rows[0]
        assert first["subset"] in ("ow", "oc", "nw", "nc")
        assert len(first["lons"]) == 4
        assert len(first["lats"]) == 4

    @pytest.mark.skipif(not METADATA_PATH.exists(), reason="DARTIS metadata table not acquired")
    def test_select_stratified_sample_deterministic(self) -> None:
        _, rows = parse_dartis_metadata(METADATA_PATH)

        sample_5 = select_stratified_sample(rows, samples_per_stratum=5)
        # 8 strata x 5 = 40 samples
        assert len(sample_5) == 40

        # Determinism: same rows in same order on repeated call
        sample_5_again = select_stratified_sample(rows, samples_per_stratum=5)
        assert [r["primary_id"] for r in sample_5] == [r["primary_id"] for r in sample_5_again]

        # Verify all 8 strata are represented
        strata_found = {(r["subset"], r["primary_id"][:3]) for r in sample_5}
        expected_strata = {
            ("ow", "S1A"), ("ow", "S1B"),
            ("oc", "S1A"), ("oc", "S1B"),
            ("nw", "S1A"), ("nw", "S1B"),
            ("nc", "S1A"), ("nc", "S1B"),
        }
        assert strata_found == expected_strata

    def test_validation_record_dataclass(self) -> None:
        rec = ValidationRecord(
            sample_index=1,
            dartis_sentinel_id="S1A_IW_GRDH_1SDV_20190101T000000_20190101T000025_000001_000001_AAAA.SAFE",
            canonical_prefix="S1A_IW_GRDH_1SDV_20190101T000000_20190101T000025_000001_000001",
            subset="ow",
            category_name="Oil Spill (Open Water)",
            platform="S1A",
            dartis_start_time="2019-01-01T00:00:00",
            dartis_end_time="2019-01-01T00:00:25",
            patch_bbox=[30.0, 32.0, 31.0, 33.0],
            classification=MatchClassification.MATCH_WITH_METADATA_DIFFERENCE.value,
            cdse_matched_id="S1A_IW_GRDH_1SDV_20190101T000000_20190101T000025_000001_000001_BBBB_COG",
            cdse_platform="sentinel-1a",
            cdse_polarizations=["VV", "VH"],
        )
        assert rec.classification == "MATCH_WITH_METADATA_DIFFERENCE"
        assert rec.cdse_platform == "sentinel-1a"
