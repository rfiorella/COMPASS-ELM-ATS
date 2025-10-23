# Evaporation Computation in ELM

## Summary

This document traces how evaporation is computed and partitioned in ELM, focusing on the combination of bare-ground evaporation and surface water evaporation for alternative hydrology models.

## 1. Surface Flux Computation

Individual evaporation fluxes are computed in the surface energy balance at the PFT level for both:

### E.g. Bare Ground (`frac_veg_nosno(p) == 0`, biogeophys/BareGroundFluxesMod.F90:208)

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

Two additional "total" fluxes are computed, also at the PFT level:

**Location**: `biogeophys/BareGroundFluxesMod.F90:397-399`
```fortran
! water fluxes from soil
qflx_evap_soi(p)  = -raiw*dqh(p)
qflx_evap_tot(p)  = qflx_evap_soi(p)
```

> **FIX ME**
>
> `qflx_evap_tot` is not necessary here, it should be removed as it is
> also set in SoilFluxesMod.F90:313, and setting it in only one place
> would be preferable.

### Or Vegetated (`frac_veg_nosno(p) == 0`, beogeophys/CanopyFluxesMod.F90:507):

**Location**: `biogeophys/CanopyFluxesMod.F90:1247-1253`
```fortran
qflx_ev_snow(p) = forc_rho(t)*wtgq(p)*delq_snow
qflx_ev_soil(p) = forc_rho(t)*wtgq(p)*delq_soil
qflx_ev_h2osfc(p) = forc_rho(t)*wtgq(p)*delq_h2osfc
```

**Location**: `biogeophys/CanopyFluxesMod.F90:1243`
```fortran
qflx_evap_soi(p) = forc_rho(t)*wtgq(p)*delq(p)
```

> **FIX ME**
>
> In most places, in the associate block, `qflx_ev_*` are commented as
> being in (W/m**2) when in fact they are mm/s, like all other qflx
> variables.  Note the implied per unit area here is surface area, not
> per unit PFT area -- they don't have the fraction factor in them.
> See for instance BareGroundFluxesMod.F90:189, but this is throughout
> the code.


Note that in the case where there is no snow layers `snl(c) >= 0` then
`qg_snow(c) = qg_soil(c)` and so, in the next timestep, 
`qflx_ev_snow == qflx_ev_soil` (biogeophys/CanopyTemperatureMod.F90:322).


## 2. Temperature increment.

The above were (presumably) computed with last timestep's
temperatures.  A correction to these are computed based on a
derivative with respect to temperature and a temperature increment
after the temperatures are updated in the
e.g. SoilTemperature/CanopyTemperature subroutines.

**Location**: `biogeophys/SoilFluxesMod.F90:218-220
```fortran
qflx_ev_snow(p) = qflx_ev_snow(p) + tinc(c)*cgrndl(p)
qflx_ev_soil(p) = qflx_ev_soil(p) + tinc(c)*cgrndl(p)
qflx_ev_h2osfc(p) = qflx_ev_h2osfc(p) + tinc(c)*cgrndl(p)
```

## 3. Water availability limitation.

Because ELM is an explicit code, evap is limited to make sure it does
not try to pull more water than is available in the top cell of the
column.  This downregulation (not needed if using ATS) is a simple
weighted rates problem -- all evap rates are multiplied by a factor
`egirat` (who comes up with these names?  Would be nice to document
what these are short for, as it would help new developers remember
them...) which is a ratio of the available water divided by the
weighted sum (across PFTs) of `qflx_evap_soi`.

**Location**: `biogeophys/SoilFluxesMod.F90:271-277`
```fortran
if (egirat(c) < 1.0_r8) then
  save_qflx_evap_soi = qflx_evap_soi(p)
  qflx_evap_soi(p) = qflx_evap_soi(p) * egirat(c)
  eflx_sh_grnd(p) = eflx_sh_grnd(p) + (save_qflx_evap_soi - qflx_evap_soi(p))*htvp(c)
  qflx_ev_snow(p) = qflx_ev_snow(p) * egirat(c)
  qflx_ev_soil(p) = qflx_ev_soil(p) * egirat(c)
  qflx_ev_h2osfc(p) = qflx_ev_h2osfc(p) * egirat(c)
end if
```

## 4. Ground Evaporation Partitioning

The flux on snow-covered ground `qflx_ev_snow` is partitioned between
liquid evaporation, ice sublimation, liquid dew, and snow dew:

**Location**: `biogeophys/SoilFluxesMod.F90:331-346`
```fortran
if (qflx_ev_snow(p) >= 0._r8) then
  ! for evaporation partitioning between liquid evap and ice sublimation,
  ! use the ratio of liquid to (liquid+ice) in the top layer to determine split
  if ((h2osoi_liq(c,j)+h2osoi_ice(c,j)) > 0.) then
    qflx_evap_grnd(p) = max(qflx_ev_snow(p)*(h2osoi_liq(c,j)/(h2osoi_liq(c,j)+h2osoi_ice(c,j))), 0._r8)
  else
    qflx_evap_grnd(p) = 0.
  end if
  qflx_sub_snow(p) = qflx_ev_snow(p) - qflx_evap_grnd(p)
