"""
Scoring-agreement evaluation.

Measures how well the AI's match score agrees with the user's own judgment —
the honest foundation for any score recalibration (you can't tune weights
without first measuring whether they're right).

Ground truth ("would I apply?") comes from two sources, merged:
  1. Application decisions: applied/replied/interview/offer => 1, rejected => 0
  2. A manual labels file (data/eval_labels.json): {job_id: 1|0} — overrides (1)

The metric is precision/recall/F1/accuracy of "AI score >= threshold" against
the user's would-apply label.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from jobpilot import config
from jobpilot.db import JobPilotDB

logger = logging.getLogger(__name__)

# Application statuses that signal the user wanted the job
POSITIVE_STATUSES = frozenset({"applied", "replied", "interview", "offer"})
NEGATIVE_STATUSES = frozenset({"rejected"})

DEFAULT_LABELS_PATH = "data/eval_labels.json"


@dataclass(frozen=True)
class EvalResult:
    """Outcome of a scoring-agreement evaluation."""

    threshold: float
    n: int
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.n if self.n else 0.0


def load_labels(
    db: JobPilotDB,
    labels_path: str | None = DEFAULT_LABELS_PATH,
    *,
    profile_id: int = config.DEFAULT_PROFILE_ID,
) -> dict[str, int]:
    """Merge application-derived labels with an optional manual labels file.

    File labels take precedence over application-derived ones.
    """
    labels: dict[str, int] = {}

    # 1. Application decisions
    for app in db.list_applications():
        if app.status in POSITIVE_STATUSES:
            labels[app.job_id] = 1
        elif app.status in NEGATIVE_STATUSES:
            labels[app.job_id] = 0

    # 2. Manual labels file (authoritative)
    if labels_path:
        path = Path(labels_path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for job_id, val in data.items():
                    labels[str(job_id)] = 1 if val else 0
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning("Failed to parse labels file %s: %s", labels_path, e)

    return labels


def read_labels_file(labels_path: str = DEFAULT_LABELS_PATH) -> dict[str, int]:
    """Read only the manual labels file (no application-derived labels)."""
    path = Path(labels_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse labels file %s: %s", labels_path, e)
        return {}
    return {str(k): (1 if v else 0) for k, v in data.items()}


def write_labels_file(labels: dict[str, int], labels_path: str = DEFAULT_LABELS_PATH) -> None:
    """Persist labels to the JSON file (sorted for stable diffs)."""
    path = Path(labels_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {k: labels[k] for k in sorted(labels)}
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate(
    db: JobPilotDB,
    labels: dict[str, int],
    *,
    threshold: float = config.MIN_RECOMMEND_SCORE,
    profile_id: int = config.DEFAULT_PROFILE_ID,
) -> EvalResult:
    """Compute scoring-agreement metrics over the labeled jobs.

    Only labeled jobs that also have an AI score are counted.
    """
    tp = fp = fn = tn = 0
    for job_id, label in labels.items():
        score = db.get_score(job_id, profile_id)
        if not score:
            continue
        predicted_positive = score.overall_score >= threshold
        actual_positive = label == 1
        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif not predicted_positive and actual_positive:
            fn += 1
        else:
            tn += 1

    return EvalResult(
        threshold=threshold,
        n=tp + fp + fn + tn,
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
    )
