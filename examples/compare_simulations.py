"""Compare ELM, ELM+ATS IC, and ELM-ATS simulation outputs.

Works with any COMPASS-ELM-ATS test case. Automatically discovers
available variables from the loaded datasets.
"""

import argparse
import glob
import os
import sys
import re

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

try:
    import cftime

    HAS_CFTIME = True
except ImportError:
    HAS_CFTIME = False

# Variables that have a vertical (depth) dimension
# Deprecated static list – depth variables are now detected dynamically based on dimensions

# Dimensions to skip when listing plottable variables
SKIP_VARS = {"time", "mcdate", "mcsec", "mdcur", "mscur", "nstep",
             "time_bounds", "date_written", "time_written",
             "lon", "lat", "area", "landfrac", "landmask", "pftmask",
             "levgrnd", "levsoi", "levdcmp", "levlak", "levurb",
             "cols1d_lon", "cols1d_lat", "cols1d_ixy", "cols1d_jxy",
             "cols1d_gridcell_index", "cols1d_wtgcell", "cols1d_active",
             "cols1d_itype_col", "cols1d_itype_lunit",
             "pfts1d_lon", "pfts1d_lat", "pfts1d_ixy", "pfts1d_jxy",
             "pfts1d_gridcell_index", "pfts1d_wtgcell", "pfts1d_active",
             "pfts1d_itype_veg", "pfts1d_itype_lunit",
             "land1d_lon", "land1d_lat", "land1d_ixy", "land1d_jxy",
             "land1d_gridcell_index", "land1d_wtgcell", "land1d_active",
             "land1d_ityplunit"}

SIM_SUFFIXES = {
    "ELM": "elm",
    "ELM+ATS IC": "ic_only",
    "ELM-ATS": "elm-ats",
}

SIM_COLORS = {
    "ELM": "C0",
    "ELM+ATS IC": "C1",
    "ELM-ATS": "C2",
}

# ----------------------------------------------------------------------
# Revised variable grouping – each group contains variables that share a scientific
# domain, regardless of the dimension on which they are stored.  The groups are
# used by the ``--groups`` command‑line flag to select a subset of variables for
# plotting.
# ----------------------------------------------------------------------
VARIABLE_GROUPS = {
    # Hydrology – water balance, soil‑hydraulic parameters, and active‑layer depth.
    "hydrology": {
        "DWB", "H2OSFC", "H2OSNO", "H2OSNO_TOP", "INT_SNOW",
        "FSAT", "FINUNDATED", "FINUNDATED_LAG",
        "WATSAT", "SUCSAT", "BSW", "HKSAT",
        "ALT", "ALTMAX", "ALTMAX_LASTYEAR",
        # Add any additional water‑related variables that appear in future cases.
    },
    # Soil – pure geometric / structural information about the soil column.
    "soil": {
        "levgrnd", "levsoi", "levdcmp", "levlak",
        "ZSOI", "DZSOI",
        "topo", "area", "landfrac", "landmask",
        "lon", "lat", "gridcell",
    },
    # Biogeochemistry – carbon, nitrogen, phosphorus pools and greenhouse‑gas
    # fluxes, regardless of the vertical dimension they are stored on.
    "biogeochemistry": {
        # Carbon pools & fluxes
        "CPOOL", "CWDC", "CWDN", "CWDP",
        "CWDC_HR", "CWDC_LOSS", "CWDC_TO_LITR2C", "CWDC_TO_LITR3C",
        "CWDN_TO_LITR2N", "CWDN_TO_LITR3N",
        "CWDP_TO_LITR2P", "CWDP_TO_LITR3P",
        "DEADCROOTC", "DEADCROOTN", "DEADCROOTP",
        "DEADSTEMC", "DEADSTEMN", "DEADSTEMP",
        # Nitrogen & phosphorus transformations
        "DENIT", "NIT", "F_DENIT", "F_DENIT_vr",
        "F_N2O_DENIT", "F_N2O_NIT",
        "BIOCHEM_PMIN", "BIOCHEM_PMIN_TO_PLANT",
        "F_PMIN", "F_PMIN_vr", "F_NMIN", "F_NMIN_vr",
        # Greenhouse‑gas production / emission
        "CH4PROD", "FCH4", "FCH4TOCO2", "FCH4_DFSAT",
        "CH4_SURF_AERE_SAT", "CH4_SURF_AERE_UNSAT",
        "CH4_SURF_DIFF_SAT", "CH4_SURF_DIFF_UNSAT",
        "CH4_SURF_EBUL_SAT", "CH4_SURF_EBUL_UNSAT",
        "CONC_CH4_SAT", "CONC_CH4_UNSAT",
        "CONC_O2_SAT", "CONC_O2_UNSAT",
        "F_CO2_SOIL", "F_CO2_SOIL_vr",
        # Misc biochemical fluxes
        "F_IRR", "F_IRR_R", "F_IRR_U",
    },
    # Vegetation – plant‑related state variables and fluxes.
    "vegetation": {
        "GPP", "AGNPP", "AGWDNPP", "ELAI", "ELAI_MAX",
        "FROOTC", "FROOTC_ALLOC", "FROOTC_LOSS",
        "FROOTN", "FROOTP",
        "FPI", "FPI_P", "FPI_vr", "FPI_P_vr",
        "FPG", "FPG_P",
        "FAREA_BURNED", "FIRE", "FIRE_R", "FIRE_U",
        "FIRA", "FIRA_R", "FIRA_U",
        "LAI", "LAI_MAX", "LAI_MIN",
    },
    # Energy – surface‑energy‑budget fluxes and radiative terms.
    "energy": {
        "EFLX_DYNBAL", "EFLX_LH_TOT", "EFLX_LH_TOT_R", "EFLX_LH_TOT_U",
        "EFLX_GRND_LAKE",
        "FCEV", "FGEV", "FSA", "FSA_R", "FSA_U",
        "FSDS", "FSDSND", "FSDSNDLN", "FSDSNI",
        "FSDSVD", "FSDSVDLN", "FSDSVI", "FSDSVILN",
        "FSAT", "FGR", "FGR_R", "FGR_U",
        "HR", "HR_vr", "ER", "ER_vr",
        "FSNO", "FSNO_EFF",
        "FIRR", "FIRR_R", "FIRR_U",
    },
}


