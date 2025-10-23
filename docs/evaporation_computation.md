# Evaporation Computation in ELM

## Summary

This document describes how evaporation is computed and partitioned in ELM, focusing on the combination of bare-ground evaporation and surface water evaporation for alternative hydrology models.

## Evaporation Components

### 1. Surface Flux Computation

Individual evaporation fluxes are computed in the surface energy balance:

**Location**: `biogeophys/BareGroundFluxesMod.F90:402-404`
```fortran
qflx_ev_snow(p)   = -raiw*(forc_q(t) - qg_snow(c))
qflx_ev_soil(p)   = -raiw*(forc_q(t) - qg_soil(c))
qflx_ev_h2osfc(p) = -raiw*(forc_q(t) - qg_h2osfc(c))
```

Where:
- `qflx_ev_soil` = evaporation from bare soil
- `qflx_ev_h2osfc` = evaporation from surface water (h2osfc)
- `qflx_ev_snow` = evaporation from snow
- `raiw` = aerodynamic resistance for water vapor
- `forc_q(t)` = atmospheric specific humidity
- `qg_*` = surface specific humidity for each surface type

### 2. Ground Evaporation Partitioning

Total ground evaporation is partitioned between liquid evaporation and ice sublimation:

**Location**: `biogeophys/SoilFluxesMod.F90:335-339`
```fortran
if ((h2osoi_liq(c,j)+h2osoi_ice(c,j)) > 0.) then
   qflx_evap_grnd(p) = max(qflx_ev_snow(p)*(h2osoi_liq(c,j)/(h2osoi_liq(c,j)+h2osoi_ice(c,j))), 0._r8)
else
   qflx_evap_grnd(p) = 0.
end if
qflx_sub_snow(p) = qflx_ev_snow(p) - qflx_evap_grnd(p)
```

This partitions total ground evaporation based on the liquid-to-total water ratio in the top soil layer:
- `qflx_evap_grnd` = liquid water evaporation from ground
- `qflx_sub_snow` = ice sublimation from ground

### 3. Hydrological Usage

Evaporation is removed from water inputs in the hydrology calculations:

**Location**: `biogeophys/SoilHydrologyMod.F90:476-477`
```fortran
qflx_in_soil(c) = qflx_in_soil(c) - (1.0_r8 - fsno - frac_h2osfc(c))*qflx_evap(c)
qflx_in_h2osfc(c) = qflx_in_h2osfc(c) - frac_h2osfc(c) * qflx_ev_h2osfc(c)
```

Where:
- `qflx_evap(c)` = `qflx_evap_grnd(c)` when no snow layers present (`SoilHydrologyMod.F90:452`)
- `fsno` = snow-covered fraction
- `frac_h2osfc(c)` = surface water fraction
- `(1.0_r8 - fsno - frac_h2osfc(c))` = exposed soil fraction

## Total Evaporation for Alternative Hydrology Models

### Area-Weighted Total Evaporation

For alternative hydrology models, the total evaporation should account for surface coverage fractions:

```fortran
! Area-weighted total evaporation accounting for surface coverage fractions
qflx_total_evap_weighted(c) = (1.0_r8 - fsno - frac_h2osfc(c)) * qflx_evap_grnd(c) + &
                              frac_h2osfc(c) * qflx_ev_h2osfc(c)
```

### Implementation

```fortran
! For alternative hydrology models
subroutine compute_total_evaporation(bounds, num_hydrologyc, filter_hydrologyc)
   
   ! Local variables
   integer :: c, fc
   real(r8) :: fsno, frac_exposed_soil
   
   do fc = 1, num_hydrologyc
      c = filter_hydrologyc(fc)
      
      ! Get snow fraction (0 if no snow)
      if (col_pp%snl(c) >= 0) then
         fsno = 0._r8
      else
         fsno = col_ws%frac_sno(c)
      end if
      
      ! Calculate exposed soil fraction
      frac_exposed_soil = 1.0_r8 - fsno - col_ws%frac_h2osfc(c)
      
      ! Total area-weighted evaporation
      qflx_total_evap(c) = frac_exposed_soil * col_wf%qflx_evap_grnd(c) + &
                           col_ws%frac_h2osfc(c) * col_wf%qflx_ev_h2osfc(c)
      
   end do
   
end subroutine compute_total_evaporation
```

## Key Variables

