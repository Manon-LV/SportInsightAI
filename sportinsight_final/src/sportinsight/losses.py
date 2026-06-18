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


class OHEMLoss(DenseAnchorLoss):
    """Focal BCE + OHEM: only the hardest `ohem_ratio` fraction of negatives contribute."""

    def __init__(self, ohem_ratio: float = 0.25, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ohem_ratio = float(ohem_ratio)

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

        weights = torch.ones_like(target)
        cw = self.class_weights.to(target.device)
        if cw.numel() == target.shape[-1]:
            weights = weights + target * (cw.view(1, 1, -1) - 1.0)

        per_elem = bce * focal * weights

        is_pos = (target > 0.5) & (mask > 0.5)
        is_neg = (target < 0.5) & (mask > 0.5)

        pos_loss = (per_elem * is_pos.float()).sum()
        n_pos = float(is_pos.float().sum())

        neg_losses = per_elem[is_neg]
        if neg_losses.numel() > 0:
            k = max(1, int(neg_losses.numel() * self.ohem_ratio))
            k = min(k, neg_losses.numel())
            hard, _ = neg_losses.topk(k)
            neg_loss = hard.sum()
            n_neg = float(k)
        else:
            neg_loss = per_elem.sum() * 0.0
            n_neg = 0.0

        return (pos_loss + neg_loss) / max(n_pos + n_neg, 1.0)


class AsymmetricLoss(DenseAnchorLoss):
    """Asymmetric Focal Loss (Ridnik et al. 2021) for multi-label imbalance.

    Positives: L+ = (1-p)^gamma_pos * -log(p)
    Negatives: L- = (p_m)^gamma_neg * -log(1-p_m),  p_m = max(p - shift, 0)
    """

    def __init__(
        self,
        gamma_pos: float = 1.0,
        gamma_neg: float = 4.0,
        prob_shift: float = 0.05,
        **kwargs,
    ) -> None:
        kwargs.pop("focal_gamma", None)
        super().__init__(focal_gamma=0.0, **kwargs)
        self.gamma_pos = float(gamma_pos)
        self.gamma_neg = float(gamma_neg)
        self.prob_shift = float(prob_shift)

    def classification_loss(
        self,
        logits: torch.Tensor,
        target: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        target = target.float()
        mask = mask.float()

        prob = torch.sigmoid(logits)
        prob_m = (prob - self.prob_shift).clamp(min=0.0)

        loss_pos = (1.0 - prob).pow(self.gamma_pos) * (-torch.log(prob.clamp(min=1e-8)))
        loss_neg = prob_m.pow(self.gamma_neg) * (-torch.log((1.0 - prob_m).clamp(min=1e-8)))
        loss = target * loss_pos + (1.0 - target) * loss_neg

        cw = self.class_weights.to(target.device)
        if cw.numel() == target.shape[-1]:
            loss = loss * (1.0 + target * (cw.view(1, 1, -1) - 1.0))

        loss = loss * mask
        return loss.sum() / mask.sum().clamp_min(1.0)


class CALFLoss(DenseAnchorLoss):
    """Focal BCE + régression avec pondération temporelle asymétrique inspirée de CALF.

    Remplace le masque binaire cls_mask par une matrice K continue calculée à partir
    de context_dist (distance signée anchor → événement le plus proche) :

        dist > 0  (anchor APRÈS l'action)  → K = k_after   (pleine pénalité, détection certaine)
        dist ∈ [-margin_before, 0)         → K = 0         (zone ambiguë, pas de pénalité)
        dist < -margin_before              → K = k_before  (contexte avant, pénalité réduite)
        dist = +inf (aucun événement)      → K = k_bg      (arrière-plan standard)

    Si context_dist est absent du batch, repli sur DenseAnchorLoss standard.

    Paramètres
    ----------
    margin_before_sec : taille de la zone ambiguë avant l'action (= ignore_radius_sec du dataset)
    k_before          : poids sur les frames loin avant un événement (< 1.0 recommandé)
    k_after           : poids sur les frames après un événement (≥ 1.0 recommandé)
    k_bg              : poids sur les frames sans événement à proximité
    """

    def __init__(
        self,
        margin_before_sec: float = 5.0,
        positive_radius_sec: float = 2.0,
        k_before: float = 0.5,
        k_after: float = 1.0,
        k_bg: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.margin_before_sec = float(margin_before_sec)
        self.positive_radius_sec = float(positive_radius_sec)
        self.k_before = float(k_before)
        self.k_after = float(k_after)
        self.k_bg = float(k_bg)

    def _calf_weights(self, context_dist: torch.Tensor) -> torch.Tensor:
        """[B, L, C] → [B, L, C] poids K selon la zone temporelle.

        Zones (dist = anchor_time - event_time) :
          dist >= -positive_radius (fini) : zone positive + après → K = k_after
          dist ∈ (-margin_before, -positive_radius) : zone ambiguë avant → K = 0
          dist < -margin_before            : loin avant → K = k_before
          dist = +inf                      : arrière-plan → K = k_bg
        """
        K = torch.full_like(context_dist, self.k_bg)

        # Zone positive et après l'événement (dist ≥ -positive_radius, fini) → k_after
        pos_or_after = context_dist.ge(-self.positive_radius_sec) & context_dist.isfinite()
        K = K.masked_fill(pos_or_after, self.k_after)

        # Zone ambiguë juste avant (-margin_before ≤ dist < -positive_radius) → 0
        just_before = context_dist.ge(-self.margin_before_sec) & context_dist.lt(-self.positive_radius_sec)
        K = K.masked_fill(just_before, 0.0)

        # Loin avant l'événement (dist < -margin_before) → k_before
        far_before = context_dist.lt(-self.margin_before_sec)
        K = K.masked_fill(far_before, self.k_before)

        return K

    def classification_loss(
        self,
        logits: torch.Tensor,
        target: torch.Tensor,
        mask: torch.Tensor,
        context_dist: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if context_dist is None:
            return super().classification_loss(logits, target, mask)

        target = target.float()

        bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        prob = torch.sigmoid(logits)
        p_t = prob * target + (1.0 - prob) * (1.0 - target)
        focal = (1.0 - p_t).clamp(min=0.0).pow(self.focal_gamma)

        cw = self.class_weights.to(target.device)
        class_w = torch.ones_like(target)
        if cw.numel() == target.shape[-1]:
            class_w = class_w + target * (cw.view(1, 1, -1) - 1.0)

        K = self._calf_weights(context_dist.to(target.device))

        loss = bce * focal * class_w * K
        denom = K.sum().clamp_min(1.0)
        return loss.sum() / denom

    def forward(
        self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]
    ) -> dict[str, torch.Tensor]:
        cls_loss = self.classification_loss(
            outputs["cls_logits"],
            batch["cls_target"],
            batch["cls_mask"],
            context_dist=batch.get("context_dist"),
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
    loss_type = str(loss_cfg.get("type", "focal")).lower()

    common = dict(
        class_weights=loss_cfg.get("class_weights", None),
        lambda_cls=float(loss_cfg.get("lambda_cls", 1.0)),
        lambda_reg=float(loss_cfg.get("lambda_reg", 0.5)),
        smooth_l1_beta=float(loss_cfg.get("smooth_l1_beta", 1.0)),
    )

    if loss_type == "calf":
        return CALFLoss(
            margin_before_sec=float(loss_cfg.get("margin_before_sec", 5.0)),
            positive_radius_sec=float(loss_cfg.get("positive_radius_sec", 2.0)),
            k_before=float(loss_cfg.get("k_before", 0.5)),
            k_after=float(loss_cfg.get("k_after", 1.0)),
            k_bg=float(loss_cfg.get("k_bg", 1.0)),
            focal_gamma=float(loss_cfg.get("focal_gamma", 2.0)),
            **common,
        )
    if loss_type == "ohem":
        return OHEMLoss(
            ohem_ratio=float(loss_cfg.get("ohem_ratio", 0.25)),
            focal_gamma=float(loss_cfg.get("focal_gamma", 2.0)),
            **common,
        )
    if loss_type == "asl":
        return AsymmetricLoss(
            gamma_pos=float(loss_cfg.get("gamma_pos", 1.0)),
            gamma_neg=float(loss_cfg.get("gamma_neg", 4.0)),
            prob_shift=float(loss_cfg.get("prob_shift", 0.05)),
            **common,
        )
    return DenseAnchorLoss(
        focal_gamma=float(loss_cfg.get("focal_gamma", 2.0)),
        **common,
    )
