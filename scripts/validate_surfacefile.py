import xarray as xr
import numpy as np
import argparse
import sys

def validate_surfacevars(ds):
    """
    Perform the following tests on a surface file for ELM-ATS:
    1) test that landunit fraction variables exist
    2) test that PCT_NATVEG = 100, and all other PCT_{landunit type} = 0.
    3) test that only one PCT_NAT_PFT = 100., and the rest = 0.
    """
    try:
        veg_lunit = ds["PCT_NATVEG"]
        lake_lunit = ds["PCT_LAKE"]
        urban_lunit = ds["PCT_URBAN"]
        glac_lunit = ds["PCT_GLACIER"]
        crop_lunit = ds["PCT_CROP"]
        wetl_lunit = ds["PCT_WETLAND"]
        pft_fractions = ds["PCT_NAT_PFT"]
    except KeyError as e:
        print(f"Missing variable:{e}", file=sys.stderr)
        sys.exit(2)

    # test the constraints above:
    if not (veg_lunit == 100.):
        print("FAIL: PCT_NATVEG not equal to 100%", file=sys.stderr)
        fail = True
    if (lake_lunit > 0.):
        print("FAIL: PCT_LAKE > 0", file=sys.stderr)
        fail = True
    if (all(urban_lunit) > 0.):
        print("FAIL: ANY PCT_LAKE > 0", file=sys.stderr)
        fail = True
    if (glac_lunit > 0.):
        print("FAIL: PCT_GLACIER > 0", file=sys.stderr)
        fail = True
    if (crop_lunit > 0.):
        print("FAIL: PCT_CROP > 0", file=sys.stderr)
        fail = True
    if (wetl_lunit > 0.):
        print("FAIL: PCT_WETLAND > 0", file=sys.stderr)
        fail = True

    # ensure there are no polygonal tundra landunits
    polygonal_vars = ['PCT_HCP', 'PCT_FCP', 'PCT_LCP']
    for var_name in polygonal_vars:
        if var_name in ds.variables:
            if not ((ds[var_name] == 0).all()):
                print(f"FAIL: {var_name} is present but contains non-zero values", file=sys.stderr)
                fail = True

    # test for only one PFT:
    pft_fracs = pft_fractions.values.flatten()
    if not (np.count_nonzero(pft_fracs == 100.) == 1 and np.count_nonzero(pft_fracs) == 1):
        print("FAIL: PCT_NAT_PFT has more than one PFT defined", file=sys.stderr)
        print(pft_fracs)
        fail = True

    if not (fail):
      print("PASS", file=sys.stdout)
    else:
      sys.exit(3)

def main():
    parser = argparse.ArgumentParser(description="Validate NetCDF Variables.")
    parser.add_argument("--file_name", type=str, required = True, help = "NetCDF surface file to validate")
    args = parser.parse_args()

    print(f"Testing dataset: {args.file_name}")
    try:
        ds = xr.open_dataset(args.file_name)
    except FileNotFoundError:
        print(f"File not found: {args.file_name}", file=sys.stderr)

    try:
        validate_surfacevars(ds)
    except Exception as e:
        print(f"Unexpected error in validation: {e}", file=sys.stderr)
        sys.exit(4)

if __name__ == "__main__":
    main()
