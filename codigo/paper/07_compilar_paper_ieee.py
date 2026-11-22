#!/usr/bin/env python3
"""
Paso 7: Generación sincronizada del artículo IEEE en LaTeX (.tex) y PDF compilado
en formato doble columna (WeasyPrint) integrando métricas geoespaciales, diseño
geofísico georreferenciado y simulación ERT 2.5D reproducible.
Proyecto Final de Geofísica Ambiental (Otoño 2026) — Facultad de Ingeniería, BUAP.
Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale.
"""

import os
import csv
import json
import html
import shutil
import pathlib
import zipfile
import weasyprint

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
SIG_DIR = os.path.join(BASE_DIR, "sig")
FIG_DIR = os.path.join(BASE_DIR, "mapas_paper_ieee")
OUT_DIR = os.path.join(BASE_DIR, "paper_ieee")
os.makedirs(OUT_DIR, exist_ok=True)


def fig_uri(filename):
    return pathlib.Path(os.path.join(FIG_DIR, filename)).resolve().as_uri()


def load_data():
    with open(os.path.join(SIG_DIR, "resumen_metricas.json"), "r", encoding="utf-8") as f:
        metrics = json.load(f)
    with open(os.path.join(SIG_DIR, "simulacion_ert_resultados.json"), "r", encoding="utf-8") as f:
        ert = json.load(f)
    with open(os.path.join(SIG_DIR, "coordenadas_diseno_geofisico.csv"), "r", encoding="utf-8") as f:
        design_rows = list(csv.DictReader(f))
    return metrics, ert, design_rows


