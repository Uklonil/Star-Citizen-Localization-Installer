from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from localization_tools import Entry, read_global_ini, resolve_path, write_global_ini


REPO_ROOT = Path(__file__).resolve().parent.parent

ENGLISH_VALUE_TRANSLATIONS = {
    "Abort Fueling": "Abortar repostaje",
    "Abort": "Abortar",
    "Fueling will stop immediately and the fuel nozzle will be disconnected.": "El repostaje se detendra de inmediato y la boquilla de combustible se desconectara.",
    "Confirm Abort Fueling": "Confirmar aborto de repostaje",
    "Caution": "Precaucion",
    "Docking": "Acoplamiento",
    "Pod will be detached from the vehicle. This cannot be undone.": "El pod se separara del vehiculo. Esta accion no se puede deshacer.",
    "Confirm Eject Pod": "Confirmar expulsion del pod",
    "Fuel Nozzle": "Boquilla de combustible",
    "Eject Pod": "Expulsar pod",
    "No pod connected": "No hay ningun pod conectado",
    "Fueling": "Repostaje",
    "Fuel Distribution": "Distribucion de combustible",
    "Fuel ordered": "Combustible solicitado",
    "Port": "Babor",
    "SCU/s": "SCU/s",
    "Starboard": "Estribor",
    "Fuel pod manual controls": "Controles manuales del pod de combustible",
    "Flow Speed": "Velocidad de flujo",
    "Avg. Mod": "Mod. media",
    "Operation Status": "Estado de la operacion",
    "Owner": "Propietario",
    "Set Auto Prices": "Establecer precios automaticos",
    "Fuel Pricing": "Precios del combustible",
    "Total capacity": "Capacidad total",
    "Purge Fuel": "Purgar combustible",
    "Purging will vent all fuel. \nThis fuel will be permanently lost.": "La purga expulsara todo el combustible. \nEste combustible se perdera permanentemente.",
    "Confirm Fuel Purge": "Confirmar purga de combustible",
    "// Refueling and Refinery Systems": "// Sistemas de repostaje y refineria",
    "Undocking": "Desacoplamiento",
    "Bricked": "Inutilizado",
    "Bricks in:": "Se inutiliza en:",
    "Claim Insured Loadout": "Reclamar equipamiento asegurado",
    "Claim Default Loadout": "Reclamar equipamiento predeterminado",
    "Current Location:": "Ubicacion actual:",
    "This hangar's at full capacity. Free up space by scrapping vehicles you are not actively using. You'll be able to claim these vehicles again later.": "Este hangar esta a plena capacidad. Libera espacio desguazando vehiculos que no estes usando activamente. Podras volver a reclamarlos mas adelante.",
    "Scrap": "Desguazar",
    "Scrap Ships": "Desguazar naves",
    "Warning: Once scrapped, you will need to file a claim to get your vehicle again. Vehicles you don't own will be permanently removed from your fleet when scrapped.": "Advertencia: una vez desguazado, tendras que presentar una reclamacion para recuperar tu vehiculo. Los vehiculos que no poseas se eliminaran permanentemente de tu flota al desguazarlos.",
    "Vehicles can't be scrapped if they're currently in the hangar.": "Los vehiculos no pueden desguazarse si estan actualmente en el hangar.",
    "Show Local Ships": "Mostrar naves locales",
    "No loadout available to claim.": "No hay ningun equipamiento disponible para reclamar.",
    "Insure Loadout": "Asegurar equipamiento",
    "Loadout Mode": "Modo de equipamiento",
    "Available": "Disponible",
    "Cost of Claim": "Coste de la reclamacion",
    "Available in": "Disponible en",
    "Do you want to insure this loadout?\nThis will override any existing loadouts for this ship.": "¿Quieres asegurar este equipamiento?\nEsto sustituira cualquier equipamiento existente para esta nave.",
    "Cooldown": "Recarga",
    "Name": "Nombre",
    "Preview Items": "Previsualizar objetos",
    "QTY": "CANT.",
    "Insure": "Asegurar",
    "SCU": "SCU",
    "You can't save the loadout of a destroyed vehicle.": "No puedes guardar el equipamiento de un vehiculo destruido.",
    "Total Items": "Objetos totales",
    "Type": "Tipo",
    "Too many bricked ships in storage.": "Demasiadas naves inutilizadas en almacenamiento.",
    "Common": "Comun",
    "Epic": "Epico",
    "Legendary": "Legendario",
    "Rare": "Raro",
    "Uncommon": "Poco comun",
    "Surface Rock (Vehicle)": "Roca superficial (vehiculo)",
    "Hand Mineable": "Mineria manual",
    "Asteroid": "Asteroide",
    "Surface Rock": "Roca superficial",
    "Aluminium": "Aluminio",
    "Copper": "Cobre",
    "Gold": "Oro",
    "Ice": "Hielo",
    "Iron": "Hierro",
    "Quartz": "Cuarzo",
    "Silicon": "Silicio",
    "Tin": "Estano",
    "Titanium": "Titanio",
    "Tungsten": "Tungsteno",
    "MobiGlas": "mobiGlas",
}

