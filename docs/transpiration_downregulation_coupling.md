# Transpiration Downregulation and Carbon-Water Coupling in ELM

## Summary

This document describes how to implement post-energy-balance transpiration downregulation while maintaining consistent carbon fluxes in ELM's `use_cn=true` mode (excluding FATES/BeTR).

## Background: Carbon-Water Coupling Mechanism

### Core Coupling Variable: `btran`

The primary water stress variable `btran` (transpiration wetness factor, 0-1) is computed in `SoilMoistStressMod.F90:391` based on soil water potential and root distribution. `btran` serves as the central coupling variable that coordinates water stress effects across both carbon and water cycles.

**Reference**: `biogeophys/SoilMoistStressMod.F90:391`
```fortran
btran(p) = btran(p) + max(rootr(p,j),0._r8)
```

### Stomatal Conductance Computation

Stomatal conductance is computed using the Ball-Berry model in `PhotosynthesisMod.F90:1564-1567`:

**Reference**: `biogeophys/PhotosynthesisMod.F90:1564-1567`
```fortran
aquad = cs
bquad = cs*(gb_mol - bbb(p)) - mbb(p)*an(p,iv)*forc_pbot(t)
cquad = -gb_mol*(cs*bbb(p) + mbb(p)*an(p,iv)*forc_pbot(t)*rh_can)
call quadratic (aquad, bquad, cquad, r1, r2)
gs_mol = max(r1,r2)
```

**Critical btran coupling**: `btran` directly affects the Ball-Berry intercept parameter:

**Reference**: `biogeophys/PhotosynthesisMod.F90:521`
```fortran
bbb(p) = max (bbbopt(p)*btran(p), 1._r8)
```

This means: **water stress (`btran`) → reduced stomatal intercept (`bbb`) → lower stomatal conductance (`gs_mol`) → reduced CO2 uptake (photosynthesis) and H2O loss (transpiration)**

## Transpiration Computation

### Energy Balance Iteration

Transpiration is computed within an iterative energy balance loop that converges on leaf temperature:

**Reference**: `biogeophys/CanopyFluxesMod.F90:782`
```fortran
ITERATION : do while (itlef <= itmax .and. fn > 0)
```

**Within each iteration**:

1. **Photosynthesis calculation** (`CanopyFluxesMod.F90:921-947`):
   ```fortran
   call Photosynthesis (bounds, fn, filterp, &
        svpts(begp:endp), eah(begp:endp), o2(begp:endp), co2(begp:endp), rb(begp:endp), btran(begp:endp), &
        dayl_factor(begp:endp), atm2lnd_vars, surfalb_vars, solarabs_vars, &
        canopystate_vars, photosyns_vars, 'sun')
   ```

2. **Transpiration flux calculation** (`CanopyFluxesMod.F90:1011-1024`):
   ```fortran
   if (btran(p) > btran0) then
      qflx_tran_veg(p) = efpot*rppdry
      rpp = rppdry + fwet(p)
   else
      !No transpiration if btran below 1.e-10
      rpp = fwet(p)
      qflx_tran_veg(p) = 0._r8
   end if
   ```

3. **Water limitation enforcement** (`CanopyFluxesMod.F90:1118-1124`):
   ```fortran
   if (qflx_tran_veg(p) > avail_pft(p)) then
      qflx_tran_veg(p) = avail_pft(p)
      qflx_deficit(p) = (efpot*rppdry - qflx_tran_veg(p))
      erre = htvp(c)*(efpot*rppdry - qflx_tran_veg(p))
      efsh = efsh + erre    ! Convert excess latent heat to sensible heat
   end if
   ```

### Water Deficit Handling

Water deficits are handled through aquifer water in the soil hydrology routines for normal vegetated columns:

**Reference**: `biogeophys/SoilWaterMovementMod.F90:163-187` (water deficit correction loop)
```fortran
do fc = 1, num_hydrologyc
   c = filter_hydrologyc(fc)
   j = nlev2bed(c)
   if (h2osoi_liq(c,j) < watmin) then
      xs(c) = watmin-h2osoi_liq(c,j)
   else
      xs(c) = 0._r8
   end if
   wa(c) = wa(c) - xs(c)  ! Reduce aquifer water
end do
```

