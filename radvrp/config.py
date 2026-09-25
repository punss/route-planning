"""Config loading and clock-time helpers.

Times are handled internally as integer minutes after midnight of the
delivery day (DESIGN_NOTES §2). Configs use "HH:MM" strings for readability.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml


def hhmm_to_min(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def min_to_hhmm(t: float) -> str:
    t = int(round(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(path: str | Path) -> dict:
    """Load an instance config, resolving `extends` and the isotope data file.

    The returned dict has an `isotope_data` key holding the entries of
    `isotopes_file` for the isotopes listed in `isotopes`.
    """
    path = Path(path)
    with open(path) as f:
        cfg = yaml.safe_load(f)

    if "extends" in cfg:
        parent = load_config(path.parent / cfg.pop("extends"))
        parent.pop("isotope_data", None)
        cfg = _deep_merge(parent, cfg)

    with open(path.parent / cfg["isotopes_file"]) as f:
        all_iso = yaml.safe_load(f)["isotopes"]
    missing = [i for i in cfg["isotopes"] if i not in all_iso]
    if missing:
        raise KeyError(f"Isotopes {missing} not defined in {cfg['isotopes_file']}")
    cfg["isotope_data"] = {i: all_iso[i] for i in cfg["isotopes"]}
    return cfg
