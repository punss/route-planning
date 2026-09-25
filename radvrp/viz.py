"""Diagnostic plots for instances (matplotlib, static).

The end goal is an interactive map (plan §6, Phase 6); these are for
checking that generated data looks sane and for explaining the decay coupling.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import geo  # noqa: E402
from .config import min_to_hhmm  # noqa: E402
from .decay import production_multiplier, remaining_fraction  # noqa: E402
from .instance import DEPOT, Instance  # noqa: E402

ISO_COLORS = {"Y-90": "#2a6fdb", "Pb-212": "#d1495b", "At-211": "#edae49"}


def _color(iso: str) -> str:
    return ISO_COLORS.get(iso, "#666666")


def plot_map(inst: Instance, ax=None):
    center = tuple(inst.config["geography"]["center"])
    ax = ax or plt.subplots(figsize=(8, 8))[1]
    coast = geo.coastline()
    cx, cy = geo.to_xy_km(coast[:, 0], coast[:, 1], center)
    ax.plot(cx, cy, color="#9ab", lw=1, label="coast (approx.)")

    x, y = geo.to_xy_km(inst.nodes["lat"], inst.nodes["lon"], center)
    nodes = inst.nodes.assign(x=x, y=y)
    n_pat = inst.patients.groupby("hospital").size()
    for typ, marker in (("academic", "s"), ("community", "o")):
        sub = nodes[nodes["type"] == typ]
        sizes = 30 + 25 * n_pat.reindex(sub.index).fillna(0)
        ax.scatter(sub["x"], sub["y"], s=sizes, marker=marker, facecolor="white",
                   edgecolor="black", zorder=3, label=f"{typ} (size ∝ patients)")
    for h, r in nodes[nodes["kind"] == "hospital"].iterrows():
        isos = [i for i in inst.isotopes.index if inst.eligible(h, i)]
        for k, iso in enumerate(isos):  # small coloured ticks = eligible isotopes
            ax.scatter(r["x"] + 1.2 + 0.9 * k, r["y"], s=14, color=_color(iso), zorder=4)
        ax.annotate(h, (r["x"], r["y"]), xytext=(-4, 7), textcoords="offset points", fontsize=7)
    d = nodes.loc[DEPOT]
    ax.scatter(d["x"], d["y"], marker="*", s=300, color="black", zorder=5, label="depot")
    for iso in inst.isotopes.index:
        ax.scatter([], [], s=14, color=_color(iso), label=f"eligible: {iso}")
    ax.set_aspect("equal")
    ax.set_xlabel("km east of downtown Boston")
    ax.set_ylabel("km north")
    ax.set_title(f"{inst.name}: depot and hospitals")
    ax.legend(fontsize=7, loc="upper left")
    return ax


def plot_doses(inst: Instance):
    isos = list(inst.isotopes.index)
    fig, axes = plt.subplots(1, len(isos), figsize=(4 * len(isos), 3.2))
    for ax, iso in zip(np.atleast_1d(axes), isos):
        d = inst.patients.loc[inst.patients["isotope"] == iso, "dose_mbq"]
        ax.hist(d, bins=12, color=_color(iso), edgecolor="white")
        ax.set_title(f"{iso}: prescribed activity (n={len(d)})")
        ax.set_xlabel("MBq at treatment time")
    fig.tight_layout()
    return fig


def plot_decay(inst: Instance, treatment: str = "12:00"):
    """Left: fraction remaining. Right: production multiplier vs batch time for one patient."""
    ops = inst.ops
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    hours = np.linspace(0, 12, 200)
    for iso, r in inst.isotopes.iterrows():
        a1.plot(hours, remaining_fraction(r["lambda_per_h"], hours * 60), color=_color(iso),
                label=f"{iso} (T½ {r['half_life_h']:g} h)")
    a1.set_xlabel("hours since production")
    a1.set_ylabel("fraction of activity remaining")
    a1.set_title("Decay")
    a1.legend()

    tau = int(treatment[:2]) * 60 + int(treatment[3:])
    latest = tau - ops.lead_time_min - ops.qc_min  # zero travel: absolute latest batch
    batches = np.arange(ops.prod_start_min, latest + 1, 5)
    for iso, r in inst.isotopes.iterrows():
        a2.plot(batches / 60, production_multiplier(r["lambda_per_h"], tau, batches), color=_color(iso),
                label=iso)
    a2.axvspan(latest / 60, tau / 60, color="#ddd", label="lead time + QC (unavoidable)")
    a2.axvline(tau / 60, color="black", ls="--", lw=1)
    ticks = np.arange(ops.prod_start_min, tau + 1, 60)
    a2.set_xticks(ticks / 60, [min_to_hhmm(t) for t in ticks], rotation=45)
    a2.set_xlabel("batch finish time")
    a2.set_ylabel("MBq to produce per MBq prescribed")
    a2.set_title(f"Production multiplier, patient treated at {treatment}")
    a2.legend()
    fig.tight_layout()
    return fig


def save_all(inst: Instance, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    if inst.nodes["lat"].notna().all():
        fig = plt.figure(figsize=(8, 8))
        plot_map(inst, fig.gca())
        paths.append(out / "map.png")
        fig.savefig(paths[-1], dpi=130, bbox_inches="tight")
        plt.close(fig)
    for name, fig in (("doses.png", plot_doses(inst)), ("decay.png", plot_decay(inst))):
        paths.append(out / name)
        fig.savefig(paths[-1], dpi=130, bbox_inches="tight")
        plt.close(fig)
    return paths
