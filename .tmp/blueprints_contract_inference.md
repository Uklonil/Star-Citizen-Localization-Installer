# Inferencia pool real desde contratos del juego

Metodo:
- Aprender `contractgenerator/*.xml -> pool` usando solo misiones ya presentes en el template.
- Aplicar ese mapa a misiones nuevas que compartan exactamente la misma ruta de contrato detectada en `Game2.dcb`.
- No usa heuristica de nombres de mision; solo reutiliza contratos detectados en el binario.

Resumen:
- Misiones template evaluadas: 322
- Enlaces directos exportados (`title/desc -> blueprintPool`): 676
- Contratos con al menos una pool observada: 30
- Misiones nuevas con inferencia directa desde export JSON: 0
- Misiones nuevas con inferencia unica estricta (contrato + missiondata): 0
- Misiones nuevas con inferencia unica solo por contrato: 15
- Misiones nuevas resueltas por endurecimiento especifico de familia: 0
- Misiones nuevas con contrato pero varias pools posibles: 1
- Misiones nuevas sin contrato util o sin aprendizaje previo: 465

## Inferencias Directas Desde Export JSON

Sin inferencias directas.

## Contrato + Missiondata A Pool

| Contrato | Missiondata | Pools observadas |
|---|---|---|
| `libs/foundry/records/contracts/contractgenerator/academyofsciences_guild/highpoint wilderness specialists/highpointwildernessspecialists_killanimals.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_RDC_Generic` x1 |
| `libs/foundry/records/contracts/contractgenerator/interstellartransport_guild/ftl/ftl_courier.xml` | `libs/foundry/records/missiondata/pu_organizations/aegisdynamics.xml` | `BP_REWARDS_FTL` x2 |
| `libs/foundry/records/contracts/contractgenerator/interstellartransport_guild/lingfamilyhauling/lingfamilyhauling_hauling.xml` | `libs/foundry/records/missiondata/pu_organizations/rayari.xml` | `BP_REWARDS_LingFamilyHauling` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/bountyhunterguild/bountyhuntersguild_fps.xml` | `libs/foundry/records/missiondata/pu_locations/templates/missiongivers/location_battaglia.xml` | `BP_MISSIONREWARD_BHG_ASDFacilityDelving_ResearchWing_EliminateSpecific` x1<br>`BP_MISSIONREWARD_BHG_ASDFacilityDelving_EngineeringWing_EliminateSpecific` x1<br>`BP_MISSIONREWARD_BountyHuntersGuild_PAF_EliminateSpecific` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_defendship.xml` | `libs/foundry/records/missiondata/pu_items/carryable_1h/missionitems/pu_hackingchip_spd3rel3.xml` | `BP_MISSIONREWARD_InterSec_DefendShip` x8<br>`BP_MISSIONREWARD_RDC_Generic` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_destroyitems.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_CitizensForProsperityDestroyItems_AB` x7<br>`BP_MISSIONREWARD_CitizensForProsperityDestroyItems_CD` x2 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `libs/foundry/records/missiondata/pu_organizations/stanton/stanton2/lingfamilyhauling.xml`<br>`libs/foundry/records/missiondata/entityclusterids/orbageddon/orbageddon_stanton2b_attritus.xml`<br>`libs/foundry/records/missiondata/pu_organizations/topsidetransfers.xml` | `BP_REWARDS_LingFamilyHauling` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_mercenary_fps.xml` | `libs/foundry/records/missiondata/declarations/locationentitytypes/deliverytargets/deliverytarget_locker_any.xml` | `BP_MISSIONREWARD_CFP_Outpost_RegionAB` x3<br>`BP_MISSIONREWARD_CFP_Outpost_RegionC` x3<br>`BP_MISSIONREWARD_CFP_EliminateAll_HeadHunters` x1<br>`BP_MISSIONREWARD_CFP_EliminateAllFromCFP_HeadHunters` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_mercenary_fps.xml` | `libs/foundry/records/missiondata/declarations/locationentitytypes/deliverytargets/deliverytarget_locker_any.xml`<br>`libs/foundry/records/missiondata/pu_items/derelictships/derelictship_freelancer.xml` | `BP_MISSIONREWARD_CFP_Outpost_RegionAB` x2<br>`BP_MISSIONREWARD_CFP_ChainElim_3` x2<br>`BP_MISSIONREWARD_CFP_ChainElim_1and2` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_mercenary_fps.xml` | `libs/foundry/records/missiondata/pu_items/derelictships/derelictship_freelancer.xml` | `BP_MISSIONREWARD_CFP_ChainElim_1and2` x1<br>`BP_MISSIONREWARD_CFP_ChainElim_3` x1<br>`BP_MISSIONREWARD_CFP_Outpost_RegionC` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_mercenary_fps.xml` | `libs/foundry/records/missiondata/pu_items/derelictships/derelictship_freelancer.xml`<br>`libs/foundry/records/missiondata/declarations/locationentitytypes/deliverytargets/deliverytarget_locker_any.xml` | `BP_MISSIONREWARD_CFP_ChainElim_1and2` x3<br>`BP_MISSIONREWARD_CFP_ChainElim_3` x2 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_defendship.xml` | `libs/foundry/records/missiondata/pu_items/carryable_1h/familyheirloom.xml`<br>`libs/foundry/records/missiondata/pu_missionlocality/stanton1.xml` | `BP_MISSIONREWARD_RDC_Generic` x6<br>`BP_MISSIONREWARD_InterSec_DefendShip` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_escortships.xml` | `libs/foundry/records/missiondata/pu_items/carryable_2h/food/lunesfruit.xml`<br>`libs/foundry/records/missiondata/pu_items/timetrials/raceclass/timetrials_raceclass_championship.xml` | `BP_REWARDS_EckhartSecurityEscortShipsEasy` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_escortships.xml` | `libs/foundry/records/missiondata/pu_missionlocality/pyro3.xml`<br>`/~/MapNamespace~/GeneralMapData/RightPanelData/MissionData/HasLinkToContractApp`<br>`/~/MapNamespace~/GeneralMapData/RightPanelData/MissionData/AcceptedMissions`<br>`/~/MapNamespace~/GeneralMapData/RightPanelData/MissionData/TrackedMissionIndex`<br>`libs/foundry/records/missiondata/pu_items/carryable_2h/food/lunesfruit.xml`<br>`/~/MapNamespace~/GeneralMapData/RightPanelData/MissionData/AcceptedMissions/[TrackedMissionIndex]/Objectives`<br>`/~/MapNamespace~/GeneralMapData/RightPanelData/MissionData/DropdownExpanded`<br>`libs/foundry/records/missiondata/pu_items/timetrials/raceclass/timetrials_raceclass_championship.xml` | `BP_REWARDS_EckhartSecurityEscortShipsEasy` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_killnpc.xml` | `libs/foundry/records/missiondata/pu_items/tbo/1scu/osoianhides_1scu.xml` | `BP_REWARDS_EckhartSecurityKillNPCBoss` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_recovercargo.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_VaughnGenerator_EliminateSpecific` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_destroyitems.xml` | `libs/foundry/records/missiondata/pu_locations/templates/system/spacestations/reststop_nyx_social_02.xml`<br>`libs/foundry/records/missiondata/pu_organizations/pontrelliexpressshipping.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_generator.xml` | `libs/foundry/records/missiondata/pu_items/tbo/1scu/redfinmodulators_1scu.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x3 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_generator.xml` | `libs/foundry/records/missiondata/pu_items/tbo/1scu/redfinmodulators_1scu.xml`<br>`libs/foundry/records/missiondata/pu_locations/templates/caves/cave.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x4<br>`BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_generator.xml` | `libs/foundry/records/missiondata/pu_locations/templates/caves/cave.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_generator.xml` | `libs/foundry/records/missiondata/pu_locations/templates/caves/cave.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/redfinmodulators_1scu.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_shipwaveattack.xml` | `libs/foundry/records/missiondata/pu_items/tbo/1scu/redfinmodulators_1scu.xml` | `BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x4<br>`BP_MISSIONREWARD_FoxwellEnforcement_Generator` x3 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_ambush.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_FoxwellEnforcement_Ambush` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_defenddestructibleentities.xml` | `libs/foundry/records/missiondata/pu_items/tbo/1scu/ammocrate_1scu.xml`<br>`libs/foundry/records/missiondata/pu_locations/templates/system/spacestations/social_spacestation.xml` | `BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x3 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_defenddestructibleentities.xml` | `libs/foundry/records/missiondata/pu_locations/templates/system/spacestations/social_spacestation.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/ammocrate_1scu.xml` | `BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x3 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_escortships.xml` | `libs/foundry/records/missiondata/pu_locations/templates/ugfs/ugf.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_EscortShips` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_patrol.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_FoxwellEnforcement_Patrol` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/hockrowagency/hockrowagency_facilitydelve.xml` | `libs/foundry/records/missiondata/pu_locations/templates/lagrange/lagrangepoint.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/moldtreatment_1scu.xml` | `BP_MISSIONREWARD_ASD2B` x1<br>`BP_MISSIONREWARD_ASD2C` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_defendship.xml` | `libs/foundry/records/missiondata/pu_organizations/redwindlinehaul.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/copper_1scu.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/souvenirs_1scu.xml` | `BP_MISSIONREWARD_InterSec_DefendShip` x3 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_defendship.xml` | `libs/foundry/records/missiondata/pu_organizations/redwindlinehaul.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/souvenirs_1scu.xml` | `BP_MISSIONREWARD_InterSec_DefendShip__02` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_defendship.xml` | `libs/foundry/records/missiondata/pu_organizations/redwindlinehaul.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/souvenirs_1scu.xml`<br>`libs/foundry/records/missiondata/pu_items/tbo/1scu/copper_1scu.xml` | `BP_MISSIONREWARD_InterSec_DefendShip` x2 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_killship.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_RDC_Generic` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_patrol.xml` | `libs/foundry/records/missiondata/pu_organizations/covalexindependentcontractors.xml` | `BP_MISSIONREWARD_InterSec_Patrol` x2 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_resourcegathering.xml` | `libs/foundry/records/missiondata/declarations/locationentitytypes/deliverytargets/deliverytarget_itemport.xml` | `BP_MISSIONREWARD_InterSec_ResourceGathering` x2 |
| `libs/foundry/records/contracts/contractgenerator/thecouncil_guild/headhunters/headhunters_mercenary_fps.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateSpecific_RegionAB` x5<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateSpecific_RegionCD` x2<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateBoss` x1 |
| `libs/foundry/records/contracts/contractgenerator/thecouncil_guild/headhunters/headhunters_mercenary_fps.xml` | `libs/foundry/records/missiondata/pu_locations/templates/derelicts/drak_caterpillar.xml` | `BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateSpecific_RegionAB` x4<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateSpecific_RegionCD` x1 |
| `libs/foundry/records/contracts/contractgenerator/thecouncil_guild/headhunters/headhunters_mercenary_fps.xml` | `libs/foundry/records/missiondata/pu_missionlocality/pyro_regions/regiond.xml` | `BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateALL_RegionAB` x17<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateALL_RegionCD` x5 |
| `libs/foundry/records/contracts/contractgenerator/thecouncil_guild/vaughn/vaughn_generator.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_VaughnGenerator_EliminateSpecific` x2 |
| `libs/foundry/records/contracts/contractgenerator/unitedresourceworkers_guild/shubin interstellar/shubin_resourcegathering_fpsmining.xml` | `libs/foundry/records/missiondata/pu_items/tbo/1scu/astatine_1scu.xml` | `BP_MISSIONREWARD_Shubin_ResourceGathering_FPSMining_Pyro` x5<br>`BP_MISSIONREWARD_Shubin_ResourceGathering_FPSMining_Stanton` x4 |
| `libs/foundry/records/contracts/contractgenerator/unitedresourceworkers_guild/shubin interstellar/shubin_resourcegathering_shipmining.xml` | `(sin missiondata)` | `BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_PyroNyx` x12<br>`BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_Stanton` x6 |
| `libs/foundry/records/contracts/contractgenerator/unitedresourceworkers_guild/shubin interstellar/shubininterstellar.xml` | `libs/foundry/records/missiondata/declarations/moduledeclarations/eliminateall.xml` | `BP_MISSIONREWARD_RDC_Exclusive` x2 |
| `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `libs/foundry/records/missiondata/pu_items/carryable_2h/waste/scrapmetal.xml` | `BP_REWARDS_LingFamilyHauling` x6 |