KEY_TRANSLATIONS = {
    "Hints_Refueling_DeployBoom_Title": "Modo de repostaje",
    "Hints_Refueling_DockingProcess": "Asegurate de alinear tu boquilla de combustible con la parte frontal de la nave del cliente.",
    "Hints_Refueling_DockingProcess_Title": "Alinear boquilla",
    "Hints_Refueling_FuelReminder": "Asegurate de que los pods externos de combustible esten llenos antes de dirigirte a la ubicacion de la nave del cliente.",
    "Hints_Refueling_FuelReminder_Title": "Pods de combustible",
    "Hints_Refueling_Refuel": "Abre los pods de combustible para iniciar la transferencia.",
    "Hints_Refueling_Refuel_Title": "Transferencia de combustible",
    "Hints_Refueling_RequestDocking": "Para enviar una solicitud de acoplamiento a la nave cliente que tengas fijada como objetivo, usa ~action(spaceship_movement|v_toggle_docking_request).",
    "Hints_Refueling_RequestDocking_Title": "Solicitud de acoplamiento",
    "Hints_Refueling_TargetShip": "Para fijar como objetivo la nave cliente para el acoplamiento, usa ~action(spaceship_targeting|v_target_lock_selected).",
    "Hints_Refueling_TargetShip_Title": "Acoplarse a la nave cliente",
    "Hints_Refueling_Undocking": "El desacoplamiento se producira automaticamente cuando termine el repostaje.",
    "Hints_Refueling_Undocking_Title": "Desacoplamiento",
    "Intersec_TSG_Assist_Solo_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Vanduul\nEspecificaciones de equipo: Nave lista para combate\nInforme: \nUna nave de seguridad de la People's Alliance de clase Idris llamada Tranquility esta enfrentandose actualmente a una <EM>nave capital Vanduul</EM4> cerca de una antigua <EM4>estacion de extraccion QV</EM4> e Intersec busca pilotos de combate que puedan prestar apoyo.\n\nAcude al area de operaciones y <EM4>enfrentate a los cazas Vanduul para que la Tranquility pueda centrarse en la nave capital</EM4>. \n\nBuena suerte,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_Assist_Solo_Title_001": "Ayuda a la nave Tranquility de la People's Alliance",
    "Intersec_TSG_Assist_Solo_obj_long_01": "Protege a la Tranquility derrotando a todos los ~mission(WaveName).",
    "Intersec_TSG_Assist_Solo_obj_marker": "Tranquility",
    "Intersec_TSG_Assist_Solo_obj_short_01": "~mission(WaveName)",
    "Intersec_TSG_Assist_Solo_obj_wavetracker": "Oleadas de Vanduul derrotadas: %ls",
    "Intersec_TSG_Assist_Solo_wavename": "Cazas Vanduul",
    "Intersec_TSG_BombRun_Solo_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Shattered Blade\nEspecificaciones de equipo: Naves de combate con armamento pesado\nInforme: \nLos recursos locales indican que elementos de Shattered Blade estan intentando reconstruir una de sus estaciones e Intersec busca un piloto que se asegure de que eso no ocurra.\n\nHan conseguido reactivar defensas basicas de torreta, pero ahora mismo solo tienen <EM4>dos reles de energia activos</EM4>. Esos seran tus objetivos, ya que <EM4>no pueden destruirse con armas de energia; necesitaras armamento balistico o municion pesada para ser eficaz</EM4>. \n\nReactivar esta estacion permitiria a Shattered Blade intentar recuperar una posicion en este sistema, y no podemos permitirlo.\n\nBuena suerte,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_BombRun_Solo_Title_001": "Bombardeo estrategico",
    "Intersec_TSG_CollectData_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Vanduul\nEspecificaciones de equipo: N/A\nInforme: \nEl capitan Martel, de la nave Tranquility de la People's Alliance, se ha puesto en contacto para informar de que te ha asignado la recuperacion de unidades de datos de la nave capital Vanduul destruida.\n\nTen cuidado al extraer dichas unidades y entregalas a la People's Alliance para su analisis una vez hayas terminado.\n\nAtentamente,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_CollectData_Title_001": "Recupera datos Vanduul",
    "Intersec_TSG_DefendShip_Solo_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Shattered Blade\nEspecificaciones de equipo: Nave lista para combate\nInforme: \nHemos recibido informacion de que un piloto de seguridad de la People's Alliance dio con un escondite de Shattered Blade y necesita ayuda inmediata. \n\nDirigete a la estacion abandonada y <EM4>proporciona cobertura hasta que pueda saltar a quantum y ponerse a salvo</EM4>.\n\nAtentamente,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_DefendShip_Solo_Title_001": "Defiende al piloto de la People's Alliance",
    "Intersec_TSG_EscortShip_Solo_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Shattered Blade\nEspecificaciones de equipo: Nave lista para combate\nInforme: \nIntersec ha interceptado comunicaciones de canales de Shattered Blade que indican que han capturado a un piloto de seguridad de la People's Alliance en una antigua estacion de extraccion bajo su control.\n\nNecesitamos un piloto de combate con experiencia que proporcione apoyo para que el piloto pueda escapar. El espacio aereo fuera del hangar esta plagado de hostiles, asi que <EM4>tendras que despejar la zona para que el piloto pueda despegar y hacer QT con seguridad</EM4>.\n\nAtentamente,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_EscortShip_Solo_Title_001": "Mision de extraccion",
    "Intersec_TSG_Group_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Shattered Blade\nEspecificaciones de equipo: Grupo de asalto\nInforme: \nHemos recibido informacion de que una nave de seguridad de la People's Alliance llamada Tranquility dio con miembros de Shattered Blade escondidos en una antigua estacion de extraccion QV. Los detalles son imprecisos, pero te pondremos en contacto con recursos locales al llegar a la zona. \n\nIntersec busca un equipo que intervenga y proteja a la Tranquility y a su personal. Segun las conversaciones con el capitan de la Tranquility, <EM4>necesitaras armamento balistico y municion pesada para derribar las defensas de la estacion</EM4> y, en ultima instancia, <EM4>desplegar personal a pie para rescatar a su piloto</EM4>.\n\n<EM4>Reclutar naves adicionales</EM4> para apoyarte en esta mision es absolutamente crucial. <EM4>Necesitaras una variedad de tipos de nave</EM4> para equilibrar multiples zonas de combate en el espacio y sobre el terreno.\n\nAtentamente,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_Group_Title_001": "Se necesita grupo de asalto tactico",
    "Intersec_TSG_P1M1_obj_long_01": "Defiende a la nave Tranquility de la People's Alliance contra los cazas de Shattered Blade.",
    "Intersec_TSG_P1M1_obj_marker": "Tranquility",
    "Intersec_TSG_P1M1_obj_short_01": "Defender a Tranquility",
    "Intersec_TSG_P2M1_obj_long_01": "Fija como objetivo y destruye los reles de energia de los brazos de la estacion para poder acceder al interior.",
    "Intersec_TSG_P2M1_obj_marker": "~mission(ItemsToDestroy)",
    "Intersec_TSG_P2M1_obj_short_01": "Destruir reles de energia",
    "Intersec_TSG_P2M1_objective": "Salud de ~mission(ItemsToDestroy)",
    "Intersec_TSG_P2M2_obj_long_01": "Entra en los brazos de la estacion para destruir las unidades de refrigeracion del recorrido y desbloquear el nucleo.",
    "Intersec_TSG_P2M2_obj_marker": "~mission(ItemsToDestroy1)",
    "Intersec_TSG_P2M2_obj_short_01": "Destruir unidades de refrigeracion",
    "Intersec_TSG_P2M2_objective": "Salud de ~mission(ItemsToDestroy1)",
    "Intersec_TSG_P3M1_obj_long_01": "Defiende a Tranquility del contraataque de Shattered Blade.",
    "Intersec_TSG_P3M1_obj_short_01": "Interceptar bombarderos",
    "Intersec_TSG_P4M1_obj_long_01": "Destruye el nucleo expuesto de la estacion para provocar un reinicio de la estructura.",
    "Intersec_TSG_P4M1_obj_marker": "~mission(ItemsToDestroy2)",
    "Intersec_TSG_P4M1_obj_marker2": "~mission(ItemsToDestroy3)",
    "Intersec_TSG_P4M1_obj_short_01": "Destruir nucleo de la estacion",
    "Intersec_TSG_P4M1_objective": "Salud de ~mission(ItemsToDestroy2) ",
    "Intersec_TSG_P4M1_objective2": "Salud de ~mission(ItemsToDestroy3) ",
    "Intersec_TSG_P5M1_access": "Puerta de acceso",
    "Intersec_TSG_P5M1_obj_long_01": "Infiltrate en la estacion de Shattered Blade para liberar al piloto capturado.",
    "Intersec_TSG_P5M1_obj_marker": "Gabe Windell",
    "Intersec_TSG_P5M1_obj_short_01": "Infiltrarse en la estacion",
    "Intersec_TSG_P5M2_obj_long_01": "Rescata al rehen localizando la terminal de seguridad que controla las puertas del hangar.",
    "Intersec_TSG_P5M2_obj_short_01": "Rescatar al piloto capturado",
    "Intersec_TSG_P5M2_secterminal": "Terminal de seguridad ",
    "Intersec_TSG_P6M1_obj_long_01": "Escolta a Gabe hasta una distancia segura del combate para que pueda escapar.",
    "Intersec_TSG_P6M1_obj_short_01": "Escoltar a Gabe ",
    "Intersec_TSG_P7M1_obj_long_01": "Encuentra las demas unidades de datos entre los restos del Mauler y haz EVA para descargar la informacion.",
    "Intersec_TSG_P7M1_obj_marker": "Unidad de datos",
    "Intersec_TSG_P7M1_obj_short_01": "Recuperar datos",
    "Intersec_TSG_StationWing_obj_marker": "Puerto de entrada",
    "Intersec_TSG_WeakenDef_Solo_Desc_001": "ESPECIFICACIONES DE LA MISION\n\nArea de operaciones: Sistema Nyx \nFuerzas hostiles: Shattered Blade\nEspecificaciones de equipo: Naves de combate con armamento pesado\nInforme: \nEl analisis regional indica la posible presencia de un escondite de Shattered Blade en una antigua estacion de extraccion QV, e Intersec busca un piloto que lance un ataque contra la infraestructura energetica de la estacion.\n\nSe tratara de un asalto en varias fases que te exigira fijar como objetivo y destruir componentes de la estacion tanto en el exterior como en el interior. En operaciones anteriores hemos aprendido que <EM4>ciertos componentes no pueden destruirse con armas de energia, por lo que necesitaras armamento balistico o municion pesada</EM4>. Historicamente, partes de la estacion han estado inundadas de <EM4>energia de distorsion intensa, por lo que deberas actuar con eficiencia mientras estes dentro</EM4>.\n\nTodos estos ataques tienen como objetivo permitirte <EM4>destruir el nucleo de energia ahora expuesto en el centro</EM4>.\n\nLa perdida de esta estacion afectaria gravemente a la capacidad operativa de la banda en el sistema, por lo que se ha considerado una prioridad alta.\n\nBuena suerte,   \n\nDeacon Tobin \nGerente de operaciones \nInterSec Defense Solutions  \n\nEsta comunicacion contiene informacion confidencial destinada unicamente al destinatario. Si la has recibido por error, ignora su contenido y notifica al remitente. Todas las operaciones se realizan bajo el riesgo personal del contratista y deben cumplir la legislacion de la UEE y del sistema cuando corresponda.",
    "Intersec_TSG_WeakenDef_Solo_Title_001": "Operacion de bombardeo tactico",
    "Intersec_TSG_cooler": "Unidades de refrigeracion",
    "Intersec_TSG_coreweakspot": "Punto debil del nucleo",
    "Intersec_TSG_faction_PA": "People's Alliance ",
    "Intersec_TSG_faction_SB": "Shattered Blade",
    "Intersec_TSG_fail_defendship": "La Tranquility fue destruida.",
    "Intersec_TSG_fail_escortship": "La nave de Gabe Windell fue destruida.",
    "Intersec_TSG_fail_playerdeath": "Todos los jugadores murieron",
    "Intersec_TSG_fail_playerleft": "Todos los jugadores abandonaron la zona de mision",
    "Intersec_TSG_location": "Estacion de extraccion QV",
    "Intersec_TSG_mission_success": "Mision completada con exito",
    "Intersec_TSG_relay": "Rele de energia",
    "Intersec_TSG_stationcore": "Nucleo",
    "UWC_Refueling_easy_desc_001": "Hola.\n\nSi tu nave esta preparada para repostar, puede que esto te interese.\n\nAcaba de activarse una baliza en <EM4>~mission(Location|Address)</EM4> de un cliente cuyo <EM4>~mission(Ship)</EM4> esta completamente seco, asi que asegurate de llevar llenos tus pods de combustible.\n\nLa nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum</EM4>, y como contratista del United Wayfarers Club tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nParece uno de esos encargos sencillos y sin drama, pero nunca esta de mas llevar los escaneres activos.\nDime si te interesa y pongamos a esta buena gente de nuevo en marcha.\n\nQuedo a la espera.\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_easy_desc_002,P": "Hola.\n\nTengo a un miembro del Club en <EM4>~mission(Location|Address)</EM4> que necesita un repostaje completo.\n\nLa nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum</EM4>, y como contratista del United Wayfarers Club tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nSi te interesa, deberia ser un encargo sencillo. La baliza lo situa lejos de las ultimas zonas conflictivas, pero nunca es mala idea vigilar los escaneres, ¿no?\n\nTienen sitios a los que llegar, asi que vamos a ponerlos de nuevo en camino.\n\nCuidate.\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_easy_title_001": "SOLICITUD DE REPOSTAJE: ~mission(Ship)",
    "UWC_Refueling_high_desc_001,P": "Hola.\n\nOtro dia, otra baliza. Hay una <EM4>~mission(Ship)</EM4> con el deposito vacio en <EM4>~mission(Location|Address)</EM4>. La nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum</EM4>, y como contratista del United Wayfarers Club tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nNo te voy a engañar: es un sitio horrible para quedarse tirado y peor aun para que te pillen por sorpresa. Hemos perdido a buena gente ahi fuera; incluso los que tuvieron suerte volvieron a casa hechos pedazos.\n\nSi decides aceptar el trabajo, hazme el favor de ir con mil ojos. Si tienes un colega con algo de tiempo libre, quiza te convenga pedir un poco de apoyo.\n\nPuede que este siendo paranoica, pero eso no significa que no vayan a por ti, como decia Mama Deloit.\nEn realidad nunca dijo eso, pero estoy bastante segura de que lo diria si se dedicara a esto.\n\nHaz el trabajo y vuelve a casa de una pieza, ¿vale?\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_high_title_001": " SOLICITUD CRITICA DE REPOSTAJE: ~mission(Ship)",
    "UWC_Refueling_intro_desc_001": "Hola.\n\nSoy DD, del United Wayfarers Club.\n\nLa UWC ofrece servicios de reparacion, rearme y repostaje por toda la UEE. Justo ahora estamos buscando nuevos afiliados con naves equipadas para repostar. Si tienes pods de combustible y te gusta que la gente se alegre de verte llegar, puede que la UWC sea tu club.\n\nY si crees que podria serlo, tengo una baliza activa que quiza te interese.\n\nSi al final te animas, un consejo: <EM4>asegurate de que tus pods de combustible esten llenos antes de salir</EM4>.\n\nA un miembro del Club se le ha agotado el combustible en <EM4>~mission(Location|Address)</EM4>. No tengo claro como ha acabado ahi fuera sin ni una gota de Go Juice, pero a la UWC no le gusta dejar a la gente tirada.\n\nLa nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum </EM4>. Como contratista del United Wayfarers Club, tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nEs un trayecto directo. Perfecto para que le cojas el pulso a este tipo de trabajos. Sal ahi fuera, llena los depositos de su <EM4>~mission(Ship)</EM4> y ponlos otra vez en marcha. Si haces suficientes encargos como este, el proceso se te quedara grabado en la memoria muscular. Hasta entonces, tienes una <EM4>entrada del diario</EM4> en tu mobiGlas llamada \"\"Refueling Protocols\"\" que cubre lo basico.\n\nNo ha habido informes de actividad forajida en ese sector, pero mantente alerta. Siempre recomiendo hacer una rotacion rapida. Cuanto antes termines, antes podre conseguirte otro contrato. La UWC siempre esta buscando nuevos afiliados.\n\nTengo ganas de trabajar contigo.\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_intro_title_001": "LA UWC BUSCA REPOSTADORES",
    "UWC_Refueling_moderate_desc_001,P": "Hola, tu.\n\nTengo una baliza en <EM4>~mission(Location|Address)</EM4>. Dicen que tienen los depositos secos y que necesitan un repostaje completo. Si te interesa, me da que se van a alegrar mucho de verte.\n\nLa nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum </EM4>, y como contratista del United Wayfarers Club tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nEstan tirados en una zona con mala fama, aunque ultimamente parece que la cosa se ha calmado un poco. Aun asi, yo seguiria atenta, por si acaso sigue habiendo problemas al acecho.\n\nEn cualquier caso, cuanto antes puedan volver todos a volar, y eso te incluye a ti, mejor.\n\nBuen camino.\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_moderate_title_001": "SOLICITUD URGENTE DE REPOSTAJE: ~mission(Ship)",
    "UWC_Refueling_multiple_hard_desc_001,P": "Hola.\n\nEn <EM4>~mission(Location|Address)</EM4> nos acaba de entrar un trabajo de repostaje para toda una pequeña flota. Desde luego, cuando llueve, diluvia.\n\nLa nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum </EM4>, y como contratista del United Wayfarers Club tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nPor desgracia, la zona donde estan detenidos no es precisamente agradable, asi que yo iria con ojo por si aparece alguna tonteria mientras haces el recorrido.\n\nLo mejor sera ponerlos a todos de nuevo en marcha cuanto antes.\n\nBuen camino.\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_multiple_hard_title_001": "REPOSTAJE CRITICO DE FLOTA",
    "UWC_Refueling_multiple_med_desc_001,P": "Hola de nuevo.\n\nTengo una baliza en <EM4>~mission(Location|Address)</EM4> y esta vez es gorda. Toda una pequeña flota se ha quedado sin combustible al mismo tiempo. Una coordinacion impresionante y una falta total de planificacion, todo a la vez.\n\nLa nave cliente te pagara a razon de <EM4>~mission(FuelRate) aUEC por SCU de hidrogeno</EM4> y <EM4>~mission(QTFuelRate) aUEC por SCU de quantum </EM4>, y como contratista del United Wayfarers Club tambien recibiras la tasa de servicio de la UWC indicada arriba al completar el trabajo.\n\nCon suerte, como la zona en la que estan es bastante segura, no deberia haber demasiados problemas al acecho, pero hoy en dia nunca se sabe. No estaria de mas devolverlos al aire tan rapido como puedas.\n\nBuen camino.\n\nDina Deloit\nCentro de despacho\nUnited Wayfarers Club\n\"We’ve got your back\"",
    "UWC_Refueling_multiple_med_title_001": "REPOSTAJE URGENTE DE FLOTA",
    "PU_DELOIT_UWC_F_PMH_GenericMissionAbandon_GP_001,P": "Vaya. Siento mucho que no vayas a poder terminar este encargo. Espero que estes bien. Bueno, quiza la proxima vez salga mejor. Hablamos pronto.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionAbandon_GP_002,P": "Vaya, ¿lo dejas? La verdad, me sorprende un poco, pero lo entiendo, la vida pasa. Solo procura que no se convierta en costumbre, ¿vale? Hasta luego.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionAbandon_GP_003,P": "Espera, ¿estas cancelando el contrato? ¿De verdad? Bueno... si crees que es lo mejor...",
    "PU_DELOIT_UWC_F_PMH_GenericMissionAccept_GP_001,P": "Hola, soy DD. Gracias por aceptar este trabajo. Creo que te viene como anillo al dedo. Ve paso a paso y cuidate ahi fuera, ¿vale?",
    "PU_DELOIT_UWC_F_PMH_GenericMissionAccept_GP_002,P": "Hola de nuevo. Soy DD. Me preguntaba cuando volverias por otro contrato. En fin, el tiempo apremia, asi que mejor nos ponemos en marcha.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionAccept_GP_003,P": "¡Hola! Soy DD otra vez. Siempre me alegra ver tu nombre aparecer en un contrato. Ya tienes los detalles, asi que portate bien ahi fuera y luego hablamos.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionComplete_GP_001,P": "Soy DD. Solo llamaba para decirte que agradezco que seas de los que cumplen. Justo el tipo de piloto que necesita Wayfarer. Vuela con cuidado y no desaparezcas, ¿me oyes?",
    "PU_DELOIT_UWC_F_PMH_GenericMissionComplete_GP_002,P": "Mira eso. Contrato completado. Siempre alegra verlo. En fin, descansa un poco y hablamos pronto.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionComplete_GP_003,P": "Wayfarer necesitaria unos cuantos pilotos mas como tu, desde luego. Disfruta del pago, que seguro que pronto tendremos otro contrato para ti.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionFail_GP_001,P": "Soy DD. Siempre cuesta cuando el trabajo no sale bien. Lo unico que podemos hacer es aprender y seguir adelante. Toma un respiro y te veo en el siguiente.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionFail_GP_002,P": "Te llama DD desde la UWC. Parece que ese trabajo no va a salir. Le pasa hasta a los mejores. No dejes que te venga abajo y vuelve pronto ahi fuera.",
    "PU_DELOIT_UWC_F_PMH_GenericMissionFail_GP_003,P": "Uf. Es un golpe duro. Siento mucho que esta vez no haya salido a tu favor. Animo, ¿vale?",
    "PU_DELOIT_UWC_F_PMH_MissionAcceptIntro_GP_001,P": "Dejame ser la primera en darte la bienvenida a bordo. Siempre hay mucha gente ahi fuera contando con la ayuda de Wayfarer, asi que viene bien cuando se suma un piloto nuevo a la lucha. Soy Dina Deloit, pero puedes llamarme DD, como todo el mundo. Sere tu principal despachadora. ¿Que te parece si te ponemos en marcha? Los clientes no van a atenderse solos.",
    "PU_DELOIT_UWC_F_PMH_RefuelingArriveonSiteCrybabyTrap_GP_001,P": "Uh oh. Algo no me cuadra... ¡Cuidado!",
    "PU_DELOIT_UWC_F_PMH_RefuelingArriveonSiteCrybabyTrap_GP_002,P": "Que raro. No veo ninguna nave... cuidado, es una trampa.",
    "PU_DELOIT_UWC_F_PMH_RefuelingArriveonSiteCrybabyTrap_GP_003,P": "¡Eh! ¡Es una encerrona! ¡Cuidado!",
    "PU_DELOIT_UWC_F_PMH_RefuelingArriveonSiteHandover_GP_001,P": "Muy bien, parece que acabas de llegar, asi que voy a pasarte con el cliente.",
    "PU_DELOIT_UWC_F_PMH_RefuelingArriveonSiteHandover_GP_002,P": "Perfecto, ya has llegado. Ahora te paso con el cliente.",
    "PU_DELOIT_UWC_F_PMH_RefuelingArriveonSiteHandover_GP_003,P": "Vale, ahora que ya estas en la zona voy a ponerte en contacto con el cliente...",
    "PU_DELOIT_UWC_F_PMH_RefuelingHostilesDetected_GP_001,P": "Eh, atencion. Tienes problemas de camino. Mantente alerta.",
    "PU_DELOIT_UWC_F_PMH_RefuelingHostilesDetected_GP_002,P": "Eh. Preparado. Tienes hostiles a punto de llegar.",
    "PU_DELOIT_UWC_F_PMH_RefuelingHostilesDetected_GP_003,P": "Malas noticias. He detectado hostiles yendo directos hacia ti.",
    "PU_DELOIT_UWC_F_PMH_RefuelingMissionAccept_GP_001,P": "Hola, soy DD. Gracias por aceptar este contrato de repostaje. No se a ti, pero a mi la idea de quedarme tirada sin combustible me da un miedo terrible. Por suerte, esta vez te tienen a ti para rescatarlos.",
    "PU_DELOIT_UWC_F_PMH_RefuelingMissionAccept_GP_002,P": "Hola, soy DD. A ver que tienes hoy entre manos... Vale, un trabajo de repostaje. ¿Que hariamos sin la gente que se olvida de rellenar depositos, eh? En fin, te dejo con ello.",
    "PU_DELOIT_UWC_F_PMH_RefuelingMissionAccept_GP_003,P": "Hola, soy DD otra vez. Parece que te hemos asignado un trabajo de repostaje. Buena suerte y cuidate ahi fuera.",
    "PU_DELOIT_UWC_F_PMH_RefuelingMissionFailClientShipDestroyed_GP_001,P": "Ay. Pobre alma... Y me temo que hay mas malas noticias. Sin una nave que repostar, tengo que cancelar el contrato. Espero que el siguiente tenga un final mas feliz. Cuidate, ¿eh?",
    "PU_DELOIT_UWC_F_PMH_RefuelingMissionFailClientShipDestroyed_GP_002,P": "No me puedo creer que el cliente no lo haya conseguido. Al menos tu sigues con nosotros, ¿no? No es mucho, pero algo es algo. Por desgracia, voy a tener que cancelar el contrato. Mejor suerte la proxima vez.",
    "PU_DELOIT_UWC_F_PMH_RefuelingMissionFailClientShipDestroyed_GP_003,P": "Aunque me encanta este trabajo, hay dias que se hacen mas duros que otros. No solo hemos perdido al cliente, sino que tambien tengo que cancelar el contrato. Bueno, mañana sera otro dia, ¿no? Hablamos pronto.",
    "PU_DELOIT_UWC_F_PMH_RefuelingTrapCompleteHazardPay_GP_001,P": "Uf. Me alegra que hayas salido de ese lio. Y no te preocupes por el contrato. He conseguido que Wayfarer te pague unos creditos igualmente. Al fin y al cabo, no fue culpa tuya que la solicitud de servicio resultara ser un cebo.",
    "PU_DELOIT_UWC_F_PMH_RefuelingTrapCompleteHazardPay_GP_002,P": "Gracias al cielo, estas bien. Normalmente, sin cliente no hay pago, pero he logrado conseguirte una compensacion por las molestias. Espero que eso te alegre un poco el dia. Cuidate ahi fuera, ¿vale?",
    "PU_DELOIT_UWC_F_PMH_RefuelingTrapCompleteHazardPay_GP_003,P": "No me puedo creer que estes bien. Ha sido bastante aterrador, pero he conseguido que te den una paga por riesgo por todas las molestias. Asi podremos ponerte de vuelta ahi fuera cuanto antes, ¿de acuerdo? Hablamos pronto.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingCombatEnds_GP_001,P": "Uf, eso ha sido absolutamente aterrador. Vale, demos prisa a esta transferencia de combustible.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingCombatEnds_GP_002,P": "¿Ya estan todos? Vale, terminemos esto y larguemonos de aqui de una vez.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingCombatEnds_GP_003,P": "Gracias. Este sistema es cada dia mas peligroso. Terminemos antes de que aparezcan mas.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingComplete_GP_001,P": "Ya esta. Listo para irme. Gracias otra vez y perdona las molestias.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingComplete_GP_002,P": "Vale. Transferencia de combustible completada. Gracias por el rescate. Espero no haberte dado demasiados problemas.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingComplete_GP_003,P": "Uf. Ya estoy completamente repostado. Muchisimas gracias por la ayuda. La proxima vez voy a intentar vigilar mejor los indicadores.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingDeathThroe_GP_001,P": "[ Grito de muerte ]",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingDockingComplete_GP_001,P": "Perfecto. Ya estamos acoplados. Autoriza la transaccion de combustible cuando quieras.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingDockingComplete_GP_002,P": "Acoplamiento completado. Solo necesito que confirmes la transaccion de combustible.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingDockingComplete_GP_003,P": "Eso deberia bastar. Fija las condiciones de la transaccion de combustible y le echo un vistazo.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingIncomplete_GP_001,P": "Espera. He perdido la conexion.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingIncomplete_GP_002,P": "Eh, todavia necesito mas combustible.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingIncomplete_GP_003,P": "Espera, la transferencia de combustible aun no habia terminado.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerArrives_GP_001,P": "Eh, gracias por venir. Me siento idiota por haberme quedado sin combustible. Si quieres acoplarte rapido, terminamos con esto enseguida.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerArrives_GP_002,P": "Eh, por aqui. Siento mucho esto. Habria jurado que calcule bien la distancia... En fin, acoplemonos para que puedas seguir tu camino.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerArrives_GP_003,P": "Hola. Perdona, esto es muy embarazoso. Tenia un monton de cosas que recoger de la ultima estacion de transferencia y supongo que se me olvido repostar. Un error de novato total. En fin, perdona; si nos acoplamos, podre dejarte salir de aqui.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_001,P": "Vale, vuelve pronto. Yo estare aqui esperando.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_002,P": "Sin problema, ocupate de lo que tengas que hacer. Yo estare aqui cuando estes listo.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_003,P": "Oh, te vas... si, claro, no pasa nada. Puedo esperar.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_001,P": "Vale, volvamos a conectarnos y salgamos de aqui.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_002,P": "Bienvenido de vuelta. Acoplemonos y terminemos el repostaje.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_003,P": "Me alegro de que hayas llegado. Estoy listo para acoplarme cuando tu quieras.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPriceAccepted_GP_001,P": "Perfecto. Ya estoy viendo la transferencia de combustible.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingPriceRejected_GP_001,P": "Ese precio es un poco mas alto de lo que esperaba.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_001,P": "¡Joder! ¿Quien demonios es ese?",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_002,P": "Tenemos compañia... y mala compañia...",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_003,P": "¡Ayuda! Estoy bajo ataque.",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_001,P": "¡Eh! ¿A que viene eso?",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_002,P": "¿Por que has hecho eso?",
    "PU_RefuelNPC01_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_003,P": "¿Que demonios te pasa?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingCombatEnds_GP_001,P": "Gracias al cielo. Tengo que admitir que por un momento se puso tenso. Ahora que ha pasado, terminemos de una vez.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingCombatEnds_GP_002,P": "Eso ha estado cerca. Terminemos de repostar para que pueda largarme.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingCombatEnds_GP_003,P": "Me alegro de que se haya acabado. Ojala podamos terminar sin mas problemas.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingComplete_GP_001,P": "Vale. Parece que hemos terminado. Yo me largo.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingComplete_GP_002,P": "Vale. Ya he repostado. Gracias. Y perdona si he sido algo seco contigo. Uno de esos dias. Vuela con cuidado.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingComplete_GP_003,P": "Ya esta. Deposito lleno. Pensaba que nunca saldria de aqui. Vale, me voy.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingDeathThroe_GP_001,P": "[ Grito de muerte ]",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingDockingComplete_GP_001,P": "Estamos conectados. Fija el precio para que podamos ponernos en marcha.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingDockingComplete_GP_002,P": "Acoplado. Adelante, enviame el precio.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingDockingComplete_GP_003,P": "Conexion confirmada. Define las condiciones de la transaccion para que podamos empezar.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingIncomplete_GP_001,P": "Eh, aun no habia terminado de repostar.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingIncomplete_GP_002,P": "¿Que pasa? Aun no hemos terminado de repostar.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingIncomplete_GP_003,P": "¿Pasa algo? Todavia necesito mas combustible.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerArrives_GP_001,P": "Bien, ya estas aqui. Acoplate para que podamos poner esto en marcha.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerArrives_GP_002,P": "Ya era hora. Estaba a punto de perder la cabeza si tenia que seguir flotando mas tiempo. Acoplate para que pueda salir de aqui.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerArrives_GP_003,P": "Menos mal que alguien ha aparecido. ¿Por que no te das prisa y te acoplas? No hay ninguna razon para que esto dure mas de lo necesario.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_001,P": "Vale... ¿Se supone que debo quedarme aqui esperando, entonces?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_002,P": "Date prisa en volver, ¿vale? No quiero pasarme todo el dia esperandote.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_003,P": "Claro... dejame aqui esperando. Como si no tuviera nada mejor que hacer.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_001,P": "¿Que tal si te acoplas para que podamos terminar esto? ¿O vas a seguir haciendome perder el tiempo?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_002,P": "Ah, ya estas aqui. Acoplate de una vez y terminamos con esto.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_003,P": "Y regresa mi salvador. ¿Que tal si te acoplas para que pueda irme?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPriceAccepted_GP_001,P": "Ya estoy llenando el deposito. Deberia quedar listo pronto.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingPriceRejected_GP_001,P": "Eso es mas de lo que puedo pagar.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_001,P": "Maldita sea. ¿Que mas puede salir mal hoy?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_002,P": "¡Mierda! ¡Quitamelos de encima!",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_003,P": "No me lo puedo creer. Primero el combustible y ahora esto.",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_001,P": "¿Que demonios estas haciendo?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_002,P": "¿Has perdido la cabeza?",
    "PU_RefuelNPC02_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_003,P": "¿A que ha venido eso?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingCombatEnds_GP_001,P": "Parece que por ahora estamos a salvo. Mejor terminamos de repostar.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingCombatEnds_GP_002,P": "Creo que esos eran los ultimos. Terminemos de arreglar mi combustible mientras podamos.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingCombatEnds_GP_003,P": "Todo despejado. Ojala podamos terminar de repostar antes de que aparezcan mas problemas.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingComplete_GP_001,P": "Y ya esta. Deposito lleno y listo para volar. Gracias por todo tu esfuerzo.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingComplete_GP_002,P": "Hecho. Gracias por el repostaje. Vuela con cuidado.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingComplete_GP_003,P": "Perfecto. Ya estoy completamente repostado. Aunque espero no volver a necesitar tus servicios en mucho tiempo.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingDeathThroe_GP_001,P": "[ Grito de muerte ]",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingDockingComplete_GP_001,P": "Muy bien. Conectados. No ha estado mal. Solo necesito que apruebes la transaccion de combustible.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingDockingComplete_GP_002,P": "Eso es. Todo enganchado. Estoy listo para revisar las condiciones de la transaccion de combustible en cuanto me las envies.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingDockingComplete_GP_003,P": "Parece que ya esta todo listo. Adelante, confirma la transaccion de combustible.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingIncomplete_GP_001,P": "Eh... sabes que aun no hemos terminado, ¿verdad?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingIncomplete_GP_002,P": "Espera un momento. Aun no he terminado de repostar.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingIncomplete_GP_003,P": "Eh, ¿que esta pasando? Todavia necesito mas combustible.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerArrives_GP_001,P": "Ah, perfecto. Ya estas aqui. Te agradezco la ayuda. No me puedo creer que me haya quedado sin combustible. En fin, estoy listo para acoplarme cuando tu quieras.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerArrives_GP_002,P": "Estupendo, gracias por venir. Estoy totalmente listo para acoplarme y podemos empezar cuando quieras. Yo mismo pilote una cisterna en su dia, asi que se lo que es. Eso hace aun mas embarazoso que se me haya secado el combustible. En fin, te dejo a lo tuyo.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerArrives_GP_003,P": "Eh, ya has llegado. Gracias por venir. ¿Donde estaria el verso sin repostadores como tu, eh? Lo tengo todo listo para que podamos empezar la transferencia en cuanto te acoples.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_001,P": "Vale, si te ha surgido algo urgente, me quedo aqui quieto hasta que vuelvas con el resto del combustible.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_002,P": "Oh, ¿te vas un momento? Sin problema. Me quedo por aqui. Solo vuelve rapido, ¿vale?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerLeavesArea_GP_003,P": "¿Nos tomamos un pequeño descanso? Solo no tardes demasiado, ¿de acuerdo? Estaria bien volver a volar pronto.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_001,P": "Bienvenido de vuelta. Sigo listo para acoplarme.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_002,P": "Me alegra volver a verte. Acoplemonos y terminemos de repostar.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPlayerReturnstoArea_GP_003,P": "Me alegro de que hayas vuelto. ¿Terminamos de una vez con este repostaje?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPriceAccepted_GP_001,P": "Vale, combustible transfiriendose ahora.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingPriceRejected_GP_001,P": "Mas vale que sea una broma ese precio. Intentalo de nuevo.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_001,P": "Oh, mierda. ¡Me estan disparando!",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_002,P": "Maldita sea. ¿No podian haber elegido un momento peor?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingShipAttackedbyOther_GP_003,P": "¿Te puedes creer a estos capullos?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_001,P": "¿Que demonios te pasa?",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_002,P": "Eh, se supone que tienes que ayudarme, no dispararme.",
    "PU_RefuelNPC03_CIV_M_ATC_RefuelingShipAttackedbyPlayer_GP_003,P": "¿A que ha venido eso?",
}