def build_latex(metrics, ert, design_rows):
    poly = metrics["poligonos"]
    ref = metrics["referencias"]
    fire = metrics["incendio_mayo_2022"]
    est = metrics["estado_actual_2026_11_03"]
    sar = metrics["sar_sentinel1_rel70"]
    topo = metrics["topografia_hidrologia"]["stats"]
    km = metrics["ml_kmeans_k5"]

    area_prin = f"{poly['cuerpo_principal']['area_ha']:.2f}"
    area_huella = f"{poly['huella_total']['area_ha']:.2f}"
    area_2011 = f"{poly['nucleo_2011']['area_ha']:.2f}"
    area_aux = f"{poly['area_auxiliar_so']['area_ha']:.2f}"
    area_lag = f"{poly['laguna_lixiviados_no']['area_m2']:.0f}"
    exp_ha = f"{poly['expansion_2011_2025_ha']:.2f}"
    exp_pct = f"{poly['expansion_2011_2025_pct']:.1f}"
    cen_utm = poly["cuerpo_principal"]["centroide_utm"]
    cen_dms = poly["cuerpo_principal"]["centroide_dms"]
    lag_utm = poly["laguna_lixiviados_no"]["centroide_utm"]
    p1 = ref["profepa"][0]
    p2 = ref["profepa"][1]
    pct_sin_veg = km[0]["pct_en_huella"] + km[1]["pct_en_huella"]
    total_ert_m = sum(int(float(r["longitud_m"])) for r in design_rows if r["tipo"].startswith("ERT"))

    rec = {r["zona"]: r for r in ert["tabla_recuperacion"]}
    res_true = rec["Residuos (1.5–14 m)"]["verdadero_ohm_m"]
    res_inv = rec["Residuos (1.5–14 m)"]["invertido_ohm_m"]
    lix_true = rec["Lixiviado (14–24 m)"]["verdadero_ohm_m"]
    lix_inv = rec["Lixiviado (14–24 m)"]["invertido_ohm_m"]
    lod_true = rec["Bolsa de lodos (3–7 m)"]["verdadero_ohm_m"]
    lod_inv = rec["Bolsa de lodos (3–7 m)"]["invertido_ohm_m"]
    nat_true = rec["Terreno natural, borde"]["verdadero_ohm_m"]
    nat_inv = rec["Terreno natural, borde"]["invertido_ohm_m"]
    deb_true = rec["Debajo del lixiviado (26–35 m)"]["verdadero_ohm_m"]
    deb_inv = rec["Debajo del lixiviado (26–35 m)"]["invertido_ohm_m"]
    roc_true = rec["Roca basal (> 28 m, centro)"]["verdadero_ohm_m"]
    roc_inv = rec["Roca basal (> 28 m, centro)"]["invertido_ohm_m"]

    pz = {r["elemento"]: r for r in design_rows if r["elemento"].startswith("P")}
    r1_row = [r for r in design_rows if r["elemento"] == "R1"][0]

    tex = rf"""\documentclass[conference]{{IEEEtran}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[spanish,es-tabla]{{babel}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{amsmath}}
\usepackage{{url}}

\begin{{document}}

\title{{Caracterizaci\'on geof\'isica propuesta del relleno sanitario de Santa Mar\'ia Coapan (Tehuac\'an, Puebla): delimitaci\'on espacial, dise\~no de campo e interpretaci\'on esperada}}

\author{{\IEEEauthorblockN{{Ian A. Sandoval-Valderr\'abano \qquad Carlos Enrique Fern\'andez Tepale}}
\IEEEauthorblockA{{Facultad de Ingenier\'ia, Benem\'erita Universidad Aut\'onoma de Puebla\\
Puebla, M\'exico}}}}

\maketitle

\begin{{abstract}}
El relleno sanitario de Tehuac\'an, en la junta auxiliar de Santa Mar\'ia Coapan (Puebla), oper\'o cerca de tres d\'ecadas. La comunidad y la organizaci\'on Greenpeace afirman que recibi\'o residuos peligrosos industriales y biol\'ogico-infecciosos. La PROFEPA orden\'o su clausura total y definitiva el 27 de junio de 2023 y pidi\'o un estudio del da\~no ambiental y un plan de remediaci\'on. Hasta donde se encontr\'o en fuentes p\'ublicas, ese estudio no se ha presentado. Este trabajo propone c\'omo usar m\'etodos geof\'isicos para responder tres preguntas que hoy no tienen respuesta medida: d\'onde est\'an los residuos, hasta d\'onde lleg\'o el lixiviado y si hay zonas con material met\'alico enterrado. Se dise\~na un levantamiento georreferenciado con tomograf\'ia de resistividad el\'ectrica (ERT) y polarizaci\'on inducida (IP), electromagn\'etico en el dominio de frecuencia (EM), magnetometr\'ia y radar de penetraci\'on terrestre (GPR), con piez\'ometros para confirmar. Para mostrar qu\'e se espera ver, se simul\'o en 2.5D un perfil sint\'etico de ERT ({ert['n_mediciones']} mediciones Wenner--Schlumberger, {ert['ruido_pct']:.0f}~\% de ruido). La inversi\'on ajust\'o con RMS de {ert['rms_final_pct']:.1f}~\%, recuper\'o bien el cuerpo de residuos ({res_inv} contra {res_true}~$\Omega\cdot$m del modelo) y ubic\'o el lixiviado, aunque lo suaviz\'o y mostr\'o m\'as resistivo ({lix_inv} contra {lix_true}~$\Omega\cdot$m) extendi\'endolo en profundidad. No existen mediciones geof\'isicas de campo: todo resultado del subsuelo es una predicci\'on. En cambio, la ubicaci\'on real, las dimensiones ({area_prin}~ha de cuerpo principal y {area_huella}~ha de huella operativa total en {cen_dms}) y la evoluci\'on superficial (1993--2025) s\'i se delimitaron mediante im\'agenes satelitales hist\'oricas y un modelo digital de elevaci\'on para georreferenciar el dise\~no propuesto.
\end{{abstract}}

\begin{{IEEEkeywords}}
geof\'isica ambiental, relleno sanitario, lixiviado, tomograf\'ia de resistividad el\'ectrica, polarizaci\'on inducida, percepci\'on remota, Tehuac\'an
\end{{IEEEkeywords}}

\section{{Introducci\'on}}
Un relleno sanitario bien dise\~nado a\'isla los residuos del suelo y del agua subterr\'anea. Un tiradero sin control no lo hace: el agua de lluvia atraviesa los residuos y forma lixiviado, un l\'iquido con sales, materia org\'anica y, a veces, metales. Si ese l\'iquido llega al acu\'ifero, la contaminaci\'on se mueve bajo tierra sin que se vea en la superficie.

La geof\'isica ayuda en este problema porque el lixiviado conduce muy bien la electricidad. Por eso baja la resistividad del terreno, y la ERT puede dibujarlo desde la superficie sin excavar~\cite{{maurya2017,helene2020}}. La polarizaci\'on inducida (IP) agrega informaci\'on sobre el tipo de material, por ejemplo, residuos con metales~\cite{{abdulrahman2016}}.

El caso elegido es el relleno sanitario municipal de Tehuac\'an, en territorio de Santa Mar\'ia Coapan, Puebla. Es un problema ambiental real, tiene una resoluci\'on oficial de clausura y, seg\'un fuentes p\'ublicas, sigue sin estudio de da\~no ni remediaci\'on~\cite{{greenpeace,profepa2023}}. Este informe no presenta mediciones geof\'isicas de campo; propone un proyecto de dise\~no completo respaldado por una delimitaci\'on satelital y topogr\'afica real en \texttt{{EPSG:32614}}, precisa la red de adquisici\'on necesaria y muestra mediante simulaci\'on num\'erica qu\'e se espera resolver y qu\'e limitaciones existen.

\section{{Problem\'atica a resolver}}
\subsection{{Qu\'e pas\'o}}
La Tabla~I resume la historia del sitio. Las fuentes documentales no coinciden en el a\~no exacto de inicio (1993 o 1995), por lo que se reportan ambas fechas acotadas adem\'as por escenas Landsat hist\'oricas.

\begin{{table}}[t]
\centering
\caption{{Cronolog\'ia del relleno sanitario de Tehuac\'an}}
\label{{tab:cronologia}}
\footnotesize
\begin{{tabular}}{{@{{}}p{{0.24\columnwidth}}p{{0.70\columnwidth}}@{{}}}}
\toprule
\textbf{{Fecha}} & \textbf{{Hecho (fuente)}} \\
\midrule
1993--1995 & Inicio de operaci\'on: 1993~\cite{{greenpeace}}; junio de 1995, con 15 a\~nos de vida \'util estimada~\cite{{linares}}. Escenas Landsat muestran terreno intacto en feb.~1993 y obra abierta en dic.~1994~\cite{{landsat}}. \\
2010 & A\~no en que, seg\'un el proyecto original, deb\'ia dejar de operar~\cite{{linares}}. \\
Oct.~2021 & La comunidad lo cierra de hecho (7 de octubre)~\cite{{greenpeace}}. \\
Mayo~2022 & Incendio en el sitio (iniciado entre el 5 y 8 de mayo seg\'un Sentinel-2; cicatriz de {fire['area_dnbr_ge_010_ha']:.2f}~ha). El Comit\'e de Bienes de Coapan afirma que borra evidencia~\cite{{incendio,sentinel}}. \\
Jun.~2022 & La SMADSOT coloca sellos de clausura (nota del 13 de junio)~\cite{{publimetro}}. \\
27~jun.~2023 & Resolucion de la PROFEPA (Exp.~PFPA/3.2/2C.27.1/00036-20): clausura total y definitiva; retirar residuos peligrosos y RPBI, estudiar el da\~no y presentar plan de remediaci\'on~\cite{{greenpeace,profepa2023}}. \\
\bottomrule
\end{{tabular}}
\end{{table}}

\subsection{{Qu\'e se dice y qu\'e est\'a comprobado}}
Hay que separar los hechos documentados de las afirmaciones. La clausura de la PROFEPA y las fechas est\'an documentadas~\cite{{greenpeace,profepa2023}}. En cambio, son afirmaciones de la comunidad y organizaciones civiles —que este trabajo no verifica en campo— el dep\'osito de lodos de lavander\'ias de mezclilla y residuos hospitalarios~\cite{{greenpeace,incendio}}, el acumulado de 3.7~millones de toneladas~\cite{{greenpeace}}, el avance de 18~ha sobre la Reserva de la Biosfera Tehuac\'an--Cuicatl\'an~\cite{{incendio}}, la filtraci\'on comprobada a la reserva y la asociaci\'on directa con casos de c\'ancer~\cite{{incendio,desinformemonos}}.

Ninguna de esas cifras de volumen o salud proviene de un estudio t\'ecnico independiente. Sin embargo, la evoluci\'on superficial s\'i puede medirse con im\'agenes satelitales: en junio de 2011 el n\'ucleo consolidado med\'ia {area_2011}~ha (acorde con las 6--7.2~ha autorizadas en el proyecto original), en agosto de 2025 el cuerpo principal alcanz\'o {area_prin}~ha (\(\sim\)10~ha citadas en~\cite{{linares}}) y la huella operativa total suma {area_huella}~ha al incluir el \'area auxiliar suroeste ({area_aux}~ha) y 0.24~ha de franjas perimetrales de acceso y maniobra~\cite{{wayback}}. La diferencia respecto a las 16.46~ha asignadas por la CONANP~\cite{{conanp}} corresponde a franjas perif\'ericas y de amortiguamiento dentro de la subzona administrativa.

\subsection{{Pregunta que se quiere responder}}
?`D\'onde est\'an los residuos y el lixiviado en el subsuelo, hasta qu\'e profundidad llegan y hacia d\'onde se mueven? Sin esa respuesta f\'isica medida no es posible dise\~nar una obra de contenci\'on y remediaci\'on conforme a la orden de la PROFEPA.

\begin{{figure*}}[t]
  \centering
  \includegraphics[width=\textwidth]{{../mapas_paper_ieee/ieee_fig1_localizacion_regional.pdf}}
  \caption{{Localizaci\'on regional del sitio de estudio. (a) Rep\'ublica Mexicana y estado de Puebla. (b) Divisi\'on municipal de Puebla; en rojo, municipio de Tehuac\'an. (c) Valle de Tehuac\'an, carretera federal MEX-125, iglesia de Santa Mar\'ia Coapan~\cite{{gcatholic}} y ubicaci\'on del relleno sanitario. Elaboraci\'on propia con l\'imites vectoriales abiertos~\cite{{ne,mexgeojson}}.}}
  \label{{fig:localizacion_regional}}
\end{{figure*}}

\section{{Localizaci\'on}}
Santa Mar\'ia Coapan es una junta auxiliar del municipio de Tehuac\'an, en el sureste del estado de Puebla (Fig.~1). El relleno se ubica junto al km~12.2 de la carretera federal Tehuac\'an--Huajuapan (\texttt{{MEX-125}})~\cite{{linares}}, dentro de la subzona de aprovechamiento especial de la Reserva de la Biosfera Tehuac\'an--Cuicatl\'an~\cite{{publimetro,conanp}}. A partir de dos coordenadas oficiales de inspecci\'on de la PROFEPA ({p1['desc']} en el acceso suroeste y {p2['desc']} al sur-sureste) y ortoim\'agenes de alta resoluci\'on (24 de agosto de 2025, 0.34~m)~\cite{{wayback}}, se delimit\'o el pol\'igono en UTM Zona 14N (\texttt{{EPSG:32614}}, Fig.~2). El centroide del cuerpo principal queda en {cen_dms} ({cen_utm[0]:,.1f}~E, {cen_utm[1]:,.1f}~N), a {ref['distancias_m']['mex_125']:.0f}~m al sureste de la carretera \texttt{{MEX-125}}, 1.79~km al noroeste de San Andr\'es Arrealco, {ref['distancias_m']['san_antonio_texcala']/1000:.2f}~km al estenoreste de San Antonio Texcala, {ref['distancias_m']['santa_maria_coapan']/1000:.2f}~km al suroeste de la iglesia de Santa Mar\'ia Coapan (18.4274$^\circ$~N, 97.4060$^\circ$~O~\cite{{gcatholic}}) y {ref['distancias_m']['tehuacan_centro']/1000:.2f}~km al suroeste del centro de Tehuac\'an.

El predio se asienta en el valle de Tehuac\'an, una depresi\'on tect\'onica limitada por fallas normales del sistema de la falla de Oaxaca, sobre dep\'ositos cenozoicos de la Formaci\'on Tehuac\'an con conglomerados y horizontes delgados de yeso~\cite{{davalos2007}}. Este marco geol\'ogico condiciona la interpretaci\'on geof\'isica: el yeso y las sales evapor\'iticas naturales tambi\'en reducen la resistividad el\'ectrica del subsuelo y pueden imitar al lixiviado. Seg\'un el Copernicus DEM GLO-30 (30~m)~\cite{{sentinel}}, el relleno est\'a encajonado en una cabecera de barranca entre {topo['elev_min_m']:,.1f} y {topo['elev_max_m']:,.1f}~m~s.n.m. ({topo['desnivel_interno_m']:.1f}~m de desnivel interno, pendiente media de {topo['pendiente_media_deg']:.1f}$^\circ$ y m\'axima de {topo['pendiente_max_deg']:.1f}$^\circ$), cerrada al oeste por un parteaguas (\(\sim\)1,830~m) y con escurrimiento superficial D8 dirigido hacia el este-noreste (azimut {topo['azimut_descenso_deg']:.1f}$^\circ$).

\begin{{figure*}}[t]
  \centering
  \includegraphics[width=\textwidth]{{../mapas_paper_ieee/ieee_fig2_delimitacion_local.pdf}}
  \caption{{Delimitaci\'on local del relleno sanitario de Santa Mar\'ia Coapan en \texttt{{EPSG:32614}}. (a) Contexto topogr\'afico (Copernicus DEM 30~m), red vial (\texttt{{MEX-125}}), localidades vecinas y rutas de drenaje D8 hacia el ENE. (b) Pol\'igonos sobre ortoimagen de alta resoluci\'on (24/08/2025, 0.34~m): cuerpo principal ({area_prin}~ha), huella total ({area_huella}~ha), n\'ucleo 2011 ({area_2011}~ha), \'area auxiliar SO ({area_aux}~ha), laguna de lixiviados NO ({area_lag}~m$^2$) y puntos de control PROFEPA. Elaboraci\'on propia con datos Esri~\cite{{wayback}} y ESA~\cite{{sentinel}}.}}
  \label{{fig:delimitacion}}
\end{{figure*}}

\begin{{figure}}[t]
  \centering
  \includegraphics[width=\columnwidth]{{../mapas_paper_ieee/ieee_fig3_evolucion_4fechas.pdf}}
  \caption{{Evoluci\'on multitemporal superficial del predio entre 1993 y 2025 con la huella actual superpuesta. (a) 15/02/1993 (Landsat-5, 30~m): terreno sin desmonte visible. (b) 06/06/2011 (0.50~m): n\'ucleo consolidado de {area_2011}~ha. (c) 18/11/2022 (0.31~m): oscurecimiento y cicatriz en cuadrante norte tras el incendio de mayo de 2022. (d) 24/08/2025 (0.34~m): cubierta mineral expuesta y laguna de lixiviados NO. Elaboraci\'on propia con acervos USGS~\cite{{landsat}} y Esri Wayback~\cite{{wayback}}.}}
  \label{{fig:evolucion}}
\end{{figure}}

El seguimiento multitemporal (1993--2025, Fig.~3) acota la apertura inicial entre febrero de 1993 y diciembre de 1994~\cite{{landsat}}, registra una expansi\'on de +{exp_ha}~ha (+{exp_pct}~\%) respecto al pol\'igono de 2011, identifica trincheras excavadas en el sector suroeste desde 2013 y documenta el incendio de mayo de 2022 ({fire['area_dnbr_ge_010_ha']:.2f}~ha con \(\text{{dNBR}} \ge 0.10\)). Una s\'intesis multisensor reciente sobre Sentinel-2 (03/11/2026) y radar SAR Sentinel-1 (19/11/2026)~\cite{{sentinel}} confirma que el {pct_sin_veg:.1f}~\% de la huella permanece como cubierta mineral o talud sin vegetaci\'on (NDVI mediano de {est['ndvi_mediana_relleno']:.3f} frente a {est['ndvi_mediana_testigo']:.3f} en el matorral testigo, retrodispersi\'on \(VV = {sar['epocas'][-1]['vv_relleno_db']:.2f}\)~dB con cambio \(\Delta VV = {sar['delta_vv_2021_2026_db']:.2f}\)~dB desde 2021) y conserva un estanque de lixiviados activo al noroeste ({area_lag}~m$^2$). El acu\'ifero regional m\'as probable es el Valle de Tehuac\'an (clave~2105), donde la CONAGUA reporta niveles est\'aticos regionales de 12 a m\'as de 110~m seg\'un la posici\'on en el pie de monte y valle~\cite{{conagua2013,conagua2105}}; la profundidad exacta bajo el predio falta y se medir\'a con piezómetros.

\section{{Objetivos}}
\subsection{{General}}
Delimitar espacialmente el relleno sanitario de Santa Mar\'ia Coapan y proponer un levantamiento geof\'isico integrado para cartografiar los residuos, la pluma de lixiviado y los posibles acumulos met\'alicos, verificando mediante simulaci\'on num\'erica qu\'e puede resolver el dise\~no planteado.

\subsection{{Espec\'ificos}}
\begin{{enumerate}}
\item Reunir y depurar la informaci\'on documental y geoespacial del caso, separando hechos medidos de afirmaciones no verificadas.
\item Delimitar el predio, su evoluci\'on superficial (1993--2026) y su red de drenaje D8 para georreferenciar el levantamiento.
\item Seleccionar los m\'etodos geof\'isicos id\'oneos para cada inc\'ognita y dise\~nar su adquisici\'on con extensi\'on \textit{{roll-along}}.
\item Simular num\'ericamente un perfil ERT 2.5D con ruido e inversi\'on independiente para cuantificar su poder de resoluci\'on y artefactos.
\item Establecer criterios de confirmaci\'on piezom\'etrica, un plan de acci\'on y un esquema de monitoreo peri\'odico.
\end{{enumerate}}

\section{{Justificaci\'on}}
La PROFEPA orden\'o un estudio del da\~no y un plan de remediaci\'on~\cite{{greenpeace,profepa2023}}, pero no existe un modelo del subsuelo que se\~nale d\'onde intervenir. Perforar a ciegas resulta costoso y puede atravesar zonas sin interceptar las rutas preferenciales de lixiviado. La combinaci\'on de m\'etodos el\'ectricos y electromagn\'eticos cubre todo el predio sin excavar, orienta la ubicaci\'on exacta de los sondeos y reduce la incertidumbre al operar dentro de la Reserva de la Biosfera Tehuac\'an--Cuicatl\'an~\cite{{conanp}}. Adicionalmente, dado que la operaci\'on se prolong\'o m\'as all\'a del horizonte original de 2010~\cite{{linares}}, aportar una l\'inea base f\'isica reproducible da sustento t\'ecnico com\'un a la comunidad, autoridades y responsables de la remediaci\'on.

\section{{M\'etodos geof\'isicos propuestos}}
La Tabla~II resume qu\'e pregunta atiende cada m\'etodo, su respuesta esperada en la literatura de rellenos sanitarios~\cite{{abdulrahman2016,rawfill}} y su limitaci\'on principal. La ERT act\'ua como m\'etodo eje por su sensibilidad directa a la conductividad i\'onica del agua intersticial. La IP comparte cableado y electrodos con bajo costo adicional, permitiendo discriminar zonas ricas en metales o grafito/carb\'on de simples fluidos salinos~\cite{{abdulrahman2016}}. El m\'etodo EM (FDEM) mapea r\'apidamente la extensi\'on lateral conductora para priorizar l\'ineas; la magnetometr\'ia localiza chatarra ferrosa y tambores; el GPR define espesores de cubierta seca; y los piez\'ometros aportan calibraci\'on hidroqu\'imica insustituible.

\begin{{table*}}[t]
\centering
\caption{{M\'etodos geof\'isicos propuestos, pregunta que responden y respuesta esperada}}
\label{{tab:metodos}}
\footnotesize
\begin{{tabular}}{{@{{}}p{{0.14\textwidth}}p{{0.24\textwidth}}p{{0.28\textwidth}}p{{0.28\textwidth}}@{{}}}}
\toprule
\textbf{{M\'etodo}} & \textbf{{Pregunta}} & \textbf{{Respuesta esperada}} & \textbf{{Limitaci\'on principal}} \\
\midrule
ERT & ?`D\'onde est\'an los residuos y el lixiviado, y a qu\'e profundidad? & Residuos: 0.5 a 30~$\Omega\cdot$m~\cite{{rawfill}}. Lixiviado: menos de 10~$\Omega\cdot$m~\cite{{abdulrahman2016}}. Fondo seco: decenas de $\Omega\cdot$m. & Las sales y yesos naturales tambi\'en bajan la resistividad; menor resoluci\'on en profundidad. \\
IP & ?`Qu\'e tipo de material genera la anomal\'ia conductora? & Residuos con metales: cargabilidad alta (\(>70\)~ms). Lixiviado disuelto: baja (\(<20\)~ms)~\cite{{abdulrahman2016}}. & Interferencia posible por carb\'on/ceniza pirog\'enica del incendio de 2022; mayor ruido que ERT. \\
EM (FDEM) & ?`Cu\'al es la extensi\'on lateral de la zona conductora? & Mapa de conductividad aparente con anomal\'ia alta sobre residuos y lixiviados someros. & Poca resoluci\'on vertical; muy sensible a cercas, tuber\'ias y chatarra superficial. \\
Magnetometr\'ia & ?`Hay tambores met\'alicos o chatarra enterrada? & Anomal\'ias dipolares intensas y locales sobre concentraciones ferromagn\'eticas. & El hierro dom\'estico (latas) genera ruido de fondo; alteraci\'on t\'ermica en zona quemada. \\
GPR & ?`Cu\'anto mide la cubierta y existen celdas o zanjas? & Reflectores someros de la interfase cubierta--residuo y paredes de celdas/trincheras. & Atenuaci\'on severa en arcillas, suelo h\'umedo o lixiviados muy conductores. \\
Piez\'ometros & ?`La anomal\'ia geof\'isica corresponde a contaminaci\'on real? & Nivel fre\'atico, conductividad el\'ectrica, iones mayores y metales pesados en agua y suelo. & Cobertura estrictamente puntual y mayor costo; sirven para calibrar y validar, no para mapear. \\
\bottomrule
\end{{tabular}}
\end{{table*}}

\section{{Dise\~no de adquisici\'on de datos}}
La Fig.~4 proyecta el levantamiento sobre el pol\'igono delimitado en \texttt{{EPSG:32614}}. Dado que el ancho del cuerpo principal alcanza 350--370~m, un tendido simple de 235~m no logra cubrir ambos contactos laterales con el terreno natural. Por ello se mantiene un espaciado interelectr\'odico de 5~m y se extienden los perfiles mediante t\'ecnica \textit{{roll-along}}: seis perfiles E--O ($L1$--$L6$, de 275 a 435~m, espaciados cada 55~m) y dos perfiles transversales N--S ($T1$ de 395~m y $T2$ de 355~m) que intersectan toda la malla para control de cruces, totalizando {total_ert_m:,}~m lineales de ERT/IP (Tabla~III y Tabla~IV). Los perfiles $L4$, $L5$ y $T1$ cruzan directamente la cicatriz del incendio de mayo de 2022 ({fire['area_dnbr_ge_010_ha']:.2f}~ha con \'indice diferencial normalizado de \'area quemada, \textit{{differenced Normalized Burn Ratio}}, \(\text{{dNBR}}\ge 0.10\)) y el borde de la laguna de lixiviados NO ({area_lag}~m$^2$), donde se medir\'a in situ conductividad el\'ectrica, pH y temperatura del fluido como cota inferior de resistividad.

\begin{{figure}}[t]
  \centering
  \includegraphics[width=\columnwidth]{{../mapas_paper_ieee/ieee_fig4_topografia_y_diseno_geofisico.pdf}}
  \caption{{Dise\~no de adquisici\'on geof\'isica y control topogr\'afico georreferenciado en \texttt{{EPSG:32614}}. Se integran las curvas de nivel cada 20~m (Copernicus DEM), las trayectorias de drenaje superficial D8 hacia el ENE (azimut {topo['azimut_descenso_deg']:.1f}$^\circ$), los perfiles ERT/IP E--O ($L1$--$L6$, 275--435~m con \textit{{roll-along}} cada 5~m), los transversales $T1$--$T2$, el perfil de fondo $R1$ aguas arriba al oeste, la malla EM/magnetom\'etrica (+50~m, 28.1~ha), la cicatriz del incendio de mayo de 2022 (\(\text{{dNBR}}\ge 0.10\)) y los piez\'ometros $P1$--$P4$. Elaboraci\'on propia.}}
  \label{{fig:diseno}}
\end{{figure}}

Con apoyo en las trayectorias D8, el perfil de fondo $R1$ (235~m, 48 electrodos) se sit\'ua aguas arriba al oeste sobre matorral intacto (\(\sim\)1,820~m~s.n.m.) para aislar la resistividad de las sales naturales sin influencia de lixiviado. An\'alogamente, los cuatro piez\'ometros quedan orientados seg\'un el gradiente ENE: $P1$ testigo aguas arriba y $P2$--$P4$ formando un tri\'angulo aguas abajo en las ca\~nadas de salida (Tabla~IV). La malla EM y magnetom\'etrica abarca 28.1~ha (\(609 \times 462\)~m), incorporando un margen de 50~m y el sector auxiliar suroeste donde hay trincheras visibles desde 2013. Para viabilizar la magnetometr\'ia en taludes de 12--28$^\circ$, se plantea una etapa regional cada 10~m (\(\sim\)28~km de caminata) con densificaci\'on a 5~m \'unicamente sobre el cuerpo principal y anomal\'ias EM. Se verificar\'a la resistencia de contacto de cada electrodo y se repetir\'an lecturas con discrepancia mayor a 3~\%. La campa\~na se estima en 15 a 18 d\'ias efectivos de campo (11--13 de ERT/IP con \textit{{roll-along}}, 3--4 de EM/magnetometr\'ia escalonada y 1 de GPR). Antes de hincar electrodos en la cicatriz quemada de 2022 es obligatorio realizar monitoreo de seguridad con detector multigas (\(\text{{CH}}_4\), \(\text{{CO}}\), \(\text{{H}}_2\text{{S}}\), \(\text{{O}}_2\)) y c\'amara t\'ermica port\'atil para descartar bolsas de gas o combusti\'on latente.

\begin{{table}}[t]
\centering
\caption{{Par\'ametros de adquisici\'on propuestos}}
\label{{tab:adquisicion}}
\footnotesize
\begin{{tabular}}{{@{{}}p{{0.24\columnwidth}}p{{0.70\columnwidth}}@{{}}}}
\toprule
\textbf{{Elemento}} & \textbf{{Par\'ametro propuesto}} \\
\midrule
ERT/IP & Electrodos cada 5~m, arreglo Wenner--Schlumberger. 6 perfiles E--O separados 55~m con \textit{{roll-along}} ($L1$--$L3$: 435~m, $L4$: 395~m, $L5$: 355~m, $L6$: 275~m), 2 transversales N--S ($T1$: 395~m, $T2$: 355~m) y fondo $R1$ (235~m). Total: {total_ert_m:,}~m. \\
Profundidad & \(\sim\)30~m en tendido base de 235~m (0.17~veces la apertura m\'axima~\cite{{edwards1977}}) y hasta \(\sim\)55--70~m en centro de l\'ineas \textit{{roll-along}} de 355--435~m. \\
IP & Dominio del tiempo sobre las mismas l\'ineas ERT; cruzar con mapa \(\text{{dNBR}}\) del incendio de 2022. \\
EM (FDEM) & Estaciones cada 10~m en l\'ineas cada 20~m sobre huella total, sector SO y margen de 50~m (28.1~ha). \\
Magnetometr\'ia & Etapa base en l\'ineas cada 10~m (lecturas 1~m) sobre 28.1~ha; detalle cada 5~m en cuerpo principal y anomal\'ias EM. \\
GPR & Tramos de 50 a 100~m sobre $L2$ y $L5$ (cubierta seca y bordes de celdas). \\
Piez\'ometros & 4 puntos ($P1$ aguas arriba; $P2$--$P4$ en tri\'angulo aguas abajo ENE): nivel est\'atico, CE, iones, metales y muestreo directo en laguna NO. \\
Posici\'on & GPS diferencial / RTK en electrodos y estaciones para topograf\'ia exacta de cada perfil. \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{table*}}[t]
\centering
\caption{{Coordenadas georreferenciadas clave del sitio y red de control (UTM Zona 14N, \texttt{{EPSG:32614}})}}
\label{{tab:coordenadas}}
\footnotesize
\begin{{tabular}}{{@{{}}p{{0.15\textwidth}}p{{0.35\textwidth}}rrp{{0.22\textwidth}}@{{}}}}
\toprule
\textbf{{Elemento}} & \textbf{{Funci\'on / Ubicaci\'on}} & \textbf{{Este (m)}} & \textbf{{Norte (m)}} & \textbf{{Cota (m s.n.m.) / Nota}} \\
\midrule
Centroide cuerpo & Centro geom\'etrico del cuerpo principal ({area_prin}~ha) & {cen_utm[0]:,.1f} & {cen_utm[1]:,.1f} & {topo['elev_media_m']:,.1f} (media huella) \\
PROFEPA-1 & V\'ertice oficial acceso SO ({p1['desc']}) & {p1['E']:,.1f} & {p1['N']:,.1f} & Control oficial acceso \\
PROFEPA-2 & V\'ertice oficial SSE ({p2['desc']}) & {p2['E']:,.1f} & {p2['N']:,.1f} & Control oficial sur \\
Laguna NO & Poza activa de lixiviados ({area_lag}~m$^2$) & {lag_utm[0]:,.1f} & {lag_utm[1]:,.1f} & Calibraci\'on CE/pH in situ \\
Perfil $R1$ & L\'inea testigo aguas arriba al oeste & {float(r1_row['inicio_o_pt_E_m']):,.1f} & {float(r1_row['inicio_o_pt_N_m']):,.0f}--{float(r1_row['fin_N_m']):,.0f} & 235~m (\(\sim\)1,820~m s.n.m.) \\
Piez\'ometro $P1$ & Testigo natural aguas arriba (O del camino) & {float(pz['P1']['inicio_o_pt_E_m']):,.1f} & {float(pz['P1']['inicio_o_pt_N_m']):,.1f} & {pz['P1']['electrodos_o_elev']} \\
Piez\'ometro $P2$ & Aguas abajo — salida ca\~nada principal NE & {float(pz['P2']['inicio_o_pt_E_m']):,.1f} & {float(pz['P2']['inicio_o_pt_N_m']):,.1f} & {pz['P2']['electrodos_o_elev']} \\
Piez\'ometro $P3$ & Aguas abajo — pie de talud E hacia tributario ENE & {float(pz['P3']['inicio_o_pt_E_m']):,.1f} & {float(pz['P3']['inicio_o_pt_N_m']):,.1f} & {pz['P3']['electrodos_o_elev']} \\
Piez\'ometro $P4$ & Aguas abajo — control distal ENE rumbo a Tehuac\'an & {float(pz['P4']['inicio_o_pt_E_m']):,.1f} & {float(pz['P4']['inicio_o_pt_N_m']):,.1f} & {pz['P4']['electrodos_o_elev']} \\
\bottomrule
\end{{tabular}}
\end{{table*}}

\section{{Procesamiento e interpretaci\'on esperada}}
\subsection{{Procesamiento}}
Los datos de ERT se filtrar\'an para remover lecturas ruidosas o con alta dispersi\'on rec\'iproca y se invertir\'an en 2D incorporando obligatoriamente la topograf\'ia medida en campo, dado el desnivel interno de {topo['desnivel_interno_m']:.1f}~m y pendientes de hasta {topo['pendiente_max_deg']:.1f}$^\circ$. Se reportar\'a el ajuste RMS y la matriz o l\'imite de sensibilidad para no sobreinterpretar zonas profundas sin cobertura~\cite{{loke1996}}, verificando posibles efectos 3D laterales en las l\'ineas marginales ($L5$--$L6$) encajonadas en la ca\~nada. La IP se invertir\'a de forma lineal tomando como base el modelo de resistividad. Los datos EM se interpolar\'an a mapas de conductividad aparente, mientras que la magnetometr\'ia recibir\'a correcci\'on por variaci\'on diurna antes de calcular la anomal\'ia de campo total.

\subsection{{Simulaci\'on sint\'etica}}
Para cuantificar qu\'e logra distinguir un tendido base antes de ir a campo, se desarroll\'o una simulaci\'on num\'erica 2.5D en vol\'umenes finitos (cuadratura de Fourier no negativa calibrada contra semiespacio homog\'eneo) e inversi\'on suavizada de tipo Loke--Barker~\cite{{loke1996}}. El modelo sint\'etico representa una cubierta seca (120~$\Omega\cdot$m), terreno natural (90~$\Omega\cdot$m), roca basal a m\'as de 28~m (300~$\Omega\cdot$m), un cuerpo de residuos entre 55 y 165~m y de 1.5 a 14~m de profundidad (30~$\Omega\cdot$m), una pluma de lixiviado subyacente hacia el este (115--205~m, 14--24~m de profundidad, 6~$\Omega\cdot$m) y una bolsa somera de lodos salinos de 20 por 4~m (8~$\Omega\cdot$m). Se calcularon {ert['n_mediciones']} mediciones Wenner--Schlumberger sobre 48 electrodos cada {ert['espaciado_m']:.0f}~m ({ert['longitud_m']:.0f}~m), se agreg\'o {ert['ruido_pct']:.0f}~\% de ruido gaussiano y se invirti\'o en una malla independiente (5~m frente a 2.5~m del modelo directo) con normalizaci\'on geom\'etrica por malla.

\subsection{{Lectura de la simulaci\'on}}
La inversi\'on convergi\'o a un RMS de {ert['rms_final_pct']:.1f}~\% y recuper\'o las estructuras mayores en su posici\'on horizontal correcta (Fig.~5 y Tabla~V). La mediana invertida en el cuerpo de residuos ({res_inv}~$\Omega\cdot$m) reproduce fielmente los {res_true}~$\Omega\cdot$m verdaderos y el borde de terreno natural recupera {nat_inv} contra {nat_true}~$\Omega\cdot$m. No obstante, emergen tres efectos f\'isicos esenciales para la interpretaci\'on de datos reales:
\begin{{itemize}}
\item El lixiviado se localiza en posici\'on correcta pero con resistividad sobreestimada ({lix_inv} contra {lix_true}~$\Omega\cdot$m) debido al suavizado de Tikhonov sobre contrastes agudos.
\item La anomal\'ia conductora se extiende hacia abajo: entre 26 y 35~m bajo el lixiviado el modelo invertido marca {deb_inv}~$\Omega\cdot$m donde el medio verdadero vale {deb_true}~$\Omega\cdot$m, por ca\'ida de sensibilidad bajo la pantalla conductora.
\item La bolsa somera de lodos de 20 por 4~m ({lod_inv} contra {lod_true}~$\Omega\cdot$m) se resuelve parcialmente integrada al techo del cuerpo de residuos y la roca basal ({roc_true}~$\Omega\cdot$m) queda atenuada ({roc_inv}~$\Omega\cdot$m) por canalizaci\'on de corriente el\'ectrica en el lixiviado superior.
\end{{itemize}}
La simulaci\'on modela un tendido simple de {ert['longitud_m']:.0f}~m; al aplicar el esquema \textit{{roll-along}} propuesto de 355--435~m en el campo, aumentar\'a la sensibilidad en el n\'ucleo hasta 55--70~m, aunque persistir\'an el suavizado de bordes y la posible interferencia en IP por carb\'on del incendio de 2022.

\begin{{figure}}[t]
  \centering
  \includegraphics[width=0.98\columnwidth]{{../mapas_paper_ieee/ieee_fig5_simulacion_ert.pdf}}
  \caption{{Simulaci\'on num\'erica 2.5D de un perfil ERT base de 48 electrodos ({ert['longitud_m']:.0f}~m). (a) Modelo verdadero sint\'etico. (b) Seudosecci\'on aparente simulada ({ert['n_mediciones']} datos Wenner--Schlumberger con {ert['ruido_pct']:.0f}~\% de ruido). (c) Modelo invertido en malla independiente (RMS = {ert['rms_final_pct']:.1f}~\%); los contornos punteados delimitan los cuerpos reales. Elaboraci\'on propia.}}
  \label{{fig:simulacion}}
\end{{figure}}

\begin{{table}}[t]
\centering
\caption{{Recuperaci\'on de los cuerpos en la simulaci\'on ERT 2.5D (mediana del modelo invertido)}}
\label{{tab:recuperacion}}
\footnotesize
\begin{{tabular}}{{@{{}}p{{0.48\columnwidth}}cc@{{}}}}
\toprule
\textbf{{Zona del modelo}} & \textbf{{Verdadero ($\Omega\cdot$m)}} & \textbf{{Invertido ($\Omega\cdot$m)}} \\
\midrule
Residuos (1.5--14~m) & {res_true} & {res_inv} \\
Lixiviado (14--24~m) & {lix_true} & {lix_inv} \\
Bolsa de lodos (3--7~m) & {lod_true} & {lod_inv} \\
Terreno natural, borde & {nat_true} & {nat_inv} \\
Debajo del lixiviado (26--35~m) & {deb_true} & {deb_inv} \\
Roca basal (> 28~m, centro) & {roc_true} & {roc_inv} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\subsection{{C\'omo se interpretar\'a con datos reales}}
Se adopta una regla operativa de tres condiciones: una zona se clasificar\'a como probable pluma de lixiviado \'unicamente si (1) exhibe resistividad menor al fondo medido en $R1$ (usando 10~$\Omega\cdot$m como referencia orientativa~\cite{{abdulrahman2016}} y ajust\'andola con la conductividad medida en la laguna NO), (2) muestra continuidad espacial en cruces de perfiles ortogonales $L$--$T$, y (3) coincide con conductividad el\'ectrica elevada en el piez\'ometro m\'as pr\'oximo. Las anomal\'ias de alta cargabilidad en IP se contrastar\'an con magnetometr\'ia y el mapa de severidad \(\text{{dNBR}}\) antes de atribuirse a metales, y ning\'un contraste geof\'isico se reportar\'a como contaminaci\'on comprobada sin respaldo hidroqu\'imico.

\section{{Impacto ambiental y plan de acci\'on}}
\subsection{{Impacto esperado}}
El an\'alisis separa lo comprobado de lo pendiente por medir. Consta documentalmente que el sitio fue clausurado por la autoridad ambiental y carece de estudio p\'ublico de remediaci\'on~\cite{{greenpeace,profepa2023}}. El modelo digital de elevaci\'on demuestra que el escurrimiento superficial D8 converge hacia el estenoreste (azimut {topo['azimut_descenso_deg']:.1f}$^\circ$) rumbo al valle de Tehuac\'an, lo que coloca en ruta preferencial de vigilancia el eje hacia Santa Mar\'ia Coapan (3.33~km al NE), mientras San Antonio Texcala (2.08~km al OSO) queda separado por el parteaguas occidental y San Andr\'es Arrealco (1.79~km al SE) permanece fuera del eje principal de escurrimiento. Con el levantamiento quedar\'a por comprobar la migraci\'on vertical hacia el acu\'ifero 2105, el alcance hacia el pol\'igono de la reserva y la presencia real de metales en suelo y agua.

\subsection{{Plan de acci\'on}}
\begin{{enumerate}}
\item \textbf{{Preparaci\'on y seguridad (semanas 1--2).}} Validar con RTK los v\'ertices de {area_prin}/{area_huella}~ha en campo, gestionar permisos con autoridades municipales, PROFEPA y comunidad, y ejecutar barrido t\'ermico y multigas en la cicatriz de 2022.
\item \textbf{{Adquisici\'on geof\'isica (semanas 3--5).}} Levantar la malla EM y magnetom\'etrica escalonada (28.1~ha), seguida de los {total_ert_m:,}~m de perfiles ERT/IP con \textit{{roll-along}} y los tramos GPR sobre $L2$ y $L5$.
\item \textbf{{Procesamiento e inversi\'on (semanas 6--7).}} Invertir ERT/IP con topograf\'ia real, mapear anomal\'ias EM/magn\'eticas y aplicar la regla de tres condiciones para fijar sitios \'optimos de perforaci\'on.
\item \textbf{{Confirmaci\'on directa (semanas 8--9).}} Perforar los cuatro piez\'ometros ($P1$--$P4$), medir nivel est\'atico real, conductividad, pH, iones mayores y metales pesados en agua, suelo y laguna NO.
\item \textbf{{Modelo conceptual 3D.}} Integrar espesores de residuos, geometr\'ia de la pluma y gradiente hidr\'aulico como base cuantitativa del estudio de da\~no ambiental requerido por la PROFEPA.
\item \textbf{{Remediaci\'on y monitoreo.}} Retirar residuos peligrosos y RPBI a sitios autorizados, construir cobertura impermeable y drenaje de lixiviados conforme a la NOM-083-SEMARNAT-2003~\cite{{nom083}}, y repetir anualmente los perfiles ERT de control~\cite{{helene2020}}.
\end{{enumerate}}

La comunidad nahua de Santa Mar\'ia Coapan debe participar de forma informada desde la planeaci\'on y recibir n\'itidamente los resultados t\'ecnicos por ser parte vecina y promovente del proceso legal; la responsabilidad ejecutiva de la remediaci\'on recae en la autoridad municipal de Tehuac\'an conforme a la resoluci\'on vigente~\cite{{greenpeace,profepa2023}}.

\section{{Conclusiones}}
\begin{{itemize}}
\item El relleno sanitario de Santa Mar\'ia Coapan representa un pasivo ambiental real en Puebla con clausura definitiva ordenada y ausencia p\'ublica de caracterizaci\'on del subsuelo.
\item La integraci\'on secuencial de EM y magnetometr\'ia escalonada sobre 28.1~ha con 3,315~m de perfiles ERT/IP \textit{{roll-along}}, tramos GPR y piez\'ometros en tri\'angulo ENE responde simult\'aneamente geometr\'ia de residuos, extensi\'on conductora y riesgo de chatarra o metales.
\item La simulaci\'on num\'erica 2.5D con inversi\'on independiente (RMS = {ert['rms_final_pct']:.1f}~\%) demuestra que un tendido base recupera fielmente el cuerpo de residuos ({res_inv} frente a {res_true}~$\Omega\cdot$m) y ubica el lixiviado, aunque sobrestima su resistividad ({lix_inv} contra {lix_true}~$\Omega\cdot$m) y lo difumina hacia abajo, limitaci\'on que los tendidos \textit{{roll-along}} de 355--435~m ayudan a mitigar.
\item Debido a la presencia regional de yesos y sales evapor\'iticas de la Formaci\'on Tehuac\'an, son indispensables el perfil testigo $R1$ aguas arriba, el muestreo directo en la laguna NO y la validaci\'on qu\'imica en $P1$--$P4$.
\item Aunque el estudio no cuenta a\'un con mediciones geof\'isicas de campo, la ubicaci\'on precisa ({cen_dms}), la delimitaci\'on multiescala ({area_prin}~ha principales y {area_huella}~ha totales), la cronolog\'ia satelital (1993--2025), la cicatriz de incendio de 2022 ({fire['area_dnbr_ge_010_ha']:.2f}~ha) y el drenaje D8 hacia el ENE quedaron plenamente documentados en \texttt{{EPSG:32614}}, dejando el dise\~no listo para su ejecuci\'on directa en campo.
\end{{itemize}}

\begin{{thebibliography}}{{99}}
\bibitem{{greenpeace}} Greenpeace M\'exico, ``Crisis ambiental y de derechos humanos en Tehuac\'an, Puebla: Greenpeace y comunidad nahua de Santa Mar\'ia Coapan protestan por basurero t\'oxico y su falta de remediaci\'on,'' comunicado de prensa. Disponible: \url{{https://www.greenpeace.org/mexico/}}
\bibitem{{linares}} A.~Linares D\'ector, ``El relleno sanitario de Tehuac\'an, Puebla: un estudio sociol\'ogico de la crisis del manejo de residuos, 2015--2022,'' tesis, Benem\'erita Univ. Aut\'onoma de Puebla. Disponible: \url{{https://repositorioinstitucional.buap.mx/}}
\bibitem{{incendio}} ``Incendio borra pruebas de que basurero en Coapan opera como tiradero t\'oxico: Comit\'e de Bienes,'' \textit{{El Ciudadano}}, 13 de mayo de 2022. Disponible: \url{{https://www.elciudadano.com/}}
\bibitem{{publimetro}} ``Cierre definitivo: relleno sanitario de Tehuac\'an es clausurado despu\'es de 25 a\~nos,'' \textit{{Publimetro}}, 13 de junio de 2022. Disponible: \url{{https://www.publimetro.com.mx/puebla/}}
\bibitem{{desinformemonos}} Comunicado ``Protesta ante PROFEPA: basureros de Tehuac\'an y Cholula,'' \textit{{Desinform\'emonos}}, 17 de julio de 2024. Disponible: \url{{https://desinformemonos.org/}}
\bibitem{{gcatholic}} GCatholic.org, ``Iglesia Santa Mar\'ia de la Asunci\'on, Santa Mar\'ia Coapan, Puebla,'' Plus Code 76C4CHGV+XJ. Disponible: \url{{https://gcatholic.org/churches/mexico/66183}}
\bibitem{{davalos2007}} O.~G.~D\'avalos-\'Alvarez, \'A.~F.~Nieto-Samaniego, S.~A.~Alaniz-\'Alvarez, E.~Mart\'inez-Hern\'andez y E.~Ram\'irez-Arriaga, ``Estratigraf\'ia cenozoica de la regi\'on de Tehuac\'an y su relaci\'on con el sector norte de la falla de Oaxaca,'' \textit{{Rev. Mex. Cienc. Geol.}}, vol.~24, n.\textsuperscript{{o}}~2, pp.~197--215, 2007.
\bibitem{{conagua2013}} Comisi\'on Nacional del Agua, ``Acuerdo por el que se actualiza la disponibilidad media anual de agua en acu\'iferos, incluido el Valle de Tehuac\'an (clave 2105),'' \textit{{Diario Oficial de la Federaci\'on}}, 5 de diciembre de 2013.
\bibitem{{abdulrahman2016}} A.~Abdulrahman \textit{{et al.}}, ``Characterization of active and closed landfill sites using 2D resistivity/IP imaging: case studies in Penang, Malaysia,'' \textit{{Environ. Earth Sci.}}, vol.~75, art.~347, 2016, doi:10.1007/s12665-015-5003-5.
\bibitem{{maurya2017}} P.~K.~Maurya \textit{{et al.}}, ``Detailed landfill leachate plume mapping using 2D and 3D electrical resistivity tomography with correlation to ionic strength measured in screens,'' \textit{{J. Appl. Geophys.}}, vol.~138, pp.~1--8, 2017.
\bibitem{{helene2020}} L.~P.~I.~Helene, C.~A.~Moreira y R.~C.~Bovi, ``Identification of leachate infiltration and its flow pathway in landfill by means of electrical resistivity tomography (ERT),'' \textit{{Environ. Monit. Assess.}}, vol.~192, 2020, doi:10.1007/s10661-020-8206-5.
\bibitem{{rawfill}} RAWFILL, ``SWOT analysis of geophysical methods for landfill characterisation,'' Interreg NWE, informe t\'ecnico. Disponible: \url{{https://vb.nweurope.eu/}}
\bibitem{{edwards1977}} L.~S.~Edwards, ``A modified pseudosection for resistivity and IP,'' \textit{{Geophysics}}, vol.~42, n.\textsuperscript{{o}}~5, pp.~1020--1036, 1977.
\bibitem{{loke1996}} M.~H.~Loke y R.~D.~Barker, ``Rapid least-squares inversion of apparent resistivity pseudosections using a quasi-Newton method,'' \textit{{Geophys. Prospect.}}, vol.~44, n.\textsuperscript{{o}}~1, pp.~131--152, 1996.
\bibitem{{nom083}} Secretar\'ia de Medio Ambiente y Recursos Naturales, ``NOM-083-SEMARNAT-2003: Especificaciones de protecci\'on ambiental para la selecci\'on del sitio, dise\~no, construcci\'on, operaci\'on, monitoreo, clausura y obras complementarias de un sitio de disposici\'on final de residuos s\'olidos urbanos y de manejo especial,'' \textit{{Diario Oficial de la Federaci\'on}}, 2004.
\bibitem{{ne}} Natural Earth, ``Admin 1 -- States, Provinces,'' conjunto de datos vectoriales, dominio p\'ublico. Disponible: \url{{https://www.naturalearthdata.com/}}
\bibitem{{mexgeojson}} PhantomInsights, ``mexico-geojson: l\'imites municipales de M\'exico (2020),'' repositorio de GitHub. Disponible: \url{{https://github.com/PhantomInsights/mexico-geojson}}
\bibitem{{conanp}} CONANP, ``Acuerdo por el que se da a conocer el Resumen del Programa de Manejo de la Reserva de la Biosfera Tehuac\'an-Cuicatl\'an,'' \textit{{Diario Oficial de la Federaci\'on}}, M\'exico (Subzona de Aprovechamiento Especial, 16.46439~ha en relleno sanitario de Tehuac\'an).
\bibitem{{conagua2105}} Comisi\'on Nacional del Agua, ``Actualizaci\'on de la disponibilidad media anual de agua en el acu\'ifero Valle de Tehuac\'an (2105), Estado de Puebla,'' Subdirecci\'on General T\'ecnica, CONAGUA, M\'exico.
\bibitem{{profepa2023}} PROFEPA, Resoluci\'on Administrativa PFPA/03.2/2C27.1/0036/23/0059 (Expediente PFPA/3.2/2C.27.1/00036-20), clausura total y definitiva del sitio de disposici\'on final en Santa Mar\'ia Coapan, 27 de junio de 2023.
\bibitem{{landsat}} U.S. Geological Survey, ``Landsat Collection 2 Level-2 Surface Reflectance (LT04, LT05, LC08, Path 025/Row 047),'' USGS / Microsoft Planetary Computer STAC, 1989--2015.
\bibitem{{sentinel}} European Space Agency, ``Copernicus Sentinel-2 L2A (T14QPF), Sentinel-1 RTC y Copernicus DEM GLO-30,'' ESA / Microsoft Planetary Computer STAC, 2020--2026.
\bibitem{{wayback}} Esri, ``World Imagery Wayback Archive (capturas 2011--2025 verificadas v\'ia SRC\_DATE2),'' Esri, Redlands, CA, 2025.
\end{{thebibliography}}

\end{{document}}
"""
    return tex


