from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from radvrp import Instance, generate, load_config
from radvrp.decay import delay_budget_h, production_multiplier
from radvrp.instance import DEPOT

CONFIGS = Path(__file__).resolve().parents[1] / "configs"


@pytest.fixture(scope="module")
def toy():
    return generate(load_config(CONFIGS / "toy_e6.yaml"))


@pytest.fixture(scope="module", params=["small", "medium", "large"])
def random_inst(request):
    return generate(load_config(CONFIGS / f"{request.param}.yaml"))


# ---------------------------------------------------------------- toy (E6)
def test_toy_latest_direct_batch(toy):
    # 09:00 treatment - 2 h lead - 30 min drive - 1 h QC = 05:30; 13:00 -> 09:30
    assert toy.patients.loc["P1", "latest_direct_batch_min"] == 5 * 60 + 30
    assert toy.patients.loc["P2", "latest_direct_batch_min"] == 9 * 60 + 30


def test_toy_lower_bounds_match_hand_calculation(toy):
    lb = toy.patients["lb_mbq"]
    assert lb["P1"] == pytest.approx(280.0, abs=0.1)   # At-211, 3.5 h
    assert lb["P2"] == pytest.approx(280.0, abs=0.1)
    assert lb["P3"] == pytest.approx(207.7, abs=0.1)   # Y-90, 3.5 h
    assert lb["P4"] == pytest.approx(207.7, abs=0.1)


def test_toy_single_truck_production_matches_e6(toy):
    # One truck serving both hospitals must finish its batch by 05:30 (H1's constraint).
    lam = toy.isotopes.at["At-211", "lambda_per_h"]
    produced = 200 * production_multiplier(lam, 9 * 60, 330) + 200 * production_multiplier(lam, 13 * 60, 330)
    assert produced == pytest.approx(691.1, abs=0.1)


def test_toy_is_valid(toy):
    assert toy.validate() == []


# ------------------------------------------------------------- decay maths
def test_route_invariance():
    # Transit decay x storage decay depends only on total elapsed time (DESIGN_NOTES §5.1).
    lam = np.log(2) / 7.214
    for arrival in (360, 480, 600):
        split = production_multiplier(lam, arrival, 300) * production_multiplier(lam, 660, arrival)
        assert split == pytest.approx(production_multiplier(lam, 660, 300))


def test_delay_budget_at211():
    assert delay_budget_h(np.log(2) / 7.214, 0.20) == pytest.approx(2.32, abs=0.01)


# ------------------------------------------------------- random instances
def test_random_valid(random_inst):
    assert random_inst.validate() == []


def test_reproducible():
    a = generate(load_config(CONFIGS / "small.yaml"))
    b = generate(load_config(CONFIGS / "small.yaml"))
    pd.testing.assert_frame_equal(a.patients, b.patients)
    pd.testing.assert_frame_equal(a.nodes, b.nodes)


def test_every_isotope_present(random_inst):
    assert set(random_inst.patients["isotope"]) == set(random_inst.isotopes.index)


def test_doses_within_models(random_inst):
    p = random_inst.patients
    y = p.loc[p["isotope"] == "Y-90", "dose_mbq"]
    assert y.between(500, 3000).all()
    pb = p[p["isotope"] == "Pb-212"]
    assert (pb["dose_mbq"] <= 203.5 + 1e-9).all()
    at = p[p["isotope"] == "At-211"]
    per_kg = at["dose_mbq"] / at["weight_kg"]
    assert per_kg.between(1.25 - 0.01, 3.5 + 0.01).all()


def test_cap_is_kappa_times_lb(random_inst):
    lb = random_inst.patients.groupby("isotope")["lb_mbq"].sum()
    kappa = random_inst.ops.capacity_factor
    for iso, cap in random_inst.isotopes["daily_cap_mbq"].items():
        assert cap == pytest.approx(kappa * lb[iso])


def test_travel_symmetric(random_inst):
    t = random_inst.travel_min.values
    assert np.allclose(t, t.T)
    assert (random_inst.travel_min.loc[DEPOT] >= 0).all()


def test_save_load_roundtrip(tmp_path):
    inst = generate(load_config(CONFIGS / "small.yaml"))
    back = Instance.load(inst.save(tmp_path / "small"))
    pd.testing.assert_frame_equal(inst.patients, back.patients, check_dtype=False)
    pd.testing.assert_frame_equal(inst.nodes, back.nodes, check_dtype=False)
    assert back.ops == inst.ops
    assert back.validate() == []