- **`qflx_evap_grnd`** - Ground evaporation from bare soil (liquid water component) [mm H2O/s]
- **`qflx_ev_h2osfc`** - Surface water evaporation from standing water [mm H2O/s]
- **`frac_h2osfc`** - Fraction of column covered by surface water [-]
- **`frac_sno`** - Fraction of column covered by snow [-]
- **`qflx_ev_soil`** - Raw evaporation flux from soil computed in energy balance [mm H2O/s]
- **`qflx_sub_snow`** - Ice sublimation component [mm H2O/s]

## Key Concepts

1. **Area-weighted approach** accounts for the fact that only exposed portions contribute to evaporation
2. **`qflx_evap_grnd`** operates on the exposed soil fraction 
3. **`qflx_ev_h2osfc`** operates on the surface water fraction
4. **Snow-covered areas** are excluded from both evaporation terms
5. **Partitioning between liquid and ice** is based on soil water phase composition

## ELM's Soil Evaporation Downregulation

### Soil Moisture Stress Factor (soilbeta)

ELM includes its own evaporation downregulation through a soil moisture stress factor based on the Lee-Pielke 1992 approach:

**Location**: `biogeophys/SurfaceResistanceMod.F90:148-158`
```fortran
if (wx < watfc(c,1)) then  ! when water content < field capacity
   fac_fc = min(1._r8, wx/watfc(c,1))
   fac_fc = max(fac_fc, 0.01_r8)
   soilbeta(c) = (1._r8-frac_sno(c)-frac_h2osfc(c)) &
        *0.25_r8*(1._r8 - cos(SHR_CONST_PI*fac_fc))**2._r8 &
        + frac_sno(c)+ frac_h2osfc(c)
else   ! when water content >= field capacity
   soilbeta(c) = 1._r8
end if
```

Where:
- `wx` = volumetric water content in top soil layer
- `watfc` = field capacity
- `soilbeta` ranges from ~0.01 to 1.0 based on soil moisture

### Application to Evaporation Fluxes

The `soilbeta` factor directly reduces aerodynamic conductance for water vapor:

**Location**: `biogeophys/BareGroundFluxesMod.F90:367-371`
```fortran
if (dqh(p) > 0._r8) then  ! dew formation
   raiw = forc_rho(t)/(raw)  ! no reduction for dew
else
   if(do_soilevap_beta())then
      raiw = soilbeta(c)*forc_rho(t)/(raw)  ! reduce evaporation by soilbeta
   endif
end if
```

This directly affects all latent heat fluxes computed from the reduced `raiw`:
```fortran
qflx_ev_snow(p)   = -raiw*(forc_q(t) - qg_snow(c))
qflx_ev_soil(p)   = -raiw*(forc_q(t) - qg_soil(c))  
qflx_ev_h2osfc(p) = -raiw*(forc_q(t) - qg_h2osfc(c))
```

### Energy Conservation Approach

**Important**: ELM does NOT explicitly convert reduced latent heat to sensible heat for soil evaporation downregulation. Energy conservation occurs through:

1. **Reduced latent heat flux** from evaporation limitation
2. **Ground temperature adjustment** in subsequent timesteps to balance the surface energy budget
3. **Iterative energy balance** in soil temperature calculations adjusts to the new energy partitioning

This is different from transpiration downregulation where excess latent heat is explicitly converted to sensible heat (`CanopyFluxesMod.F90:1124`).

## Implementation Considerations for Alternative Hydrology

### Option 1: Follow ELM's Approach
- Modify aerodynamic conductance with your additional stress factor
- Let energy balance adjust naturally through ground temperature changes

### Option 2: Explicit Energy Conservation
For more conservative energy balance, explicitly convert excess latent heat to sensible heat:

```fortran
! Calculate reduction in latent heat
original_latent_heat = qflx_ev_original * htvp(c)
reduced_latent_heat = qflx_ev_reduced * htvp(c) 
excess_latent_heat = original_latent_heat - reduced_latent_heat

! Convert to sensible heat
eflx_sh_grnd(p) = eflx_sh_grnd(p) + excess_latent_heat
```

## Dew Formation (Condensation) Handling

### Surface Humidity and Flux Calculations

ELM computes three separate surface evaporation fluxes based on surface-specific humidity:

**Location**: `biogeophys/BareGroundFluxesMod.F90:402-404`
```fortran
qflx_ev_snow(p)   = -raiw*(forc_q(t) - qg_snow(c))   ! Snow surface
qflx_ev_soil(p)   = -raiw*(forc_q(t) - qg_soil(c))   ! Soil surface  
qflx_ev_h2osfc(p) = -raiw*(forc_q(t) - qg_h2osfc(c)) ! Surface water
```

