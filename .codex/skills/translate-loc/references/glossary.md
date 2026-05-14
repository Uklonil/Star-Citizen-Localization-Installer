# Star Citizen localization glossary (starter)

This is a starter glossary. Replace or expand entries to match your project's preferred terminology.

## Approved translations
Inventory = Inventario
Contracts = Contratos
Loadout = Equipamiento
Mining = Minería
Refinery = Refinería
Commodity = Mercancía
Ship Weapons = Armas de la nave
Personal Weapons = Armas personales
Undersuit = Mono interior
Helmet = Casco
MedPen = MedPen
Tractor Beam = Rayo tractor
Freight Elevator = Ascensor de carga
Hangar = Hangar
Starmap = Mapa estelar
Quantum Travel = Viaje cuántico
Jump Point = Punto de salto
Reputation = Reputación
Bounty = Recompensa
Bounty Hunter = Cazarrecompensas
Server Blade = unidad de servidor

## Usually do not translate
Stanton
Pyro
Hurston
ArcCorp
microTech
Crusader
UEC
aUEC
mobiGlas
Quantum Drive
RSI
Drake
Anvil
Aegis
Origin

## Style notes
- Prefer concise menu text over literal translation.
- Keep item brand names in original form unless the project has a canonical translation.
- For mission text, favor readability over rigid literalism.

## Never translate / internal identifiers

Do not translate strings that are clearly internal identifiers, including:

- `BP_MISSIONREWARD_*`
- `OVERLAY_*`
- `LOC_*`
- `item_*`
- `vehicle_*`
- `ContractGenerator.*`
- `contractgenerator/*.xml`
- `missiondata/*.xml`
- file paths
- UUIDs
- entity class names
- blueprint pool IDs

## Approved translations

Salvage = Chatarreo
Salvaging = Chatarreo
Crafting = Fabricación
Blueprint = Plano
Blueprints = Planos
Schematic = Esquema
Components = Componentes
Cargo = Carga
Freight = Carga
Hauling = Transporte de carga
Delivery = Entrega
Outpost = Puesto avanzado
Settlement = Asentamiento
Bunker = Búnker
Contractor = Contratista
Security = Seguridad
Patrol = Patrulla
Recover = Recuperar
Recovery = Recuperación
Eliminate = Eliminar
Hostiles = Hostiles
Vice = Vicio
Vices = Vicios

## Style decisions

- Use “plano” for blueprint when referring to crafting or unlockable recipes.
- Use “esquema” only if the source clearly refers to a schematic-like object.
- Use “chatarreo” for the salvage gameplay loop.
- Use “recuperar” for mission objectives involving item/cargo retrieval.
- Keep faction/company names untranslated.