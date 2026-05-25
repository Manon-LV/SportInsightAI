from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class ConvBlock1D(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int = 3, dropout: float = 0.0, dilation: int = 1):
        super().__init__()
        padding = dilation * (kernel_size // 2)
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel_size, padding=padding, dilation=dilation),
            nn.BatchNorm1d(out_ch),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(out_ch, out_ch, kernel_size, padding=padding, dilation=dilation),
            nn.BatchNorm1d(out_ch),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class UNet1D(nn.Module):
    """Small 1D U-Net preserving temporal resolution."""

    def __init__(self, channels: int = 256, num_layers: int = 3, dropout: float = 0.1):
        super().__init__()
        self.num_layers = num_layers
        self.enc_blocks = nn.ModuleList()
        self.downs = nn.ModuleList()
        self.dec_blocks = nn.ModuleList()
        self.up_projs = nn.ModuleList()

        ch = channels
        for _ in range(num_layers):
            self.enc_blocks.append(ConvBlock1D(ch, ch, dropout=dropout))
            self.downs.append(nn.Conv1d(ch, ch, kernel_size=4, stride=2, padding=1))

        self.bottleneck = ConvBlock1D(ch, ch, dropout=dropout, dilation=2)

        for _ in range(num_layers):
            self.up_projs.append(nn.Conv1d(ch, ch, kernel_size=1))
            self.dec_blocks.append(ConvBlock1D(ch * 2, ch, dropout=dropout))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, C, T]
        skips = []
        out = x
        for enc, down in zip(self.enc_blocks, self.downs):
            out = enc(out)
            skips.append(out)
            out = down(out)

        out = self.bottleneck(out)

        for up_proj, dec in zip(self.up_projs, self.dec_blocks):
            skip = skips.pop()
            out = F.interpolate(out, size=skip.shape[-1], mode="linear", align_corners=False)
            out = up_proj(out)
            out = torch.cat([out, skip], dim=1)
            out = dec(out)
        return out


class TCN1D(nn.Module):
    """Dilated temporal convolutional fallback. Simpler than U-Net."""

    def __init__(self, channels: int = 256, num_layers: int = 5, dropout: float = 0.1):
        super().__init__()
        blocks = []
        for i in range(num_layers):
            dilation = 2 ** i
            blocks.append(ConvBlock1D(channels, channels, dropout=dropout, dilation=dilation))
        self.blocks = nn.ModuleList(blocks)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = x
        for block in self.blocks:
            out = out + block(out)
        return out


class DenseAnchorSpotter(nn.Module):
    """Dense temporal anchor model for SoccerNet action spotting.

    Inputs are feature sequences [B, T, input_dim]. Outputs are:
      - cls_logits: [B, T, C]
      - offsets: [B, T, C], seconds, bounded by max_offset_sec
    """

    def __init__(
        self,
        input_dim: int = 512,
        hidden_dim: int = 256,
        num_classes: int = 4,
        num_layers: int = 3,
        dropout: float = 0.2,
        backbone: str = "unet",
        max_offset_sec: float = 5.0,
        use_projection: bool = True,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.requested_hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.max_offset_sec = float(max_offset_sec)
        self.use_projection = bool(use_projection)

        # Backward-compatible name: existing checkpoints contain keys under `proj.*`.
        # When use_projection=False, the model keeps the 512-d feature space and only
        # normalizes/regularizes the pre-extracted ResNet PCA descriptors.
        if self.use_projection:
            self.proj = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout),
            )
            model_dim = hidden_dim
        else:
            self.proj = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Dropout(dropout),
            )
            model_dim = input_dim

        self.hidden_dim = model_dim

        if backbone == "unet":
            self.backbone = UNet1D(model_dim, num_layers=num_layers, dropout=dropout)
        elif backbone == "tcn":
            self.backbone = TCN1D(model_dim, num_layers=max(3, num_layers + 2), dropout=dropout)
        else:
            raise ValueError(f"Unknown backbone {backbone!r}. Expected 'unet' or 'tcn'.")

        head_dim = max(1, model_dim // 2)
        self.cls_head = nn.Sequential(
            nn.LayerNorm(model_dim),
            nn.Linear(model_dim, head_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(head_dim, num_classes),
        )
        self.reg_head = nn.Sequential(
            nn.LayerNorm(model_dim),
            nn.Linear(model_dim, head_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(head_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        # x: [B, T, D]
        z = self.proj(x)              # [B, T, H]
        z = z.transpose(1, 2)         # [B, H, T]
        z = self.backbone(z)          # [B, H, T]
        z = z.transpose(1, 2)         # [B, T, H]
        cls_logits = self.cls_head(z)
        offsets = torch.tanh(self.reg_head(z)) * self.max_offset_sec
        return {"cls_logits": cls_logits, "offsets": offsets, "features": z}


def build_model(config: dict) -> DenseAnchorSpotter:
    data_cfg = config.get("data", {})
    model_cfg = config.get("model", {})
    classes = data_cfg.get("classes", ["Goal", "Corner", "Yellow card", "Red card"])
    return DenseAnchorSpotter(
        input_dim=int(model_cfg.get("input_dim", 512)),
        hidden_dim=int(model_cfg.get("hidden_dim", 256)),
        num_classes=len(classes),
        num_layers=int(model_cfg.get("num_layers", 3)),
        dropout=float(model_cfg.get("dropout", 0.2)),
        backbone=str(model_cfg.get("backbone", "unet")),
        max_offset_sec=float(model_cfg.get("max_offset_sec", 5.0)),
        use_projection=bool(model_cfg.get("use_projection", True)),
    )
