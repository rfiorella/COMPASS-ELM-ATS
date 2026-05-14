"""Water balance diagnostic plots for ELM, ELM-IC, and ELM-ATS simulations.

Produces a 3x2 figure: rows = model variants, left = cumulative fluxes,
right = monthly fluxes with residual shading.
"""

import argparse
import glob
import warnings

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

try:
    import cftime

    HAS_CFTIME = True
except ImportError:
    HAS_CFTIME = False

# Variant labels and CLI arg names
VARIANTS = [
    ("ELM", "elm"),
    ("ELM-IC", "elm_ic"),
    ("ELM-ATS", "elm_ats"),
]

# Style definitions for monthly flux lines
FLUX_STYLES = {
    "P":              dict(color="tab:blue",   ls="-",  lw=2,   label="P (precip)"),
    "ET":             dict(color="tab:green",  ls="-",  lw=2,   label="ET (total)"),
    "QVEGE":          dict(color="lightgreen", ls="--", lw=1,   label="Canopy Evap"),
    "QSOIL":          dict(color="olive",      ls="--", lw=1,   label="Soil Evap"),
    "QVEGT":          dict(color="teal",       ls="--", lw=1,   label="Transpiration"),
    "QRUNOFF":        dict(color="tab:orange", ls="-",  lw=1.5, label="QRUNOFF"),
    "QDRAI":          dict(color="saddlebrown",ls="-",  lw=1.5, label="QDRAIN"),
    "QOVER":          dict(color="orangered",  ls=":",  lw=1.5, label="QOVER"),
    "dS":             dict(color="tab:purple", ls="-",  lw=1.5, label="\u0394S"),
}

