# ELM Gross Water Source Analysis

## Overview

ATS needs the gross water source to the top of both surface water and bare soil.  The majority of this is expressed in `col_wf%qflx_top_soil`.

- **Location**: `WaterfluxType.F90:74`
- **Description**: "col net water input into soil from top (mm/s)"
- **Units**: mm/s (millimeters per second)
- **History**: available as diagnostic variable "QTOPSOIL" (`ColumnDataType.F90:5904`)

A few additional dew-based terms need to be included as well.

## 1. Snow melt water.

The first computation occurs in **`SnowHydrologyMod.F90`** (lines 462-472):

### For Snow-Covered Columns (filter_snowc):
```fortran
qflx_top_soil(c) = (qout(c) / dtime) &
```
- `qout(c) / dtime`: Snow melt water output from snow bottom layer

### For Non-Snow Columns (filter_nosnowc):
```fortran
qflx_top_soil(c) = qflx_rain_grnd(c) + qflx_snomelt(c)
```
- `qflx_snomelt(c)`: Snow melt from any residual snow

- **Snow pack drainage**: `qout(c)` - liquid water draining from snow bottom



## 2. Precipitation Components

`qflx_rain_grnd` is added to `qflx_top_soil` in **`SnowHydrologyMod.F90`** (lines 462-472):

For Snow-Covered Columns (filter_snowc):
- `(1.0_r8 - frac_sno_eff(c)) * qflx_rain_grnd(c)`: Rain falling on exposed (non-snow covered) ground

For Non-Snow Columns (filter_nosnowc):
- `qflx_rain_grnd(c)`: Rain reaching ground after canopy interception

`qflx_rain_grnd` includes (from CanopyHydrology) (**line numbers needed**):

- **Atmospheric forcing**: `forc_rain(t)` - atmospheric rain rate
- **Canopy throughfall**: `qflx_through_rain(p)` - rain passing through vegetation
- **Canopy drainage**: `qflx_candrip(p) * fracrain(p)` - rain dripping from canopy


## 3. Irrigation (from CanopyHydrology:413,420)
```fortran
qflx_prec_grnd_rain(p) = qflx_prec_grnd_rain(p) + qflx_real_irrig(p)
```

Irrigation water is added to precipitation reaching ground


## 4. Additional Water Sources (from SoilHydrologyMod:257,284)
```fortran
qflx_top_soil(c) = qflx_top_soil(c) + qflx_snow_h2osfc(c) + qflx_floodc(c)
qflx_top_soil(c) = qflx_top_soil(c) + qflx_from_uphill(c)
```
- **Surface water snow**: `qflx_snow_h2osfc(c)` - snow falling on surface water
- **Flood water**: `qflx_floodc(c)` - flood water flux from MOSART
- **Uphill flow**: `qflx_from_uphill(c)` - lateral water flow from uphill areas (msut be zero for use_ats!)


## 5. Dew

In most cases, dew is included as negative evaporation.

In one very specific case, dew **IS NOT** included in evaporation.
See evaporation_computation section on "Add back in dew".  In other
cases and ground surface fractions, dew **IS** included as negative
evaporation.

So we choose to **NOT** consider dew in this calculation.

## Summary

In summary, it appears that all needed fluxes are included in `col_wf%qflx_top_soil`.