def _fix_time(ds):
    """Convert cftime datetimes to standard datetimes for matplotlib."""
    if HAS_CFTIME and len(ds["time"]) > 0:
        if isinstance(ds["time"].values[0], cftime.datetime):
            import pandas as pd

            ds["time"] = pd.to_datetime(
                [t.strftime("%Y-%m-%d %H:%M:%S") for t in ds["time"].values]
            )
    return ds


def _discover_variables(datasets):
    """Return list of plottable variables found across all datasets."""
    all_vars = set()
    for ds in datasets.values():
        for var in ds.data_vars:
            if var in SKIP_VARS:
                continue
            dims = ds[var].dims
            # Must have a time dimension to be plottable
            if "time" not in dims:
                continue
            all_vars.add(var)
    return sorted(all_vars)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare ELM, ELM+ATS IC, and ELM-ATS simulations."
    )
    parser.add_argument(
        "--base-dir",
        required=True,
        help="Path to E3SM_WORK_DIR (contains output/ subdirectory).",
    )
    parser.add_argument(
        "--case-name",
        required=True,
        help="Case name as it appears in output paths (e.g. oakharbor_column, "
        "oakharbor_transect.np1).",
    )
    parser.add_argument(
        "--hist-file",
        default="h0",
        choices=["h0", "h1"],
        help="History file stream to load (default: h0).",
    )
    parser.add_argument(
        "--output-dir",
        default="./figures",
        help="Directory for saved figures (default: ./figures).",
    )
    parser.add_argument(
        "--variables",
        nargs="+",
        default=None,
        help="Specific variables to plot (default: auto-discover from data).",
    )
    parser.add_argument(
        "--groups",
        nargs="+",
        default=None,
        help="Pre‑defined groups of variables to plot (e.g. hydrology soil).",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="Print the available variable groups and exit.",
    )
    return parser.parse_args()


def load_simulations(base_dir, case_name, hist_file):
    """Load output datasets for all three simulations.

    Returns a dict mapping simulation label to xarray.Dataset.
    """
    datasets = {}
    for label, suffix in SIM_SUFFIXES.items():
        pattern = os.path.join(
            base_dir,
            "output",
            f"{case_name}.{suffix}",
            "run",
            f"{case_name}.{suffix}.elm.{hist_file}.*.nc",
        )
        print(f"Loading {label}: {pattern}")
        files = sorted(glob.glob(pattern))
        if not files:
            print(f"  No files found for {label}, skipping.")
            continue
        ds = xr.concat(
            [xr.open_dataset(f, decode_times=False) for f in files],
            dim="time",
        )
        datasets[label] = _fix_time(ds)
    return datasets