# Cumulative plot styles (subset)
CUM_STYLES = {
    "P":  dict(color="tab:blue",   ls="-", lw=2,   label="P"),
    "ET": dict(color="tab:green",  ls="-", lw=2,   label="ET"),
    "R":  dict(color="tab:orange", ls="-", lw=1.5, label="R"),
    "dS": dict(color="tab:purple", ls="-", lw=1.5, label="\u0394S"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fix_time(ds):
    """Convert cftime datetimes to pandas datetimes for matplotlib."""
    if HAS_CFTIME and len(ds["time"]) > 0:
        if isinstance(ds["time"].values[0], cftime.datetime):
            import pandas as pd

            ds["time"] = pd.to_datetime(
                [t.strftime("%Y-%m-%d %H:%M:%S") for t in ds["time"].values]
            )
    return ds


def _seconds_per_month(time_coord):
    """Return an array of seconds in each month from a datetime64 time coordinate."""
    import pandas as pd

    times = pd.DatetimeIndex(time_coord.values)
    days = times.days_in_month
    return xr.DataArray(
        days.values.astype(float) * 86400.0,
        dims=["time"],
        coords={"time": time_coord},
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_variant(run_dir):
    """Load ELM h0 history files from a run directory."""
    pattern = f"{run_dir}/*.elm.h0.*.nc"
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern}")
    ds = xr.concat(
        [xr.open_dataset(f) for f in files],
        dim="time",
    )
    return _fix_time(ds)


# ---------------------------------------------------------------------------
# Water balance computation
# ---------------------------------------------------------------------------

def _safe_get(ds, name):
    """Return ds[name].squeeze() if present, else None with a warning."""
    if name in ds:
        return ds[name].squeeze()
    warnings.warn(f"Variable '{name}' not found in dataset, treating as zero.")
    return None


def _get_dzsoi(ds):
    """Get soil layer thicknesses, trying DZSOI then DZSOI_DECOMP."""
    for name in ("DZSOI", "DZSOI_DECOMP"):
        if name in ds:
            return ds[name].squeeze()
    raise KeyError("Neither DZSOI nor DZSOI_DECOMP found in dataset.")


def compute_water_balance(ds):
    """Compute water balance terms from an ELM dataset.

    Returns a dict of xarray DataArrays with keys:
        P, ET, R, dS, residual (all in mm/month)
        QVEGE, QSOIL, QVEGT, QRUNOFF, QDRAI, QOVER
        (individual components in mm/month, QOVER may be None)
    """
    sec_per_month = _seconds_per_month(ds["time"])

    # --- Fluxes (mm/s -> mm/month) ---
    rain = ds["RAIN"].squeeze()
    snow = ds["SNOW"].squeeze()
    P = (rain + snow) * sec_per_month

    evap_veg = ds["QVEGE"].squeeze()
    evap_grnd = ds["QSOIL"].squeeze()
    tran_veg = ds["QVEGT"].squeeze()
    ET = (evap_veg + evap_grnd + tran_veg) * sec_per_month

    qrunoff = ds["QRUNOFF"].squeeze()
    qdrain = ds["QDRAI"].squeeze()
    R = (qrunoff + qdrain) * sec_per_month

    qover_da = _safe_get(ds, "QOVER")
    if qover_da is not None:
        R = R + qover_da * sec_per_month

    # --- Storage (mm) ---
    dzsoi = _get_dzsoi(ds)
    h2osoi = ds["H2OSOI"].squeeze()
    column_soil_water = (h2osoi * dzsoi * 1000.0).sum(dim="levgrnd")

    swe = ds["H2OSNO"].squeeze()
    S = column_soil_water + swe

    # dS = S(t) - S(t-1), first month is NaN
    dS = S.diff(dim="time")
    # Prepend a NaN for the first timestep
    nan_first = S.isel(time=0) * np.nan
    dS = xr.concat([nan_first, dS], dim="time")

    residual = P - ET - R - dS

    # Individual components in mm/month for the monthly panel
    result = {
        "P": P,
        "ET": ET,
        "R": R,
        "dS": dS,
        "residual": residual,
        "QVEGE": evap_veg * sec_per_month,
        "QSOIL": evap_grnd * sec_per_month,
        "QVEGT": tran_veg * sec_per_month,
        "QRUNOFF": qrunoff * sec_per_month,
        "QDRAI": qdrain * sec_per_month,
    }
    if qover_da is not None:
        result["QOVER"] = qover_da * sec_per_month

    return result


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_water_balance(variant_data, title=None):
    """Create 3x2 water balance figure.

    Parameters
    ----------
    variant_data : list of (label, wb_dict) tuples
        Each wb_dict is the output of compute_water_balance().
    title : str, optional
        Super-title for the figure.

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    fig, axes = plt.subplots(
        len(variant_data), 2,
        figsize=(14, 10),
        constrained_layout=True,
        squeeze=False,
    )

    for row, (label, wb) in enumerate(variant_data):
        ax_cum = axes[row, 0]
        ax_mon = axes[row, 1]
        time = wb["P"]["time"]

        # --- Left: cumulative ---
        for key, style in CUM_STYLES.items():
            vals = wb[key]
            cum = vals.cumsum(dim="time", skipna=True)
            ax_cum.plot(time, cum, **style)

        ax_cum.set_ylabel(f"{label}\nCumulative flux (mm)", fontsize=12)
        ax_cum.legend(fontsize=9, loc="best")
        ax_cum.grid(True, alpha=0.3)
        ax_cum.tick_params(labelsize=11)

        # --- Right: monthly fluxes ---
        for key in ("P", "ET", "QVEGE", "QSOIL", "QVEGT",
                     "QRUNOFF", "QDRAI", "QOVER", "dS"):
            if key not in wb:
                continue
            style = FLUX_STYLES[key]
            ax_mon.plot(time, wb[key], **style)

        # Residual shading
        ax_mon.fill_between(
            time.values, 0, wb["residual"].values,
            color="gray", alpha=0.3, label="Residual",
        )

        ax_mon.set_ylabel("Flux (mm/month)", fontsize=12)
        ax_mon.legend(fontsize=8, loc="best", ncol=2)
        ax_mon.grid(True, alpha=0.3)
        ax_mon.tick_params(labelsize=11)

        # Only bottom row gets x-axis tick labels
        if row < len(variant_data) - 1:
            ax_cum.tick_params(labelbottom=False)
            ax_mon.tick_params(labelbottom=False)

    # Column titles
    axes[0, 0].set_title("Cumulative Fluxes (mm)", fontsize=13)
    axes[0, 1].set_title("Monthly Fluxes (mm/month)", fontsize=13)

    if title:
        fig.suptitle(title, fontsize=15)

    return fig


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Water balance diagnostic plot for ELM variants."
    )
    parser.add_argument("--elm", required=True, help="Path to ELM run directory.")
    parser.add_argument("--elm-ic", required=True, help="Path to ELM-IC run directory.")
    parser.add_argument("--elm-ats", required=True, help="Path to ELM-ATS run directory.")
    parser.add_argument("-o", "--out", default="water_balance.png",
                        help="Output figure path (default: water_balance.png).")
    parser.add_argument("--dpi", type=int, default=150, help="Figure DPI (default: 150).")
    parser.add_argument("--title", default=None, help="Optional super-title.")
    parser.add_argument("--no-show", action="store_true", help="Suppress plt.show().")
    return parser.parse_args()


def main():
    args = parse_args()

    dirs = {
        "ELM": args.elm,
        "ELM-IC": args.elm_ic,
        "ELM-ATS": args.elm_ats,
    }

    variant_data = []
    for label, run_dir in dirs.items():
        print(f"Loading {label}: {run_dir}")
        ds = load_variant(run_dir)
        print(f"  {len(ds['time'])} timesteps")
        wb = compute_water_balance(ds)
        variant_data.append((label, wb))

    print("Plotting...")
    fig = plot_water_balance(variant_data, title=args.title)
    fig.savefig(args.out, dpi=args.dpi)
    print(f"Saved {args.out}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