def build_html(metrics, ert, design_rows):
    poly = metrics["poligonos"]
    ref = metrics["referencias"]
    fire = metrics["incendio_mayo_2022"]
    est = metrics["estado_actual_2026_11_03"]
    sar = metrics["sar_sentinel1_rel70"]
    topo = metrics["topografia_hidrologia"]["stats"]
    km = metrics["ml_kmeans_k5"]

    area_prin = f"{poly['cuerpo_principal']['area_ha']:.2f}"
    area_huella = f"{poly['huella_total']['area_ha']:.2f}"
    area_2011 = f"{poly['nucleo_2011']['area_ha']:.2f}"
    area_aux = f"{poly['area_auxiliar_so']['area_ha']:.2f}"
    area_lag = f"{poly['laguna_lixiviados_no']['area_m2']:.0f}"
    exp_ha = f"{poly['expansion_2011_2025_ha']:.2f}"
    exp_pct = f"{poly['expansion_2011_2025_pct']:.1f}"
    cen_utm = poly["cuerpo_principal"]["centroide_utm"]
    cen_dms = poly["cuerpo_principal"]["centroide_dms"]
    lag_utm = poly["laguna_lixiviados_no"]["centroide_utm"]
    p1 = ref["profepa"][0]
    p2 = ref["profepa"][1]
    pct_sin_veg = km[0]["pct_en_huella"] + km[1]["pct_en_huella"]
    total_ert_m = sum(int(float(r["longitud_m"])) for r in design_rows if r["tipo"].startswith("ERT"))

    rec = {r["zona"]: r for r in ert["tabla_recuperacion"]}
    res_true = rec["Residuos (1.5–14 m)"]["verdadero_ohm_m"]
    res_inv = rec["Residuos (1.5–14 m)"]["invertido_ohm_m"]
    lix_true = rec["Lixiviado (14–24 m)"]["verdadero_ohm_m"]
    lix_inv = rec["Lixiviado (14–24 m)"]["invertido_ohm_m"]
    lod_true = rec["Bolsa de lodos (3–7 m)"]["verdadero_ohm_m"]
    lod_inv = rec["Bolsa de lodos (3–7 m)"]["invertido_ohm_m"]
    nat_true = rec["Terreno natural, borde"]["verdadero_ohm_m"]
    nat_inv = rec["Terreno natural, borde"]["invertido_ohm_m"]
    deb_true = rec["Debajo del lixiviado (26–35 m)"]["verdadero_ohm_m"]
    deb_inv = rec["Debajo del lixiviado (26–35 m)"]["invertido_ohm_m"]
    roc_true = rec["Roca basal (> 28 m, centro)"]["verdadero_ohm_m"]
    roc_inv = rec["Roca basal (> 28 m, centro)"]["invertido_ohm_m"]

    pz = {r["elemento"]: r for r in design_rows if r["elemento"].startswith("P")}
    r1_row = [r for r in design_rows if r["elemento"] == "R1"][0]

    rec_rows_html = "\n".join(
        f"<tr><td>{html.escape(r['zona'])}</td><td class='num'>{r['verdadero_ohm_m']}</td><td class='num'>{r['invertido_ohm_m']}</td></tr>"
        for r in ert["tabla_recuperacion"]
    )

    f1_uri = fig_uri("ieee_fig1_localizacion_regional.png")
    f2_uri = fig_uri("ieee_fig2_delimitacion_local.png")
    f3_uri = fig_uri("ieee_fig3_evolucion_4fechas.png")
    f4_uri = fig_uri("ieee_fig4_topografia_y_diseno_geofisico.png")
    f5_uri = fig_uri("ieee_fig5_simulacion_ert.png")

    doc_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Caracterización geofísica propuesta del relleno sanitario de Santa María Coapan (Tehuacán, Puebla)</title>
