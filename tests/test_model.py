"""Phase 2a validation (DESIGN_NOTES §5.7): hand-checkable toys, independent checker, waste split."""

import copy
from pathlib import Path

import pytest

from radvrp import generate, load_config
from radvrp.checker import Trip, check, simulate
from radvrp.model import SolveSettings, solve
from radvrp.report import waste_table

CONFIGS = Path(__file__).resolve().parents[1] / "configs"
WASTE_HEAVY = SolveSettings(w_over=1000, w_dist=0.001, w_trip=0.001)
ROUTE_HEAVY = SolveSettings(w_over=0.001, w_dist=1, w_trip=100)


def load(name):
    return generate(load_config(CONFIGS / f"{name}.yaml"))


def produced_by_isotope(inst, trips):
    return waste_table(inst, trips).groupby("isotope")["produced_mbq"].sum()


def trips_to(trips, hospital):
    return [t for t in trips if hospital in t.stops]


# --------------------------------------------------------------- E6 toy
def test_e6_waste_heavy_reaches_lower_bound():
    inst = load("toy_e6")
    res = solve(inst, WASTE_HEAVY)
    assert res.status == "optimal"
    assert len(res.trips) == 4                       # every vial on its own truck
    prod = produced_by_isotope(inst, res.trips)
    assert prod["At-211"] == pytest.approx(559.9, abs=0.1)   # 2 x 279.95
    assert prod["Y-90"] == pytest.approx(415.4, abs=0.1)
    assert check(inst, res.trips, res.claimed_produced, res.objectives["dist"]).ok


def test_e6_route_heavy_consolidates():
    inst = load("toy_e6")
    res = solve(inst, ROUTE_HEAVY)
    assert len(res.trips) == 2                       # one truck per isotope
    prod = produced_by_isotope(inst, res.trips)
    assert prod["At-211"] == pytest.approx(691.1, abs=0.1)
    assert prod["Y-90"] == pytest.approx(424.6, abs=0.1)
    assert check(inst, res.trips, res.claimed_produced, res.objectives["dist"]).ok


def test_e6_default_weights_split_only_the_short_isotope():
    # The isotope-dependent trade-off: a 2nd truck is worth it for At-211, not Y-90.
    inst = load("toy_e6")
    res = solve(inst, SolveSettings())
    by_iso = {i: sum(t.isotope == i for t in res.trips) for i in ("At-211", "Y-90")}
    assert by_iso == {"At-211": 2, "Y-90": 1}


def test_e6_lexicographic_waste_first():
    inst = load("toy_e6")
    res = solve(inst, SolveSettings(mode="lexicographic", priority=("over", "dist", "trip")))
    assert produced_by_isotope(inst, res.trips).sum() == pytest.approx(559.9 + 415.4, abs=0.2)
    res2 = solve(inst, SolveSettings(mode="lexicographic", priority=("trip", "dist", "over")))
    assert len(res2.trips) == 2


# ------------------------------------------------------------- splits
def test_capacity_forces_split():
    inst = load("toy_split_capacity")                # 7 vials, Pb-212 truck holds 6
    res = solve(inst, ROUTE_HEAVY)
    assert len(trips_to(res.trips, "H1")) == 2
    assert sorted(len(t.patients) for t in res.trips) in ([1, 6], [2, 5], [3, 4])
    assert check(inst, res.trips).ok


def test_no_split_when_capacity_allows():
    inst = load("toy_split_capacity")
    inst.isotopes.loc["Pb-212", "vials_per_truck"] = 20
    res = solve(inst, ROUTE_HEAVY)
    assert len(res.trips) == 1


def test_deadline_driven_split():
    inst = load("toy_split_deadline")
    assert len(trips_to(solve(inst, WASTE_HEAVY).trips, "H1")) == 2
    assert len(trips_to(solve(inst, ROUTE_HEAVY).trips, "H1")) == 1


# ------------------------------------------------------- random instances
@pytest.mark.parametrize("name", ["small", "medium"])
def test_random_instance_solves_and_checks(name):
    inst = load(name)
    res = solve(inst, SolveSettings(time_limit=120))
    assert res.status == "optimal"
    chk = check(inst, res.trips, res.claimed_produced, res.objectives["dist"])
    assert chk.ok, chk.violations
    # Every trip ends up at its latest feasible slot (the re-timing step).
    slot = inst.ops.batch_slot_min
    for t in res.trips:
        assert simulate(inst, t).latest_batch_min - t.batch_min < slot


def test_waste_split_adds_up_and_is_nonnegative():
    inst = load("small")
    res = solve(inst, SolveSettings())
    w = waste_table(inst, res.trips)
    parts = w[["irreducible_mbq", "routing_mbq", "discretization_mbq"]]
    assert (parts >= -1e-6).all().all()
    assert (parts.sum(axis=1) - (w["produced_mbq"] - w["dose_mbq"])).abs().max() < 1e-6
    # Solver's objective and the independent recomputation agree.
    assert w["waste_doses"].sum() == pytest.approx(res.objectives["over"], rel=1e-6)


# -------------------------------------- checker catches broken plans
@pytest.fixture(scope="module")
def good():
    inst = load("toy_e6")
    return inst, solve(inst, WASTE_HEAVY).trips


def _broken(trips, fn):
    t = copy.deepcopy(trips)
    fn(t)
    return t


@pytest.mark.parametrize("mutation, expected", [
    (lambda t: t.pop(), "delivered 0 times"),                                         # vial missing
    (lambda t: t.append(copy.deepcopy(t[0])), "delivered 2 times"),                   # vial twice
    (lambda t: setattr(t[0], "batch_min", t[0].batch_min + 120), "arrives"),         # batch too late
    (lambda t: setattr(t[0], "batch_min", t[0].batch_min + 7), "slot grid"),          # off-grid batch
    (lambda t: setattr(t[0], "isotope", "Y-90" if t[0].isotope == "At-211" else "At-211"), "needs"),
])
def test_checker_catches(good, mutation, expected):
    inst, trips = good
    res = check(inst, _broken(trips, mutation))
    assert not res.ok
    assert any(expected in v for v in res.violations), res.violations


def test_checker_catches_capacity(good):
    inst, _ = good
    inst2 = copy.deepcopy(inst)
    inst2.isotopes.loc["Y-90", "vials_per_truck"] = 1
    both = Trip("Y-90", 330, ["H1", "H2"], {"H1": ["P3"], "H2": ["P4"]})
    at = [Trip("At-211", 330, ["H1"], {"H1": ["P1"]}), Trip("At-211", 570, ["H2"], {"H2": ["P2"]})]
    assert any("capacity" in v for v in check(inst2, [both] + at).violations)


def test_checker_catches_underproduction_claim(good):
    inst, trips = good
    fake = {p: 1.0 for t in trips for p in t.patients}
    assert any("physics needs" in v for v in check(inst, trips, claimed_produced=fake).violations)


# ------------------------------------------- truck assignment (presentation)
@pytest.mark.parametrize("name", ["toy_e6", "small", "medium"])
def test_truck_assignment_is_minimal_and_non_overlapping(name):
    from radvrp.fleet import assign_trucks, busy_intervals, max_overlap

    inst = load(name)
    trips = solve(inst, SolveSettings()).trips
    truck, iv = assign_trucks(inst, trips), busy_intervals(inst, trips)
    assert max(truck) == max_overlap(inst, trips)          # interval-graph optimum
    for v in set(truck):
        mine = sorted(iv[n] for n in range(len(trips)) if truck[n] == v)
        assert all(a[1] <= b[0] + 1e-9 for a, b in zip(mine, mine[1:]))  # never double-booked