else
  if (t_grnd(c) < tfrz) then
    qflx_dew_snow(p) = abs(qflx_ev_snow(p))
  else
    qflx_dew_grnd(p) = abs(qflx_ev_snow(p))
  end if
end if
```

Note that this is ONLY for `qflx_ev_snow`, but it actually would be
valid for `qfx_ev_grnd` too IF there are no snow layers, as in that
case, `qflx_ev_snow == qflx_ev_grnd`?

> NOTE:
> 
> It remains to be seen if, in the case of no snow layers, whether
> these get hit by the area fractions and therefore are zero, or only
> one gets used, or what?


## 5. Patch to Column

These are then accumulated to the column level. `main/elm_driver.F90:891,1782`


## 6. Column-level usage -- combining evap and input water to get final fluxes.

Things begin to split with lots of cases and get hard to track code
here.  This could be improved upon, or at least lots of comments added.

Note that the below are all in subroutines in SoilHydrologyMod, which
are CALLED in HydrologyNoDrainageMod.



### Case for snow layers?

**Location**: SoilHydrologyMod.F90:448 (Infiltration)

**if snl >= 0 (no snow layers)**

- `fsno` is explicitly set to 0
- `qflx_evap` gets `qflx_evap_grnd` which is the liquid evaporation portion of `qflx_ev_snow` (or equivalently `qflx_ev_soil`), but does not include condensation.

**there are snow layers**
- `fsno` is explicitly set to frac_sno
- `qflx_evap` gets `qflx_ev_soil` which DOES include liquid condensation


### Partition inputs of water to surface water and soil

**Location**: SoilHydrologyMod.F90:473 (Infiltration)
``` fortran
!1. partition surface inputs between soil and h2osfc
qflx_in_soil(c) = (1._r8 - frac_h2osfc(c)) * (qflx_top_soil(c)  - qflx_surf(c))
qflx_in_h2osfc(c) = frac_h2osfc(c) * (qflx_top_soil(c)  - qflx_surf(c))
```

Note that `qflx_top_soil` is discussed extensively in another notes
file.  `qlfx_surf` is surface runoff.  So this is partitioning
incoming water between inundated area and not-inundated area.

### Remove evaporation

**Location**: SoilHydrologyMod.F90:475 (Infiltration)
```fortran
!2. remove evaporation (snow treated in SnowHydrology)
qflx_in_soil(c) = qflx_in_soil(c) - (1.0_r8 - fsno - frac_h2osfc(c))*qflx_evap(c)
qflx_in_h2osfc(c) = qflx_in_h2osfc(c) - frac_h2osfc(c) * qflx_ev_h2osfc(c)
```

So, **if no snow layers**, this is the evaporation (but not
condensation) portion of `qflx_ev_snow`, which is also the same as
`qflx_ev_soil`, on the non-inundated portion?  

> NOTE:
> 
> To me this seems like it ought to be that qflx_evap, as used here,
> should be based on `qflx_ev_soil` not `qf_ev_snow` in the branch for
> no snow levels (e.g. through qflx_evap).  But it isn't **wrong**,
> just oddly coded to rely on snow being set the same as bare ground
> calculations.

Otherwise, this is the evaporation or condensation of `qflx_ev_soil`,
on the bare portion.

> NOTE:
>
> Potential bug here?  There is an asymetry that smells here.  In the
> case where there are no snow layers, dew is removed.  In the case
> where there are snow layers, dew is included (on the
> 1-fsno-frac-h2osfc portion).  So hopefully `qflx_dew_grnd` better get
> added back in only under the condition that snl >= 0 (no snow
> layers)?  Or if it gets added unilaterally on the bare ground
> portion then there is double-counting of dew_grnd.


### Add back in dew

**Location**: SoilHydrologyMod.F90:1005 (WaterTable)
```fortran
if (snl(c)+1 >= 1) then
  ...
  h2osoi_liq(c,1) = h2osoi_liq(c,1) + (1._r8 - frac_h2osfc(c))*qflx_dew_grnd(c) * dtime
  ...
end if
```

Ok, so this looks right -- adding back in `qflx_dew_grnd` on the
non-inundated area is in fact correctly a function of no snow layer,
though why write `snl(c)+1 >= 1` when everywhere else it is `snl(c) >=
0`.

But note that dew is therefore, in the case of no snow layers,
**manually added** and is not a part of any of the other fluxes
(e.g. not in `qflx_top_soil`).  So it will need to be accounted for in
ATS coupling.


## ELM's Soil Evaporation Downregulation

### Soil Moisture Stress Factor (soilbeta)

ELM includes its own evaporation downregulation through a soil
moisture stress factor based on the Lee-Pielke 1992 approach, which is
computed during the CanopyTemperature call but used the next timestep
during the CanopyFluxes call (why?!?).  Flow of this code is seriously
questionable with no documentation or comments.

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