def plot_timeseries(datasets, variables, output_dir, hist_file):
    """Plot time series for each variable, comparing all simulations."""
    for var in variables:
        available = {k: ds for k, ds in datasets.items() if var in ds}
        if not available:
            print(f"  Skipping {var}: not found in any dataset.")
            continue

        sample_ds = next(iter(available.values()))
        dims = sample_ds[var].dims
        has_depth = any(d in dims for d in ("levgrnd", "levsoi", "levdcmp"))

        if has_depth:
            # 2‑D contour: time vs depth, one subplot per simulation (stacked vertically)
            depth_dim = next(d for d in ("levgrnd", "levsoi", "levdcmp") if d in dims)
            depth_vals = sample_ds[depth_dim].values
            # Gather data from all simulations to compute a common colour scale
            all_data = []
            for ds in available.values():
                d = ds[var].values
                d = np.squeeze(d)
                if d.ndim == 2:
                    if d.shape[0] == len(depth_vals) and d.shape[1] == len(ds["time"]):
                        d = d.T
                elif d.ndim > 2:
                    d = d.mean(axis=tuple(range(2, d.ndim)))
                    if d.shape[0] == len(depth_vals) and d.shape[1] == len(ds["time"]):
                        d = d.T
                # Align shapes (trim if needed)
                t_vals = ds["time"].values
                if d.shape != (len(depth_vals), len(t_vals)):
                    if d.shape == (len(t_vals), len(depth_vals)):
                        d = d.T
                    else:
                        min_len = min(d.shape[-1], len(t_vals))
                        min_dep = min(d.shape[0], len(depth_vals))
                        d = d[:min_dep, :min_len]
                        t_vals = t_vals[:min_len]
                        depth_vals = depth_vals[:min_dep]
                all_data.append(d)
            # Compute global min/max ignoring NaNs
            global_min = np.nanmin([np.nanmin(d) for d in all_data])
            global_max = np.nanmax([np.nanmax(d) for d in all_data])
            # Create subplots
            fig, axes = plt.subplots(
                len(available), 1, figsize=(10, 3 * len(available)), sharex=True, sharey=True
            )
            if len(available) == 1:
                axes = [axes]
            # Ensure deterministic order of simulations
            sim_items = list(available.items())
            cf = None  # will hold the last contour for colorbar
            for ax, (label, ds) in zip(axes, sim_items):
                data = ds[var].values
                data = np.squeeze(data)
                if data.ndim == 2:
                    if data.shape[0] == len(depth_vals) and data.shape[1] == len(ds["time"]):
                        data = data.T
                elif data.ndim > 2:
                    data = data.mean(axis=tuple(range(2, data.ndim)))
                    if data.shape[0] == len(depth_vals) and data.shape[1] == len(ds["time"]):
                        data = data.T
                time_vals = ds["time"].values
                if data.shape != (len(depth_vals), len(time_vals)):
                    if data.shape == (len(time_vals), len(depth_vals)):
                        data = data.T
                    else:
                        min_len = min(data.shape[-1], len(time_vals))
                        min_dep = min(data.shape[0], len(depth_vals))
                        data = data[:min_dep, :min_len]
                        time_vals = time_vals[:min_len]
                        depth_vals = depth_vals[:min_dep]
                # Use common colour limits
                cf = ax.contourf(time_vals, depth_vals, data, cmap="viridis", vmin=global_min, vmax=global_max)
                ax.set_ylabel("Depth (m)")
                ax.set_title(label)
                ax.invert_yaxis()
            # Add a single shared colourbar for the whole figure
            fig.colorbar(cf, ax=axes, orientation="vertical", label=var)
            axes[-1].set_xlabel("Time")
            fig.suptitle(f"{var} — Time‑Depth Contour", fontsize=14)
        else:
            fig, ax = plt.subplots(figsize=(10, 4))
            for label, ds in available.items():
                data = ds[var].squeeze()
                ax.plot(ds["time"], data, label=label, color=SIM_COLORS[label])
            ax.set_ylabel(var)
            ax.set_xlabel("Time")
            ax.set_title(f"{var} — Time Series")
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, f"timeseries_{var}_{hist_file}.png"), dpi=150)
        plt.close(fig)
        print(f"  Saved timeseries_{var}_{hist_file}.png")


