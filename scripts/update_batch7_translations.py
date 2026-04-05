from pathlib import Path


MAPPING = {
    "Covalex_Delivery_Nyx_Medium_Title_001": "Entrega Covalex de media distancia en Nyx",
    "Covalex_Delivery_Stanton_Hard_Title_001": "Entrega Covalex de larga distancia en Stanton",
    "Covalex_Delivery_Stanton_Medium_Title_001": "Entrega Covalex de media distancia en Stanton",
    "Covalex_Delivery_Stanton_Super_Title_001": "Entrega especial de Covalex en el sistema Stanton",
    "Covalex_Delivery_Stanton_VeryHard_Title_001": "Entrega Covalex de muy larga distancia en Stanton",
    "Covalex_HaulCargo_AToB_Intro_title": "Oportunidad para transportista independiente de carga",
    "Covalex_HaulCargo_AToB_Rehire_title": "Reevaluacion de transporte de carga de Covalex",
    "Covalex_HaulCargo_AToB_title": "~mission(ReputationRank) Rango - Transporte directo de carga ~mission(CargoGradeToken)",
    "Covalex_HaulCargo_LinearChain_title": "~mission(ReputationRank) Rango  - Transporte de carga ~mission(CargoGradeToken)",
    "Covalex_HaulCargo_MultiToSingle_title": "~mission(ReputationRank) Rango - Transporte de carga ~mission(CargoGradeToken)",
    "Covalex_HaulCargo_RoundDelivery_title": "~mission(ReputationRank) Rango - Circuito de transporte de carga ~mission(CargoGradeToken)",
    "Covalex_HaulCargo_SingleToMulti_title": "~mission(ReputationRank) Rango - Transporte de carga ~mission(CargoGradeToken) ",
    "Covalex_LocalDelivery_header_01": "Ruta de reparto local de Covalex",
    "Covalex_LocalDelivery_title_01": "Ruta de reparto local de Covalex",
    "Covalex_LocalDelivery_title_intro": "Evaluacion de Covalex",
    "Covalex_LocalDelivery_title_rehire": "Reevaluacion de Covalex",
    "Covalex_LogIn": "INICIO_DE_SESION\\nREQUERIDO",
    "Covalex_LogInText": "COLOQUE LOS DEDOS EN EL TECLADO\\nPARA LA VERIFICACION",
    "Covalex_Messages": "NUEVOS\\nMENSAJES\\nPENDIENTES",
    "Covalex_QuantumSensitiveDelivery_Title_001": "Error de envio - carga sensible al QT",
    "Covalex_RecoverCargo_Medium_Title": "Envio mediano de Covalex por recuperar",
    "Covalex_RecoverCargo_Super_Title": "Recupera un envio VIP de Covalex",
    "Covalex_RecoverCargo_VeryHard_Title": "Envio masivo de Covalex por recuperar",
    "Covalex_RepUI_Focus": "Entregas, transporte, servicios de mensajeria",
    "Covalex_SignOff_001": "Gracias de antemano por garantizar un servicio rapido,",
    "Covalex_SignOff_002": "Buena suerte ahi fuera.",
    "Covalex_SignOff_003": "Hablamos pronto,",
    "Covalex_SignOff_004": "Y como dice el cartel de mi pared: 'Bee Safe, Honey!'",
    "Covalex_SignOff_005": "Estoy deseando saber como sale todo,",
    "Covalex_SignOff_006": "Que vaya bien,",
    "Covalex_SignOff_007": "Buen viaje y vuela seguro.",
    "Covalex_SignOff_008": "Confio en ti. Haz que me sienta orgulloso.",
    "Covalex_courier_dc_small_title_001": "Ruta local de envio de Covalex",
    "Craft": "Fabricar",
    "CraftingHangarMedium,P": "[M] Hangar de fabricacion",
    "CraftingHangarSmall,P": "[S] Hangar de fabricacion",
    "CraftingKiosk": "Quiosco de fabricacion",
    "Criminal_LocalDelivery_desc_01": "Nos estamos quedando cortos de suministro y necesitamos un piloto extra que ayude a mover las cosas.\\n\\nRecogeras los ingredientes en bruto de la granja, los dejaras en el laboratorio, llevaras el material refinado al alijo para que lo corten y empaqueten, y despues sacaras el producto final a nuestros distribuidores. \\n\\nAqui lo tienes bien claro para que no te lies -\\n\\n~mission(Itinerary)\\n\\nY para asegurarnos de que seguridad no empiece a husmear, hemos preparado un dead-drop para la entrega final. \\n\\nSolo mantenlo simple y sigue el plan y todo deberia ir sobre ruedas. Ocupate de todo lo de la lista y te llevaras una buena parte de los creditos.\\n",
    "Criminal_LocalDelivery_desc_02": "Las cosas estan empezando a escasear en ~mission(DropOff1) y necesitamos poner a cocinar una nueva tanda.  \\n\\nCrees que puedes ayudarnos a hacer esto de la granja a la mesa?\\n\\n~mission(Itinerary)\\n\\nCuando hagas el dead-drop final a los distribuidores, recibiras una buena y jugosa parte. \\n\\nY hazme un favor. Procura que no te arresten.\\n",
    "Criminal_LocalDelivery_desc_03": "Gracias a un desafortunado accidente, nos hemos quedado sin un piloto y tenemos toda una tanda que hay que procesar y empaquetar cuanto antes para sacarla al mercado antes de que se eche a perder. \\n\\nEsto es lo que necesitamos -\\n\\n~mission(Itinerary)\\n\\nSe que la seguridad puede ser un problema, asi que mantente discreto e intenta ser sutil cuando uses el dead-drop en ~mission(DropOff1). \\n",
    "Covalex_RecoverCargo_Easy_Title": "Pequeño envio de Covalex por recuperar",
    "Covalex_RecoverCargo_Hard_Title": "Gran envio de Covalex por recuperar",
    "Covalex_RecoverCargo_Intro_Description": "[PH] Descripcion inicial de recuperacion de carga de Covalex sin combate",
    "Covalex_RecoverCargo_Intro_Title": "[PH] Titulo inicial de recuperacion de carga de Covalex",
    "Criminal_LocalDelivery_title_01": "Reaprovisionamiento",
    "Criminal_Localdelivery_header_01": "Reaprovisionamiento",
    "Criminal_RepUI_Area,P": "[PH] Area",
    "Criminal_RepUI_Description,P": "[PH] Descripcion criminal",
    "Criminal_RepUI_Focus,P": "[PH] Enfoque criminal",
    "Criminal_RepUI_Founded,P": "[PH] N/A",
    "Criminal_RepUI_Headquarters,P": "[PH] Cuartel criminal",
    "Criminal_RepUI_Leadership,P": "[PH] Liderazgo criminal",
    "Criminal_RepUI_Name,P": "[PH] Criminal",
    "Criminal_RetrieveData_Reclaimer_desc": "Llevaba tiempo persiguiendo un determinado lote de datos y, justo cuando parecia que iba a lograrlo, la nave fue atacada por este Reclaimer convertido de Nine Tails llamado el Black Kite. Intente hackear los servidores del Black Kite para ver si habian copiado los datos, pero no encontre forma de superar a distancia sus protocolos de cifrado sin la clave fisica.\\n\\nAqui es donde entras tu. Necesito a alguien que aborde su nave, consiga la clave de descifrado y descifre el servidor para que yo pueda descargar a distancia lo que necesito.\\n\\nEres lo bastante listo como para saber con quien nos estamos metiendo, asi que planifica en consecuencia. Como esto va a remover plumas poderosas, no dejemos nada al azar. Destruye el Black Kite cuando termines para cubrirnos las espaldas.\\n",
    "Criminal_RetrieveData_Reclaimer_obj_long_01": "Aborda el Black Kite.",
    "Criminal_RetrieveData_Reclaimer_obj_long_02": "Encuentra la clave de descifrado.",
    "Criminal_RetrieveData_Reclaimer_obj_long_03": "Inserta la clave de descifrado en el servidor.",
    "Criminal_RetrieveData_Reclaimer_obj_long_04": "Destruye el Black Kite.",
    "Criminal_RetrieveData_Reclaimer_obj_marker_03": "Clave de descifrado",
    "Criminal_RetrieveData_Reclaimer_obj_short_01": "Aborda el Black Kite",
    "Criminal_RetrieveData_Reclaimer_obj_short_02": "Encuentra la clave de descifrado.",
    "Criminal_RetrieveData_Reclaimer_obj_short_03": "Inserta la clave de descifrado en el servidor",
    "Criminal_RetrieveData_Reclaimer_obj_short_04": "Destruye el Black Kite",
    "Criminal_RetrieveData_Reclaimer_obj_short_05": "Autodestruccion del Black Kite: %ls",
    "Criminal_RetrieveData_Reclaimer_title": "Hazte con los datos",
    "Criminal_Steal_Danger_Easy_001": "Texto provisional de peligro criminal facil",
    "Criminal_Steal_Danger_Medium_001": "Texto provisional de peligro criminal medio",
    "Criminal_Steal_Easy_Title_001": "Texto provisional de titulo criminal facil",
    "Criminal_Steal_Medium_Title_001": "Texto provisional de titulo criminal medio",
    "Criminal_Steal_Timed_Easy_001": "Texto provisional de tiempo criminal facil",
    "Criminal_Steal_Timed_Medium_001": "Texto provisional de tiempo criminal medio",
    "Criminal_from": "REMITENTE NO ENCONTRADO",
    "Crus_HistMarker_Text_28": "Cellin recibio su nombre por el hermano menor del clasico cuento infantil A Gift for Baba, ya que los numerosos volcanes dormidos de la luna encarnaban la ira contenida del personaje. Este volcan inactivo, bautizado por los vulcanologos como Cellin's Peak, se vigila y monitoriza cuidadosamente porque se cree que tiene muchas probabilidades de activarse algun dia. ",
    "Crus_HistMarker_Text_29": "Daymar recibio su nombre por el hermano mediano de A Gift for Baba. Conocido por su tendencia a perderse, su nombre tambien fue dado a este cañon serpenteante por los primeros exploradores. ",
    "Crus_HistMarker_Text_30": "Yela recibio su nombre por la hermana mayor de A Gift for Baba, conocida por su caracter frio y calculador. Esta llanura extensa registro la temperatura mas baja anotada por la primera expedicion cientifica a la luna, lo que le valio el nombre de Yela's Plain. ",
    "Crus_HistMarker_Text_31": "El estudio de los geiseres de Cellin comenzo con una estacion de observacion construida en este lugar en 2908. El geologo Randell Engler paso casi una decada investigando estas maravillas naturales. Fue el primero en plantear la hipotesis de que los geiseres de la luna desempeñaban un papel importante en la dispersion de nutrientes y minerales vitales por el suelo.",
    "Crus_HistMarker_Text_32": "Durante el viaje del Imperator Costigan al sistema Stanton en 2944, compartio una comida aqui, en Gallete Family Farms. Costigan esperaba que su visita llamara la atencion sobre los agricultores independientes y trabajadores de todo el Imperio que se beneficiarian de la legislacion sobre subsidios agricolas debatida por el Senado en aquel momento.",
    "Crus_HistMarker_Text_33": "En 2927, Fakih Borisov introdujo una manada de grandes cangrejos terrestres modificados geneticamente en Daymar. Criados para soportar las condiciones secas de la luna, los cangrejos recorrieron esta parte de Daymar durante casi una decada, pero el sueño de Borisov de convertir la luna en el paraiso de un ranchero nunca llego a materializarse. Un componente clave de su plan era que los cangrejos pastaran sobre la escasa vegetacion natural de la luna, pero esto impregnaba a los animales de un olor desagradable que se adheria a cualquier producto derivado de ellos.  ",
    "Crus_HistMarker_Text_34": "El 22 de agosto de 2924, el arqueologo aficionado Sonny Pak revelo un fosil que, segun afirmaba, pertenecia a una nueva especie inteligente que habia habitado esta luna. La noticia del descubrimiento se difundio por Spectrum y entusiasmo a la comunidad cientifica. Sin embargo, en lugar de permitir que los cientificos examinaran el especimen, Sonny llevo los restos de gira promocional e incluso vendio entradas a quienes quisieran verlos. Sus actos fueron condenados por la comunidad cientifica y, tras la intervencion del gobierno de la UEE, se demostro que el fosil era falso.",
    "Crus_HistMarker_Text_35": "Los romanticos creen que los amantes que se declaran su afecto mutuamente en esta cornisa estaran juntos para siempre. Esta leyenda tiene su origen en la macabra historia de la famosa pareja de forajidos Akiko 'Jackal' Bazin y Rick 'Shady' Milligan. En 2913, a escasos instantes de ser capturados, decidieron evitar la carcel y se arrojaron al vacio cogidos de la mano.",
    "Crus_HistMarker_Text_36": "El 31 de diciembre de 2940, el equipo de sataball Stanton Knights aterrizo aqui para que su nave recibiera reparaciones de emergencia. Mientras esperaban, el equipo trazo su estrategia para el partido del campeonato contra los Kiel Guardians, programado para el dia siguiente. Segun los miembros del equipo, fue aqui donde concibieron la ya famosa jugada 'Franklin Flip', que impulso al equipo a la victoria y al primer campeonato SBPL de la historia del club.",
    "Crus_HistMarker_Text_37": "El 17 de marzo de 2904, Meiko Norwood se desplomo aqui mientras cargaba muestras de suelo en su nave. Fallecio mas tarde aquel mismo dia por complicaciones derivadas de una valvula cardiaca artificial, convirtiendose en la primera persona en morir en Daymar.",
    "Crus_HistMarker_Text_38": "En 2939, Crusader Security capturo aqui a un fugitivo buscado por su relacion con un robo masivo de chits de credito. El dinero no se recupero durante el arresto, pero circularon rumores de que el forajido llevaba herramientas de excavacion. Desde entonces, los cazatesoros acuden en masa aqui en busca de la fortuna perdida, aunque los escaneos repetidos no han mostrado señal alguna de ella. \\n\\nCrusader Industries desaconseja excavar la zona y pide que cualquier terreno removido se vuelva a colocar en su lugar para preservar la belleza natural de la luna.",
    "Crus_HistMarker_Text_39": "La pintura de Greg Caldwell \"The Starman's Farewell\", perdida durante mucho tiempo, fue descubierta enterrada bajo un mojon de piedra en este lugar en 2908. Robada del Terra Museum of Contemporary Art en 2731, sigue siendo un misterio como acabo aqui esta obra de arte. La pintura fue devuelta a Terra.",
    "Crus_HistMarker_Text_40": "En 2945, el minero independiente Bruce Amodeo descubrio una gran gema de serendibita cerca de este puesto. Su venta en subasta a un comprador anonimo batio records de creditos por quilate pagados por una serendibita. Desde entonces, los mineros han acudido en masa a la region en busca de nuevos depositos de serendibita.",
    "Crus_HistMarker_Text_41": "La tragedia golpeo al puesto de Cuadrado el 15 de mayo de 2941 debido a un sistema de soporte vital defectuoso. Un exceso de oxigeno que se filtraba al puesto se inflamo, provocando una explosion que costo nueve vidas. La catastrofe llevo a Crusader Industries a endurecer las normativas sobre los puestos avanzados y a exigir revisiones de mantenimiento mas frecuentes en todas las instalaciones.",
    "Crus_HistMarker_Text_42": "Crusader Industries felicita a Bountiful Harvest Hydroponics por su extraordinaria respuesta a quienes necesitaban ayuda en Vega. Tras los horribles ataques Vanduul del 5 de octubre de 2945, Bountiful Harvest produjo y dono mas suministros alimentarios de emergencia para el esfuerzo de socorro en Vega que cualquier otro puesto de las lunas de Crusader. El extraordinario sacrificio de este puesto sirve como recordatorio de que la UEE siempre respaldara a quienes se enfrenten cara a cara a la amenaza Vanduul.",
    "Crus_HistMarker_Text_43": "La celebre actriz y conocida naturista Millicent Silverton solia acudir a esta zona remota a acampar en plena naturaleza. Le gustaba tanto el lugar que pidio que se incluyera en la pelicula de 2941 \"Onto the Break.\"",
    "Crus_HistMarker_Text_44": "Los geiseres de aqui presentan un conjunto unico de pequeñas fisuras que, cuando la presion alcanza una cantidad determinada, producen un sonido similar a un gemido. Es este fenomeno el que ha dado pie a los rumores erroneos de que el lugar esta encantado.",
    "Crus_HistMarker_Text_45": "En 2932, este lugar acogio el infame Slim Chance Rally. Esta reunion de entusiastas de los buggies Greycat se celebra una vez al año en una localizacion remota para competir en un derby de destruccion ilicito.",
    "Crus_HistMarker_Text_46": "Crusader Industries utiliza a menudo esta ubicacion y su terreno irregular para probar sobre el terreno los sistemas de aterrizaje de sus nuevos diseños de naves. Fue aqui, el 25 de marzo de 2934, donde se produjo el primer y unico aterrizaje del fallido diseño de nave Juno.",
    "Crus_HistMarker_Title_01": "Lugar de nacimiento de Vortex Thorson",
}


def main() -> None:
    path = Path("input/translation-batches/batch-0007/translated.ini")
    lines = path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    for line in lines:
        if "=" not in line:
            updated.append(line)
            continue
        key, value = line.split("=", 1)
        if key in MAPPING:
            updated.append(f"{key}={MAPPING[key]}")
        else:
            updated.append(line)
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
