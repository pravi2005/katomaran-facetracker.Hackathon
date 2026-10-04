import numpy as np
import pytest

from app.recognition.calibration import compute_report


def vec(seed, dim=32):
    return np.random.default_rng(seed).normal(size=dim)


def test_separable_groups_give_threshold_between_distributions():
    rng = np.random.default_rng(0)
    a, b = vec(1), vec(2)
    groups = {"a": [a + rng.normal(scale=0.1, size=32) for _ in range(5)],
              "b": [b + rng.normal(scale=0.1, size=32) for _ in range(5)]}
    report = compute_report(groups)
    assert report.separable and report.same_p05 > report.different_p95
    assert report.different_p95 < report.suggested_threshold < report.same_p05
    assert report.same_count == 20 and report.different_count == 25


def test_overlapping_groups_not_separable():
    rng = np.random.default_rng(0)
    base = vec(3)
    groups = {"a": [base + rng.normal(scale=2.0, size=32) for _ in range(4)],
              "b": [base + rng.normal(scale=2.0, size=32) for _ in range(4)]}
    assert compute_report(groups).suggested_threshold is None


def test_needs_enough_data():
    with pytest.raises(ValueError):
        compute_report({"a": [vec(1), vec(2)]})