**Critical Insight**: When no snow layers exist (`snl >= 0`):
```fortran
qg_snow(c) = qg_soil(c)  ! CanopyTemperatureMod.F90:322
```
Therefore: **`qflx_ev_snow = qflx_ev_soil`** when there are no snow layers.

### Dew vs. Evaporation Partitioning

**Only `qflx_ev_snow`** goes through dew partitioning logic:

**Location**: `biogeophys/SoilFluxesMod.F90:340-346`
```fortran
if (qflx_ev_snow(p) >= 0._r8) then
   ! evaporation case - partition between liquid and ice
   qflx_evap_grnd(p) = max(qflx_ev_snow(p)*(h2osoi_liq(c,j)/(h2osoi_liq(c,j)+h2osoi_ice(c,j))), 0._r8)
   qflx_sub_snow(p) = qflx_ev_snow(p) - qflx_evap_grnd(p)
else
   ! condensation case - separate dew variables
   if (t_grnd(c) < tfrz) then
      qflx_dew_snow(p) = abs(qflx_ev_snow(p))
   else
      qflx_dew_grnd(p) = abs(qflx_ev_snow(p))
   end if
end if
```

**`qflx_ev_soil` and `qflx_ev_h2osfc` do NOT get converted to dew variables** - they remain as potentially negative fluxes.

## Complete Dew/Evaporation Tracking by Case

### Case 1: Snow Layers Exist (`snl < 0`)

**Surface Areas:**
- Snow-covered: `frac_sno_eff`
- Bare soil: `(1 - frac_sno_eff - frac_h2osfc)`  
- Surface water: `frac_h2osfc`

**Surface Fluxes:**
- `qflx_ev_snow` ≠ `qflx_ev_soil` (different surface humidities)

**Evaporation (positive fluxes):**
- **Snow surface**: `qflx_evap_grnd` and `qflx_sub_snow` → removed from snow layers with area weight `frac_sno_eff`
- **Bare soil**: `qflx_ev_soil` → removed via infiltration: `qflx_infl -= (1 - frac_sno) * qflx_ev_soil`
- **Surface water**: `qflx_ev_h2osfc` → removed from `h2osfc` with area weight `frac_h2osfc`

**Condensation (negative fluxes):**
- **Snow surface**: `qflx_dew_grnd`/`qflx_dew_snow` → **added to snow layers** with area weight `frac_sno_eff`
- **Bare soil**: Negative `qflx_ev_soil` → **added via infiltration**: `qflx_infl += abs(qflx_ev_soil) * (1 - frac_sno)`
- **Surface water**: Negative `qflx_ev_h2osfc` → **added to `h2osfc`** with area weight `frac_h2osfc`

**⚠️ POTENTIAL BUG**: Bare soil dew uses area weight `(1 - frac_sno)` instead of `(1 - frac_sno - frac_h2osfc)`, potentially double-counting surface water areas.

### Case 2: No Snow Layers but Snow Cover (`snl >= 0, frac_sno > 0`)

**Surface Areas:**  
- Thin snow: `frac_sno`
- Bare soil: `(1 - frac_sno - frac_h2osfc)`
- Surface water: `frac_h2osfc`

**Surface Fluxes:**
- `qflx_ev_snow = qflx_ev_soil` (identical due to `qg_snow = qg_soil`)

**Evaporation (positive fluxes):**
- **All non-snow surfaces**: `qflx_ev_soil` → removed via infiltration: `qflx_infl -= (1 - frac_sno) * qflx_ev_soil`
- **Surface water**: `qflx_ev_h2osfc` → removed from `h2osfc` with area weight `frac_h2osfc`

**Condensation (negative fluxes):**
- **All non-snow surfaces**: `qflx_dew_grnd`/`qflx_dew_snow` → **added to top soil layer** with area weight `(1 - frac_h2osfc)`
- **Surface water**: Negative `qflx_ev_h2osfc` → **added to `h2osfc`** with area weight `frac_h2osfc`

**⚠️ POTENTIAL INCONSISTENCY**: The same surface gets dew through both mechanisms:
1. Via `qflx_dew_*` (from `qflx_ev_snow`) with weight `(1 - frac_h2osfc)`
2. Via negative `qflx_ev_soil` in infiltration with weight `(1 - frac_sno)`