<style>
  @page {{
    size: letter;
    margin: 0.62in 0.58in 0.64in 0.58in;
    @bottom-center {{
      content: counter(page);
      font-family: "Liberation Serif", "Times New Roman", serif;
      font-size: 8.5pt;
      color: #111;
    }}
  }}
  body {{
    font-family: "Liberation Serif", "Times New Roman", serif;
    font-size: 9.2pt;
    line-height: 1.24;
    color: #111;
    margin: 0;
    padding: 0;
  }}
  .header-block {{
    text-align: center;
    margin-bottom: 10pt;
    border-bottom: 0.6pt solid #999;
    padding-bottom: 7pt;
  }}
  h1.paper-title {{
    font-size: 16.5pt;
    font-weight: bold;
    line-height: 1.15;
    margin: 0 0 7pt 0;
    color: #000;
  }}
  .authors {{
    font-size: 10pt;
    margin: 0 0 2pt 0;
  }}
  .affil {{
    font-size: 8.8pt;
    font-style: italic;
    color: #222;
    margin: 0;
  }}
  .two-cols {{
    columns: 2;
    column-gap: 0.22in;
    text-align: justify;
    hyphens: auto;
  }}
  .abstract {{
    font-size: 8.8pt;
    line-height: 1.22;
    margin: 0 0 6pt 0;
    text-align: justify;
  }}
  .abstract b, .keywords b {{
    font-style: italic;
  }}
  .keywords {{
    font-size: 8.5pt;
    line-height: 1.2;
    margin: 0 0 9pt 0;
    text-align: justify;
  }}
  h2.sec {{
    font-size: 9.8pt;
    font-weight: normal;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin: 9pt 0 4pt 0;
    break-after: avoid;
    page-break-after: avoid;
    font-variant: small-caps;
    border-bottom: 0.4pt solid #ccc;
    padding-bottom: 1.5pt;
  }}
  h3.subsec {{
    font-size: 9.2pt;
    font-style: italic;
    font-weight: bold;
    margin: 6pt 0 2.5pt 0;
    break-after: avoid;
    page-break-after: avoid;
    text-align: left;
  }}
  p {{
    margin: 0 0 4.5pt 0;
    text-indent: 1em;
  }}
  p.noindent {{
    text-indent: 0;
  }}
  ol.tight, ul.tight {{
    margin: 3pt 0 5pt 0;
    padding-left: 14pt;
  }}
  ol.tight li, ul.tight li {{
    margin-bottom: 2.5pt;
  }}
  .span-all {{
    column-span: all;
    margin: 6pt 0 7pt 0;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .fig-single {{
    margin: 6pt 0 7pt 0;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .fig-box img {{
    display: block;
    margin: 0 auto;
    max-width: 100%;
    height: auto;
  }}
  .span-all img {{
    width: 100%;
    max-height: 3.10in;
    object-fit: contain;
  }}
  .fig-single img {{
    width: 99%;
    max-height: 4.65in;
    object-fit: contain;
  }}
  .caption {{
    font-size: 8.1pt;
    line-height: 1.18;
    text-align: justify;
    margin-top: 3pt;
    color: #111;
  }}
  .table-wrap {{
    margin: 6pt 0 7pt 0;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .table-title {{
    font-size: 8.0pt;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.3pt;
    margin: 0 0 3pt 0;
    font-weight: bold;
  }}
  .table-title span.tnum {{
    display: block;
    font-size: 7.8pt;
    margin-bottom: 1pt;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 7.8pt;
    line-height: 1.16;
    text-align: left;
  }}
  thead tr {{
    border-top: 1.1pt solid #111;
    border-bottom: 0.7pt solid #111;
  }}
  tbody tr:last-child {{
    border-bottom: 1.1pt solid #111;
  }}
  th, td {{
    padding: 2.6pt 4.2pt;
    vertical-align: top;
  }}
  td.num, th.num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }}
  .refs {{
    font-size: 7.8pt;
    line-height: 1.16;
    text-align: justify;
  }}
  .refs p {{
    text-indent: -16pt;
    padding-left: 16pt;
    margin: 0 0 2.8pt 0;
    overflow-wrap: anywhere;
  }}
  code.epsg {{
    font-family: "Liberation Mono", monospace;
    font-size: 8.3pt;
  }}
</style>
</head>
<body>

<div class="header-block">
  <h1 class="paper-title">Caracterización geofísica propuesta del relleno sanitario de Santa María Coapan (Tehuacán, Puebla): delimitación espacial, diseño de campo e interpretación esperada</h1>
  <div class="authors">Ian A. Sandoval-Valderrábano &nbsp;&nbsp;&nbsp;&nbsp; Carlos Enrique Fernández Tepale</div>
  <div class="affil">Facultad de Ingeniería, Benemérita Universidad Autónoma de Puebla, Puebla, México</div>
</div>

<div class="two-cols">

  <div class="abstract">
    <b>Resumen—</b> El relleno sanitario de Tehuacán, en la junta auxiliar de Santa María Coapan (Puebla), operó cerca de tres décadas. La comunidad y la organización Greenpeace afirman que recibió residuos peligrosos industriales y biológico-infecciosos. La PROFEPA ordenó su clausura total y definitiva el 27 de junio de 2023 y pidió un estudio del daño ambiental y un plan de remediación. Hasta donde se encontró en fuentes públicas, ese estudio no se ha presentado. Este trabajo propone cómo usar métodos geofísicos para responder tres preguntas que hoy no tienen respuesta medida: dónde están los residuos, hasta dónde llegó el lixiviado y si hay zonas con material metálico enterrado. Se diseña un levantamiento georreferenciado con tomografía de resistividad eléctrica (ERT) y polarización inducida (IP), electromagnético en el dominio de frecuencia (EM), magnetometría y radar de penetración terrestre (GPR), con piezómetros para confirmar. Para mostrar qué se espera ver, se simuló en 2.5D un perfil sintético de ERT ({ert['n_mediciones']} mediciones Wenner–Schlumberger, {ert['ruido_pct']:.0f} % de ruido). La inversión ajustó con RMS de {ert['rms_final_pct']:.1f} %, recuperó bien el cuerpo de residuos ({res_inv} contra {res_true} Ω·m del modelo) y ubicó el lixiviado, aunque lo suavizó y mostró más resistivo ({lix_inv} contra {lix_true} Ω·m) extendiéndolo en profundidad. No hay mediciones geofísicas de campo: todo resultado del subsuelo es una predicción. En cambio, la ubicación real, las dimensiones ({area_prin} ha de cuerpo principal y {area_huella} ha de huella operativa total en {html.escape(cen_dms)}) y la evolución superficial (1993–2025) sí se delimitaron mediante imágenes satelitales históricas y un modelo digital de elevación para georreferenciar el diseño propuesto.
  </div>

  <div class="keywords">
    <b>Palabras clave—</b> geofísica ambiental, relleno sanitario, lixiviado, tomografía de resistividad eléctrica, polarización inducida, percepción remota, Tehuacán.
  </div>

  <h2 class="sec">I. Introducción</h2>
  <p class="noindent">Un relleno sanitario bien diseñado aísla los residuos del suelo y del agua subterránea. Un tiradero sin control no lo hace: el agua de lluvia atraviesa los residuos y forma lixiviado, un líquido con sales, materia orgánica y, a veces, metales. Si ese líquido llega al acuífero, la contaminación se mueve bajo tierra sin que se vea en la superficie.</p>
  <p>La geofísica ayuda en este problema porque el lixiviado conduce muy bien la electricidad. Por eso baja la resistividad del terreno, y la ERT puede dibujarlo desde la superficie sin excavar [10], [11]. La polarización inducida (IP) agrega información sobre el tipo de material, por ejemplo, residuos con metales [9].</p>
  <p>El caso elegido es el relleno sanitario municipal de Tehuacán, en territorio de Santa María Coapan, Puebla. Es un problema ambiental real, tiene una resolución oficial de clausura y, según fuentes públicas, sigue sin estudio de daño ni remediación [1], [20]. Este informe no presenta mediciones geofísicas de campo; propone un proyecto de diseño respaldado por una delimitación satelital y topográfica real en <code class="epsg">EPSG:32614</code> y muestra con una simulación numérica qué se espera resolver y qué no.</p>

  <h2 class="sec">II. Problemática a resolver</h2>
  <h3 class="subsec">A. Qué pasó</h3>
  <p class="noindent">La Tabla I resume la historia del sitio. Las fuentes documentales no coinciden en el año de inicio (1993 o 1995), así que se reportan ambas fechas acotadas además por escenas Landsat históricas.</p>

  <div class="table-wrap">
    <div class="table-title"><span class="tnum">Tabla I</span>Cronología del relleno sanitario de Tehuacán</div>
    <table>
      <thead>
        <tr><th style="width:24%">Fecha</th><th>Hecho (fuente)</th></tr>
      </thead>
      <tbody>
        <tr><td>1993–1995</td><td>Inicio de operación: 1993 [1]; junio de 1995, con 15 años de vida útil estimada [2]. Escenas Landsat muestran terreno intacto en feb. 1993 y obra abierta en dic. 1994 [21].</td></tr>
        <tr><td>2010</td><td>Año en que, según el proyecto original, debía dejar de operar [2].</td></tr>
        <tr><td>Oct. 2021</td><td>La comunidad lo cierra de hecho (7 de octubre) [1].</td></tr>
        <tr><td>Mayo 2022</td><td>Incendio en el sitio (iniciado entre el 5 y 8 de mayo según Sentinel-2; cicatriz de {fire['area_dnbr_ge_010_ha']:.2f} ha). El Comité de Bienes afirma que borra evidencia [3], [22].</td></tr>
        <tr><td>Jun. 2022</td><td>La SMADSOT coloca sellos de clausura (nota del 13 de junio) [4].</td></tr>
        <tr><td>27 jun. 2023</td><td>Resolución de la PROFEPA (Exp. PFPA/3.2/2C.27.1/00036-20): clausura total y definitiva; retirar residuos peligrosos y RPBI, estudiar el daño y presentar un plan de remediación [1], [20].</td></tr>
      </tbody>
    </table>
  </div>

  <h3 class="subsec">B. Qué se dice y qué está comprobado</h3>
  <p class="noindent">Hay que separar los hechos documentados de las afirmaciones. La clausura de la PROFEPA y las fechas son documentadas [1], [20]. En cambio, lo siguiente son afirmaciones de la comunidad y de organizaciones, y este trabajo no las verifica: que se depositaron lodos industriales de lavanderías de mezclilla y residuos hospitalarios [1], [3], que se acumularon 3.7 millones de toneladas [1], que el sitio creció 18 ha dentro de la Reserva de la Biosfera Tehuacán-Cuicatlán [3], que hay filtración de lixiviados a la reserva y que hay casos de cáncer [3], [5].</p>
  <p>Ninguna de esas cifras de volumen o salud viene de un estudio técnico independiente. En cambio, la evolución superficial sí puede medirse con imágenes satelitales: en junio de 2011 el núcleo consolidado medía {area_2011} ha (acorde con las 6–7.2 ha autorizadas para el periodo original), en agosto de 2025 el cuerpo principal alcanzó {area_prin} ha (~10 ha citadas en la tesis de Linares [2]) y la huella total perturbada suma {area_huella} ha al incluir un área auxiliar suroeste ({area_aux} ha) y 0.24 ha de franjas perimetrales de acceso y maniobra [23]. La diferencia respecto a las 16.46 ha asignadas por la CONANP [18] corresponde a franjas periféricas dentro de la subzona administrativa.</p>

  <h3 class="subsec">C. Pregunta que se quiere responder</h3>
  <p class="noindent">¿Dónde están los residuos y el lixiviado en el subsuelo, hasta qué profundidad llegan y hacia dónde se mueven? Sin esa respuesta física medida no es posible diseñar una remediación acorde con la resolución de la PROFEPA.</p>

  <div class="span-all fig-box">
    <img src="{f1_uri}" alt="Figura 1. Localización regional">
    <div class="caption"><b>Fig. 1.</b> Localización regional del caso de estudio. (a) República Mexicana y estado de Puebla. (b) Municipios de Puebla; en rojo, Tehuacán. (c) Valle de Tehuacán, carretera federal MEX-125, iglesia de Santa María Coapan [6] y ubicación del relleno sanitario. Elaboración propia con límites vectoriales abiertos [16], [17].</div>
  </div>

  <h2 class="sec">III. Localización</h2>
  <p class="noindent">Santa María Coapan es una junta auxiliar del municipio de Tehuacán, en el sureste del estado de Puebla (Fig. 1). El relleno se ubica junto al km 12.2 de la carretera federal Tehuacán–Huajuapan (<code class="epsg">MEX-125</code>) [2], dentro de la subzona de aprovechamiento especial de la Reserva de la Biosfera Tehuacán–Cuicatlán [4], [18]. A partir de dos coordenadas oficiales de inspección de la PROFEPA ({html.escape(p1['desc'])} en el acceso suroeste y {html.escape(p2['desc'])} al sur-sureste) y ortoimágenes de alta resolución (24 de agosto de 2025, 0.34 m) [23], se delimitó el predio en coordenadas UTM Zona 14N (<code class="epsg">EPSG:32614</code>, Fig. 2). El centroide del cuerpo principal queda en {html.escape(cen_dms)} ({cen_utm[0]:,.1f} E, {cen_utm[1]:,.1f} N), a {ref['distancias_m']['mex_125']:.0f} m al sureste de la carretera <code class="epsg">MEX-125</code>, 1.79 km al noroeste de San Andrés Arrealco, {ref['distancias_m']['san_antonio_texcala']/1000:.2f} km al estenoreste de San Antonio Texcala, {ref['distancias_m']['santa_maria_coapan']/1000:.2f} km al suroeste de la iglesia de Santa María Coapan (18.4274° N, 97.4060° O [6]) y {ref['distancias_m']['tehuacan_centro']/1000:.2f} km al suroeste del centro de Tehuacán.</p>
  <p>El sitio está en el valle de Tehuacán, una depresión tectónica limitada por fallas normales del sistema de la falla de Oaxaca, sobre depósitos cenozoicos de la Formación Tehuacán con conglomerados y capas delgadas de yeso [7]. Esto importa para la interpretación: el yeso y otras sales naturales también bajan la resistividad y pueden parecerse al lixiviado. Según el Copernicus DEM GLO-30 (30 m) [22], el relleno está encajonado en una cabecera entre {topo['elev_min_m']:,.1f} y {topo['elev_max_m']:,.1f} m s.n.m. ({topo['desnivel_interno_m']:.1f} m de desnivel interno, pendiente media de {topo['pendiente_media_deg']:.1f}° y máxima de {topo['pendiente_max_deg']:.1f}°), limitada al oeste por un parteaguas (~1,830 m) y con drenaje superficial D8 hacia el este-noreste (azimut {topo['azimut_descenso_deg']:.1f}°).</p>

  <div class="span-all fig-box">
    <img src="{f2_uri}" alt="Figura 2. Delimitación local">
    <div class="caption"><b>Fig. 2.</b> Localización local y delimitación del relleno sanitario de Santa María Coapan en UTM Zona 14N (<code class="epsg">EPSG:32614</code>). (a) Relieve (Copernicus DEM 30 m), carretera federal MEX-125, localidades cercanas y rutas de escurrimiento D8 hacia el ENE. (b) Delimitación sobre ortoimagen de alta resolución (24/08/2025, 0.34 m): cuerpo principal ({area_prin} ha), huella operativa total ({area_huella} ha), núcleo 2011 ({area_2011} ha), área auxiliar SO ({area_aux} ha), laguna de lixiviados NO ({area_lag} m²) y puntos de inspección PROFEPA. Elaboración propia con datos Esri Wayback [23] y ESA [22].</div>
  </div>

  <p>El análisis multitemporal (1993–2025, Fig. 3) acota el desmonte inicial entre febrero de 1993 y diciembre de 1994 [21], muestra una expansión de +{exp_ha} ha (+{exp_pct} %) posterior a 2010 y revela trincheras en el sector suroeste desde 2013. Una síntesis multisensor de noviembre de 2026 sobre Sentinel-2 (03/11/2026) y SAR Sentinel-1 (19/11/2026) [22] confirma que el {pct_sin_veg:.1f} % de la huella permanece como cubierta mineral o suelo desnudo sin vegetación (NDVI mediano de {est['ndvi_mediana_relleno']:.3f} frente a {est['ndvi_mediana_testigo']:.3f} en matorral testigo; retrodispersión VV = {sar['epocas'][-1]['vv_relleno_db']:.2f} dB con cambio ΔVV = {sar['delta_vv_2021_2026_db']:.2f} dB desde octubre de 2021) y conserva una poza activa de lixiviados en el borde noroeste ({area_lag} m²). El acuífero regional más probable es el Valle de Tehuacán (clave 2105), donde la CONAGUA reporta niveles estáticos entre 12 y más de 110 m según la posición en el valle [8], [19]; la profundidad exacta del nivel del agua bajo el sitio falta y se medirá en los piezómetros.</p>

  <div class="fig-single fig-box">
    <img src="{f3_uri}" alt="Figura 3. Evolución 1993-2025">
    <div class="caption"><b>Fig. 3.</b> Evolución superficial del sitio entre 1993 y 2025 con la huella actual superpuesta. (a) 15/02/1993 (Landsat-5, 30 m): terreno sin desmonte visible. (b) 06/06/2011 (0.50 m): núcleo de {area_2011} ha tras concluir la vida útil original. (c) 18/11/2022 (0.31 m): cicatriz oscura tras el incendio de mayo de 2022. (d) 24/08/2025 (0.34 m): cubierta mineral sin vegetación y laguna de lixiviados NO. Elaboración propia con datos USGS Landsat C2 L2 [21] y Esri World Imagery Wayback [23].</div>
  </div>

  <h2 class="sec">IV. Objetivos</h2>
  <h3 class="subsec">A. General</h3>
  <p class="noindent">Delimitar espacialmente el relleno sanitario de Santa María Coapan y proponer un levantamiento geofísico integrado para delimitar los residuos y el lixiviado, mostrando con una simulación qué se puede resolver con ese diseño.</p>

  <h3 class="subsec">B. Específicos</h3>
  <ol class="tight">
    <li>Reunir y ordenar la información pública del caso, separando hechos de afirmaciones.</li>
    <li>Delimitar geoespacialmente el predio, su evolución superficial (1993–2026) y su red de escurrimiento D8 en <code class="epsg">EPSG:32614</code>.</li>
    <li>Elegir los métodos geofísicos adecuados para cada pregunta y diseñar la adquisición con extensión <i>roll-along</i>.</li>
    <li>Simular en 2.5D un perfil de ERT para estimar qué tan bien se recuperarían el cuerpo de residuos y el lixiviado.</li>
    <li>Proponer cómo confirmar las anomalías con piezómetros, definir un plan de acción y plantear monitoreo anual.</li>
  </ol>

  <h2 class="sec">V. Justificación</h2>
  <p class="noindent">La PROFEPA ordenó un estudio del daño y un plan de remediación [1], [20], pero no hay un mapa del subsuelo que diga dónde actuar. Perforar sin guía es caro y puede pasar de largo el lixiviado. Los métodos eléctricos y electromagnéticos cubren el predio completo en pocos días, no abren el terreno y orientan dónde conviene perforar. Además, el sitio está en una subzona de aprovechamiento especial de la Reserva de la Biosfera Tehuacán–Cuicatlán [4], [18], así que saber si el lixiviado avanza hacia el área protegida tiene valor ambiental directo. Por último, el relleno debía cerrar en 2010 y siguió operando [2]; documentar el daño con datos físicos da una base técnica común a la comunidad, a las autoridades y a quien ejecute la remediación.</p>

  <h2 class="sec">VI. Métodos geofísicos propuestos</h2>
  <p class="noindent">La Tabla II resume qué método responde qué pregunta. Los valores de resistividad y cargabilidad son de otros rellenos [9], [12]; en Coapan pueden ser distintos. La ERT es el método central porque la resistividad responde directo a la salinidad del agua en el terreno. La IP se mide con los mismos equipos y electrodos, así que su costo extra es bajo. El EM cubre rápido todo el predio y decide dónde priorizar anomalías. La magnetometría se agrega por la sospecha de residuos industriales metálicos. El GPR se usa solo en tramos cortos. Ningún método basta solo, y por eso se proponen varios junto con confirmación hidroquímica directa.</p>

  <div class="span-all table-wrap">
    <div class="table-title"><span class="tnum">Tabla II</span>Métodos geofísicos propuestos, pregunta que responden y respuesta esperada</div>
    <table>
      <thead>
        <tr><th style="width:13%">Método</th><th style="width:24%">Pregunta</th><th style="width:31%">Respuesta esperada</th><th style="width:32%">Limitación principal</th></tr>
      </thead>
      <tbody>
        <tr><td><b>ERT</b></td><td>¿Dónde están los residuos y el lixiviado, y a qué profundidad?</td><td>Residuos: 0.5 a 30 Ω·m [12]. Lixiviado: menos de 10 Ω·m [9]. Fondo seco: decenas de Ω·m.</td><td>Las sales naturales también bajan la resistividad. Resolución disminuye con la profundidad.</td></tr>
        <tr><td><b>IP</b></td><td>¿Qué tipo de material genera la anomalía?</td><td>Residuos con metales: cargabilidad alta (&gt; 70 ms en un caso). Lixiviado disuelto: baja (&lt; 20 ms) [9].</td><td>Posible ambigüedad por carbón y cenizas del incendio de 2022; ruido mayor que en ERT.</td></tr>
        <tr><td><b>EM (FDEM)</b></td><td>¿Cuál es la extensión lateral de la zona conductora?</td><td>Mapa de conductividad aparente; anomalía alta sobre residuos y lixiviado somero.</td><td>Poca resolución en profundidad; muy sensible a cercas metálicas y objetos superficiales.</td></tr>
        <tr><td><b>Magnetometría</b></td><td>¿Hay tambores metálicos o chatarra enterrada?</td><td>Anomalías dipolares locales e intensas sobre concentraciones metálicas.</td><td>Las latas y el hierro de residuos urbanos dan ruido de fondo; alteración térmica en área quemada.</td></tr>
        <tr><td><b>GPR</b></td><td>¿Cuánto mide la cubierta y hay celdas o zanjas?</td><td>Reflectores someros de la cubierta y bordes de celdas o trincheras.</td><td>Se atenúa muy rápido en suelo húmedo, arcilloso o con lixiviado conductor.</td></tr>
        <tr><td><b>Piezómetros y muestras</b></td><td>¿La anomalía geofísica es contaminación real?</td><td>Nivel del agua, conductividad eléctrica, iones y metales pesados en agua y suelo.</td><td>Cobertura puntual y mayor costo; sirven para calibrar y confirmar, no para mapear.</td></tr>
      </tbody>
    </table>
  </div>

  <h2 class="sec">VII. Diseño de adquisición de datos</h2>
  <p class="noindent">La Fig. 4 proyecta el levantamiento sobre el polígono real en <code class="epsg">EPSG:32614</code>. Como el ancho del cuerpo principal alcanza 350–370 m, un tendido fijo de 235 m no cubre ambos bordes naturales. Por ello se mantiene el espaciado de electrodos de 5 m y se amplían las líneas mediante extensión <i>roll-along</i>: seis perfiles E–O (<i>L1–L6</i>, 275 a 435 m, separados 55 m) y dos transversales N–S (<i>T1</i> de 395 m y <i>T2</i> de 355 m) que se cruzan para control de consistencia, sumando {total_ert_m:,} m de ERT/IP (Tabla III y Tabla IV). Los perfiles <i>L4</i>, <i>L5</i> y <i>T1</i> atraviesan además la zona quemada en mayo de 2022 ({fire['area_dnbr_ge_010_ha']:.2f} ha con índice diferencial normalizado de área quemada, <i>differenced Normalized Burn Ratio</i>, dNBR ≥ 0.10) y el borde del estanque de lixiviados noroeste ({area_lag} m²), donde se tomará conductividad eléctrica, pH y temperatura directa del líquido superficial como referencia física.</p>
  <p>Con base en el modelo de flujo superficial D8, el perfil de fondo <i>R1</i> (235 m, 48 electrodos) se sitúa aguas arriba al oeste sobre matorral intacto (~1,820 m s.n.m.), evitando contaminación por escorrentía para aislar la resistividad natural de las sales y yesos del terreno. Los piezómetros quedan orientados por el gradiente topográfico hacia el ENE: <i>P1</i> testigo aguas arriba al oeste y <i>P2–P4</i> formando un triángulo aguas abajo en las cañadas de descarga (Tabla IV). La malla EM y magnetométrica (28.1 ha, 609 × 462 m) cubre toda la huella más 50 m de margen, incluyendo el sector auxiliar suroeste con trincheras históricas. Para hacer viable la magnetometría en laderas de 12–28°, se plantea una etapa base con líneas cada 10 m en toda la malla y detalle cada 5 m solo sobre el cuerpo principal y anomalías EM.</p>

  <p>Se debe medir la resistencia de contacto de cada electrodo y repetir mediciones con error mayor a 3 %. El levantamiento se estima en 15–18 días de campo (11–13 de ERT/IP con <i>roll-along</i>, 3–4 de EM/magnetometría escalonada y 1 de GPR). Por el incendio de mayo de 2022 y los residuos peligrosos, es obligatorio inspeccionar previamente con detector multigas (CH₄, CO, H₂S, O₂) y cámara térmica portátil antes de hincar electrodos.</p>

  <div class="fig-single fig-box">
    <img src="{f4_uri}" alt="Figura 4. Diseño geofísico y control topográfico">
    <div class="caption"><b>Fig. 4.</b> Diseño de adquisición geofísica y control topográfico georreferenciado en <code class="epsg">EPSG:32614</code>. Se integran curvas de nivel cada 20 m (Copernicus DEM), drenaje superficial D8 hacia el ENE (azimut {topo['azimut_descenso_deg']:.1f}°), perfiles ERT/IP E–O (<i>L1–L6</i>, 275–435 m con <i>roll-along</i> cada 5 m), transversales <i>T1–T2</i>, perfil de fondo <i>R1</i> aguas arriba al oeste, malla EM/magnetométrica (+50 m, 28.1 ha), cicatriz del incendio de mayo de 2022 (dNBR ≥ 0.10) y piezómetros <i>P1–P4</i>. Elaboración propia.</div>
  </div>

  <div class="table-wrap">
    <div class="table-title"><span class="tnum">Tabla III</span>Parámetros de adquisición propuestos</div>
    <table>
      <thead>
        <tr><th style="width:26%">Elemento</th><th>Parámetro propuesto</th></tr>
      </thead>
      <tbody>
        <tr><td><b>ERT/IP</b></td><td>Electrodos cada 5 m, arreglo Wenner–Schlumberger. 6 perfiles E–O separados 55 m con <i>roll-along</i> (<i>L1–L3</i>: 435 m, <i>L4</i>: 395 m, <i>L5</i>: 355 m, <i>L6</i>: 275 m), 2 transversales N–S (<i>T1</i>: 395 m, <i>T2</i>: 355 m) y fondo <i>R1</i> (235 m). Total: {total_ert_m:,} m.</td></tr>
        <tr><td><b>Profundidad</b></td><td>~30 m en tendido base de 235 m (0.17 veces la apertura máxima [13]) y hasta ~55–70 m en el centro de líneas <i>roll-along</i> de 355–435 m.</td></tr>
        <tr><td><b>IP</b></td><td>Dominio del tiempo en las mismas líneas ERT; interpretar junto con dNBR para no confundir carbón/cenizas con chatarra.</td></tr>
        <tr><td><b>EM (FDEM)</b></td><td>Estaciones cada 10 m en líneas cada 20 m sobre la huella total, sector auxiliar SO y 50 m de amortiguamiento (28.1 ha).</td></tr>
        <tr><td><b>Magnetometría</b></td><td>Malla regional con líneas cada 10 m (lecturas 1 m) en 28.1 ha, y relleno cada 5 m sobre el cuerpo principal y anomalías EM.</td></tr>
        <tr><td><b>GPR</b></td><td>Tramos de 50 a 100 m sobre <i>L2</i> y <i>L5</i> (cubierta seca y bordes de celdas).</td></tr>
        <tr><td><b>Piezómetros</b></td><td>4 puntos (<i>P1</i> testigo aguas arriba; <i>P2–P4</i> en triángulo aguas abajo hacia el ENE según flujo D8); nivel del agua, CE, iones y metales, más muestreo directo en laguna NO.</td></tr>
        <tr><td><b>Posición</b></td><td>GPS diferencial / RTK en electrodos y estaciones con levantamiento topográfico completo para inversión 2D con topografía.</td></tr>
      </tbody>
    </table>
  </div>

  <h2 class="sec">VIII. Procesamiento e interpretación esperada</h2>
  <h3 class="subsec">A. Procesamiento</h3>
  <p class="noindent">Los datos de ERT se editarán para eliminar mediciones ruidosas y se invertirán en 2D incluyendo obligatoriamente la topografía real medida a lo largo de cada perfil (desnivel interno de {topo['desnivel_interno_m']:.1f} m y taludes de hasta {topo['pendiente_max_deg']:.1f}°), con criterio de suavidad. Se reportará el ajuste (RMS) y la zona que los datos sí alcanzan a resolver para no interpretar fuera de ella [14], evaluando además posibles artefactos 3D laterales en las líneas cercanas a la barranca (<i>L5–L6</i>). La IP se invertirá de forma lineal sobre el modelo de resistividad. El EM se interpolará a un mapa de conductividad aparente, y la magnetometría se corregirá por variación diurna antes de obtener la anomalía de campo total.</p>

  <h3 class="subsec">B. Simulación sintética</h3>
  <p class="noindent">Para evaluar la respuesta esperada, se implementó un código propio de modelado directo en 2.5D por volúmenes finitos (cuadratura de Fourier no negativa calibrada contra semiespacio homogéneo) acoplado a una inversión suavizada de tipo Loke–Barker [14]. El modelo sintético utiliza valores de literatura: cubierta seca (120 Ω·m), terreno natural (90 Ω·m), roca basal a más de 28 m (300 Ω·m), un cuerpo de residuos entre 55 y 165 m de distancia y 1.5 a 14 m de profundidad (30 Ω·m), una pluma de lixiviado subyacente hacia el este (115–205 m, 14–24 m, 6 Ω·m) y una bolsa somera de lodos salinos de 20 por 4 m (8 Ω·m). Se calcularon {ert['n_mediciones']} mediciones con el arreglo {html.escape(ert['arreglo'])} sobre {ert['n_electrodos']} electrodos cada {ert['espaciado_m']:.0f} m ({ert['longitud_m']:.0f} m), se les agregó {ert['ruido_pct']:.0f} % de ruido gaussiano y se invirtieron sobre una malla independiente (dx = 5 m frente a 2.5 m de la malla directa) para no favorecer el ajuste.</p>

  <div class="span-all table-wrap">
    <div class="table-title"><span class="tnum">Tabla IV</span>Coordenadas georreferenciadas clave del sitio y red de control (UTM Zona 14N, <code class="epsg">EPSG:32614</code>)</div>
    <table>
      <thead>
        <tr><th style="width:14%">Elemento</th><th style="width:37%">Función / Ubicación</th><th class="num" style="width:11%">Este (m)</th><th class="num" style="width:18%">Norte (m)</th><th style="width:20%">Cota (m s.n.m.) / Nota</th></tr>
      </thead>
      <tbody>
        <tr><td>Centroide cuerpo</td><td>Centro geométrico del cuerpo principal ({area_prin} ha)</td><td class="num">{cen_utm[0]:,.1f}</td><td class="num">{cen_utm[1]:,.1f}</td><td>{topo['elev_media_m']:,.1f} (media huella)</td></tr>
        <tr><td>PROFEPA-1</td><td>Acceso SO ({html.escape(p1['desc'])})</td><td class="num">{p1['E']:,.1f}</td><td class="num">{p1['N']:,.1f}</td><td>Referencia oficial</td></tr>
        <tr><td>PROFEPA-2</td><td>Control SSE ({html.escape(p2['desc'])})</td><td class="num">{p2['E']:,.1f}</td><td class="num">{p2['N']:,.1f}</td><td>Referencia oficial</td></tr>
        <tr><td>Laguna NO</td><td>Poza activa de lixiviados ({area_lag} m²)</td><td class="num">{lag_utm[0]:,.1f}</td><td class="num">{lag_utm[1]:,.1f}</td><td>Calibración CE/pH in situ</td></tr>
        <tr><td>Perfil <i>R1</i></td><td>Fondo testigo aguas arriba (O)</td><td class="num">{float(r1_row['inicio_o_pt_E_m']):,.1f}</td><td class="num">{float(r1_row['inicio_o_pt_N_m']):,.0f}–{float(r1_row['fin_N_m']):,.0f}</td><td>235 m (~1,820 m s.n.m.)</td></tr>
        <tr><td><i>P1</i></td><td>Piezómetro testigo aguas arriba (O del camino)</td><td class="num">{float(pz['P1']['inicio_o_pt_E_m']):,.1f}</td><td class="num">{float(pz['P1']['inicio_o_pt_N_m']):,.1f}</td><td>{html.escape(pz['P1']['electrodos_o_elev'])}</td></tr>
        <tr><td><i>P2</i></td><td>Aguas abajo — salida cañada principal NE</td><td class="num">{float(pz['P2']['inicio_o_pt_E_m']):,.1f}</td><td class="num">{float(pz['P2']['inicio_o_pt_N_m']):,.1f}</td><td>{html.escape(pz['P2']['electrodos_o_elev'])}</td></tr>
        <tr><td><i>P3</i></td><td>Aguas abajo — pie de talud E hacia tributario ENE</td><td class="num">{float(pz['P3']['inicio_o_pt_E_m']):,.1f}</td><td class="num">{float(pz['P3']['inicio_o_pt_N_m']):,.1f}</td><td>{html.escape(pz['P3']['electrodos_o_elev'])}</td></tr>
        <tr><td><i>P4</i></td><td>Aguas abajo — control distal ENE rumbo a Tehuacán</td><td class="num">{float(pz['P4']['inicio_o_pt_E_m']):,.1f}</td><td class="num">{float(pz['P4']['inicio_o_pt_N_m']):,.1f}</td><td>{html.escape(pz['P4']['electrodos_o_elev'])}</td></tr>
      </tbody>
    </table>
  </div>

  <div class="fig-single fig-box">
    <img src="{f5_uri}" alt="Figura 5. Simulación sintética ERT">
    <div class="caption"><b>Fig. 5.</b> Simulación numérica 2.5D de un perfil ERT base de 48 electrodos ({ert['longitud_m']:.0f} m). (a) Modelo verdadero sintético. (b) Seudosección de resistividad aparente simulada con {ert['ruido_pct']:.0f} % de ruido ({ert['n_mediciones']} datos Wenner–Schlumberger). (c) Modelo invertido en malla independiente (RMS = {ert['rms_final_pct']:.1f} %); los contornos punteados marcan los cuerpos del modelo verdadero. Elaboración propia.</div>
  </div>

  <div class="table-wrap">
    <div class="table-title"><span class="tnum">Tabla V</span>Recuperación de los cuerpos en la simulación (mediana del modelo invertido)</div>
    <table>
      <thead>
        <tr><th>Zona del modelo</th><th class="num">Verdadero (Ω·m)</th><th class="num">Invertido (Ω·m)</th></tr>
      </thead>
      <tbody>
        {rec_rows_html}
      </tbody>
    </table>
  </div>

  <h3 class="subsec">C. Lectura de la simulación</h3>
  <p class="noindent">La inversión ajustó los datos con un RMS de {ert['rms_final_pct']:.1f} % y recuperó adecuadamente las anomalías principales (Fig. 5, Tabla V). El cuerpo de residuos quedó en su posición y muy próximo al valor verdadero ({res_inv} contra {res_true} Ω·m), al igual que el terreno natural en borde ({nat_inv} contra {nat_true} Ω·m). Sin embargo, el lixiviado muestra tres limitaciones físicas que deben considerarse al leer perfiles reales:</p>
  <ul class="tight">
    <li>La resistividad recuperada resulta mayor ({lix_inv} contra {lix_true} Ω·m), porque la regularización suaviza los contrastes bruscos.</li>
    <li>La zona conductora se prolonga hacia abajo: entre 26 y 35 m el modelo invertido arroja {deb_inv} Ω·m donde el medio vale {deb_true} Ω·m; un lixiviado real no debe declararse profundo solo por ese borde de baja sensibilidad.</li>
    <li>La bolsa de lodos (20 × 4 m, {lod_inv} contra {lod_true} Ω·m) aparece parcialmente diluida dentro de la masa de residuos y la roca basal ({roc_true} Ω·m) resulta atenuada ({roc_inv} Ω·m) por canalización de corriente en el conductor superior.</li>
  </ul>
  <p>Esta simulación representa un tendido simple de {ert['longitud_m']:.0f} m; con la extensión <i>roll-along</i> a 355–435 m propuesta para la zona central, aumentará la sensibilidad en profundidad (~55–70 m), aunque persistirán el suavizado de contrastes y la necesidad de cruzar IP con el mapa dNBR del incendio de 2022.</p>

  <h3 class="subsec">D. Cómo se interpretará con datos reales</h3>
  <p class="noindent">Se propone una regla operativa de tres condiciones: una anomalía se designará probable lixiviado únicamente si (1) presenta resistividad inferior al valor de fondo medido en <i>R1</i> (con 10 Ω·m como guía [9], calibrada contra la conductividad medida en la laguna NO), (2) muestra continuidad espacial en cruces de perfiles <i>L–T</i>, y (3) coincide con una conductividad eléctrica elevada en el piezómetro cercano. Los cuerpos de alta cargabilidad en IP se contrastarán con magnetometría y la cicatriz dNBR antes de asociarse a metales; ninguna anomalía se presentará como contaminación comprobada sin validación hidroquímica.</p>

  <h2 class="sec">IX. Impacto ambiental y plan de acción</h2>
  <h3 class="subsec">A. Impacto esperado</h3>
  <p class="noindent">El impacto se divide entre lo documentado y lo que resta comprobar en campo. Consta oficialmente que el relleno fue clausurado y que no se ha hecho público el estudio de remediación exigido [1], [20]. El análisis D8 muestra que el escurrimiento superficial converge hacia el ENE (azimut {topo['azimut_descenso_deg']:.1f}°), rumbo al valle de Tehuacán, por lo que la vigilancia hidrológica prioritaria corresponde a ese eje en dirección general hacia Santa María Coapan (3.33 km al NE), mientras San Antonio Texcala (2.08 km al OSO) queda separado por el parteaguas occidental y San Andrés Arrealco (1.79 km al SE) se sitúa fuera del eje principal. Queda por verificar si existe migración hacia el acuífero 2105, alcance hacia la reserva o presencia de metales en suelo y agua.</p>

  <h3 class="subsec">B. Plan de acción</h3>
  <ol class="tight">
    <li><b>Preparación y seguridad (semanas 1–2).</b> Validar con RTK en campo los vértices delimitados ({area_prin}/{area_huella} ha), gestionar permisos municipales y comunitarios y ejecutar inspección térmica y multigas sobre la cicatriz de 2022.</li>
    <li><b>Adquisición geofísica (semanas 3–5).</b> Medir la malla EM y magnetométrica escalonada (28.1 ha), seguida de los {total_ert_m:,} m de perfiles ERT/IP con <i>roll-along</i> y tramos GPR (Tabla III).</li>
    <li><b>Procesamiento (semanas 6–7).</b> Invertir con topografía real, mapear anomalías y aplicar la regla de tres condiciones para seleccionar los puntos de perforación.</li>
    <li><b>Confirmación directa (semanas 8–9).</b> Perforar piezómetros <i>P1–P4</i>, medir nivel del agua y tomar muestras de agua, suelo y laguna NO (CE, pH, iones mayores y metales) para contrastarlas con las secciones invertidas.</li>
    <li><b>Modelo conceptual y riesgo.</b> Integrar todo en un modelo 3D (volumen de residuos, geometría del lixiviado y dirección del flujo) como base técnica del estudio de daño requerido por la PROFEPA.</li>
    <li><b>Remediación y monitoreo.</b> Retirar residuos peligrosos y RPBI a sitios autorizados, construir cobertura final y drenaje conforme a la NOM-083-SEMARNAT-2003 [15] y repetir anualmente la ERT en las mismas líneas de control [11].</li>
  </ol>
  <p>La comunidad nahua de Santa María Coapan debe participar desde la planeación y recibir los resultados íntegros, por habitar junto al sitio y haber promovido su defensa legal; la responsabilidad de ejecutar la remediación corresponde al gobierno municipal de Tehuacán conforme a la resolución vigente [1], [20].</p>

  <h2 class="sec">X. Conclusiones</h2>
  <ul class="tight">
    <li>El relleno sanitario de Santa María Coapan es un caso ambiental real en Puebla con clausura definitiva ordenada y sin estudio público del daño ni caracterización del subsuelo.</li>
    <li>Una combinación georreferenciada de EM y magnetometría escalonada (28.1 ha), {total_ert_m:,} m de ERT/IP <i>roll-along</i>, GPR y cuatro piezómetros permite delimitar residuos, rutas de lixiviado y chatarra enterrada; la ERT actúa como método central.</li>
    <li>La simulación 2.5D en malla independiente (RMS = {ert['rms_final_pct']:.1f} %) muestra que un tendido base recupera bien la geometría y resistividad de los residuos ({res_inv} contra {res_true} Ω·m), aunque sobreestima la resistividad del lixiviado ({lix_inv} contra {lix_true} Ω·m) y lo suaviza hacia abajo, limitación parcialmente compensada mediante extensión <i>roll-along</i> a 355–435 m.</li>
    <li>Las sales y yesos naturales del valle de Tehuacán pueden imitar la firma del lixiviado; por ello son indispensables el perfil testigo <i>R1</i> aguas arriba al oeste, la medición in situ en la laguna NO y el muestreo en <i>P1–P4</i>.</li>
    <li>Aunque este trabajo no cuenta aún con mediciones geofísicas de campo, la ubicación real ({html.escape(cen_dms)}), la delimitación multiescala ({area_prin} ha principales y {area_huella} ha totales), la evolución satelital (1993–2025), la cicatriz de incendio ({fire['area_dnbr_ge_010_ha']:.2f} ha) y el escurrimiento D8 hacia el ENE quedaron documentados en <code class="epsg">EPSG:32614</code>, dejando el levantamiento listo para ejecutarse sin etapa exploratoria ciega.</li>
  </ul>

  <h2 class="sec">Referencias</h2>
  <div class="refs">
    <p>[1] Greenpeace México, “Crisis ambiental y de derechos humanos en Tehuacán, Puebla: Greenpeace y comunidad nahua de Santa María Coapan protestan por basurero tóxico y su falta de remediación,” comunicado de prensa. Disponible: https://www.greenpeace.org/mexico/</p>
    <p>[2] A. Linares Déctor, “El relleno sanitario de Tehuacán, Puebla: un estudio sociológico de la crisis del manejo de residuos, 2015–2022,” tesis, Benemérita Univ. Autónoma de Puebla. Disponible: https://repositorioinstitucional.buap.mx/</p>
    <p>[3] “Incendio borra pruebas de que basurero en Coapan opera como tiradero tóxico: Comité de Bienes,” <i>El Ciudadano</i>, 13 de mayo de 2022. Disponible: https://www.elciudadano.com/</p>
    <p>[4] “Cierre definitivo: relleno sanitario de Tehuacán es clausurado después de 25 años,” <i>Publimetro</i>, 13 de junio de 2022. Disponible: https://www.publimetro.com.mx/puebla/</p>
    <p>[5] Comunicado “Protesta ante PROFEPA: basureros de Tehuacán y Cholula,” <i>Desinformémonos</i>, 17 de julio de 2024. Disponible: https://desinformemonos.org/</p>
    <p>[6] GCatholic.org, “Iglesia Santa María de la Asunción, Santa María Coapan, Puebla,” Plus Code 76C4CHGV+XJ. Disponible: https://gcatholic.org/churches/mexico/66183</p>
    <p>[7] O. G. Dávalos-Álvarez, Á. F. Nieto-Samaniego, S. A. Alaniz-Álvarez, E. Martínez-Hernández y E. Ramírez-Arriaga, “Estratigrafía cenozoica de la región de Tehuacán y su relación con el sector norte de la falla de Oaxaca,” <i>Rev. Mex. Cienc. Geol.</i>, vol. 24, n.º 2, pp. 197–215, 2007.</p>
    <p>[8] Comisión Nacional del Agua, “Acuerdo por el que se actualiza la disponibilidad media anual de agua en acuíferos, incluido el Valle de Tehuacán (clave 2105),” <i>Diario Oficial de la Federación</i>, 5 de diciembre de 2013.</p>
    <p>[9] A. Abdulrahman et al., “Characterization of active and closed landfill sites using 2D resistivity/IP imaging: case studies in Penang, Malaysia,” <i>Environ. Earth Sci.</i>, vol. 75, art. 347, 2016, doi:10.1007/s12665-015-5003-5.</p>
    <p>[10] P. K. Maurya et al., “Detailed landfill leachate plume mapping using 2D and 3D electrical resistivity tomography with correlation to ionic strength measured in screens,” <i>J. Appl. Geophys.</i>, vol. 138, pp. 1–8, 2017.</p>
    <p>[11] L. P. I. Helene, C. A. Moreira y R. C. Bovi, “Identification of leachate infiltration and its flow pathway in landfill by means of electrical resistivity tomography (ERT),” <i>Environ. Monit. Assess.</i>, vol. 192, 2020, doi:10.1007/s10661-020-8206-5.</p>
    <p>[12] RAWFILL, “SWOT analysis of geophysical methods for landfill characterisation,” Interreg NWE, informe técnico. Disponible: https://vb.nweurope.eu/</p>
    <p>[13] L. S. Edwards, “A modified pseudosection for resistivity and IP,” <i>Geophysics</i>, vol. 42, n.º 5, pp. 1020–1036, 1977.</p>
    <p>[14] M. H. Loke y R. D. Barker, “Rapid least-squares inversion of apparent resistivity pseudosections using a quasi-Newton method,” <i>Geophys. Prospect.</i>, vol. 44, n.º 1, pp. 131–152, 1996.</p>
    <p>[15] Secretaría de Medio Ambiente y Recursos Naturales, “NOM-083-SEMARNAT-2003: Especificaciones de protección ambiental para la selección del sitio, diseño, construcción, operación, monitoreo, clausura y obras complementarias de un sitio de disposición final de residuos sólidos urbanos y de manejo especial,” <i>Diario Oficial de la Federación</i>, 2004.</p>
    <p>[16] Natural Earth, “Admin 1 – States, Provinces,” conjunto de datos vectoriales, dominio público. Disponible: https://www.naturalearthdata.com/</p>
    <p>[17] PhantomInsights, “mexico-geojson: límites municipales de México (2020),” repositorio de GitHub. Disponible: https://github.com/PhantomInsights/mexico-geojson</p>
    <p>[18] CONANP, “Acuerdo por el que se da a conocer el Resumen del Programa de Manejo de la Reserva de la Biosfera Tehuacán-Cuicatlán,” <i>Diario Oficial de la Federación</i>, México (Subzona de Aprovechamiento Especial, 16.46439 ha en relleno sanitario de Tehuacán).</p>
    <p>[19] Comisión Nacional del Agua, “Actualización de la disponibilidad media anual de agua en el acuífero Valle de Tehuacán (2105), Estado de Puebla,” Subdirección General Técnica, CONAGUA, México.</p>
    <p>[20] PROFEPA, Resolución Administrativa PFPA/03.2/2C27.1/0036/23/0059 (Expediente PFPA/3.2/2C.27.1/00036-20), clausura total y definitiva del sitio de disposición final en Santa María Coapan, 27 de junio de 2023.</p>
    <p>[21] U.S. Geological Survey, “Landsat Collection 2 Level-2 Surface Reflectance (LT04, LT05, LC08, Path 025/Row 047),” USGS / Microsoft Planetary Computer STAC, 1989–2015.</p>
    <p>[22] European Space Agency, “Copernicus Sentinel-2 L2A (T14QPF), Sentinel-1 RTC y Copernicus DEM GLO-30,” ESA / Microsoft Planetary Computer STAC, 2020–2026.</p>
    <p>[23] Esri, “World Imagery Wayback Archive (capturas 2011–2025 verificadas vía SRC_DATE2),” Esri, Redlands, CA, 2025.</p>
  </div>

</div>
</body>
</html>
"""
    return doc_html


OVERLEAF_TEMPLATE_ZIP = (
    "/home/carlos-enrique/.gemini/antigravity/brain/"
    "0718c26b-a9a9-403a-b2a6-2f391648d814/.user_uploaded/"
    "media_1795324950266_03be042c.zip"
)


def build_overleaf_zip():
    """Actualiza el proyecto LaTeX para Overleaf con las correcciones editoriales y figuras vigentes."""
    src_zip = OVERLEAF_TEMPLATE_ZIP
    fallback_zip = os.path.join(OUT_DIR, "Caracterizacion_Coapan_IEEE_overleaf.zip")
    if not os.path.exists(src_zip) and os.path.exists(fallback_zip):
        src_zip = fallback_zip
    if not os.path.exists(src_zip):
        print(f"Aviso: plantilla Overleaf no encontrada en {src_zip}; se omite actualización de Overleaf.")
        return None

    with zipfile.ZipFile(src_zip, "r") as zsrc:
        main_tex = zsrc.read("main.tex")
        hyph_tex = zsrc.read("hyph_es.tex")
        cuerpo = zsrc.read("cuerpo.tex").decode("utf-8")

    replacements = [
        (
            "la huella total perturbada suma 12.15\\,ha al incluir un área auxiliar suroeste (2.11\\,ha) \\cite{esri}.",
            "la huella total perturbada suma 12.15\\,ha al incluir un área auxiliar suroeste (2.11\\,ha) y 0.24\\,ha de franjas perimetrales de acceso y maniobra \\cite{esri}.",
        ),
        ("97\\textdegree25$'$41.8$''$W", "97\\textdegree25$'$41.8$''$O"),
        ("97\\textdegree25$'$30.03$''$W", "97\\textdegree25$'$30.03$''$O"),
        (
            "(2.92\\,ha con dNBR $\\geq$ 0.10)",
            "(2.92\\,ha con índice diferencial normalizado de área quemada, \\emph{differenced Normalized Burn Ratio}, dNBR $\\geq$ 0.10)",
        ),
        ("(dNBR $\\geq$ 0.12)", "(dNBR $\\geq$ 0.10)"),
        ("reemplaza el esquema local previo y ", ""),
    ]
    for old, new in replacements:
        cuerpo = cuerpo.replace(old, new)

    # Verificar que no queden inconsistencias pendientes en cuerpo.tex
    for forbidden in ("0.12", "$''$W", "esquema local previo"):
        assert forbidden not in cuerpo, f"Cadena no esperada en cuerpo.tex: {forbidden}"

    fig_map = {
        "figs/f1_localizacion.png": os.path.join(FIG_DIR, "ieee_fig1_localizacion_regional.png"),
        "figs/f2_delimitacion.png": os.path.join(FIG_DIR, "ieee_fig2_delimitacion_local.png"),
        "figs/f3_evolucion.png": os.path.join(FIG_DIR, "ieee_fig3_evolucion_4fechas.png"),
        "figs/f4_diseno.png": os.path.join(FIG_DIR, "ieee_fig4_topografia_y_diseno_geofisico.png"),
        "figs/f5_simulacion.png": os.path.join(FIG_DIR, "ieee_fig5_simulacion_ert.png"),
    }

    out_overleaf = os.path.join(OUT_DIR, "Caracterizacion_Coapan_IEEE_overleaf.zip")
    tmp_overleaf = out_overleaf + ".tmp"
    with zipfile.ZipFile(tmp_overleaf, "w", zipfile.ZIP_DEFLATED) as zdst:
        zdst.writestr("main.tex", main_tex)
        zdst.writestr("cuerpo.tex", cuerpo.encode("utf-8"))
        zdst.writestr("hyph_es.tex", hyph_tex)
        for arc, full in fig_map.items():
            zdst.write(full, arcname=arc)
    os.replace(tmp_overleaf, out_overleaf)

    dest_paq = os.path.join(BASE_DIR, "paquetes_zip", "Caracterizacion_Coapan_IEEE_overleaf.zip")
    shutil.copy2(out_overleaf, dest_paq)
    print(f"ZIP Overleaf actualizado: {out_overleaf} y {dest_paq}")
    return out_overleaf


def main():
    print("=== Paso 7: Compilación sincronizada de LaTeX (.tex) y PDF IEEE ===")
    metrics, ert, design_rows = load_data()

    tex_path = os.path.join(OUT_DIR, "relleno_coapan_ieee.tex")
    html_path = os.path.join(OUT_DIR, "paper_ieee.html")
    pdf_path = os.path.join(OUT_DIR, "Caracterizacion_geofisica_relleno_Coapan_BUAP_2026.pdf")

    tex_content = build_latex(metrics, ert, design_rows)
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    print(f"LaTeX generado: {tex_path}")

    html_content = build_html(metrics, ert, design_rows)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML base generado: {html_path}")

    weasyprint.HTML(filename=html_path, base_url=BASE_DIR).write_pdf(pdf_path)
    print(f"PDF IEEE compilado: {pdf_path}")

    build_overleaf_zip()


if __name__ == "__main__":
    main()
