"""Assign trips to physical trucks (and drivers) after solving.

The model never decides which truck does which trip (DESIGN_NOTES §5.5):
trucks and drivers are interchangeable and every trip starts and ends at
the depot. Trips therefore form an *interval graph*. The minimum number of
trucks equals the maximum number of trips occupying a truck at the same
time, and the greedy rule below (in order of departure, reuse any truck
that is back and turned around, otherwise add one) always achieves it.

This is used for presentation ("Truck 2 does T0 then T2") and, in Phase 2b,
to check a fleet cap independently of the MILP. Drivers are shown paired
with trucks; any pairing works because drivers are interchangeable too.
"""

from __future__ import annotations

from .checker import Trip, simulate
from .instance import Instance


def busy_intervals(inst: Instance, trips: list[Trip]) -> list[tuple[float, float]]:
    """(start, end) a truck is occupied per trip: departure → return + turnaround."""
    out = []
    for tr in trips:
        sc = simulate(inst, tr)
        out.append((sc.depart_min, sc.return_min + inst.ops.turnaround_min))
    return out


def assign_trucks(inst: Instance, trips: list[Trip]) -> list[int]:
    """Truck number (1-based) per trip; uses the minimum possible number of trucks."""
    iv = busy_intervals(inst, trips)
    free_at: list[float] = []            # free_at[v] = time truck v+1 is available again
    truck = [0] * len(trips)
    for n in sorted(range(len(trips)), key=lambda n: iv[n][0]):
        start, end = iv[n]
        avail = [v for v, f in enumerate(free_at) if f <= start + 1e-9]
        v = min(avail) if avail else len(free_at)   # lowest-numbered free truck, for readability
        if v == len(free_at):
            free_at.append(end)
        else:
            free_at[v] = end
        truck[n] = v + 1
    return truck


def max_overlap(inst: Instance, trips: list[Trip]) -> int:
    """Peak number of trucks busy at once (independent of `assign_trucks`)."""
    events = sorted([(s, 1) for s, _ in busy_intervals(inst, trips)] +
                    [(e, -1) for _, e in busy_intervals(inst, trips)], key=lambda x: (x[0], x[1]))
    cur = peak = 0
    for _, delta in events:            # ends sort before starts at equal times: back-to-back reuse OK
        cur += delta
        peak = max(peak, cur)
    return peak