def _format_time(t):
    """Return a short string representation of a time coordinate element.

    Handles NumPy ``datetime64`` objects, pandas ``Timestamp``/``datetime``
    objects, and plain numeric values (e.g., days since a reference).
    """
    # NumPy datetime64 (or generic NumPy scalar that can be cast)
    if isinstance(t, np.generic):
        # Convert NumPy scalar (including datetime64) to string safely
        try:
            return str(t)
        except Exception:
            pass
    # pandas Timestamp or Python datetime – both have ``strftime``
    if hasattr(t, "strftime"):
        try:
            return t.strftime("%Y-%m-%d")
        except Exception:
            pass
    # Fallback: handle pure numeric values (e.g., days since reference) or generic fallback
    if isinstance(t, (int, float, np.number)):
        return str(t)
    try:
        return np.datetime_as_string(np.array(t, dtype="datetime64[ns]"), unit="D")
    except Exception:
        return str(t)

def plot_profiles(datasets, variables, output_dir, hist_file):
    """Plot vertical profiles for soil variables at selected time steps."""
    # Identify variables that have a depth dimension across any dataset
    depth_vars = []
    for v in variables:
        for ds in datasets.values():
            if v in ds and any(d in ds[v].dims for d in ("levgrnd", "levsoi", "levdcmp")):
                depth_vars.append(v)
                break
    if not depth_vars:
        return
    for var in depth_vars:
        available = {k: ds for k, ds in datasets.items() if var in ds}
        if not available:
            print(f"  Skipping profile for {var}: not found.")
            continue

        sample_ds = next(iter(available.values()))
        dims = sample_ds[var].dims
        depth_dim = next(
            (d for d in ("levgrnd", "levsoi", "levdcmp") if d in dims), None
        )
        if depth_dim is None:
            continue

        # Determine the smallest time dimension among the available datasets for this variable
        min_n = min(len(ds["time"]) for ds in available.values())
        # Build candidate indices based on this minimum length to avoid out‑of‑bounds errors
        cand = [0, min_n // 2, min_n - 1]
        snap_indices = sorted({i for i in cand if 0 <= i < min_n})

        fig, axes = plt.subplots(
            1, len(snap_indices), figsize=(5 * len(snap_indices), 6), sharey=True
        )
        if len(snap_indices) == 1:
            axes = [axes]

        for ax, ti in zip(axes, snap_indices):
            # Use robust formatting for the time label
            t_val = _format_time(sample_ds["time"].values[ti])
            for label, ds in available.items():
                depths = ds[depth_dim].values
                values = ds[var].isel(time=ti).squeeze().values
                ax.plot(values, depths, label=label, color=SIM_COLORS[label])
            ax.set_title(f"t = {t_val}")
            ax.set_xlabel(var)
            ax.invert_yaxis()
            ax.legend(fontsize="small")
            ax.grid(True, alpha=0.3)

        axes[0].set_ylabel("Depth (m)")
        fig.suptitle(f"{var} — Vertical Profiles", fontsize=14)
        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, f"profile_{var}_{hist_file}.png"), dpi=150)
        plt.close(fig)
        print(f"  Saved profile_{var}.png")


