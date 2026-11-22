# Caracterización geofísica propuesta del relleno sanitario de Santa María Coapan (Tehuacán, Puebla)

Delimitación espacial con datos satelitales, diseño de un levantamiento geofísico (ERT/IP, EM, magnetometría y GPR) y simulación de un perfil sintético de ERT 2.5D.

**Autores del artículo:** Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale (Facultad de Ingeniería, BUAP).

## Contenido
- [`paper/Caracterizacion_Coapan_IEEE.pdf`](paper/Caracterizacion_Coapan_IEEE.pdf): artículo en formato IEEE (7 páginas).
- [`paper/overleaf/`](paper/overleaf): fuentes LaTeX (`main.tex`, `cuerpo.tex`, `hyph_es.tex`) y figuras. Se compila en Overleaf con la clase `IEEEtran` y el paquete `babel` en español.
- [`presentacion/Presentacion_Coapan_BUAP_2026.pdf`](presentacion/Presentacion_Coapan_BUAP_2026.pdf): presentación del artículo (26 diapositivas).
- [`codigo/paper/`](codigo/paper): scripts del análisis del artículo, en orden `01` a `07` (inspección, descarga multisensor, delimitación, mapas, figuras, simulación ERT 2.5D y compilación). Las rutas de entrada y salida están fijas dentro de cada script (`BASE_DIR`) y deben ajustarse.
- [`codigo/preliminar/`](codigo/preliminar): primera simulación en 2D (`sim_ert.py` → `inv_sim.py` → `descargar_limites.py` → `figuras.py`). Se conserva como versión previa.

## Resultados principales
- Cuerpo principal del relleno: 9.80 ha (huella de 12.15 ha). Desde 2011 la zona de disposición creció 3.05 ha (+45.2 %).
- Laguna de lixiviado: 315 m². Cicatriz de incendio: 2.92 ha. Superficie desnuda: 87.5 %.
- Diseño de campo: 3,315 m de ERT/IP y una malla de EM y magnetometría de 28.1 ha.
- Simulación sintética (ERT 2.5D, Wenner-Schlumberger, 48 electrodos, 901 mediciones, 3 % de ruido): la inversión converge con un error relativo (RMS) de 3.5 %. Recupera el cuerpo de residuos (28 contra 30 Ω·m), pero muestra el lixiviado más resistivo (17 contra 6 Ω·m) y los lodos también (13 contra 8 Ω·m).
- Plan de acción de 9 semanas y regla de interpretación con tres condiciones.

## Importante
No hay datos de campo. Los valores del modelo son supuestos tomados de la literatura y los resultados son una predicción, no una medición. La ubicación exacta del polígono debe confirmarse en campo. Las cifras de `codigo/preliminar/` (736 mediciones, 31 contra 30 Ω·m) corresponden a la versión previa y las del artículo son las de arriba.

## Uso del código previo
```
pip install numpy scipy matplotlib shapely pyproj
python codigo/preliminar/sim_ert.py
```

## Licencia
MIT.
