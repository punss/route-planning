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


# ------------------------------------------------------------------ solutions
def plot_routes(inst: Instance, trips, ax=None):
    """Instance map with one polyline per trip, coloured by isotope."""
    from .checker import Trip  # noqa: F401  (type only)

    ax = plot_map(inst, ax)
    center = tuple(inst.config["geography"]["center"])
    x, y = geo.to_xy_km(inst.nodes["lat"], inst.nodes["lon"], center)
    xy = dict(zip(inst.nodes.index, zip(x, y)))
    from .fleet import assign_trucks

    truck = assign_trucks(inst, trips)
    offsets = np.linspace(-0.4, 0.4, max(len(trips), 1))  # separate overlapping trips a little
    for n, tr in enumerate(trips):
        path = [DEPOT] + tr.stops + [DEPOT]
        px = [xy[v][0] + offsets[n] for v in path]
        py = [xy[v][1] + offsets[n] for v in path]
        ax.plot(px, py, color=_color(tr.isotope), lw=1.6, alpha=0.8, zorder=2)
        mid = len(path) // 2
        ax.annotate(f"T{n}·truck {truck[n]}", (px[mid], py[mid]), fontsize=7, color=_color(tr.isotope))
    ax.set_title(f"{inst.name}: {len(trips)} trips on {max(truck)} trucks")
    return ax


def _draw_trip(ax, inst: Instance, tr, sc, row: float, label_levels: tuple[float, float],
               show_qc: bool) -> None:
    """Draw one trip on row `row`: [QC] → drive → stop → … → drive back.

    `label_levels` are the y-offsets for stop labels, alternated so nearby
    stops don't collide (negative = above the bar, positive = below).
    """
    ops, pts, t, nodes = inst.ops, inst.patients, inst.travel_min, inst.nodes
    c = _color(tr.isotope)
    bar = dict(height=0.4, color=c, edgecolor="none")
    if show_qc:
        ax.barh(row, ops.qc_min / 60, left=tr.batch_min / 60, height=0.4, color="white",
                edgecolor=c, hatch="////", lw=0.8)
        ax.text(tr.batch_min / 60 - 0.05, row, f"batch {min_to_hhmm(tr.batch_min)}", ha="right",
                va="center", fontsize=7, color="#444")
    prev, leave = DEPOT, sc.depart_min
    for j, h in enumerate(tr.stops):
        drive_end = leave + t.at[prev, h]
        ax.barh(row, (drive_end - leave) / 60, left=leave / 60, **bar)
        if sc.arrival_min[h] > drive_end + 1e-6:  # waiting for the hot lab to open
            ax.plot([drive_end / 60, sc.arrival_min[h] / 60], [row, row], ls=":", color=c, lw=1.5)
        svc = max(nodes.at[h, "service_min"], 3)  # draw at least a sliver
        ax.barh(row, svc / 60, left=sc.arrival_min[h] / 60, height=0.4, color="#222")
        dls = [pts.at[q, "deadline_min"] for q in tr.drops.get(h, [])]
        slack = f"\nslack {min(dls) - sc.arrival_min[h]:.0f} min" if dls else ""
        label = f"{h} · {len(dls)} vial{'s' if len(dls) != 1 else ''}{slack}"
        off = label_levels[j % 2]
        ax.text(sc.arrival_min[h] / 60, row + off, label, ha="center",
                va="bottom" if off < 0 else "top", fontsize=6.5, linespacing=1.1)
        if dls:  # thin bracket from arrival to the earliest deadline at this stop
            y0 = row + 0.25
            ax.plot([sc.arrival_min[h] / 60, min(dls) / 60], [y0, y0], color="#999", lw=0.8)
            ax.plot([min(dls) / 60], [y0], marker="|", color="#c00", ms=6, mew=1.4)
        prev, leave = h, sc.arrival_min[h] + nodes.at[h, "service_min"]
    ax.barh(row, (sc.return_min - leave) / 60, left=leave / 60, height=0.4, color=c,
            alpha=0.35, edgecolor="none")