def plot_differences(datasets, variables, output_dir, hist_file):
    """Plot differences relative to ELM-only for each variable."""
    if "ELM" not in datasets:
        print("  ELM baseline not available; skipping difference plots.")
        return

    ref = datasets["ELM"]
    diff_labels = {
        "ELM-ATS minus ELM": "ELM-ATS",
        "ELM+ATS IC minus ELM": "ELM+ATS IC",
    }
    diff_colors = {
        "ELM-ATS minus ELM": "C2",
        "ELM+ATS IC minus ELM": "C1",
    }

    for var in variables:
        if var not in ref:
            continue

        dims = ref[var].dims
        has_depth = any(d in dims for d in ("levgrnd", "levsoi", "levdcmp"))

        if has_depth:
            depth_dim = next(
                d for d in ("levgrnd", "levsoi", "levdcmp") if d in dims
            )
            fig, ax = plt.subplots(figsize=(10, 4))
            for diff_label, sim_label in diff_labels.items():
                if sim_label not in datasets or var not in datasets[sim_label]:
                    continue
                sim_ds = datasets[sim_label]
                # Align times for depth-averaged diff
                common_times = np.intersect1d(ref["time"].values, sim_ds["time"].values)
                if common_times.size == 0:
                    print(f"  Skipping {var} diff for {sim_label}: no overlapping times.")
                    continue
                ref_sel = ref.sel(time=common_times)
                sim_sel = sim_ds.sel(time=common_times)
                diff = (
                    sim_sel[var].mean(dim=depth_dim) - ref_sel[var].mean(dim=depth_dim)
                ).squeeze()
                ax.plot(
                    common_times, diff, label=diff_label, color=diff_colors[diff_label]
                )
            ax.set_ylabel(f"Delta {var} (depth-averaged)")
        else:
            fig, ax = plt.subplots(figsize=(10, 4))
        for diff_label, sim_label in diff_labels.items():
            if sim_label not in datasets or var not in datasets[sim_label]:
                continue
            # Align times between reference and simulation to avoid length mismatches
            sim_ds = datasets[sim_label]
            # Find common time values (exact match). If none, skip.
            common_times = np.intersect1d(ref["time"].values, sim_ds["time"].values)
            if common_times.size == 0:
                print(f"  Skipping {var} diff for {sim_label}: no overlapping times.")
                continue
            # Select the overlapping slice from both datasets
            ref_sel = ref.sel(time=common_times)
            sim_sel = sim_ds.sel(time=common_times)
            diff = (sim_sel[var] - ref_sel[var]).squeeze()
            ax.plot(
                common_times, diff, label=diff_label, color=diff_colors[diff_label]
            )
            ax.set_ylabel(f"Delta {var}")

        ax.axhline(0, color="k", linewidth=0.5)
        ax.set_xlabel("Time")
        ax.set_title(f"{var} — Differences from ELM")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, f"diff_{var}_{hist_file}.png"), dpi=150)
        plt.close(fig)
        print(f"  Saved diff_{var}.png")


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Optional: list the variable groups and exit.
    # ------------------------------------------------------------------
    if args.list_groups:
        print("Available variable groups:")
        for g, vars_ in VARIABLE_GROUPS.items():
            print(f"  {g}: {', '.join(sorted(vars_))}")
        sys.exit(0)

    print("Loading simulations...")
    datasets = load_simulations(args.base_dir, args.case_name, args.hist_file)
    # ------------------------------------------------------------------
    # Expand the hydrology group to include any variable that looks like a
    # water‑related state or flux. This captures the many Q* (flux), RAIN,
    # SNOW, soil‑water, and related variables that were not enumerated
    # explicitly in the static definition.
    # ------------------------------------------------------------------
    # Gather all variable names present in the loaded datasets.
    all_vars = set()
    for ds in datasets.values():
        all_vars.update(ds.data_vars)
    # Patterns that identify hydrology‑related variables (case‑insensitive).
    hydro_patterns = [
        r'^Q', r'RAIN', r'SNOW', r'H2OS?FC', r'H2OSNO', r'WATSAT', r'SUCSAT', r'BSW', r'HKSAT',
        r'FINUNDATED', r'INT_SNOW', r'FSAT', r'ZWT', r'ZWT_', r'RETRANSP', r'RETRANSN', r'OVER',
        r'IRR', r'DRIP', r'DWB', r'WATER', r'ALT', r'ALTMAX', r'ALTMAX_LASTYEAR', r'SOILLIQ', r'SOILICE',
    ]
    for v in all_vars:
        if any(re.search(p, v, re.I) for p in hydro_patterns):
            VARIABLE_GROUPS.setdefault('hydrology', set()).add(v)

    if not datasets:
        print("No simulation data found. Nothing to plot.")
        return

    # ------------------------------------------------------------------
    # Determine which variables the user actually wants plotted.
    # ------------------------------------------------------------------
    requested = set()
    if args.variables:
        requested.update(args.variables)
    if args.groups:
        # Validate that all requested groups exist.
        unknown = [g for g in args.groups if g not in VARIABLE_GROUPS]
        if unknown:
            sys.exit(f"Error: unknown group(s): {', '.join(unknown)}")
        for g in args.groups:
            requested.update(VARIABLE_GROUPS[g])

    if not requested:
        # No explicit request – fall back to auto‑discover (original behaviour).
        available_vars = _discover_variables(datasets)
    else:
        # Keep only variables that are actually present in any of the loaded datasets.
        available_vars = sorted(v for v in requested if any(v in ds for ds in datasets.values()))
        missing = requested - set(available_vars)
        if missing:
            print(f"Warning: the following requested variables were not found in any file: {', '.join(sorted(missing))}")

    print(f"Variables to plot: {available_vars}")

    print("\nGenerating time series plots...")
    plot_timeseries(datasets, available_vars, args.output_dir, args.hist_file)

    print("\nGenerating vertical profile plots...")
    plot_profiles(datasets, available_vars, args.output_dir, args.hist_file)

    print("\nGenerating difference plots...")
    plot_differences(datasets, available_vars, args.output_dir, args.hist_file)

    print(f"\nDone. Figures saved to {args.output_dir}/")

if __name__ == "__main__":
    main()