Note: `filter_hydrologyc` includes soil columns (`istsoil`), crop columns (`istcrop`), and pervious road columns (`icol_road_perv`) as defined in `main/filterMod.F90:396-397`.

## ELM Driver Timing Sequence

The critical timing in `main/elm_driver.F90` for carbon allocation vs. soil hydrology:

### Phase 1: Energy Balance & Photosynthesis (Lines 788-792)
```fortran
call CanopyFluxes(bounds_clump, &
     filter(nc)%num_nolakeurbanp, filter(nc)%nolakeurbanp, &
     atm2lnd_vars, canopystate_vars, cnstate_vars, energyflux_vars, &
     frictionvel_vars, soilstate_vars, solarabs_vars, surfalb_vars, &
     ch4_vars, photosyns_vars )
```

### Phase 2: Carbon Allocation (Lines 1048-1133)
**Reference**: `main/elm_driver.F90:1038`
```fortran
if (use_cn .or. use_fates) then
```

**Reference**: `main/elm_driver.F90:1048-1053`
```fortran
call EcosystemDynNoLeaching1(bounds_clump, &
      filter(nc)%num_soilc, filter(nc)%soilc, &
      filter(nc)%num_soilp, filter(nc)%soilp, &
      filter(nc)%num_pcropp, filter(nc)%pcropp, &
      cnstate_vars, &
      atm2lnd_vars, &
```

**Reference**: `main/elm_driver.F90:1125-1133`
```fortran
call EcosystemDynNoLeaching2(bounds_clump, &
      filter(nc)%num_soilc, filter(nc)%soilc, &
      filter(nc)%num_soilp, filter(nc)%soilp, &
      filter(nc)%num_pcropp, filter(nc)%pcropp, doalb, &
      filter(nc)%num_ppercropp, filter(nc)%ppercropp, &
      cnstate_vars, atm2lnd_vars, &
      canopystate_vars, soilstate_vars, crop_vars, ch4_vars, &
      photosyns_vars, soilhydrology_vars, energyflux_vars, &
      sedflux_vars, solarabs_vars)
```

### Phase 3: Soil Hydrology (Lines 1227-1252)
**Reference**: `main/elm_driver.F90:1242-1248`
```fortran
call HydrologyDrainage(bounds_clump, &
   filter(nc)%num_nolakec, filter(nc)%nolakec, &
   filter(nc)%num_hydrologyc, filter(nc)%hydrologyc, &
   filter(nc)%num_urbanc, filter(nc)%urbanc, &
   filter(nc)%num_do_smb_c, filter(nc)%do_smb_c, &
   atm2lnd_vars, glc2lnd_vars, &
   soilhydrology_vars, soilstate_vars)
```

## Implementation Strategy

### Timing Requirement

**Critical**: Modify `btran` and recompute photosynthesis **between lines 792-1048** in `elm_driver.F90`:
- **After line 792**: `CanopyFluxes` has computed initial photosynthesis with standard soil water stress
- **Before line 1048**: `EcosystemDynNoLeaching1` allocates carbon to biomass pools

### Code Blocks to Reproduce

To implement transpiration downregulation with consistent carbon fluxes, the following code blocks must be reproduced:

#### 1. Ball-Berry Parameter Update
**Location**: `biogeophys/PhotosynthesisMod.F90:521-522`
```fortran
bbb(p) = max (bbbopt(p)*btran_modified(p), 1._r8)
mbb(p) = mbbopt(p)
```

#### 2. Photosynthesis Recalculation for Sunlit Leaves
**Location**: `biogeophys/CanopyFluxesMod.F90:921-925`
```fortran
call Photosynthesis (bounds, fn, filterp, &
     svpts(begp:endp), eah(begp:endp), o2(begp:endp), co2(begp:endp), rb(begp:endp), btran_modified(begp:endp), &
     dayl_factor(begp:endp), atm2lnd_vars, surfalb_vars, solarabs_vars, &
     canopystate_vars, photosyns_vars, 'sun')
```

