"""U-Net Segmentation Architectures for Ocean Sentinel SAR Imagery.

Implements:
1. ResNet34UNet: U-Net with ResNet-34 encoder adapted for 2-channel SAR input
   with mathematically justified pretrained weight initialization.
2. VanillaUNet: Classic 4-stage U-Net baseline with ~32 base channels (for EXP-04).

Key architectural invariants:
- Explicit input contract: [B, 2, H, W] float32 tensor (H, W divisible by 32).
- Explicit output contract: [B, 1, H, W] float32 raw logits (no sigmoid).
- No hidden resizing or unintended interpolation.
- Strict parameter measurement utilities.
"""

from __future__ import annotations

import math
from typing import Literal

import torch
import torch.nn as nn
import torchvision.models as models
from torchvision.models import ResNet34_Weights

ChannelAdaptationMethod = Literal[
    "slice_variance_scaled",
    "average_distributed",
    "slice",
    "rgb_luminance",
]


class DoubleConv(nn.Module):
    """Two consecutive [Conv2d -> BatchNorm2d -> ReLU] blocks."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        mid_channels: int | None = None,
    ) -> None:
        super().__init__()
        if mid_channels is None:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.double_conv(x)


class DecoderBlock(nn.Module):
    """Decoder block: ConvTranspose2d upsampling + Skip concatenation + DoubleConv."""

    def __init__(
        self,
        in_channels: int,
        skip_channels: int,
        out_channels: int,
    ) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(
            in_channels,
            in_channels // 2,
            kernel_size=2,
            stride=2,
        )
        self.conv = DoubleConv(
            (in_channels // 2) + skip_channels,
            out_channels,
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x_up = self.up(x)
        # Check spatial dimension match
        if x_up.shape[-2:] != skip.shape[-2:]:
            diff_y = skip.size(2) - x_up.size(2)
            diff_x = skip.size(3) - x_up.size(3)
            x_up = nn.functional.pad(
                x_up,
                [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2],
            )
        x_cat = torch.cat([x_up, skip], dim=1)
        return self.conv(x_cat)


def adapt_resnet_conv1_weights(
    pretrained_weights: torch.Tensor,
    method: ChannelAdaptationMethod = "slice_variance_scaled",
) -> torch.Tensor:
    """Adapt pretrained 3-channel (RGB) conv1 kernel to 2-channel SAR input.

    Parameters
    ----------
    pretrained_weights : torch.Tensor
        Weight tensor from torchvision resnet34 conv1, shape [64, 3, 7, 7].
    method : ChannelAdaptationMethod
        Adaptation strategy:
        - "slice_variance_scaled":
            W' = W[:, 0:2] * sqrt(3/2).
            Assuming independent, standardized input channels (mean 0, var 1),
            the sum over 2 channels has variance 2 * (alpha * sigma_w)^2.
            Equating to original variance 3 * sigma_w^2 yields alpha = sqrt(3/2) ≈ 1.2247.
        - "average_distributed":
            W'[:, 0] = W[:, 0] + 0.5 * W[:, 2]
            W'[:, 1] = W[:, 1] + 0.5 * W[:, 2]
            Preserves total weight sum per filter: sum_c W'_c = sum_c W_c.
        - "slice":
            W' = W[:, 0:2].
            Direct slice without scaling. Output variance is 2/3 of original.
        - "rgb_luminance":
            W_lum = mean(W, dim=1, keepdim=True) * sqrt(3/2)
            W' = cat([W_lum, W_lum], dim=1)
            Applies equalized luminance edge-detection kernel to each SAR channel.

    Returns
    -------
    torch.Tensor
        Adapted weight tensor of shape [64, 2, 7, 7].
    """
    if pretrained_weights.shape[1] != 3:
        raise ValueError(
            f"Expected pretrained conv1 weights with 3 channels, got {pretrained_weights.shape[1]}"
        )

    w = pretrained_weights.clone()

    if method == "slice_variance_scaled":
        scale = math.sqrt(3.0 / 2.0)
        return w[:, 0:2, :, :] * scale

    elif method == "average_distributed":
        w_0 = w[:, 0:1, :, :] + 0.5 * w[:, 2:3, :, :]
        w_1 = w[:, 1:2, :, :] + 0.5 * w[:, 2:3, :, :]
        return torch.cat([w_0, w_1], dim=1)

    elif method == "slice":
        return w[:, 0:2, :, :]

    elif method == "rgb_luminance":
        w_lum = w.mean(dim=1, keepdim=True) * math.sqrt(3.0 / 2.0)
        return torch.cat([w_lum, w_lum], dim=1)

    else:
        raise ValueError(f"Unknown channel adaptation method: {method}")


class ResNet34UNet(nn.Module):
    """U-Net with ResNet-34 encoder adapted for 2-channel SAR input.

    Contract:
    - Input: [B, 2, H, W] float32 tensor (H, W must be multiples of 32).
    - Output: [B, 1, H, W] float32 raw logits (before sigmoid).

    Parameters
    ----------
    in_channels : int
        Must be 2 for Ocean Sentinel SAR.
    num_classes : int
        Must be 1 for binary segmentation.
    pretrained : bool
        Whether to initialize encoder with ImageNet pretrained weights.
    adaptation_method : ChannelAdaptationMethod
        Strategy for adapting 3-channel RGB conv1 to 2-channel SAR.
    """

    def __init__(
        self,
        in_channels: int = 2,
        num_classes: int = 1,
        pretrained: bool = True,
        adaptation_method: ChannelAdaptationMethod = "slice_variance_scaled",
    ) -> None:
        super().__init__()
        if in_channels != 2:
            raise ValueError(f"ResNet34UNet requires in_channels=2, got {in_channels}")
        if num_classes != 1:
            raise ValueError(f"ResNet34UNet requires num_classes=1, got {num_classes}")

        self.in_channels = in_channels
        self.num_classes = num_classes
        self.pretrained = pretrained
        self.adaptation_method = adaptation_method

        # 1. Instantiate ResNet-34 encoder
        weights = ResNet34_Weights.DEFAULT if pretrained else None
        base_resnet = models.resnet34(weights=weights)

        # 2. Adapt first convolution (conv1) from 3 to 2 channels
        orig_conv1 = base_resnet.conv1
        new_conv1 = nn.Conv2d(
            in_channels=2,
            out_channels=orig_conv1.out_channels,
            kernel_size=orig_conv1.kernel_size,
            stride=orig_conv1.stride,
            padding=orig_conv1.padding,
            bias=orig_conv1.bias is not None,
        )

        if pretrained:
            adapted_w = adapt_resnet_conv1_weights(orig_conv1.weight.data, method=adaptation_method)
            new_conv1.weight.data.copy_(adapted_w)
            if orig_conv1.bias is not None:
                new_conv1.bias.data.copy_(orig_conv1.bias.data)
        else:
            nn.init.kaiming_normal_(new_conv1.weight, mode="fan_out", nonlinearity="relu")
            if new_conv1.bias is not None:
                nn.init.constant_(new_conv1.bias, 0)

        # Encoder stages
        self.conv1 = new_conv1
        self.bn1 = base_resnet.bn1
        self.relu = base_resnet.relu
        self.maxpool = base_resnet.maxpool

        self.layer1 = base_resnet.layer1  # out: 64 ch, H/4
        self.layer2 = base_resnet.layer2  # out: 128 ch, H/8
        self.layer3 = base_resnet.layer3  # out: 256 ch, H/16
        self.layer4 = base_resnet.layer4  # out: 512 ch, H/32

        # 3. Decoder stages
        # Block 4: 512 -> up to 256, concat skip3 (256) -> out 256 (H/16)
        self.dec4 = DecoderBlock(in_channels=512, skip_channels=256, out_channels=256)
        # Block 3: 256 -> up to 128, concat skip2 (128) -> out 128 (H/8)
        self.dec3 = DecoderBlock(in_channels=256, skip_channels=128, out_channels=128)
        # Block 2: 128 -> up to 64, concat skip1 (64) -> out 64 (H/4)
        self.dec2 = DecoderBlock(in_channels=128, skip_channels=64, out_channels=64)
        # Block 1: 64 -> up to 32, concat skip0 (64) -> out 32 (H/2)
        self.dec1 = DecoderBlock(in_channels=64, skip_channels=64, out_channels=32)
        # Final block: 32 -> up to 16, H/2 -> H, out 16 (H)
        self.final_up = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2)
        self.final_conv = DoubleConv(16, 16)
        # Final 1x1 conv to produce logits
        self.head = nn.Conv2d(16, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape [B, 2, H, W] float32.

        Returns
        -------
        torch.Tensor
            Raw logits of shape [B, 1, H, W] float32.
        """
        # Validate input contract
        if x.dim() != 4:
            msg = f"Expected 4D input [B, C, H, W], got {x.dim()}D (shape {tuple(x.shape)})"
            raise ValueError(msg)
        if x.shape[1] != self.in_channels:
            msg = (
                f"Expected {self.in_channels} input channels, "
                f"got {x.shape[1]} (shape {tuple(x.shape)})"
            )
            raise ValueError(msg)
        b, c, h, w = x.shape
        if h % 32 != 0 or w % 32 != 0:
            raise ValueError(
                f"Input dimensions ({h}x{w}) must be divisible by 32, got shape {tuple(x.shape)}"
            )

        # Encoder forward pass with skip extraction
        # skip0: after initial conv + bn + relu, shape [B, 64, H/2, W/2]
        x0 = self.relu(self.bn1(self.conv1(x)))
        # maxpool -> [B, 64, H/4, W/4]
        x_pool = self.maxpool(x0)

        # skip1: layer1 output [B, 64, H/4, W/4]
        x1 = self.layer1(x_pool)
        # skip2: layer2 output [B, 128, H/8, W/8]
        x2 = self.layer2(x1)
        # skip3: layer3 output [B, 256, H/16, W/16]
        x3 = self.layer3(x2)
        # bottleneck: layer4 output [B, 512, H/32, W/32]
        x4 = self.layer4(x3)

        # Decoder forward pass
        d4 = self.dec4(x4, x3)   # [B, 256, H/16, W/16]
        d3 = self.dec3(d4, x2)   # [B, 128, H/8, W/8]
        d2 = self.dec2(d3, x1)   # [B, 64, H/4, W/4]
        d1 = self.dec1(d2, x0)   # [B, 32, H/2, W/2]

        # Final full-resolution upsampling
        up0 = self.final_up(d1)  # [B, 16, H, W]
        feat = self.final_conv(up0)  # [B, 16, H, W]
        logits = self.head(feat)     # [B, 1, H, W]

        return logits


