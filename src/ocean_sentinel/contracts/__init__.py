"""Ocean Sentinel Contract and Interface Foundations.

Exposes domain contracts for Path B multistage architecture:
1. CandidateProposal
2. CandidateRegion
3. LookalikeAssessment
4. TemporalEvidence
5. AISCompatibilityEvidence
6. FusionEvidence
"""

from ocean_sentinel.contracts.path_b import (
    AISCompatibilityEvidence,
    CandidateProposal,
    CandidateProposalProtocol,
    CandidateRegion,
    EXP06CandidateProposalAdapter,
    EvidenceStatus,
    ExecutionMode,
    FusionEvidence,
    LineageRecord,
    LookalikeAssessment,
    LookalikeSuppressionAction,
    LookalikeSuppressionCategory,
    PathBContractError,
    ProvenanceGateViolationError,
    ReplaceableCandidateProposalEngine,
    ScientificBoundaryViolationError,
    TemporalConsistencyStatus,
    TemporalEvidence,
    assess_lookalikes,
    correlate_ais_candidates,
    extract_candidate_regions,
    fuse_path_b_evidence,
    reason_temporal_repeat_pass,
)

__all__ = [
    "AISCompatibilityEvidence",
    "CandidateProposal",
    "CandidateProposalProtocol",
    "CandidateRegion",
    "EXP06CandidateProposalAdapter",
    "EvidenceStatus",
    "ExecutionMode",
    "FusionEvidence",
    "LineageRecord",
    "LookalikeAssessment",
    "LookalikeSuppressionAction",
    "LookalikeSuppressionCategory",
    "PathBContractError",
    "ProvenanceGateViolationError",
    "ReplaceableCandidateProposalEngine",
    "ScientificBoundaryViolationError",
    "TemporalConsistencyStatus",
    "TemporalEvidence",
    "assess_lookalikes",
    "correlate_ais_candidates",
    "extract_candidate_regions",
    "fuse_path_b_evidence",
    "reason_temporal_repeat_pass",
]
