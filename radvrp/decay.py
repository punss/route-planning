"""Radioactive decay maths.

A(t) = A0 * exp(-lambda * t),  lambda = ln 2 / half-life.

The key modelling identity (DESIGN_NOTES §5.1): the activity that must be
produced at time P so that x is left at time tau is x * exp(lambda*(tau - P)).
It depends only on tau - P, not on where the vial spends that time.
"""

from __future__ import annotations

import numpy as np

LN2 = np.log(2.0)


def decay_constant_per_h(half_life_h: float) -> float:
    return LN2 / half_life_h


def remaining_fraction(lambda_per_h: float, elapsed_min):
    """Fraction of activity left after `elapsed_min` minutes."""
    return np.exp(-lambda_per_h * np.asarray(elapsed_min) / 60.0)


def production_multiplier(lambda_per_h: float, treatment_min, batch_min):
    """mu = exp(lambda * (tau - P)): produced activity per unit of prescribed activity."""
    return np.exp(lambda_per_h * (np.asarray(treatment_min) - np.asarray(batch_min)) / 60.0)


def delay_budget_h(lambda_per_h: float, tolerance: float) -> float:
    """Treatment delay a patient dosed at x can absorb before falling below (1 - tol) * x."""
    return float(np.log(1.0 / (1.0 - tolerance)) / lambda_per_h)
