"""Ocean Sentinel Machine Learning & Deep Learning Subsystem.

Provides:
- Architectures: ResNet34UNet, VanillaUNet, count_parameters
- Losses: CombinedBCEAndDiceLoss, SoftDiceLoss, FocalTverskyLoss
- Metrics: SegmentationMeter, compute_batch_metrics, compute_metrics_from_counts
- Threshold: optimize_threshold_on_validation, ThresholdOptimizationResult
- Augmentation: SARGeometricAugmentation, IdentityTransform
"""

from ocean_sentinel.ml.augmentation import IdentityTransform, SARGeometricAugmentation
from ocean_sentinel.ml.losses import CombinedBCEAndDiceLoss, FocalTverskyLoss, SoftDiceLoss
from ocean_sentinel.ml.metrics import (
    SegmentationMeter,
    compute_batch_metrics,
    compute_confusion_matrix_counts,
    compute_metrics_from_counts,
)
from ocean_sentinel.ml.threshold import (
    ThresholdOptimizationResult,
    generate_default_threshold_grid,
    optimize_threshold_on_validation,
)
from ocean_sentinel.ml.unet_resnet import (
    ChannelAdaptationMethod,
    ResNet34UNet,
    VanillaUNet,
    adapt_resnet_conv1_weights,
    count_parameters,
)

from ocean_sentinel.ml.canonical_exp01 import (
    EXP01_NAME,
    EXP01_REVISION,
    CANONICAL_OPTIMIZER_LR,
    CANONICAL_OPTIMIZER_WEIGHT_DECAY,
    CANONICAL_SCHEDULER_CLASS,
    CANONICAL_SCHEDULER_T_MAX,
    CANONICAL_MAX_EPOCHS,
    verify_canonical_exp01_config,
    build_canonical_fingerprint_dict,
)

__all__ = [
    "ResNet34UNet",
    "VanillaUNet",
    "ChannelAdaptationMethod",
    "adapt_resnet_conv1_weights",
    "count_parameters",
    "SoftDiceLoss",
    "CombinedBCEAndDiceLoss",
    "FocalTverskyLoss",
    "SegmentationMeter",
    "compute_batch_metrics",
    "compute_confusion_matrix_counts",
    "compute_metrics_from_counts",
    "optimize_threshold_on_validation",
    "generate_default_threshold_grid",
    "ThresholdOptimizationResult",
    "SARGeometricAugmentation",
    "IdentityTransform",
    "EXP01_NAME",
    "EXP01_REVISION",
    "CANONICAL_OPTIMIZER_LR",
    "CANONICAL_OPTIMIZER_WEIGHT_DECAY",
    "CANONICAL_SCHEDULER_CLASS",
    "CANONICAL_SCHEDULER_T_MAX",
    "CANONICAL_MAX_EPOCHS",
    "verify_canonical_exp01_config",
    "build_canonical_fingerprint_dict",
]