## Contrato A Pool

| Contrato | Pools observadas |
|---|---|
| `libs/foundry/records/contracts/contractgenerator/academyofsciences_guild/highpoint wilderness specialists/highpointwildernessspecialists_killanimals.xml` | `BP_MISSIONREWARD_RDC_Generic` x1 |
| `libs/foundry/records/contracts/contractgenerator/interstellartransport_guild/ftl/ftl_courier.xml` | `BP_REWARDS_FTL` x2 |
| `libs/foundry/records/contracts/contractgenerator/interstellartransport_guild/lingfamilyhauling/lingfamilyhauling_hauling.xml` | `BP_REWARDS_LingFamilyHauling` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/bountyhunterguild/bountyhuntersguild_fps.xml` | `BP_MISSIONREWARD_BHG_ASDFacilityDelving_ResearchWing_EliminateSpecific` x1<br>`BP_MISSIONREWARD_BHG_ASDFacilityDelving_EngineeringWing_EliminateSpecific` x1<br>`BP_MISSIONREWARD_BountyHuntersGuild_PAF_EliminateSpecific` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_defendship.xml` | `BP_MISSIONREWARD_InterSec_DefendShip` x8<br>`BP_MISSIONREWARD_RDC_Generic` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_destroyitems.xml` | `BP_MISSIONREWARD_CitizensForProsperityDestroyItems_AB` x7<br>`BP_MISSIONREWARD_CitizensForProsperityDestroyItems_CD` x2 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_mercenary_fps.xml` | `BP_MISSIONREWARD_CFP_Outpost_RegionAB` x5<br>`BP_MISSIONREWARD_CFP_ChainElim_3` x5<br>`BP_MISSIONREWARD_CFP_ChainElim_1and2` x5<br>`BP_MISSIONREWARD_CFP_Outpost_RegionC` x4<br>`BP_MISSIONREWARD_CFP_EliminateAll_HeadHunters` x1<br>`BP_MISSIONREWARD_CFP_EliminateAllFromCFP_HeadHunters` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_defendship.xml` | `BP_MISSIONREWARD_RDC_Generic` x6<br>`BP_MISSIONREWARD_InterSec_DefendShip` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_escortships.xml` | `BP_REWARDS_EckhartSecurityEscortShipsEasy` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_killnpc.xml` | `BP_REWARDS_EckhartSecurityKillNPCBoss` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/eckhartsecurity/eckhartsecurity_recovercargo.xml` | `BP_MISSIONREWARD_VaughnGenerator_EliminateSpecific` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_destroyitems.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_generator.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Generator` x18<br>`BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/foxwellenforcement_shipwaveattack.xml` | `BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x4<br>`BP_MISSIONREWARD_FoxwellEnforcement_Generator` x3 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_ambush.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Ambush` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_defenddestructibleentities.xml` | `BP_MISSIONREWARD_Foxwell_DefendEntitiesAndEscort` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_escortships.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_EscortShips` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/foxwellenforcement/shipbattles/foxwellenforcement_patrol.xml` | `BP_MISSIONREWARD_FoxwellEnforcement_Patrol` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/hockrowagency/hockrowagency_facilitydelve.xml` | `BP_MISSIONREWARD_ASD2B` x1<br>`BP_MISSIONREWARD_ASD2C` x1 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_defendship.xml` | `BP_MISSIONREWARD_InterSec_DefendShip__02` x6<br>`BP_MISSIONREWARD_InterSec_DefendShip` x5 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_killship.xml` | `BP_MISSIONREWARD_RDC_Generic` x6 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_patrol.xml` | `BP_MISSIONREWARD_InterSec_Patrol` x2 |
| `libs/foundry/records/contracts/contractgenerator/mercenary_guild/intersecdefensesolutions/intersec_resourcegathering.xml` | `BP_MISSIONREWARD_InterSec_ResourceGathering` x2 |
| `libs/foundry/records/contracts/contractgenerator/thecouncil_guild/headhunters/headhunters_mercenary_fps.xml` | `BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateALL_RegionAB` x17<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateSpecific_RegionAB` x9<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateALL_RegionCD` x5<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateSpecific_RegionCD` x3<br>`BP_MISSIONREWARD_HeadHunters_MercenaryFPS_EliminateBoss` x1 |
| `libs/foundry/records/contracts/contractgenerator/thecouncil_guild/vaughn/vaughn_generator.xml` | `BP_MISSIONREWARD_VaughnGenerator_EliminateSpecific` x2 |
| `libs/foundry/records/contracts/contractgenerator/unitedresourceworkers_guild/shubin interstellar/shubin_resourcegathering_fpsmining.xml` | `BP_MISSIONREWARD_Shubin_ResourceGathering_FPSMining_Pyro` x5<br>`BP_MISSIONREWARD_Shubin_ResourceGathering_FPSMining_Stanton` x4 |
| `libs/foundry/records/contracts/contractgenerator/unitedresourceworkers_guild/shubin interstellar/shubin_resourcegathering_shipmining.xml` | `BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_PyroNyx` x12<br>`BP_MISSIONREWARD_Shubin_ResourceGathering_ShipMining_Stanton` x6 |
| `libs/foundry/records/contracts/contractgenerator/unitedresourceworkers_guild/shubin interstellar/shubininterstellar.xml` | `BP_MISSIONREWARD_RDC_Exclusive` x2 |
| `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` x6 |

## Inferencias Unicas Estrictas

Sin inferencias estrictas.

## Inferencias Unicas Solo Por Contrato

| Titulo ingles | `title` | `desc` | Contrato | Pool inferida |
|---|---|---|---|---|
| `Need a Hauler` | `cfp_HaulCargo_RegionLink_title_001` | `cfp_HaulCargo_RegionLink_desc_001` | `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` |
| `First Haul in System` | `cfp_hauling_intro_title_001` | `cfp_hauling_intro_desc_001` | `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Disable Headhunter Comm Towers` | `CFP_SabotageRelays_HH_001_Title` | `CFP_SabotageRelays_HH_001_Desc` | `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Shutdown Xenothreat Comm Towers` | `CFP_SabotageRelays_XT_001_Title` | `CFP_SabotageRelays_XT_001_Desc` | `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Clear ~mission(Location) of Salvage` | `CFP_Salvage_FPS_title_001` | `CFP_Salvage_FPS_desc_001` | `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Ship in Trouble` | `CleanAir_DefendShip_Easy_title` | `CleanAir_DefendShip_Easy_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Ship Under Attack` | `CleanAir_DefendShip_Hard_title` | `CleanAir_DefendShip_Hard_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Ship in Distress` | `CleanAir_DefendShip_Medium_title` | `CleanAir_DefendShip_Medium_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Collect Manufacturing Resource - Large Scale` | `CleanAir_ResourceGathering_Bulk_Filters_title` | `CleanAir_ResourceGathering_Bulk_Filters_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Large Supply of Research Resource` | `CleanAir_ResourceGathering_Bulk_MoldResearch_title` | `CleanAir_ResourceGathering_Bulk_MoldResearch_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Collect Manufacturing Resource - Small Scale` | `CleanAir_ResourceGathering_Small_Filters_title` | `CleanAir_ResourceGathering_Small_Filters_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Small Supply of Research Resource` | `CleanAir_ResourceGathering_Small_MoldResearch_title` | `CleanAir_ResourceGathering_Small_MoldResearch_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Collect Manufacturing Resource - Medium Scale` | `CleanAir_ResourceGathering_Supply_Filters_title` | `CleanAir_ResourceGathering_Supply_Filters_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Alliance Aid: Med. Supply of Research Resource` | `CleanAir_ResourceGathering_Supply_MoldResearch_title` | `CleanAir_ResourceGathering_Supply_MoldResearch_desc` | `libs/foundry/records/contracts/contractgenerator/yearspecificcontent/cleanair.xml` | `BP_REWARDS_LingFamilyHauling` |
| `Ripe for Retribution ` | `headhunters_eliminatespecific_title_001` | `headhunters_eliminatespecific_desc_001` | `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_generator.xml` | `BP_REWARDS_LingFamilyHauling` |

## Inferencias Endurecidas Por Familia

Sin inferencias endurecidas por familia.

## Ambiguas

### Establishing Security

- `title`: `cfp_eliminateall_intro_title_001`
- `desc`: `cfp_eliminateall_intro_desc_001`
- Missiondata detectado: `libs/foundry/records/missiondata/declarations/locationentitytypes/deliverytargets/deliverytarget_locker_any.xml`
- Contrato: `libs/foundry/records/contracts/contractgenerator/mercenary_guild/citizensforprosperity/citizensforprosperity_mercenary_fps.xml`
- Pools observadas: `BP_MISSIONREWARD_CFP_Outpost_RegionAB` x5, `BP_MISSIONREWARD_CFP_ChainElim_3` x5, `BP_MISSIONREWARD_CFP_ChainElim_1and2` x5, `BP_MISSIONREWARD_CFP_Outpost_RegionC` x4, `BP_MISSIONREWARD_CFP_EliminateAll_HeadHunters` x1, `BP_MISSIONREWARD_CFP_EliminateAllFromCFP_HeadHunters` x1
- Pools con mismo missiondata: `BP_MISSIONREWARD_CFP_Outpost_RegionAB` x3, `BP_MISSIONREWARD_CFP_Outpost_RegionC` x3, `BP_MISSIONREWARD_CFP_EliminateAll_HeadHunters` x1, `BP_MISSIONREWARD_CFP_EliminateAllFromCFP_HeadHunters` x1
- Afinidad por `title_key`: `BP_MISSIONREWARD_CFP_EliminateAllFromCFP_HeadHunters` score=2 via `cfp_eliminateall_fromCFP_hh_M_title_001`, `BP_MISSIONREWARD_CFP_EliminateAll_HeadHunters` score=2 via `cfp_eliminateall_hh_E_title_001`, `BP_MISSIONREWARD_CFP_Outpost_RegionC` score=2 via `cfp_eliminateall_XT_E_title_001`, `BP_MISSIONREWARD_CFP_Outpost_RegionAB` score=1 via `cfp_defend_cave_Generic_title_001`