def escape_ini_value(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def load_new_keys(report_path: Path) -> list[str]:
    keys: list[str] = []
    capture = False
    for line in report_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "Claves nuevas:":
            capture = True
            continue
        if stripped == "Claves obsoletas:":
            break
        if capture and stripped:
            keys.append(stripped)
    return keys


def load_previous_translation() -> dict[str, str]:
    blob = subprocess.run(
        ["git", "show", "HEAD:source/languages/es-es/translation.ini"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8-sig")
    temp_path = REPO_ROOT / "dist" / "validation" / "_seed_previous_translation.ini"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(blob, encoding="utf-8-sig")
    return read_global_ini(temp_path).mapping


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplica traducciones seguras reutilizables a las claves nuevas del parche 4.8.")
    parser.add_argument("--report", default="informes/TRANSLATION_MEMORY_REFRESH_REPORT.md")
    parser.add_argument("--english-global-ini", default="input/current/global.ini")
    parser.add_argument("--translation-memory", default="source/languages/es-es/translation.ini")
    args = parser.parse_args()

    report_path = resolve_path(args.report)
    english_path = resolve_path(args.english_global_ini)
    translation_path = resolve_path(args.translation_memory)

    new_keys = load_new_keys(report_path)
    english_data = read_global_ini(english_path)
    translation_data = read_global_ini(translation_path)
    previous_translation = load_previous_translation()

    by_english_value: dict[str, set[str]] = defaultdict(set)
    for key, value in previous_translation.items():
        english_value = english_data.mapping.get(key)
        if english_value is None:
            continue
        if value == english_value:
            continue
        by_english_value[english_value].add(value)

    replacements: dict[str, str] = {}
    rename_hits = 0
    exact_hits = 0
    manual_hits = 0

    for key in new_keys:
        english_value = english_data.mapping.get(key)
        if english_value is None:
            continue
        current_value = translation_data.mapping.get(key)
        if current_value != english_value:
            continue

        reused = KEY_TRANSLATIONS.get(key)
        if reused is not None:
            replacements[key] = escape_ini_value(reused)
            manual_hits += 1
            continue

        candidates = (
            key,
            re.sub(r",P$", "", key),
            f"{key},P",
        )
        reused = None
        for candidate in candidates:
            previous_value = previous_translation.get(candidate)
            if previous_value and previous_value != english_value:
                reused = previous_value
                rename_hits += 1
                break
        if reused is None:
            exact_values = by_english_value.get(english_value, set())
            if len(exact_values) == 1:
                reused = next(iter(exact_values))
                exact_hits += 1
        if reused is None:
            reused = ENGLISH_VALUE_TRANSLATIONS.get(english_value)
            if reused is not None:
                manual_hits += 1
        if reused is not None:
            replacements[key] = escape_ini_value(reused)

    updated_entries = [
        Entry(key=entry.key, value=replacements.get(entry.key, entry.value))
        for entry in translation_data.entries
    ]
    write_global_ini(updated_entries, translation_path)

    pending_after = sum(
        1
        for key in new_keys
        if english_data.mapping.get(key) is not None
        and replacements.get(key, translation_data.mapping.get(key)) == english_data.mapping[key]
    )

    print(f"Reutilizadas por renombre: {rename_hits}")
    print(f"Reutilizadas por texto ingles exacto: {exact_hits}")
    print(f"Traducidas por mapa manual: {manual_hits}")
    print(f"Total actualizadas: {len(replacements)}")
    print(f"Claves nuevas aun sin traducir: {pending_after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
