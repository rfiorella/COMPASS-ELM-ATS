"""
ATS-ify an ELM surface data file.

Enforces the constraints required for ELM-ATS single-PFT, pure natural
vegetation runs:
  - PCT_NATVEG = 100, all other landunit fractions = 0
  - PCT_NAT_PFT: dominant PFT (by total area) set to 100, rest 0
  - URBAN_REGION_ID = 0
"""

import xarray as xr
import numpy as np
import argparse
import sys


def find_dominant_pft(ds):
    pft = ds["PCT_NAT_PFT"].values
    # sum over all non-PFT dimensions
    totals = pft.sum(axis=tuple(range(1, pft.ndim)))
    return int(np.argmax(totals))


def atself_surfdata(ds, pft_index=None):
    ds = ds.copy()

    if pft_index is None:
        pft_index = find_dominant_pft(ds)
        print(f"Dominant PFT index: {pft_index}")

    # force pure natural vegetation landunit
    for var in ["PCT_LAKE", "PCT_CROP", "PCT_GLACIER", "PCT_WETLAND"]:
        if var in ds:
            ds[var] = xr.zeros_like(ds[var])

    ds["PCT_NATVEG"] = xr.full_like(ds["PCT_NATVEG"], 100.0)

    # zero all urban fractions across numurbl dimension
    if "PCT_URBAN" in ds:
        ds["PCT_URBAN"] = xr.zeros_like(ds["PCT_URBAN"])
    if "URBAN_REGION_ID" in ds:
        ds["URBAN_REGION_ID"] = xr.zeros_like(ds["URBAN_REGION_ID"])

    # set single dominant PFT
    pft = xr.zeros_like(ds["PCT_NAT_PFT"])
    # select the pft_index slice regardless of dimension layout
    pft_dim = ds["PCT_NAT_PFT"].dims[0]  # natpft is always the first dim
    pft[{pft_dim: pft_index}] = 100.0
    ds["PCT_NAT_PFT"] = pft

    return ds, pft_index


def main():
    parser = argparse.ArgumentParser(
        description="ATS-ify an ELM surface data file."
    )
    parser.add_argument("INPUT", help="Input ELM surface NetCDF file")
    parser.add_argument("OUTPUT", help="Output ATS-ified NetCDF file")
    parser.add_argument(
        "--pft",
        type=int,
        default=None,
        metavar="INDEX",
        help="PFT index to use (default: dominant by total area)",
    )
    args = parser.parse_args()

    print(f"Reading: {args.INPUT}")
    try:
        ds = xr.load_dataset(args.INPUT)
    except FileNotFoundError:
        print(f"File not found: {args.INPUT}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error opening file: {e}", file=sys.stderr)
        sys.exit(1)

    ds_out, pft_index = atself_surfdata(ds, pft_index=args.pft)

    print(f"Writing: {args.OUTPUT}  (PFT index {pft_index})")
    ds_out.to_netcdf(args.OUTPUT)
    print("Done.")


if __name__ == "__main__":
    main()
