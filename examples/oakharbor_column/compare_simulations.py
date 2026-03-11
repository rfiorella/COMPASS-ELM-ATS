"""Compare ELM, ELM+ATS IC, and ELM-ATS simulation outputs."""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

VARIABLES = [
    "TBOT", "PBOT", "RH", "RAIN", "SNOW",
    "TLAI", "ZWT", "SMP", "SOILLIQ", "SOILICE",
]

# Variables that have a vertical (depth) dimension
SOIL_VARIABLES = {"SMP", "SOILLIQ", "SOILICE"}

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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare ELM, ELM+ATS IC, and ELM-ATS simulations."
    )
    parser.add_argument(
        "--base-dir",
        required=True,
        help="Path to E3SM_WORK_DIR (contains cases/ subdirectory).",
    )
    parser.add_argument(
        "--case-name",
        default="oakharbor_column",
        help="Case name (default: oakharbor_column).",
    )
    parser.add_argument(
        "--hist-file",
        default="h1",
        choices=["h0", "h1"],
        help="History file stream to load (default: h1 for daily output).",
    )
    parser.add_argument(
        "--output-dir",
        default="./figures",
        help="Directory for saved figures (default: ./figures).",
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
            "cases",
            f"{case_name}.{suffix}",
            "run",
            f"{case_name}.{suffix}.elm.{hist_file}.*.nc",
        )
        print(f"Loading {label}: {pattern}")
        ds = xr.open_mfdataset(pattern, combine="by_coords")
        datasets[label] = ds
    return datasets


def plot_timeseries(datasets, variables, output_dir):
    """Plot time series for each variable, comparing all simulations."""
    for var in variables:
        # Check the variable exists in at least one dataset
        available = {k: ds for k, ds in datasets.items() if var in ds}
        if not available:
            print(f"  Skipping {var}: not found in any dataset.")
            continue

        # Determine if this is a soil (3D) variable
        sample_ds = next(iter(available.values()))
        dims = sample_ds[var].dims
        has_depth = any(d in dims for d in ("levgrnd", "levsoi", "levdcmp"))

        if has_depth and var in SOIL_VARIABLES:
            # Find the depth dimension name
            depth_dim = next(d for d in ("levgrnd", "levsoi", "levdcmp") if d in dims)
            depth_vals = sample_ds[depth_dim].values
            # Select a few representative depth levels
            n_levels = len(depth_vals)
            indices = [0, n_levels // 4, n_levels // 2, 3 * n_levels // 4, n_levels - 1]
            indices = sorted(set(indices))

            fig, axes = plt.subplots(
                len(indices), 1, figsize=(10, 3 * len(indices)), sharex=True
            )
            if len(indices) == 1:
                axes = [axes]

            for ax, idx in zip(axes, indices):
                depth = depth_vals[idx]
                for label, ds in available.items():
                    data = ds[var].isel({depth_dim: idx}).squeeze()
                    ax.plot(ds["time"], data, label=label, color=SIM_COLORS[label])
                ax.set_ylabel(f"{var} (depth={depth:.2f} m)")
                ax.legend(fontsize="small")
                ax.grid(True, alpha=0.3)
            axes[-1].set_xlabel("Time")
            fig.suptitle(f"{var} — Time Series by Depth", fontsize=14)
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
        fig.savefig(os.path.join(output_dir, f"timeseries_{var}.png"), dpi=150)
        plt.close(fig)
        print(f"  Saved timeseries_{var}.png")


def plot_profiles(datasets, variables, output_dir):
    """Plot vertical profiles for soil variables at selected time steps."""
    soil_vars = [v for v in variables if v in SOIL_VARIABLES]
    if not soil_vars:
        return

    for var in soil_vars:
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

        times = sample_ds["time"].values
        n_times = len(times)
        # Select start, middle, and end time steps
        snap_indices = [0, n_times // 2, n_times - 1]
        snap_indices = sorted(set(snap_indices))

        fig, axes = plt.subplots(
            1, len(snap_indices), figsize=(5 * len(snap_indices), 6), sharey=True
        )
        if len(snap_indices) == 1:
            axes = [axes]

        for ax, ti in zip(axes, snap_indices):
            t_val = np.datetime_as_string(times[ti], unit="D")
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
        fig.savefig(os.path.join(output_dir, f"profile_{var}.png"), dpi=150)
        plt.close(fig)
        print(f"  Saved profile_{var}.png")


def plot_differences(datasets, variables, output_dir):
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

        if has_depth and var in SOIL_VARIABLES:
            depth_dim = next(d for d in ("levgrnd", "levsoi", "levdcmp") if d in dims)
            # Plot depth-averaged difference
            fig, ax = plt.subplots(figsize=(10, 4))
            for diff_label, sim_label in diff_labels.items():
                if sim_label not in datasets or var not in datasets[sim_label]:
                    continue
                diff = (
                    datasets[sim_label][var].mean(dim=depth_dim)
                    - ref[var].mean(dim=depth_dim)
                ).squeeze()
                ax.plot(
                    ref["time"], diff, label=diff_label, color=diff_colors[diff_label]
                )
            ax.set_ylabel(f"Delta {var} (depth-averaged)")
        else:
            fig, ax = plt.subplots(figsize=(10, 4))
            for diff_label, sim_label in diff_labels.items():
                if sim_label not in datasets or var not in datasets[sim_label]:
                    continue
                diff = (datasets[sim_label][var] - ref[var]).squeeze()
                ax.plot(
                    ref["time"], diff, label=diff_label, color=diff_colors[diff_label]
                )
            ax.set_ylabel(f"Delta {var}")

        ax.axhline(0, color="k", linewidth=0.5)
        ax.set_xlabel("Time")
        ax.set_title(f"{var} — Differences from ELM")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, f"diff_{var}.png"), dpi=150)
        plt.close(fig)
        print(f"  Saved diff_{var}.png")


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading simulations...")
    datasets = load_simulations(args.base_dir, args.case_name, args.hist_file)

    # Only plot variables that exist in at least one dataset
    available_vars = [
        v for v in VARIABLES if any(v in ds for ds in datasets.values())
    ]
    print(f"Variables available: {available_vars}")

    print("\nGenerating time series plots...")
    plot_timeseries(datasets, available_vars, args.output_dir)

    print("\nGenerating vertical profile plots...")
    plot_profiles(datasets, available_vars, args.output_dir)

    print("\nGenerating difference plots...")
    plot_differences(datasets, available_vars, args.output_dir)

    print(f"\nDone. Figures saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
