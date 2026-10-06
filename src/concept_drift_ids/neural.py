from __future__ import annotations

import math
import os
import random

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
from scipy.stats import t
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class BinaryMLP(nn.Module):
    """Compact binary MLP shared by neural-only and later matched systems."""

    def __init__(
        self,
        *,
        input_features: int,
        hidden_layers: tuple[int, ...],
        dropout: float,
    ) -> None:
        super().__init__()

        layers: list[nn.Module] = []
        previous = input_features
        for width in hidden_layers:
            layers.extend(
                (
                    nn.Linear(previous, width),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                )
            )
            previous = width
        layers.append(nn.Linear(previous, 1))

        self.network = nn.Sequential(*layers)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, nonlinearity="relu")
                nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(1)


def set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    torch.use_deterministic_algorithms(True, warn_only=True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")
    return device


@torch.inference_mode()
def predict_probabilities(
    model: nn.Module,
    X: np.ndarray,
    *,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()
    loader = DataLoader(
        TensorDataset(torch.from_numpy(X)),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )

    chunks: list[np.ndarray] = []
    for (batch_X,) in loader:
        logits = model(batch_X.to(device=device, non_blocking=False))
        chunks.append(torch.sigmoid(logits).cpu().numpy())

    return np.concatenate(chunks).astype(np.float64, copy=False)


def binary_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float]:
    y = np.asarray(y_true, dtype=np.int8)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    prediction = (probabilities >= threshold).astype(np.int8)

    benign = y == 0
    fp = int(np.logical_and(prediction == 1, benign).sum())
    tn = int(np.logical_and(prediction == 0, benign).sum())
    fpr = fp / (fp + tn) if fp + tn else 0.0

    return {
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "fpr": float(fpr),
        "mcc": float(matthews_corrcoef(y, prediction)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "average_precision": float(
            average_precision_score(y, probabilities)
        ),
    }


def select_mcc_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[float, dict[str, float]]:
    """Select threshold by MCC, then F1, lower FPR, closeness to 0.5."""
    y = np.asarray(y_true, dtype=np.int8)
    probabilities = np.asarray(probabilities, dtype=np.float64)

    fpr, tpr, thresholds = roc_curve(
        y,
        probabilities,
        drop_intermediate=False,
    )
    finite = np.isfinite(thresholds)
    fpr, tpr, thresholds = fpr[finite], tpr[finite], thresholds[finite]

    positives = int((y == 1).sum())
    negatives = int((y == 0).sum())

    tp = tpr * positives
    fn = positives - tp
    fp = fpr * negatives
    tn = negatives - fp

    denominator = np.sqrt(
        (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    )
    mcc = np.divide(
        tp * tn - fp * fn,
        denominator,
        out=np.zeros_like(tp),
        where=denominator != 0,
    )

    precision = np.divide(
        tp,
        tp + fp,
        out=np.zeros_like(tp),
        where=(tp + fp) != 0,
    )
    recall = np.divide(
        tp,
        tp + fn,
        out=np.zeros_like(tp),
        where=(tp + fn) != 0,
    )
    f1 = np.divide(
        2.0 * precision * recall,
        precision + recall,
        out=np.zeros_like(tp),
        where=(precision + recall) != 0,
    )

    best = max(
        range(len(thresholds)),
        key=lambda i: (
            float(mcc[i]),
            float(f1[i]),
            -float(fpr[i]),
            -abs(float(thresholds[i]) - 0.5),
        ),
    )
    threshold = float(np.clip(thresholds[best], 0.0, 1.0))
    return threshold, binary_metrics(y, probabilities, threshold)


def mean_ci95(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    mean = float(array.mean())
    if len(array) < 2:
        return {"mean": mean, "ci95_low": mean, "ci95_high": mean}

    sem = float(array.std(ddof=1) / math.sqrt(len(array)))
    margin = float(t.ppf(0.975, df=len(array) - 1) * sem)
    return {
        "mean": mean,
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
    }