#### 3. Photosynthesis Recalculation for Shaded Leaves
**Location**: `biogeophys/CanopyFluxesMod.F90:943-947`
```fortran
call Photosynthesis (bounds, fn, filterp, &
     svpts(begp:endp), eah(begp:endp), o2(begp:endp), co2(begp:endp), rb(begp:endp), btran_modified(begp:endp), &
     dayl_factor(begp:endp), atm2lnd_vars, surfalb_vars, solarabs_vars, &
     canopystate_vars, photosyns_vars, 'sha')
```

#### 4. Photosynthesis Totaling
**Location**: `biogeophys/CanopyFluxesMod.F90:1313-1314`
```fortran
call PhotosynthesisTotal(fn, filterp, &
     atm2lnd_vars, cnstate_vars, canopystate_vars, photosyns_vars)
```

### What Changes When `btran` is Modified

#### Stomatal Conductance Changes
**Yes**, stomatal conductance will change because `btran` directly affects the Ball-Berry intercept parameter (`PhotosynthesisMod.F90:521`), which reduces stomatal conductance through the Ball-Berry equation (`PhotosynthesisMod.F90:1564-1567`).

#### Leaf Temperature Doesn't Change  
**Correct**, leaf temperature won't change because the energy balance has already converged in the iteration loop (`CanopyFluxesMod.F90:782`).

#### PhotosynthesisTotal Variables That Change
**Location**: `biogeophys/PhotosynthesisMod.F90:1035-1038`

The modified `btran` → changed stomatal conductance → affects these key photosynthesis variables:
- `psnsun(p)`, `psnsha(p)` - sunlit and shaded leaf photosynthesis rates
- `psnsun_wc(p)`, `psnsha_wc(p)` - Rubisco-limited photosynthesis 
- `psnsun_wj(p)`, `psnsha_wj(p)` - RuBP-limited photosynthesis
- `psnsun_wp(p)`, `psnsha_wp(p)` - Product-limited photosynthesis

These are combined to produce the final patch-level carbon flux:
```fortran
fpsn(p) = psnsun(p)*laisun(p) + psnsha(p)*laisha(p)
```

Additionally, stomatal resistance values (`rssun`, `rssha`) are automatically updated as outputs from the `Photosynthesis` calls and will reflect the new water stress.

### Implementation Approach

1. **Compute additional water stress factor** based on your alternative hydrology model
2. **Calculate effective btran**: `btran_eff = btran * additional_stress_factor`
3. **Update Ball-Berry parameters** with `btran_eff`
4. **Recompute photosynthesis** for both sunlit and shaded leaves
5. **Recalculate photosynthesis totals** for patch-level fluxes
6. **Proceed with carbon allocation** using the corrected photosynthesis rates

### Energy Balance Considerations

Since the energy balance has already converged in `CanopyFluxes`, you may need to:
- Convert excess latent heat to sensible heat if transpiration is further reduced
- Ensure leaf temperature remains consistent with the converged energy balance

**Reference**: `biogeophys/CanopyFluxesMod.F90:1124`
```fortran
efsh = efsh + erre    ! Convert excess latent heat to sensible heat
```

## Key Files and Locations

- **Driver sequence**: `main/elm_driver.F90:788-1252`
- **Stomatal conductance**: `biogeophys/PhotosynthesisMod.F90:521, 1564-1567`
- **Photosynthesis**: `biogeophys/PhotosynthesisMod.F90:921-947`
- **Transpiration**: `biogeophys/CanopyFluxesMod.F90:1011-1024`
- **Water stress**: `biogeophys/SoilMoistStressMod.F90:391`
- **Water deficit handling**: `biogeophys/SoilWaterMovementMod.F90:163-187`
- **Column filters**: `main/filterMod.F90:396-397`

This approach ensures that both water fluxes and carbon allocation are consistent with your enhanced water limitation while maintaining the fundamental physiological coupling between carbon and water cycles through the stomatal conductance mechanism.