### Case 3: No Snow, No Snow Layers (`snl >= 0, frac_sno = 0`)

**Surface Areas:**
- Bare soil: `(1 - frac_h2osfc)`
- Surface water: `frac_h2osfc`

**Surface Fluxes:**
- `qflx_ev_snow = qflx_ev_soil` (identical)

**Evaporation (positive fluxes):**
- **Bare soil**: `qflx_ev_soil` → removed via infiltration: `qflx_infl -= qflx_ev_soil`
- **Surface water**: `qflx_ev_h2osfc` → removed from `h2osfc` with area weight `frac_h2osfc`

**Condensation (negative fluxes):**
- **Bare soil**: `qflx_dew_grnd`/`qflx_dew_snow` → **added to top soil layer** with area weight `(1 - frac_h2osfc)`  
- **Surface water**: Negative `qflx_ev_h2osfc` → **added to `h2osfc`** with area weight `frac_h2osfc`

**✅ CONSISTENT**: No double counting since `frac_sno = 0`.

## Water Balance Destinations Summary

| Surface Type | Evaporation Destination | Condensation Destination | Area Weight |
|-------------|------------------------|-------------------------|-------------|
| **Snow layers** | Snow layer water removal | Snow layer water addition (`qflx_dew_*`) | `frac_sno_eff` |
| **Bare soil** | Infiltration reduction | Infiltration increase (negative `qflx_ev_soil`) | `(1 - frac_sno)` ⚠️ |
| | | **OR** Direct soil addition (`qflx_dew_*`) | `(1 - frac_h2osfc)` |
| **Surface water** | `h2osfc` removal | `h2osfc` addition (negative `qflx_ev_h2osfc`) | `frac_h2osfc` |

### Key Issues Identified

1. **Asymmetric dew handling**: Only `qflx_ev_snow` gets converted to explicit dew variables; other surfaces remain as negative evaporation.

2. **Area weighting inconsistency**: Bare soil dew via infiltration uses `(1 - frac_sno)` instead of `(1 - frac_sno - frac_h2osfc)`, potentially including surface water areas.

3. **Potential double counting**: In Case 2, the same condensation could be counted through both dew variables and negative infiltration.

### Implementation Notes for Alternative Hydrology

**Complete water source tracking requires:**

1. **`qflx_top_soil`** (rain, snowmelt, irrigation, floods)
2. **Snow surface dew**: `qflx_dew_grnd + qflx_dew_snow` (when snow layers exist)
3. **Bare soil dew**: 
   - `qflx_dew_grnd + qflx_dew_snow` (when no snow layers) with weight `(1 - frac_h2osfc)`
   - **OR** `abs(qflx_ev_soil)` when `qflx_ev_soil < 0` with weight `(1 - frac_sno)` ⚠️
4. **Surface water dew**: `abs(qflx_ev_h2osfc)` when `qflx_ev_h2osfc < 0` with weight `frac_h2osfc`

**Recommendation**: Use the explicit dew variables (`qflx_dew_*`) when available to avoid the area weighting inconsistencies in the infiltration calculation.

## File References

- **Surface flux computation**: `biogeophys/BareGroundFluxesMod.F90:402-404`
- **Surface humidity calculation**: `biogeophys/CanopyTemperatureMod.F90:308,316,322,331`
- **Dew partitioning logic**: `biogeophys/SoilFluxesMod.F90:340-346`
- **Dew addition to soil layers**: `biogeophys/SoilHydrologyMod.F90:1005-1006`
- **Dew addition to snow layers**: `biogeophys/SnowHydrologyMod.F90:247,254`
- **Soil evaporation in infiltration**: `biogeophys/SoilHydrologyMod.F90:677,679`
- **Ground evaporation partitioning**: `biogeophys/SoilFluxesMod.F90:335-339`  
- **Hydrological removal**: `biogeophys/SoilHydrologyMod.F90:476-477`
- **Snow fraction logic**: `biogeophys/SoilHydrologyMod.F90:449-456`
- **Soil beta computation**: `biogeophys/SurfaceResistanceMod.F90:148-158`
- **Soil beta application**: `biogeophys/BareGroundFluxesMod.F90:367-371`
- **Transpiration energy conversion example**: `biogeophys/CanopyFluxesMod.F90:1124`
- **Variable definitions**: `ColumnDataType` for water flux and state variables
