# ELM Gross Water Source Analysis: `qflx_top_soil`

## Overview

This document analyzes `col_wf%qflx_top_soil`, the gross water source to the top of the surface and subsurface water column in the Energy Exascale Land Model (ELM).

## Variable Definition

- **Location**: `WaterfluxType.F90:74`
- **Description**: "col net water input into soil from top (mm/s)"
- **Units**: mm/s (millimeters per second)
- **Type**: Column-level water flux variable

## Primary Computation Location

The main computation occurs in **`SnowHydrologyMod.F90`** (lines 462-472):

### For Snow-Covered Columns (filter_snowc):
```fortran
qflx_top_soil(c) = (qout(c) / dtime) &
                 + (1.0_r8 - frac_sno_eff(c)) * qflx_rain_grnd(c)
```
- `qout(c) / dtime`: Snow melt water output from snow bottom layer
- `(1.0_r8 - frac_sno_eff(c)) * qflx_rain_grnd(c)`: Rain falling on exposed (non-snow covered) ground

### For Non-Snow Columns (filter_nosnowc):
```fortran
qflx_top_soil(c) = qflx_rain_grnd(c) + qflx_snomelt(c)
```
- `qflx_rain_grnd(c)`: Rain reaching ground after canopy interception
- `qflx_snomelt(c)`: Snow melt from any residual snow

## Contributing Water Sources

### 1. Precipitation Components (from CanopyHydrology)
- **Atmospheric forcing**: `forc_rain(t)` - atmospheric rain rate
- **Canopy throughfall**: `qflx_through_rain(p)` - rain passing through vegetation
- **Canopy drainage**: `qflx_candrip(p) * fracrain(p)` - rain dripping from canopy
- **Total to ground**: `qflx_rain_grnd = qflx_through_rain + canopy_drainage`

### 2. Irrigation (from CanopyHydrology:413,420)
```fortran
qflx_prec_grnd_rain(p) = qflx_prec_grnd_rain(p) + qflx_real_irrig(p)
```
- Irrigation water is added to precipitation reaching ground

### 3. Snow Melt Components (from SnowHydrology)
- **Snow pack drainage**: `qout(c)` - liquid water draining from snow bottom
- **Residual snow melt**: `qflx_snomelt(c)` - melt from small snow amounts

### 4. Additional Water Sources (from SoilHydrologyMod:257,284)
```fortran
qflx_top_soil(c) = qflx_top_soil(c) + qflx_snow_h2osfc(c) + qflx_floodc(c)
qflx_top_soil(c) = qflx_top_soil(c) + qflx_from_uphill(c)
```
- **Surface water snow**: `qflx_snow_h2osfc(c)` - snow falling on surface water
- **Flood water**: `qflx_floodc(c)` - flood water flux from river transport model
- **Uphill flow**: `qflx_from_uphill(c)` - lateral water flow from uphill areas

## Code Sections That Write to qflx_top_soil

1. **SnowHydrologyMod.F90:462-472** - Primary computation combining snow melt and rain
2. **SoilHydrologyMod.F90:257** - Adds surface water and flood contributions  
3. **SoilHydrologyMod.F90:284** - Adds lateral flow from uphill (if hillslope hydrology enabled)

## Where qflx_top_soil is Used

### 1. Balance Checks
Used in water balance verification:
- `BalanceCheckMod.F90:247,568,1000`

### 2. External Model Coupling
- **ATS interface**: Passed as "gross surface water source" (`ExternalModelATS.F90:227`)
- **PFLOTRAN interface**: Used as top boundary condition for reactive transport (`elm_interface_pflotranMod.F90:2549,2551,3608`)

### 3. Hydrology Modules
- Input to infiltration and surface runoff calculations

### 4. History Output
- Available as diagnostic variable "QTOPSOIL" (`ColumnDataType.F90:5904`)

## Physical Interpretation

`qflx_top_soil` represents the **total liquid water input rate to the top of the soil column**, combining:

- **Precipitation (rain)** after canopy interception
- **Snow melt** from overlying snow layers  
- **Irrigation water** applied to the surface
- **Flood water** from rivers via coupling
- **Lateral subsurface flow** from uphill areas
- **Snow falling on surface water** bodies

This variable serves as the key **gross water source term** that drives:
- Infiltration into the soil profile
- Surface runoff generation
- Vertical water movement through the subsurface
- Coupling with external hydrologic models (ATS, PFLOTRAN)

## Flow Diagram

```
Atmospheric Forcing (forc_rain)
        ↓
Canopy Interception & Throughfall
        ↓
qflx_rain_grnd ←─── Irrigation
        ↓
Snow Layer Processing
        ↓
qflx_top_soil ←─── Snow Melt
        ↓        ←─── Flood Water
        ↓        ←─── Uphill Flow  
        ↓        ←─── Surface Water Snow
Soil Infiltration & Surface Runoff
```

## Key Dependencies

- **Snow dynamics**: Snow accumulation, melt, and drainage processes
- **Canopy processes**: Vegetation interception and throughfall
- **Irrigation**: Agricultural water management
- **Topographic flow**: Hillslope lateral flow (if enabled)
- **River coupling**: Flood water inputs from MOSART