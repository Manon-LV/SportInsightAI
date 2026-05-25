from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class DenseAnchorLoss(nn.Module):
    """Focal BCE classification + Smooth L1 temporal offset regression."""

    def __init__(
        self,
        class_weights: list[float] | torch.Tensor | None = None,
        focal_gamma: float = 2.0,
        lambda_cls: float = 1.0,
        lambda_reg: float = 0.5,
        smooth_l1_beta: float = 1.0,
    ) -> None:
        super().__init__()
        if class_weights is None:
            class_weights = torch.ones(1)
        class_weights = torch.as_tensor(class_weights, dtype=torch.float32)
        self.register_buffer("class_weights", class_weights)
        self.focal_gamma = float(focal_gamma)
        self.lambda_cls = float(lambda_cls)
        self.lambda_reg = float(lambda_reg)
        self.smooth_l1_beta = float(smooth_l1_beta)

    def classification_loss(
        self,
        logits: torch.Tensor,
        target: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        target = target.float()
        mask = mask.float()

        bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        prob = torch.sigmoid(logits)
        p_t = prob * target + (1.0 - prob) * (1.0 - target)
        focal = (1.0 - p_t).clamp(min=0.0).pow(self.focal_gamma)

        # Positive class weighting. We do not over-weight all negatives of rare classes.
        weights = torch.ones_like(target)
        cw = self.class_weights.to(target.device)
        if cw.numel() == target.shape[-1]:
            weights = weights + target * (cw.view(1, 1, -1) - 1.0)

        loss = bce * focal * weights * mask
        denom = mask.sum().clamp_min(1.0)
        return loss.sum() / denom

    def regression_loss(
        self,
        pred_offsets: torch.Tensor,
        target_offsets: torch.Tensor,
        reg_mask: torch.Tensor,
    ) -> torch.Tensor:
        reg_mask = reg_mask.float()
        if reg_mask.sum() < 1:
            return pred_offsets.sum() * 0.0
        loss = F.smooth_l1_loss(
            pred_offsets,
            target_offsets.float(),
            beta=self.smooth_l1_beta,
            reduction="none",
        )
        loss = loss * reg_mask
        return loss.sum() / reg_mask.sum().clamp_min(1.0)

    def forward(self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        cls_loss = self.classification_loss(
            outputs["cls_logits"],
            batch["cls_target"],
            batch["cls_mask"],
        )
        reg_loss = self.regression_loss(
            outputs["offsets"],
            batch["reg_target"],
            batch["reg_mask"],
        )
        total = self.lambda_cls * cls_loss + self.lambda_reg * reg_loss
        return {"loss": total, "loss_cls": cls_loss, "loss_reg": reg_loss}


def build_loss(config: dict) -> DenseAnchorLoss:
    loss_cfg = config.get("loss", {})
    return DenseAnchorLoss(
        class_weights=loss_cfg.get("class_weights", None),
        focal_gamma=float(loss_cfg.get("focal_gamma", 2.0)),
        lambda_cls=float(loss_cfg.get("lambda_cls", 1.0)),
        lambda_reg=float(loss_cfg.get("lambda_reg", 0.5)),
        smooth_l1_beta=float(loss_cfg.get("smooth_l1_beta", 1.0)),
    )
