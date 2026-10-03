"""Update PHASE_7A_DATA_PROTOCOL_FOUNDATION_REPORT_20260912.md with Phase 7A.2 corrections."""
import re
from pathlib import Path

REPORT_PATH = Path("experiments/PHASE_7A_DATA_PROTOCOL_FOUNDATION_REPORT_20260912.md")
lines = REPORT_PATH.read_text(encoding="utf-8").splitlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # 1. Update Header disposition
    if "**Overall Disposition**:" in line:
        new_lines.append("**Overall Disposition**: **PHASE_7A_FOUNDATION = COMPLETE | PROXY_IMAGERY_VALIDATION = PENDING (EXP-07 TRAINING STRICTLY BLOCKED)**")
        i += 1
        continue

    # 2. Update Section 3 diagram and text
    if "CONFIRMED_NEGATIVE   (Disjoint from Part III & Part I; authorized for negative training)" in line:
        new_lines.append("     └── PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY (Disjoint from Part III & Part I; provisional until physical raster validation)")
        i += 1
        continue

    if "- **`CONFIRMED_NEGATIVE`**: **547 candidate regions** across 343 parent scenes" in line:
        new_lines.append("- **`PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY`**: **547 candidate regions** across **343 parent products**. Metadata and geospatial boundary tests confirm complete disjointness from both Part III and Part I; physical raster validation remains pending.")
        new_lines.append("  - *Definition*: *\"Metadata/provenance/geospatial tests indicate eligibility for subsequent physical proxy validation; semantic suitability as a negative training example has not yet been confirmed.\"*")
        i += 1
        continue

    # 3. Update Section 4 counts
    if "- **Direct Candidate Intersections**: $355$ candidate regions directly intersect Part III scene bounding boxes." in line:
        new_lines.append("- **Direct Region Overlap (`DIRECT_OVERLAP_COUNT`)**: $355$ candidate regions directly intersect Part III scene bounding boxes.")
        i += 1
        continue

    if "- **Contaminated Parent Products**: Exactly $195$ unique Sentinel-1 parent products contain at least one Part III intersecting region." in line:
        new_lines.append("- **Contaminated Parent Products (`PARENT_PRODUCT_CONTAMINATION_COUNT`)**: Exactly $195$ unique Sentinel-1 parent products contain at least one Part III intersecting region.")
        i += 1
        continue

    if "- **Scene-Level Exclusion**: To eliminate co-scene radiometric and contextual leakage" in line:
        new_lines.append("- **Parent-Scene Level Contamination (`TOTAL_REJECTED_REGION_COUNT`)**: $680$ candidate regions ($355$ direct $+ 325$ co-scene regions) belonging to these $195$ parent products are marked `REJECTED` and excluded.")
        i += 1
        continue

    if "- **Cleared Pool**: $1,610$ candidate regions across $674$ parent products are certified 100% free of Part III contamination." in line:
        new_lines.append("- **Cleared Candidate Regions (`CLEARED_REGION_COUNT`)**: $1,610$ candidate regions are certified 100% free of Part III contamination.")
        new_lines.append("- **Cleared Parent Products (`CLEARED_PARENT_PRODUCT_COUNT`)**: $674$ parent products ($869 - 195 = 674$).")
        i += 1
        continue

    # 4. Update Section 5 with full reconciliation
    if "## 5. Part-I Leakage Firewall & Geographic Clustering" in line:
        new_lines.append("## 5. Part-I Leakage Firewall & Candidate Set Arithmetic Reconciliation")
        new_lines.append("")
        new_lines.append("The cleared candidate pool ($1,610$ regions across $674$ parent products) was audited against all 1,200 parent scenes of Trujillo Part I:")
        new_lines.append("")
        new_lines.append("### 5.1 Exact Set Definitions & Counts:")
        new_lines.append("- **`SET_A` (All Raw Candidates)**: $2,290$ regions across $869$ parent products ($1,939\\text{ nw} + 351\\text{ nc}$).")
        new_lines.append("- **`SET_B` (Part III Direct Overlap)**: $355$ regions across $195$ parent products.")
        new_lines.append("- **`SET_C` (Part III Scene-Contaminated)**: $680$ regions across $195$ parent products ($355$ direct $+ 325$ co-scene).")
        new_lines.append("- **`SET_D` (Part III Cleared)**: $1,610$ regions across $674$ parent products ($2,290 - 680 = 1,610$; $869 - 195 = 674$).")
        new_lines.append("- **`SET_E_direct` (Part I Direct Overlap in SET D)**: $543$ regions across $331$ parent products.")
        new_lines.append("- **`SET_E_scene` (Part I Scene-Expanded Overlap in SET D)**: $1,063$ regions across $331$ parent products ($543$ direct $+ 520$ co-scene indirect).")
        new_lines.append("- **`SET_F` (Fully Disjoint Candidates in SET D)**: $547$ regions across $343$ parent products ($1,610 - 1,063 = 547$; $674 - 331 = 343$).")
        new_lines.append("- **`SET_G` (Provisional Proxy Candidates)**: $547$ regions across $343$ parent products (classified `PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY`).")
        new_lines.append("")
        new_lines.append("### 5.2 Mathematical Resolution of the Apparent Inconsistency:")
        new_lines.append("An apparent contradiction existed between:")
        new_lines.append("$$1,610 - 543 = 1,067$$")
        new_lines.append("and:")
        new_lines.append("$$547 + 1,063 = 1,610$$")
        new_lines.append("**Audit Resolution**:")
        new_lines.append("1. The value **$543$** is strictly the count of candidate regions with **direct geometric footprint overlap** with Part I.")
        new_lines.append("2. The value **$1,063$** is the count of all candidate regions whose **parent product** has a direct overlap with Part I ($543$ direct $+ 520$ co-scene indirect).")
        new_lines.append("3. Because data governance mandates **parent-scene level exclusion** to prevent co-scene radiometric leakage, all $1,063$ candidate regions belonging to those $331$ parent products are classified as `DEVELOPMENT_ONLY`.")
        new_lines.append("4. Therefore, the true count of candidate regions from **fully disjoint parent products** is:")
        new_lines.append("   $$1,610 - 1,063 = 547\\text{ regions across } 343\\text{ parent products}$$")
        new_lines.append("5. Subtracting $543$ from $1,610$ yielded $1,067$ because it mixed region-level direct overlap with parent-scene level exclusion. When decomposed consistently:")
        new_lines.append("   $$1,610 = 543\\text{ (direct overlap)} + 520\\text{ (co-scene indirect)} + 547\\text{ (disjoint)}$$")
        new_lines.append("   The arithmetic reconciles with 100% mathematical precision.")
        new_lines.append("")
        # Skip the original preamble line
        i += 2
        continue

    # 5. IoU terminology
    if "| **Micro Mean IoU** |" in line:
        line = line.replace("| **Micro Mean IoU** |", "| **Micro Pooled IoU** |")
    if "| **Primary Micro Mean IoU** |" in line:
        line = line.replace("| **Primary Micro Mean IoU** |", "| **Primary Micro Pooled IoU** |")

    # 6. Baseline Scope Protection note
    if "experiments/performance/exp06_positive_bce_weight/exp06_frozen_dev_baseline.json" in line:
        new_lines.append(line)
        new_lines.append("")
        new_lines.append("> [!IMPORTANT]")
        new_lines.append("> **Baseline Population Scope & Protection (Sections 11 & 12)**:")
        new_lines.append("> This frozen baseline is valid **exclusively for the canonical Part-I DEV population** ($180$ parent scenes, $2,880$ tiles, $1,053$ positive, $1,827$ clean water). It serves as a regression baseline for the Part-I distribution.")
        new_lines.append("> It is **NOT** a lookalike baseline or proxy baseline. Future proxy evaluation will establish a separate, unadapted zero-shot baseline on the physical proxy imagery once acquired. Lookalike FAR gates cannot be defined until physical imagery exists and the relevant evaluation unit is frozen.")
        i += 1
        continue

    # 7. Section 14
    if "## 14. Definitive Recommendation for Phase 7A.2" in line:
        new_lines.append("## 14. Definitive Recommendation for Phase 7A.2 & Phase Status")
        new_lines.append("")
        new_lines.append("- **Phase Status Certification**:")
        new_lines.append("  - `PHASE_7A_FOUNDATION = COMPLETE`")
        new_lines.append("  - `PROXY_IMAGERY_VALIDATION = PENDING`")
        new_lines.append("- **Candidate Training**: **`EXP-07 TRAINING STRICTLY FORBIDDEN`**")
        new_lines.append("")
        new_lines.append("1. **EXP-07 Training Remains BLOCKED**: No candidate model training is authorized.")
        new_lines.append("2. **Authorized Next Step: Phase 7A.2 Data Acquisition & Validation**:")
        new_lines.append("   - Acquire physical raster imagery for the **547 provisionally eligible negative proxy regions** (`PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY`, disjoint from both Part III and Part I) via the validated Copernicus Data Space Ecosystem (CDSE) Process API.")
        new_lines.append("   - Perform physical data quality validation on disk: verify file existence, source product ID, acquisition time, dual-polarization (VV+VH), dimensions ($512 \\times 512$ / $640 \\times 640$), raster readability, band identity, CRS/geolocation, checksums, duplicate status, and absence of corruption.")
        new_lines.append("   - Only upon passing physical raster validation may eligible samples be promoted to `PHYSICALLY_VALIDATED_NEGATIVE`.")
        new_lines.append("   - Evaluate zero-shot EXP-06 baseline on the newly acquired physical proxy dataset to establish the unadapted lookalike false-alarm rate before training.")
        new_lines.append("3. **Subsequent Step (Phase 7B)**: Only after Phase 7A.2 physical raster acquisition, validation, and zero-shot baseline measurement are complete may **Family A (Controlled Data Intervention)** training contracts be considered.")
        # Skip until section 15
        while i < len(lines) and not lines[i].startswith("## 15."):
            i += 1
        continue

    # 8. Matrix update
    if "4-tier taxonomy (`CONFIRMED_NEGATIVE`: 547)" in line:
        line = line.replace("4-tier taxonomy (`CONFIRMED_NEGATIVE`: 547)", "Taxonomy updated (`PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY`: 547)")

    new_lines.append(line)
    i += 1

REPORT_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("Report successfully updated line-by-line!")
