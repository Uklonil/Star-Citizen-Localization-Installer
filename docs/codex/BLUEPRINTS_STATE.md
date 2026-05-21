# Blueprints State

## Current Sources of Truth

- `source/blueprints/blueprints_template.ini`
- `source/blueprints/pools.json`

## Generated Artifacts

- `source/shared/overlays/blueprints.ini`
- `informes/BLUEPRINTS_POOLS_DISCOVERY.json`

## Current Audit Summary

- Last review pass completed on `2026-05-18`.
- Existing live extraction dated `2026-05-14` matched the current `LIVE` `Data.p4k`, so no re-extraction was required.
- High-confidence mission families were applied from contract and missiondata evidence.
- Transitional blueprint overlays were reduced to two unresolved cases.

## Known Confirmed Pools

- `bhg_bounty_*_FPS_intro` -> `BP_MISSIONREWARD_BountyHuntersGuild_PAF_EliminateSpecific`
- `Foxwell_DefendDestructibleEntites_*` -> `BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort`
- `Eckhart_EscortShips_{M,H,S,VH}_*` -> `BP_REWARDS_EckhartSecurityEscortShipsEasy`
- `EckhartSecurity_EliminateAll_*` and `EckhartSecurity_EliminateSpecific_DC_*` -> `BP_REWARDS_EckhartSecurityKillNPCBoss`
- `vaughn_assassination_FPS_UGF_{legal,illegal}_boss_*` -> `BP_MISSIONREWARD_VaughnGenerator_EliminateBoss`
- `Vaughn_EliminateBoss_FPS_Rockcracker_Warehouse_*` and `bhg_EliminateBoss_FPS_Rockcracker_Warehouse_*` -> `BP_MISSIONREWARD_RDC_Boss`
- `Vaughn_EliminateSpecific_FPS_Rockcracker_*` and `bhg_bounty_*_Rockcracker_*` now use explicit canonical pools instead of transitional overlays.

## Transitional Overlays

Resolved on `2026-05-18`:

- `recovery_desc`
- `Hockrow_FacilityDelve_P2M1_Repeat_desc`
- `Hockrow_FacilityDelve_P2M2_Repeat_desc`
- `Hockrow_FacilityDelve_P2M3_Repeat_desc`
- `Kaboos_Mission_Description`
- `Foxwell_ShipWaveAttack_ClearHostiles_Desc_M_001`
- `Foxwell_ShipWaveAttack_ClearHostiles_Desc_VE_001`
- `Vaughn_EliminateSpecific_FPS_Rockcracker_*`
- `bhg_bounty_desc_Rockcracker_*`
- `vaughn_assassination_FPS_UGF_{legal,illegal}_boss_desc_001`
- `Vaughn_EliminateBoss_FPS_Rockcracker_Warehouse_desc_001`
- `bhg_EliminateBoss_FPS_Rockcracker_Warehouse_desc_001`

Still intentionally unresolved:

- `Outpost_CleanUp_desc`
- `LOC_UNINITIALIZED`

## Known Blockers

- `Outpost_CleanUp_desc` still lacks a canonical pool mapping with sufficient evidence.
- `LOC_UNINITIALIZED` is a special placeholder and should not be normalized as a normal mission reward entry.
- Ambiguous candidates such as `cfp_eliminateall_intro_*` should stay out of the structured source until a strict mapping is available.

## Last Validated Builds

- Distribution build validated with `4.8.0-live.11825000.1`.
- Installer rebuilt successfully after BOM handling fix for staged language metadata.

## Next Priorities

- Revisit `Outpost_CleanUp_desc` only if a future extraction or live verification provides direct pool evidence.
- Keep using review reports in `informes/` before touching `blueprints_template.ini` or `pools.json`.