class VanillaUNet(nn.Module):
    """Vanilla 4-stage U-Net baseline with ~32 base channels (for future EXP-04).

    Contract:
    - Input: [B, 2, H, W] float32 tensor (H, W divisible by 16).
    - Output: [B, 1, H, W] float32 raw logits (before sigmoid).
    """

    def __init__(
        self,
        in_channels: int = 2,
        num_classes: int = 1,
        base_channels: int = 32,
    ) -> None:
        super().__init__()
        if in_channels != 2:
            raise ValueError(f"VanillaUNet requires in_channels=2, got {in_channels}")
        if num_classes != 1:
            raise ValueError(f"VanillaUNet requires num_classes=1, got {num_classes}")

        self.in_channels = in_channels
        self.num_classes = num_classes
        c = base_channels

        # Encoder
        self.inc = DoubleConv(in_channels, c)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c, c * 2))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c * 2, c * 4))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c * 4, c * 8))
        self.down4 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c * 8, c * 16))

        # Decoder
        self.up4 = DecoderBlock(c * 16, c * 8, c * 8)
        self.up3 = DecoderBlock(c * 8, c * 4, c * 4)
        self.up2 = DecoderBlock(c * 4, c * 2, c * 2)
        self.up1 = DecoderBlock(c * 2, c, c)

        self.outc = nn.Conv2d(c, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 4:
            raise ValueError(f"Expected 4D input [B, C, H, W], got {x.dim()}D")
        if x.shape[1] != self.in_channels:
            raise ValueError(f"Expected {self.in_channels} input channels, got {x.shape[1]}")
        h, w = x.shape[-2:]
        if h % 16 != 0 or w % 16 != 0:
            raise ValueError(f"Input dimensions ({h}x{w}) must be divisible by 16")

        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        d4 = self.up4(x5, x4)
        d3 = self.up3(d4, x3)
        d2 = self.up2(d3, x2)
        d1 = self.up1(d2, x1)

        logits = self.outc(d1)
        return logits


def count_parameters(model: nn.Module) -> dict[str, int]:
    """Measure exact total and trainable parameter counts for a model.

    Returns
    -------
    dict[str, int]
        {"total": int, "trainable": int, "non_trainable": int}
    """
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return {
        "total": total,
        "trainable": trainable,
        "non_trainable": total - trainable,
    }
