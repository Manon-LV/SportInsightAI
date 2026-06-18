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


class TemporalAttentionBlock(nn.Module):
    """Pre-norm transformer block for global temporal context.

    Applied at the U-Net bottleneck where the sequence is ~8x shorter,
    enabling full self-attention across the 120s window at low cost.
    Inspired by the temporal pooling module in CALF and E2E-Spot architectures.
    """

    def __init__(self, channels: int, num_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(channels)
        self.attn = nn.MultiheadAttention(channels, num_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(channels)
        self.ffn = nn.Sequential(
            nn.Linear(channels, channels * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(channels * 2, channels),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, C, T]
        x_t = x.transpose(1, 2)  # [B, T, C]
        n = self.norm1(x_t)
        attn_out, _ = self.attn(n, n, n)
        x_t = x_t + self.drop(attn_out)
        x_t = x_t + self.drop(self.ffn(self.norm2(x_t)))
        return x_t.transpose(1, 2)  # [B, C, T]


class GRUNeck(nn.Module):
    """Bidirectional GRU neck with residual connection.

    Applied after the U-Net decoder to capture sequential temporal dependencies
    across the full 120s window. Mirrors the GRU head used in E2E-Spot.
    """

    def __init__(self, channels: int, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        gru_dropout = dropout if num_layers > 1 else 0.0
        self.gru = nn.GRU(
            channels, channels // 2,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=gru_dropout,
        )
        self.norm = nn.LayerNorm(channels)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, C]
        out, _ = self.gru(x)
        return self.norm(x + self.drop(out))


class UNet1D(nn.Module):
    """1D U-Net with optional multi-head self-attention at the bottleneck."""

    def __init__(self, channels: int = 256, num_layers: int = 3, dropout: float = 0.1, use_attention: bool = True):
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

        # num_heads: 4 pour 256-dim (64-dim par tête), 8 pour 512-dim
        num_heads = max(1, ch // 64)
        if use_attention:
            self.bottleneck = nn.Sequential(
                ConvBlock1D(ch, ch, dropout=dropout, dilation=2),
                TemporalAttentionBlock(ch, num_heads=num_heads, dropout=dropout),
            )
        else:
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


class TemporalDropout(nn.Module):
    """Masque chaque position temporelle avec probabilité p et la remplace par
    un token appris. Actif uniquement en mode training.

    Reproduit le Temporal Dropout d'ASTRA (Xarles et al., 2024) :
    ptd=0.5, appliqué après la projection sur l'espace caché.
    """

    def __init__(self, channels: int, p: float = 0.5):
        super().__init__()
        self.p = float(p)
        self.mask_token = nn.Parameter(torch.zeros(channels))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, C]
        if not self.training or self.p <= 0.0:
            return x
        mask = torch.rand(x.shape[0], x.shape[1], device=x.device) < self.p
        token = self.mask_token.view(1, 1, -1).expand_as(x)
        return torch.where(mask.unsqueeze(-1), token, x)


class DenseAnchorSpotter(nn.Module):
    """Dense temporal anchor model for SoccerNet action spotting.

    Architecture:
      Input [B, T, 512]
        → Learned linear projection [B, T, H]
        → TemporalDropout (masque aléatoire des positions, ASTRA 2024)
        → U-Net 1D encoder/decoder (multi-scale local features)
           └─ bottleneck: Conv + Multi-Head Self-Attention (global context)
        → BiGRU neck (sequential temporal modeling)
        → cls_head: [B, T, C] logits
        → reg_head: [B, T, C] offsets in seconds
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
        use_attention_bottleneck: bool = True,
        temporal_neck: str = "gru",
        temporal_dropout_p: float = 0.0,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.requested_hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.max_offset_sec = float(max_offset_sec)
        self.use_projection = bool(use_projection)

        # Backward-compatible name: existing checkpoints contain keys under `proj.*`.
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

        self.temporal_drop: nn.Module | None = (
            TemporalDropout(model_dim, p=temporal_dropout_p)
            if temporal_dropout_p > 0.0 else None
        )

        if backbone == "unet":
            self.backbone = UNet1D(
                model_dim, num_layers=num_layers, dropout=dropout,
                use_attention=use_attention_bottleneck,
            )
        elif backbone == "tcn":
            self.backbone = TCN1D(model_dim, num_layers=max(3, num_layers + 2), dropout=dropout)
        else:
            raise ValueError(f"Unknown backbone {backbone!r}. Expected 'unet' or 'tcn'.")

        if temporal_neck == "gru":
            self.neck: nn.Module | None = GRUNeck(model_dim, dropout=dropout)
        else:
            self.neck = None

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
        if self.temporal_drop is not None:
            z = self.temporal_drop(z) # [B, T, H] — masquage train only
        z = z.transpose(1, 2)         # [B, H, T]
        z = self.backbone(z)          # [B, H, T]
        z = z.transpose(1, 2)         # [B, T, H]
        if self.neck is not None:
            z = self.neck(z)          # [B, T, H]
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
        use_attention_bottleneck=bool(model_cfg.get("use_attention_bottleneck", True)),
        temporal_neck=str(model_cfg.get("temporal_neck", "gru")),
        temporal_dropout_p=float(model_cfg.get("temporal_dropout_p", 0.0)),
    )
