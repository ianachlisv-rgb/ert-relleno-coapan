# Diseño de un levantamiento geofísico para el relleno sanitario de Santa María Coapan (Tehuacán, Puebla)

Propuesta de levantamiento (ERT, IP, EM, magnetometría y GPR) y simulación de un perfil sintético de ERT con código propio en Python.

**Autores del artículo:** Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale. **Código:** Ian A. Sandoval-Valderrábano (BUAP).

## Contenido
- [`paper/Relleno_Coapan_IEEE.pdf`](paper/Relleno_Coapan_IEEE.pdf): artículo en formato IEEE (5 páginas).
- [`codigo/`](codigo): simulación y figuras. Orden: `sim_ert.py` → `inv_sim.py` → `descargar_limites.py` → `figuras.py`.

## Resultado principal
Con un perfil sintético (Wenner-Schlumberger, 48 electrodos, 736 mediciones, 3 % de ruido) la inversión recupera el cuerpo de residuos (31 contra 30 Ω·m) y ubica el lixiviado, pero lo muestra más resistivo (11 contra 6 Ω·m) y más profundo de lo real.

## Importante
No hay datos de campo: todos los valores del modelo son supuestos tomados de la literatura y los resultados son una predicción. La ubicación exacta del polígono debe confirmarse en campo.

## Uso
```
pip install numpy scipy matplotlib shapely pyproj
python codigo/sim_ert.py
```

## Licencia
MIT.