def _style_time_axis(ax, lo_min: float, hi_min: float) -> None:
    lo, hi = lo_min / 60, hi_min / 60
    ax.set_xlim(lo, hi)
    hours = np.arange(np.floor(lo), np.ceil(hi) + 1)
    ax.set_xticks(hours, [f"{int(h):02d}:00" for h in hours], fontsize=8)
    ax.grid(axis="x", color="#eee", zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _legend(ax, trips, extra):
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    handles = [Patch(facecolor=_color(i), label=i) for i in dict.fromkeys(tr.isotope for tr in trips)]
    handles += extra + [
        Patch(facecolor="#888", label="driving"),
        Patch(facecolor="#222", label="at hospital (label: vials dropped, slack)"),
        Patch(facecolor="#888", alpha=0.35, label="driving back to depot"),
        Line2D([], [], color="#888", ls=":", lw=1.5, label="waiting for hot lab"),
        Line2D([], [], color="#888", marker="|", mec="#c00", ms=7, mew=1.5,
               label="slack: arrival → earliest vial deadline"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=4, fontsize=7,
              frameon=False)


def plot_gantt(inst: Instance, trips):
    """Per-trip view: one row per trip, ordered by departure, including batch → QC."""
    from matplotlib.patches import Patch

    from .checker import simulate

    scheds = [simulate(inst, tr) for tr in trips]
    order = sorted(range(len(trips)), key=lambda n: (scheds[n].depart_min, trips[n].isotope))
    fig, ax = plt.subplots(figsize=(12, 1.15 * len(trips) + 2.2))
    for row, n in enumerate(order):
        _draw_trip(ax, inst, trips[n], scheds[n], row, (-0.27, 0.33), show_qc=True)
    labels = [f"T{n}  {trips[n].isotope}  ·  {len(trips[n].patients)} vial"
              f"{'s' if len(trips[n].patients) != 1 else ''}" for n in order]
    ax.set_yticks(range(len(order)), labels, fontsize=8)
    ax.set_ylim(len(order) - 0.35, -0.75)
    pts = inst.patients
    _style_time_axis(ax, min(tr.batch_min for tr in trips) - 60,
                     max(max(sc.return_min for sc in scheds),
                         max(pts.loc[tr.patients, "deadline_min"].max() for tr in trips)) + 36)
    _legend(ax, trips, [Patch(facecolor="white", edgecolor="#666", hatch="////",
                              label="batch ready → QC / loading")])
    ax.set_title(f"{inst.name}: trip schedule ({len(trips)} trips, ordered by departure)", fontsize=10)
    fig.tight_layout()
    return fig


def plot_truck_schedule(inst: Instance, trips):
    """Per-truck view: which truck (and driver) does which trip, for a third-party reader.

    The model treats trucks and drivers as interchangeable; this assignment is
    computed after solving (radvrp.fleet) and uses the minimum number of trucks.
    """
    from matplotlib.patches import Patch

    from .checker import simulate
    from .fleet import assign_trucks

    ops, pts = inst.ops, inst.patients
    scheds = [simulate(inst, tr) for tr in trips]
    truck = assign_trucks(inst, trips)
    n_trucks = max(truck)
    pitch = 1.6
    fig, ax = plt.subplots(figsize=(12, 1.45 * n_trucks + 2.4))
    for n, (tr, sc) in enumerate(zip(trips, scheds)):
        row = (truck[n] - 1) * pitch
        _draw_trip(ax, inst, tr, sc, row, (0.33, 0.66), show_qc=False)
        ax.text(sc.depart_min / 60, row - 0.27, f"T{n} · {tr.isotope} · batch {min_to_hhmm(tr.batch_min)}",
                ha="left", va="bottom", fontsize=7, fontweight="bold", color=_color(tr.isotope))
        if ops.turnaround_min:
            ax.barh(row, ops.turnaround_min / 60, left=sc.return_min / 60, height=0.4, color="white",
                    edgecolor="#999", hatch="....", lw=0.6)
    ax.set_yticks([v * pitch for v in range(n_trucks)],
                  [f"Truck {v + 1}\n(driver {v + 1})" for v in range(n_trucks)], fontsize=8)
    ax.set_ylim((n_trucks - 1) * pitch + 1.25, -0.75)
    _style_time_axis(ax, min(sc.depart_min for sc in scheds) - 30,
                     max(max(sc.return_min for sc in scheds) + ops.turnaround_min,
                         max(pts.loc[tr.patients, "deadline_min"].max() for tr in trips)) + 36)
    _legend(ax, trips, [Patch(facecolor="white", edgecolor="#999", hatch="....",
                              label=f"turnaround at depot ({ops.turnaround_min} min)")])
    ax.set_title(f"{inst.name}: {len(trips)} trips on {n_trucks} trucks "
                 f"(trucks and drivers are interchangeable; assignment made after solving)", fontsize=10)
    fig.tight_layout()
    return fig


def save_solution(inst: Instance, trips, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    if inst.nodes["lat"].notna().all():
        fig = plt.figure(figsize=(8, 8))
        plot_routes(inst, trips, fig.gca())
        paths.append(out / "routes.png")
        fig.savefig(paths[-1], dpi=130, bbox_inches="tight")
        plt.close(fig)
    for name, fig in (("schedule_by_truck.png", plot_truck_schedule(inst, trips)),
                      ("schedule_by_trip.png", plot_gantt(inst, trips))):
        paths.append(out / name)
        fig.savefig(paths[-1], dpi=130, bbox_inches="tight")
        plt.close(fig)
    return paths
