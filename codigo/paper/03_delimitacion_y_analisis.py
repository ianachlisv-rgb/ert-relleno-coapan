#!/usr/bin/env python3
"""
Paso 3: Delimitación georreferenciada de precisión, verificación visual,
análisis multitemporal (1989-2026), índices ópticos y dNBR (incendio mayo 2022),
retrodispersión SAR Sentinel-1, clasificación K-Means (ML), modelado hidrológico D8
(Copernicus DEM) y rediseño geofísico georreferenciado en EPSG:32614.

Proyecto Final de Geofísica Ambiental (Otoño 2026) — Facultad de Ingeniería, BUAP.
Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale.
"""

import os
import json
import csv
import heapq
import subprocess

import numpy as np
from PIL import Image
from scipy.cluster.vq import kmeans2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import Polygon as MplPolygon

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
RASTERS_DIR = os.path.join(BASE_DIR, "rasters")
SIG_DIR = os.path.join(BASE_DIR, "sig")
os.makedirs(SIG_DIR, exist_ok=True)

with open(os.path.join(RASTERS_DIR, "manifesto_sensores.json"), "r", encoding="utf-8") as f:
    MANIFEST = json.load(f)

# ==============================================================================
# 1. POLÍGONOS DIGITALIZADOS SOBRE ORTOFOTO ALTA RESOLUCIÓN (EPSG:32614, m)
# ==============================================================================

# Polígono A: Cuerpo principal aterrazado de residuos (2025-08-24, 0.34 m)
POLY_PRINCIPAL = [
    (666025.0, 2035552.0),  # V01: Esquina SO junto al acceso (cerca de PROFEPA-1)
    (666016.0, 2035615.0),  # V02: Borde oeste sur
    (666010.0, 2035675.0),  # V03: Borde oeste medio
    (666006.0, 2035725.0),  # V04: Borde oeste camino perimetral
    (666006.0, 2035775.0),  # V05: Borde oeste junto a laguna de lixiviados NO
    (666026.0, 2035825.0),  # V06: Flanco noroeste
    (666048.0, 2035888.0),  # V07: Hombro noroeste
    (666066.0, 2035904.0),  # V08: Ápice norte
    (666094.0, 2035898.0),  # V09: Borde norte superior
    (666118.0, 2035884.0),  # V10: Borde norte sobre pozas superiores
    (666172.0, 2035875.0),  # V11: Borde noreste alto
    (666208.0, 2035855.0),  # V12: Hombro noreste
    (666248.0, 2035816.0),  # V13: Escotadura noreste (borde exterior del bordo)
    (666275.0, 2035790.0),  # V14: Transición lóbulo este
    (666304.0, 2035766.0),  # V15: Lóbulo este
    (666328.0, 2035736.0),  # V16: Talud este superior
    (666352.0, 2035698.0),  # V17: Talud este medio
    (666366.0, 2035648.0),  # V18: Talud este inferior
    (666374.0, 2035595.0),  # V19: Borde sureste
    (666373.0, 2035560.0),  # V20: Esquina sureste (caseta/portón)
    (666260.0, 2035556.0),  # V21: Borde sur medio
    (666125.0, 2035552.0),  # V22: Borde sur oeste
]

# Polígono B: Huella operativa total (cuerpo principal + zona auxiliar/préstamo SO)
POLY_TOTAL = [
    (665898.0, 2035542.0),  # T01: Curva camino sur-suroeste
    (665875.0, 2035575.0),  # T02: Borde oeste área auxiliar SO (borde interno del camino)
    (665865.0, 2035630.0),  # T03: Borde oeste terracería SO
    (665872.0, 2035685.0),  # T04: Límite noroeste área préstamo SO
    (665902.0, 2035718.0),  # T05: Esquina norte área auxiliar SO
    (665955.0, 2035705.0),  # T06: Borde noreste área auxiliar SO
    (665998.0, 2035685.0),  # T07: Unión con camino interno hacia cuerpo principal
    (666006.0, 2035725.0),  # T08: Borde oeste camino perimetral
    (666006.0, 2035775.0),  # T09: Flanco laguna lixiviados NO
    (666026.0, 2035825.0),  # T10: Flanco noroeste
    (666048.0, 2035888.0),  # T11: Hombro noroeste
    (666066.0, 2035904.0),  # T12: Ápice norte
    (666094.0, 2035898.0),  # T13: Borde norte superior
    (666118.0, 2035884.0),  # T14: Borde norte sobre pozas
    (666172.0, 2035875.0),  # T15: Borde noreste alto
    (666208.0, 2035855.0),  # T16: Hombro noreste
    (666248.0, 2035816.0),  # T17: Escotadura noreste
    (666275.0, 2035790.0),  # T18: Transición lóbulo este
    (666304.0, 2035766.0),  # T19: Lóbulo este
    (666328.0, 2035736.0),  # T20: Talud este superior
    (666352.0, 2035698.0),  # T21: Talud este medio
    (666366.0, 2035648.0),  # T22: Talud este inferior
    (666374.0, 2035595.0),  # T23: Borde sureste
    (666373.0, 2035560.0),  # T24: Esquina sureste
    (666260.0, 2035556.0),  # T25: Borde sur medio
    (666125.0, 2035552.0),  # T26: Borde sur oeste
    (666020.0, 2035542.0),  # T27: Acceso principal (PROFEPA-1)
]

# Polígono C: Núcleo histórico observable en 2011-06-06 (Wayback rid=10, 0.5 m)
POLY_2011 = [
    (666038.0, 2035558.0),
    (666048.0, 2035650.0),
    (666062.0, 2035750.0),
    (666080.0, 2035835.0),
    (666102.0, 2035874.0),
    (666148.0, 2035874.0),
    (666208.0, 2035838.0),
    (666248.0, 2035775.0),
    (666284.0, 2035710.0),
    (666325.0, 2035635.0),
    (666355.0, 2035568.0),
    (666285.0, 2035562.0),
    (666165.0, 2035558.0),
]

# Subzona 1: Laguna/estanque de lixiviados flanco NO
POLY_LAGUNA_NO = [
    (666017.0, 2035762.0),
    (666021.0, 2035785.0),
    (666035.0, 2035782.0),
    (666030.0, 2035760.0),
]

# Subzona 2: Área auxiliar / préstamo / trincheras SO
POLY_AUX_SO = [
    (665898.0, 2035542.0),
    (665875.0, 2035575.0),
    (665865.0, 2035630.0),
    (665872.0, 2035685.0),
    (665902.0, 2035718.0),
    (665955.0, 2035705.0),
    (666002.0, 2035680.0),
    (666014.0, 2035550.0),
]

PROFEPA_PTS = [
    {"id": "PROFEPA-1", "desc": "18°24'12.3\"N, 97°25'41.8\"O", "lat": 18 + 24/60 + 12.3/3600, "lon": -(97 + 25/60 + 41.8/3600)},
    {"id": "PROFEPA-2", "desc": "18°24'05.88\"N, 97°25'30.03\"O", "lat": 18 + 24/60 + 5.88/3600, "lon": -(97 + 25/60 + 30.03/3600)},
]

# Referencias locales de contexto (UTM convertidas en tiempo de ejecución)
COAPAN_IGLESIA = {"id": "Santa María Coapan", "lat": 18.4274, "lon": -97.4060}

# ==============================================================================
# 2. UTILIDADES GEOMÉTRICAS Y RASTER
# ==============================================================================

def read_tif(rel_or_abs):
    p = rel_or_abs if os.path.isabs(rel_or_abs) else os.path.join(BASE_DIR, rel_or_abs)
    tmp = p + ".tmp_read.tif"
    subprocess.run(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=NONE", p, tmp],
                   check=True, capture_output=True)
    arr = np.array(Image.open(tmp), dtype=np.float32)
    os.remove(tmp)
    return arr


def write_geotiff_like(out_path, arr, bbox, dtype="float32", nodata=None):
    xmin, ymin, xmax, ymax = bbox
    h, w = arr.shape[:2]
    px = (xmax - xmin) / w
    py = (ymax - ymin) / h
    tmp_raw = out_path + ".raw.tif"
    mode = "F" if dtype == "float32" else ("L" if arr.dtype == np.uint8 else "F")
    if dtype == "uint8":
        Image.fromarray(arr.astype(np.uint8), mode="L").save(tmp_raw)
    else:
        Image.fromarray(arr.astype(np.float32), mode="F").save(tmp_raw)
    cmd = [
        "gdal_translate", "-of", "GTiff", "-a_srs", "EPSG:32614",
        "-a_ullr", str(xmin), str(ymax), str(xmax), str(ymin),
        "-co", "COMPRESS=DEFLATE",
    ]
    if nodata is not None:
        cmd.extend(["-a_nodata", str(nodata)])
    cmd.extend([tmp_raw, out_path])
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.exists(tmp_raw):
        os.remove(tmp_raw)


def utm_to_latlon(pts):
    inp = "\n".join(f"{e} {n}" for e, n in pts) + "\n"
    res = subprocess.run(["gdaltransform", "-s_srs", "EPSG:32614", "-t_srs", "EPSG:4326"],
                         input=inp, text=True, capture_output=True, check=True)
    return [tuple(map(float, line.strip().split()[:2])) for line in res.stdout.strip().splitlines()]


def latlon_to_utm(pts):
    inp = "\n".join(f"{lon} {lat}" for lon, lat in pts) + "\n"
    res = subprocess.run(["gdaltransform", "-s_srs", "EPSG:4326", "-t_srs", "EPSG:32614"],
                         input=inp, text=True, capture_output=True, check=True)
    return [tuple(map(float, line.strip().split()[:2])) for line in res.stdout.strip().splitlines()]


def to_dms(deg, is_lat=True):
    hemi = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "O")
    d = abs(deg)
    g = int(d)
    m = int((d - g) * 60)
    s = (d - g - m / 60) * 3600
    return f"{g}°{m:02d}'{s:05.2f}\"{hemi}"


def polygon_metrics(coords):
    """Área (m², ha), perímetro (m) y centroide exacto en EPSG:32614 mediante Shoelace."""
    x = np.array([p[0] for p in coords], dtype=np.float64)
    y = np.array([p[1] for p in coords], dtype=np.float64)
    x2 = np.roll(x, -1)
    y2 = np.roll(y, -1)
    cross = x * y2 - x2 * y
    signed_area = 0.5 * np.sum(cross)
    area_m2 = abs(signed_area)
    cx = np.sum((x + x2) * cross) / (6.0 * signed_area)
    cy = np.sum((y + y2) * cross) / (6.0 * signed_area)
    perim_m = float(np.sum(np.hypot(x2 - x, y2 - y)))
    return {
        "area_m2": round(float(area_m2), 1),
        "area_ha": round(float(area_m2 / 10000.0), 3),
        "perimetro_m": round(perim_m, 1),
        "centroide_utm": [round(float(cx), 2), round(float(cy), 2)],
    }


def rasterize_polygon(coords, bbox, shape):
    """Máscara booleana para centros de píxel dentro del polígono (origin='upper')."""
    xmin, ymin, xmax, ymax = bbox
    h, w = shape
    dx = (xmax - xmin) / w
    dy = (ymax - ymin) / h
    xs = xmin + (np.arange(w) + 0.5) * dx
    ys = ymax - (np.arange(h) + 0.5) * dy
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    path = MplPath(coords)
    return path.contains_points(pts).reshape((h, w))


def point_to_polyline_dist(pt, lines):
    px, py = pt
    best = 1e12
    for line in lines:
        for i in range(len(line) - 1):
            x1, y1 = line[i]
            x2, y2 = line[i + 1]
            dx, dy = x2 - x1, y2 - y1
            l2 = dx * dx + dy * dy
            if l2 == 0:
                d = np.hypot(px - x1, py - y1)
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
                d = np.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
            if d < best:
                best = d
    return float(best)


# ==============================================================================
# 3. ANÁLISIS PRINCIPAL
# ==============================================================================

def main():
    print("=== Paso 3: Delimitación, análisis multisensor, ML, hidrología y diseño geofísico ===")

    # 3.1 Métricas geométricas de polígonos
    m_princ = polygon_metrics(POLY_PRINCIPAL)
    m_total = polygon_metrics(POLY_TOTAL)
    m_2011 = polygon_metrics(POLY_2011)
    m_laguna = polygon_metrics(POLY_LAGUNA_NO)
    m_aux = polygon_metrics(POLY_AUX_SO)

    for m in (m_princ, m_total, m_2011, m_laguna, m_aux):
        lon, lat = utm_to_latlon([tuple(m["centroide_utm"])])[0]
        m["centroide_wgs84"] = [round(lat, 6), round(lon, 6)]
        m["centroide_dms"] = f"{to_dms(lat, True)}, {to_dms(lon, False)}"

    exp_ha = round(m_princ["area_ha"] - m_2011["area_ha"], 3)
    exp_pct = round((exp_ha / m_2011["area_ha"]) * 100.0, 1)

    print(f"Cuerpo principal (2025): {m_princ['area_ha']} ha, perim={m_princ['perimetro_m']} m, centroide={m_princ['centroide_dms']}")
    print(f"Huella operativa total:  {m_total['area_ha']} ha, perim={m_total['perimetro_m']} m")
    print(f"Núcleo histórico (2011): {m_2011['area_ha']} ha -> Expansión 2011-2025: +{exp_ha} ha (+{exp_pct}%)")
    print(f"Área auxiliar SO: {m_aux['area_ha']} ha | Laguna NO: {m_laguna['area_ha']} ha ({m_laguna['area_m2']} m²)")

    # Puntos de referencia y distancias
    for p in PROFEPA_PTS:
        e, n = latlon_to_utm([(p["lon"], p["lat"])])[0]
        p["E"], p["N"] = round(e, 2), round(n, 2)
    coap_e, coap_n = latlon_to_utm([(COAPAN_IGLESIA["lon"], COAPAN_IGLESIA["lat"])])[0]
    COAPAN_IGLESIA["E"], COAPAN_IGLESIA["N"] = round(coap_e, 2), round(coap_n, 2)

    cx, cy = m_princ["centroide_utm"]
    dist_coapan = round(float(np.hypot(cx - coap_e, cy - coap_n)), 1)

    # Distancias a MEX-125 y San Antonio Texcala desde OSM
    osm_path = os.path.join(SIG_DIR, "osm_contexto_utm14n.geojson")
    mex125_lines = []
    texcala_pt = None
    tehuacan_pt = None
    with open(osm_path, "r", encoding="utf-8") as f:
        osm_gj = json.load(f)
    for ft in osm_gj["features"]:
        pr = ft["properties"]
        gm = ft["geometry"]
        if pr.get("layer") == "highway" and pr.get("ref") == "MEX 125" and gm["type"] == "LineString":
            mex125_lines.append(gm["coordinates"])
        if pr.get("layer") == "place" and pr.get("name") == "San Antonio Texcala":
            texcala_pt = gm["coordinates"]
        if pr.get("layer") == "place" and pr.get("name") == "Tehuacán":
            tehuacan_pt = gm["coordinates"]

    dist_mex125 = round(point_to_polyline_dist((cx, cy), mex125_lines), 1) if mex125_lines else None
    dist_texcala = round(float(np.hypot(cx - texcala_pt[0], cy - texcala_pt[1])), 1) if texcala_pt else None
    dist_tehuacan = round(float(np.hypot(cx - tehuacan_pt[0], cy - tehuacan_pt[1])), 1) if tehuacan_pt else None
    print(f"Distancias desde centroide: MEX-125={dist_mex125} m, Coapan={dist_coapan} m, Texcala={dist_texcala} m, Tehuacán={dist_tehuacan} m")

    # 3.2 Máscaras 10 m (MED_BBOX) y 30 m (REG_BBOX)
    med_bbox = tuple(MANIFEST["med_bbox"])
    reg_bbox = tuple(MANIFEST["reg_bbox"])
    fine_bbox = tuple(MANIFEST["fine_bbox"])

    sample_s2 = read_tif(MANIFEST["sentinel2"][0]["bands"]["B04"])
    med_shape = sample_s2.shape  # (480, 450)
    sample_ls = read_tif(MANIFEST["landsat"][0]["bands"]["red"])
    reg_shape = sample_ls.shape  # (210, 210)

    mask_princ_10 = rasterize_polygon(POLY_PRINCIPAL, med_bbox, med_shape)
    mask_total_10 = rasterize_polygon(POLY_TOTAL, med_bbox, med_shape)
    mask_princ_30 = rasterize_polygon(POLY_PRINCIPAL, reg_bbox, reg_shape)

    # Anillo testigo natural (150-450 m alrededor del centroide, fuera de huella_total + 100 m, excluyendo oeste carretera)
    # Construimos un anillo 200-450 m alrededor de POLY_TOTAL y excluimos caminos obvios usando distancia al centroide
    mx0, my0, mx1, my1 = med_bbox
    xs10 = mx0 + (np.arange(med_shape[1]) + 0.5) * 10.0
    ys10 = my1 - (np.arange(med_shape[0]) + 0.5) * 10.0
    gx10, gy10 = np.meshgrid(xs10, ys10)
    dist_c10 = np.hypot(gx10 - cx, gy10 - cy)
    # Testigo natural: 380 m a 650 m alrededor del centroide (matorral xerófilo intacto al N, E y S)
    mask_ctrl_10 = (dist_c10 >= 380.0) & (dist_c10 <= 650.0) & (~mask_total_10)

    rx0, ry0, rx1, ry1 = reg_bbox
    xs30 = rx0 + (np.arange(reg_shape[1]) + 0.5) * 30.0
    ys30 = ry1 - (np.arange(reg_shape[0]) + 0.5) * 30.0
    gx30, gy30 = np.meshgrid(xs30, ys30)
    dist_c30 = np.hypot(gx30 - cx, gy30 - cy)
    mask_ctrl_30 = (dist_c30 >= 380.0) & (dist_c30 <= 650.0) & (~rasterize_polygon(POLY_TOTAL, reg_bbox, reg_shape))

    # 3.3 Serie temporal multiespectral 1989-2026 (Landsat + Sentinel-2)
    print("\n--- Serie temporal multiespectral 1989-2026 ---")
    ts_records = []
    for rec in MANIFEST["landsat"]:
        b = rec["bands"]
        blue = np.clip(read_tif(b["blue"]) * 0.0000275 - 0.2, 0.001, 1.0)
        red = np.clip(read_tif(b["red"]) * 0.0000275 - 0.2, 0.001, 1.0)
        nir = np.clip(read_tif(b["nir08"]) * 0.0000275 - 0.2, 0.001, 1.0)
        swir1 = np.clip(read_tif(b["swir16"]) * 0.0000275 - 0.2, 0.001, 1.0)
        ndvi = (nir - red) / (nir + red + 1e-6)
        bsi = ((swir1 + red) - (nir + blue)) / ((swir1 + red) + (nir + blue) + 1e-6)
        ndvi_p = float(np.median(ndvi[mask_princ_30]))
        ndvi_c = float(np.median(ndvi[mask_ctrl_30]))
        bsi_p = float(np.median(bsi[mask_princ_30]))
        bsi_c = float(np.median(bsi[mask_ctrl_30]))
        ts_records.append({
            "date": rec["date"], "sensor": rec["platform"], "tag": rec["tag"],
            "ndvi_relleno": round(ndvi_p, 4), "ndvi_testigo": round(ndvi_c, 4),
            "delta_ndvi": round(ndvi_p - ndvi_c, 4),
            "bsi_relleno": round(bsi_p, 4), "bsi_testigo": round(bsi_c, 4),
            "delta_bsi": round(bsi_p - bsi_c, 4),
        })

    s2_by_tag = {r["tag"]: r for r in MANIFEST["sentinel2"]}
    def load_s2_scaled(rec):
        off = rec["boa_offset"]
        sc = rec["scale"]
        b = rec["bands"]
        out = {}
        for k in ("B02", "B03", "B04", "B08", "B8A", "B11", "B12"):
            out[k] = np.clip((read_tif(b[k]) + off) * sc, 0.001, 1.0)
        return out

    for tag in ("2020_op", "2022_prefire_0418", "2022_postfire_0518", "2026_cur_1103"):
        rec = s2_by_tag[tag]
        d = load_s2_scaled(rec)
        ndvi = (d["B08"] - d["B04"]) / (d["B08"] + d["B04"] + 1e-6)
        bsi = ((d["B11"] + d["B04"]) - (d["B08"] + d["B02"])) / ((d["B11"] + d["B04"]) + (d["B08"] + d["B02"]) + 1e-6)
        ndvi_p = float(np.median(ndvi[mask_princ_10]))
        ndvi_c = float(np.median(ndvi[mask_ctrl_10]))
        bsi_p = float(np.median(bsi[mask_princ_10]))
        bsi_c = float(np.median(bsi[mask_ctrl_10]))
        ts_records.append({
            "date": rec["date"], "sensor": "sentinel-2", "tag": tag,
            "ndvi_relleno": round(ndvi_p, 4), "ndvi_testigo": round(ndvi_c, 4),
            "delta_ndvi": round(ndvi_p - ndvi_c, 4),
            "bsi_relleno": round(bsi_p, 4), "bsi_testigo": round(bsi_c, 4),
            "delta_bsi": round(bsi_p - bsi_c, 4),
        })

    ts_records.sort(key=lambda x: x["date"])
    for row in ts_records:
        print(f"  {row['date']} ({row['sensor']:10s}): NDVI_r={row['ndvi_relleno']:+.3f} (Δ={row['delta_ndvi']:+.3f}) | BSI_r={row['bsi_relleno']:+.3f} (Δ={row['delta_bsi']:+.3f})")

    # 3.4 Evento de incendio mayo 2022 (dNBR = NBR_2022-04-18 - NBR_2022-05-18)
    s2_pre = load_s2_scaled(s2_by_tag["2022_prefire_0418"])
    s2_post = load_s2_scaled(s2_by_tag["2022_postfire_0518"])
    nbr_pre = (s2_pre["B08"] - s2_pre["B12"]) / (s2_pre["B08"] + s2_pre["B12"] + 1e-6)
    nbr_post = (s2_post["B08"] - s2_post["B12"]) / (s2_post["B08"] + s2_post["B12"] + 1e-6)
    dnbr = nbr_pre - nbr_post
    write_geotiff_like(os.path.join(RASTERS_DIR, "s2_2022_dnbr_utm14n.tif"), dnbr, med_bbox)

    burn_low_mod = (dnbr >= 0.10) & mask_total_10
    burn_mod_high = (dnbr >= 0.27) & mask_total_10
    burn_ha_10 = round(float(np.sum(burn_low_mod) * 100.0 / 10000.0), 3)
    burn_ha_27 = round(float(np.sum(burn_mod_high) * 100.0 / 10000.0), 3)
    dnbr_max = round(float(np.max(dnbr[mask_total_10])), 3)
    dnbr_mean_scar = round(float(np.mean(dnbr[burn_low_mod])), 3) if np.any(burn_low_mod) else 0.0
    print(f"\nIncendio mayo 2022 (dNBR): área dNBR>=0.10 = {burn_ha_10} ha ({burn_ha_10/m_total['area_ha']*100:.1f}% huella); "
          f"dNBR>=0.27 = {burn_ha_27} ha; max={dnbr_max}, media cicatriz={dnbr_mean_scar}")

    # 3.5 Estado óptico actual (2026-11-03)
    s2_cur = load_s2_scaled(s2_by_tag["2026_cur_1103"])
    ndvi_2026 = (s2_cur["B08"] - s2_cur["B04"]) / (s2_cur["B08"] + s2_cur["B04"] + 1e-6)
    bsi_2026 = ((s2_cur["B11"] + s2_cur["B04"]) - (s2_cur["B08"] + s2_cur["B02"])) / ((s2_cur["B11"] + s2_cur["B04"]) + (s2_cur["B08"] + s2_cur["B02"]) + 1e-6)
    ndbi_2026 = (s2_cur["B11"] - s2_cur["B08"]) / (s2_cur["B11"] + s2_cur["B08"] + 1e-6)
    write_geotiff_like(os.path.join(RASTERS_DIR, "s2_2026_ndvi_utm14n.tif"), ndvi_2026, med_bbox)
    write_geotiff_like(os.path.join(RASTERS_DIR, "s2_2026_bsi_utm14n.tif"), bsi_2026, med_bbox)

    # 3.6 Radar SAR Sentinel-1 RTC (banda C, rel=70 descendente)
    print("\n--- Sentinel-1 RTC SAR (dB) ---")
    s1_stats = []
    s1_arrays = {}
    for rec in MANIFEST["sentinel1"]:
        vv_lin = read_tif(rec["pols"]["vv"])
        vh_lin = read_tif(rec["pols"]["vh"])
        vv_db = 10.0 * np.log10(np.where(vv_lin > 0, vv_lin, np.nan))
        vh_db = 10.0 * np.log10(np.where(vh_lin > 0, vh_lin, np.nan))
        ratio = vh_db - vv_db
        s1_arrays[rec["tag"]] = (vv_db, vh_db, ratio)
        st = {
            "tag": rec["tag"], "date": rec["date"], "platform": rec["platform"],
            "vv_relleno_db": round(float(np.nanmedian(vv_db[mask_princ_10])), 2),
            "vh_relleno_db": round(float(np.nanmedian(vh_db[mask_princ_10])), 2),
            "vh_vv_relleno_db": round(float(np.nanmedian(ratio[mask_princ_10])), 2),
            "vv_testigo_db": round(float(np.nanmedian(vv_db[mask_ctrl_10])), 2),
            "vh_testigo_db": round(float(np.nanmedian(vh_db[mask_ctrl_10])), 2),
            "vh_vv_testigo_db": round(float(np.nanmedian(ratio[mask_ctrl_10])), 2),
        }
        s1_stats.append(st)
        print(f"  {rec['date']} ({rec['platform']}): Relleno VV={st['vv_relleno_db']} dB, VH={st['vh_relleno_db']} dB, VH-VV={st['vh_vv_relleno_db']} dB | "
              f"Testigo VV={st['vv_testigo_db']} dB, VH={st['vh_testigo_db']} dB")

    vv_26, vh_26, _ = s1_arrays["2026_actual"]
    vv_21, vh_21, _ = s1_arrays["2021_pre_cierre"]
    write_geotiff_like(os.path.join(RASTERS_DIR, "s1_2026_vv_db_utm14n.tif"), np.nan_to_num(vv_26, nan=-9999.0), med_bbox, nodata=-9999.0)
    write_geotiff_like(os.path.join(RASTERS_DIR, "s1_2026_vh_db_utm14n.tif"), np.nan_to_num(vh_26, nan=-9999.0), med_bbox, nodata=-9999.0)

    dvv = float(np.nanmedian((vv_26 - vv_21)[mask_princ_10]))
    dvh = float(np.nanmedian((vh_26 - vh_21)[mask_princ_10]))

    # 3.7 Clasificación por Aprendizaje Automático (K-Means multisensor k=5 sobre ventana 2x2 km)
    print("\n--- Aprendizaje Automático: K-Means multisensor (k=5, semilla=42) ---")
    slope_10 = read_tif(MANIFEST["dem"]["slope_10m"])
    # Ventana de entrenamiento enfocada (2.0 x 2.0 km): E 665100..667100, N 2034700..2036700
    r0_ml = int((my1 - 2036700) / 10)
    r1_ml = int((my1 - 2034700) / 10)
    c0_ml = int((665100 - mx0) / 10)
    c1_ml = int((667100 - mx0) / 10)

    feat_stack = np.stack([
        s2_cur["B04"], s2_cur["B08"], s2_cur["B11"], s2_cur["B12"],
        ndvi_2026, bsi_2026,
        np.nan_to_num(vv_26, nan=float(np.nanmedian(vv_26))),
        np.nan_to_num(vh_26, nan=float(np.nanmedian(vh_26))),
        slope_10,
    ], axis=-1)

    sub_feats = feat_stack[r0_ml:r1_ml, c0_ml:c1_ml, :].reshape(-1, 9)
    mu = np.mean(sub_feats, axis=0)
    sd = np.std(sub_feats, axis=0) + 1e-6
    sub_z = (sub_feats - mu) / sd

    rng = np.random.default_rng(42)
    centroids, labels_sub = kmeans2(sub_z, 5, minit="points", iter=40, seed=rng)
    # Asignar toda la escena MED_BBOX para consistencia espacial
    all_z = (feat_stack.reshape(-1, 9) - mu) / sd
    dists = np.linalg.norm(all_z[:, None, :] - centroids[None, :, :], axis=2)
    labels_full = np.argmin(dists, axis=1).reshape(med_shape).astype(np.uint8)

    # Analizar propiedades físicas de cada clúster dentro de ventana local (2x2 km) para nombrarlos rigurosamente
    sub_lbl = labels_full[r0_ml:r1_ml, c0_ml:c1_ml]
    sub_ndvi = ndvi_2026[r0_ml:r1_ml, c0_ml:c1_ml]
    sub_bsi = bsi_2026[r0_ml:r1_ml, c0_ml:c1_ml]
    sub_b11 = s2_cur["B11"][r0_ml:r1_ml, c0_ml:c1_ml]
    sub_vv = vv_26[r0_ml:r1_ml, c0_ml:c1_ml]
    sub_vh = vh_26[r0_ml:r1_ml, c0_ml:c1_ml]
    sub_slp = slope_10[r0_ml:r1_ml, c0_ml:c1_ml]
    sub_in_poly = mask_total_10[r0_ml:r1_ml, c0_ml:c1_ml]

    cluster_profiles = []
    for k in range(5):
        m_k = sub_lbl == k
        in_p_frac = float(np.sum(m_k & sub_in_poly) / max(1, np.sum(sub_in_poly)) * 100.0)
        cluster_profiles.append({
            "raw_id": k,
            "ndvi": round(float(np.mean(sub_ndvi[m_k])), 3),
            "bsi": round(float(np.mean(sub_bsi[m_k])), 3),
            "b11": round(float(np.mean(sub_b11[m_k])), 3),
            "vv_db": round(float(np.nanmean(sub_vv[m_k])), 2),
            "vh_db": round(float(np.nanmean(sub_vh[m_k])), 2),
            "slope_deg": round(float(np.mean(sub_slp[m_k])), 1),
            "pct_en_huella": round(in_p_frac, 1),
            "ha_en_huella": round(float(np.sum(m_k & sub_in_poly) * 100.0 / 10000.0), 3),
        })

    # Ordenar por BSI descendente / NDVI ascendente para etiquetado físico determinístico
    # Imprimir perfiles crudos y asignar nombres según firma física verificada
    for cp in sorted(cluster_profiles, key=lambda x: (-x["bsi"], x["ndvi"])):
        print(f"  Clúster {cp['raw_id']}: BSI={cp['bsi']:+.3f}, NDVI={cp['ndvi']:+.3f}, B11={cp['b11']:.3f}, "
              f"VV={cp['vv_db']}dB, VH={cp['vh_db']}dB, Slope={cp['slope_deg']}° -> {cp['ha_en_huella']} ha ({cp['pct_en_huella']}% en huella)")

    # Ordenamiento físico semántico por NDVI ascendente (y B11 descendente) verificado por firma espectral + SAR + pendiente
    sorted_phys = sorted(cluster_profiles, key=lambda x: (x["ndvi"], -x["b11"]))
    rank_names = [
        "Cubierta mineral / residuos compactados sin vegetación",
        "Taludes perturbados / suelo desnudo y caminos internos",
        "Escarpa de alta pendiente y rugosidad SAR",
        "Matorral ralo / vegetación pionera sobre suelo alterado",
        "Matorral xerófilo denso (entorno natural)",
    ]
    remap = np.zeros_like(labels_full)
    ml_classes = []
    for new_id, cp in enumerate(sorted_phys):
        remap[labels_full == cp["raw_id"]] = new_id
        cp_copy = dict(cp)
        cp_copy["class_id"] = new_id
        cp_copy["label"] = rank_names[new_id]
        ml_classes.append(cp_copy)

    write_geotiff_like(os.path.join(RASTERS_DIR, "ml_kmeans_2026_utm14n.tif"), remap.astype(np.float32), med_bbox)

    # 3.8 Modelado topográfico e hidrológico D8 (Copernicus DEM 30 m)
    print("\n--- Modelado Topográfico e Hidrológico D8 (Copernicus DEM 30 m) ---")
    dem30 = read_tif(MANIFEST["dem"]["dem_30m"]).astype(np.float64)
    slope30 = read_tif(MANIFEST["dem"]["slope_30m"]).astype(np.float64)
    dem10 = read_tif(MANIFEST["dem"]["dem_10m"]).astype(np.float64)

    # Estadísticas topográficas dentro del cuerpo principal y huella total (usando DEM 10 m)
    elev_p = dem10[mask_princ_10]
    elev_t = dem10[mask_total_10]
    slp_t = slope_10[mask_total_10]
    # Aspecto dominante en huella total
    gy_e, gx_e = np.gradient(dem10, 10.0)
    # En imagen origin='upper', dy positivo es hacia el Sur -> dZ/dN = -gy_e, dZ/dE = gx_e
    mean_dz_de = float(np.mean(gx_e[mask_total_10]))
    mean_dz_dn = float(np.mean(-gy_e[mask_total_10]))
    # Azimut hacia donde desciende el terreno (-gradiente)
    down_az = (np.degrees(np.arctan2(-mean_dz_de, -mean_dz_dn)) + 360.0) % 360.0

    topo_stats = {
        "elev_min_m": round(float(np.min(elev_t)), 1),
        "elev_max_m": round(float(np.max(elev_t)), 1),
        "elev_media_m": round(float(np.mean(elev_t)), 1),
        "desnivel_interno_m": round(float(np.max(elev_t) - np.min(elev_t)), 1),
        "pendiente_media_deg": round(float(np.mean(slp_t)), 1),
        "pendiente_max_deg": round(float(np.max(slp_t)), 1),
        "azimut_descenso_deg": round(float(down_az), 1),
    }
    print(f"Topografía huella total: elev {topo_stats['elev_min_m']}–{topo_stats['elev_max_m']} m (media {topo_stats['elev_media_m']} m), "
          f"pendiente media={topo_stats['pendiente_media_deg']}°, max={topo_stats['pendiente_max_deg']}°, descenso hacia azimut={topo_stats['azimut_descenso_deg']}° (ENE)")

    # Rellenado Wang & Liu + D8 + Acumulación
    rows30, cols30 = dem30.shape
    filled = dem30.copy()
    vis = np.zeros_like(dem30, dtype=bool)
    pq = []
    for r in range(rows30):
        for c in (0, cols30 - 1):
            vis[r, c] = True
            heapq.heappush(pq, (filled[r, c], r, c))
    for c in range(1, cols30 - 1):
        for r in (0, rows30 - 1):
            vis[r, c] = True
            heapq.heappush(pq, (filled[r, c], r, c))
    nbrs = [(-1, -1, 1.41421356), (-1, 0, 1.0), (-1, 1, 1.41421356),
            (0, -1, 1.0),                      (0, 1, 1.0),
            (1, -1, 1.41421356),  (1, 0, 1.0), (1, 1, 1.41421356)]
    while pq:
        el, r, c = heapq.heappop(pq)
        for dr, dc, _ in nbrs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows30 and 0 <= nc < cols30 and not vis[nr, nc]:
                vis[nr, nc] = True
                if filled[nr, nc] < el + 1e-4:
                    filled[nr, nc] = el + 1e-4
                heapq.heappush(pq, (filled[nr, nc], nr, nc))

    d8 = np.full((rows30, cols30), -1, dtype=np.int8)
    for r in range(1, rows30 - 1):
        for c in range(1, cols30 - 1):
            bs, bk = 0.0, -1
            z0 = filled[r, c]
            for k, (dr, dc, dist) in enumerate(nbrs):
                s = (z0 - filled[r + dr, c + dc]) / dist
                if s > bs:
                    bs, bk = s, k
            d8[r, c] = bk

    acc = np.ones((rows30, cols30), dtype=np.float64)
    for idx in np.argsort(-filled.ravel()):
        r, c = divmod(int(idx), cols30)
        k = d8[r, c]
        if k >= 0:
            dr, dc, _ = nbrs[k]
            acc[r + dr, c + dc] += acc[r, c]

    # Extraer líneas de drenaje (acc >= 35 celdas = 3.15 ha) y rutas trazadas desde el relleno
    stream_lines = []
    for r in range(1, rows30 - 1):
        for c in range(1, cols30 - 1):
            if acc[r, c] >= 35 and d8[r, c] >= 0:
                dr, dc, _ = nbrs[d8[r, c]]
                e1, n1 = rx0 + (c + 0.5) * 30.0, ry1 - (r + 0.5) * 30.0
                e2, n2 = rx0 + (c + dc + 0.5) * 30.0, ry1 - (r + dr + 0.5) * 30.0
                stream_lines.append({
                    "coords": [[e1, n1], [e2, n2]],
                    "acc_ha": round(float(acc[r, c] * 900.0 / 10000.0), 2),
                    "tipo": "red_drenaje_d8",
                })

    # Trazas explícitas desde puntos clave del relleno hasta 2.5 km aguas abajo
    landfill_flow_paths = []
    seed_pts = [
        ("Escurrimiento principal (laguna NO -> cañada NE)", 666030.0, 2035770.0),
        ("Escurrimiento corona norte -> cañada NE", 666135.0, 2035855.0),
        ("Escurrimiento flanco SE -> tributario ENE", 666315.0, 2035615.0),
    ]
    for label, se, sn in seed_pts:
        c = int((se - rx0) / 30.0)
        r = int((ry1 - sn) / 30.0)
        pts = []
        for _ in range(90):
            if not (0 <= r < rows30 and 0 <= c < cols30):
                break
            pts.append([round(rx0 + (c + 0.5) * 30.0, 1), round(ry1 - (r + 0.5) * 30.0, 1)])
            k = d8[r, c]
            if k < 0:
                break
            dr, dc, _ = nbrs[k]
            r += dr
            c += dc
        landfill_flow_paths.append({"label": label, "coords": pts})

    # Perfiles topográficos O-E (N=2035710) y N-S (E=666170) de 1600 m en DEM 10 m
    prof_oe_e = np.arange(665400.0, 666850.0, 10.0)
    r_oe = int((my1 - 2035710.0) / 10.0)
    prof_oe_z = [float(dem10[r_oe, int((e - mx0) / 10.0)]) for e in prof_oe_e]

    prof_ns_n = np.arange(2035050.0, 2036300.0, 10.0)
    c_ns = int((666170.0 - mx0) / 10.0)
    prof_ns_z = [float(dem10[int((my1 - n) / 10.0), c_ns]) for n in prof_ns_n]

    # 3.9 Rediseño georreferenciado del levantamiento geofísico (EPSG:32614)
    # 6 perfiles E-O (L1-L6) cubriendo todo el cuerpo de residuos + bordes en terreno natural (espaciado ~55 m)
    # 2 transversales N-S (T1-T2) cruzando L1-L6, cicatriz de incendio y flanco NO
    # 1 perfil de fondo (R1, 235 m) AGUAS ARRIBA (Oeste del camino, cota ~1815-1825 m)
    # 4 piezómetros (P1 testigo aguas arriba; P2-P4 triángulo aguas abajo en salidas D8 hacia ENE/NE)
    profiles_geo = [
        {"id": "L1", "tipo": "ERT/IP longitudinal", "coords": [[665975.0, 2035575.0], [666410.0, 2035575.0]], "longitud_m": 435, "electrodos": 88, "nota": "Roll-along 5m (48+40 el.); cruza contacto O, base sur y contacto E"},
        {"id": "L2", "tipo": "ERT/IP + GPR", "coords": [[665965.0, 2035630.0], [666400.0, 2035630.0]], "longitud_m": 435, "electrodos": 88, "nota": "Roll-along 5m + tramo GPR; cruza área auxiliar SO, cuerpo central y lóbulo E"},
        {"id": "L3", "tipo": "ERT/IP longitudinal", "coords": [[665960.0, 2035685.0], [666395.0, 2035685.0]], "longitud_m": 435, "electrodos": 88, "nota": "Roll-along 5m; cruza núcleo de residuos y escarpa E"},
        {"id": "L4", "tipo": "ERT/IP longitudinal", "coords": [[665965.0, 2035740.0], [666360.0, 2035740.0]], "longitud_m": 395, "electrodos": 80, "nota": "Roll-along 5m; cruza cicatriz incendio mayo 2022 y descarga lateral E"},
        {"id": "L5", "tipo": "ERT/IP + GPR", "coords": [[665970.0, 2035795.0], [666325.0, 2035795.0]], "longitud_m": 355, "electrodos": 72, "nota": "Roll-along 5m + GPR; cruza laguna de lixiviados NO y zona quemada"},
        {"id": "L6", "tipo": "ERT/IP longitudinal", "coords": [[665985.0, 2035850.0], [666260.0, 2035850.0]], "longitud_m": 275, "electrodos": 56, "nota": "Roll-along corto 5m; corona norte y salida hacia cañada NE"},
        {"id": "T1", "tipo": "ERT/IP transversal", "coords": [[666090.0, 2035525.0], [666090.0, 2035920.0]], "longitud_m": 395, "electrodos": 80, "nota": "Cruce N-S occidental (control de cruces L1-L6 y cicatriz incendio)"},
        {"id": "T2", "tipo": "ERT/IP transversal", "coords": [[666210.0, 2035525.0], [666210.0, 2035880.0]], "longitud_m": 355, "electrodos": 72, "nota": "Cruce N-S oriental (control de cruces L1-L6 y cuerpo principal)"},
        {"id": "R1", "tipo": "ERT/IP fondo (aguas arriba)", "coords": [[665680.0, 2035500.0], [665680.0, 2035735.0]], "longitud_m": 235, "electrodos": 48, "nota": "Tendido simple 48 el. @5m; testigo natural aguas arriba (~1815-1825 m)"},
    ]

    piezometros = [
        {"id": "P1", "rol": "Testigo aguas arriba", "E": 665790.0, "N": 2035680.0, "nota": "Matorral intacto aguas arriba (~1810 m) al O del camino"},
        {"id": "P2", "rol": "Aguas abajo — cañada principal NE", "E": 666320.0, "N": 2035870.0, "nota": "Salida directa del drenaje D8 desde laguna NO y corona norte (~1735 m)"},
        {"id": "P3", "rol": "Aguas abajo — pie de talud E", "E": 666435.0, "N": 2035685.0, "nota": "Drenaje del flanco sureste hacia tributario ENE (~1748 m)"},
        {"id": "P4", "rol": "Aguas abajo — control distal NE", "E": 666560.0, "N": 2036045.0, "nota": "Cierre de triángulo hidráulico sobre el arroyo principal hacia Tehuacán (~1692 m)"},
    ]
    for pz in piezometros:
        lon, lat = utm_to_latlon([(pz["E"], pz["N"])])[0]
        pz["lat"], pz["lon"] = round(lat, 6), round(lon, 6)
        r_p = int((my1 - pz["N"]) / 10.0)
        c_p = int((pz["E"] - mx0) / 10.0)
        pz["elev_m"] = round(float(dem10[r_p, c_p]), 1)

    for pf in profiles_geo:
        p0, p1 = pf["coords"]
        (lon0, lat0), (lon1, lat1) = utm_to_latlon([tuple(p0), tuple(p1)])
        pf["wgs84_start"] = [round(lat0, 6), round(lon0, 6)]
        pf["wgs84_end"] = [round(lat1, 6), round(lon1, 6)]

    # Malla EM/magnetometría: envolvente rectangular rotada o buffer de 50 m alrededor de POLY_TOTAL
    txs = [p[0] for p in POLY_TOTAL]
    tys = [p[1] for p in POLY_TOTAL]
    em_bbox = [min(txs) - 50.0, min(tys) - 50.0, max(txs) + 50.0, max(tys) + 50.0]
    em_poly = [
        [em_bbox[0], em_bbox[1]],
        [em_bbox[0], em_bbox[3]],
        [em_bbox[2], em_bbox[3]],
        [em_bbox[2], em_bbox[1]],
        [em_bbox[0], em_bbox[1]],
    ]

    # 3.10 Imagen obligatoria de verificación visual del polígono (_verificacion_poligono_2026.png)
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), dpi=180)
    im_2025 = read_tif(MANIFEST["wayback"][-1]["file"]).astype(np.uint8)
    im_2011 = read_tif(MANIFEST["wayback"][0]["file"]).astype(np.uint8)

    # Panel 1: 2025-08-24 + Polígono A (vértices numerados), Polígono B, subzonas, PROFEPA
    ax = axes[0]
    ax.imshow(im_2025, extent=[fine_bbox[0], fine_bbox[2], fine_bbox[1], fine_bbox[3]], origin="upper")
    ax.add_patch(MplPolygon(POLY_TOTAL, closed=True, fill=False, edgecolor="#FFD600", lw=1.8, ls="--", label="Huella total (B)"))
    ax.add_patch(MplPolygon(POLY_PRINCIPAL, closed=True, fill=False, edgecolor="#00E5FF", lw=2.0, label="Cuerpo principal (A)"))
    ax.add_patch(MplPolygon(POLY_LAGUNA_NO, closed=True, fill=False, edgecolor="#FF4081", lw=1.8, label="Laguna NO"))
    for i, (vx, vy) in enumerate(POLY_PRINCIPAL, 1):
        ax.plot(vx, vy, "o", color="#00E5FF", ms=4, markeredgecolor="black", mew=0.6)
        ax.text(vx + 3, vy + 3, f"V{i}", color="white", fontsize=6, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.1", fc="black", alpha=0.55, lw=0))
    for p in PROFEPA_PTS:
        ax.plot(p["E"], p["N"], "^", color="#FF1744", ms=8, markeredgecolor="white", mew=1.0)
        ax.text(p["E"] + 6, p["N"] - 12, p["id"], color="#FF5252", fontsize=7.5, fontweight="bold",
                bbox=dict(fc="black", alpha=0.65, lw=0, pad=1))
    ax.set_xlim(665820, 666430); ax.set_ylim(2035490, 2035940)
    ax.set_title(f"Verificación 2025-08-24 (0.34 m)\nPrincipal={m_princ['area_ha']} ha | Total={m_total['area_ha']} ha", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_xticks([]); ax.set_yticks([])

    # Panel 2: 2011-06-06 + Núcleo 2011 vs Cuerpo principal 2025
    ax = axes[1]
    ax.imshow(im_2011, extent=[fine_bbox[0], fine_bbox[2], fine_bbox[1], fine_bbox[3]], origin="upper")
    ax.add_patch(MplPolygon(POLY_2011, closed=True, fill=False, edgecolor="#76FF03", lw=2.2, label=f"Núcleo 2011 ({m_2011['area_ha']} ha)"))
    ax.add_patch(MplPolygon(POLY_PRINCIPAL, closed=True, fill=False, edgecolor="#00E5FF", lw=1.6, ls="--", label=f"Expansión 2025 ({m_princ['area_ha']} ha)"))
    ax.set_xlim(665820, 666430); ax.set_ylim(2035490, 2035940)
    ax.set_title(f"Verificación 2011-06-06 (0.5 m)\nExpansión post-2010: +{exp_ha} ha (+{exp_pct}%)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_xticks([]); ax.set_yticks([])

    # Panel 3: dNBR mayo 2022 + huella total + perfiles geofísicos propuestos
    ax = axes[2]
    ax.imshow(im_2025, extent=[fine_bbox[0], fine_bbox[2], fine_bbox[1], fine_bbox[3]], origin="upper", alpha=0.82)
    ax.add_patch(MplPolygon(POLY_TOTAL, closed=True, fill=False, edgecolor="#FFD600", lw=1.8, ls="--"))
    ax.contour(xs10, ys10, dnbr, levels=[0.10, 0.27], colors=["#FF9100", "#FF1744"], linewidths=[1.5, 2.0])
    for pf in profiles_geo:
        c = "#00E676" if pf["id"].startswith("L") else ("#2979FF" if pf["id"].startswith("T") else "#FFFFFF")
        (x0, y0), (x1, y1) = pf["coords"]
        ax.plot([x0, x1], [y0, y1], color=c, lw=1.8)
        ax.text(x0 - 8, y0 + 4, pf["id"], color=c, fontsize=7, fontweight="bold", bbox=dict(fc="black", alpha=0.6, lw=0, pad=0.8))
    for pz in piezometros:
        ax.plot(pz["E"], pz["N"], "s", color="#E040FB", ms=6, markeredgecolor="white", mew=0.8)
        ax.text(pz["E"] + 8, pz["N"] + 6, pz["id"], color="#E040FB", fontsize=7.5, fontweight="bold", bbox=dict(fc="black", alpha=0.65, lw=0, pad=0.8))
    ax.set_xlim(665600, 666620); ax.set_ylim(2035420, 2036120)
    ax.set_title("Verificación incendio dNBR + Diseño geofísico\n(L1-L6, T1-T2, R1 aguas arriba, P1-P4)", fontsize=10, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])

    fig.tight_layout()
    verif_png = os.path.join(RASTERS_DIR, "_verificacion_poligono_2026.png")
    fig.savefig(verif_png, dpi=180)
    plt.close(fig)
    print(f"\nGuardada imagen de verificación: {verif_png}")

    # 3.11 Exportar todos los entregables SIG (GeoJSON, SHP, KML, GPKG, CSV, JSON)
    print("\n--- Exportando archivos SIG en sig/ ---")
    def ring(coords):
        return [list(p) for p in coords] + [list(coords[0])]

    fc_polys_utm = {
        "type": "FeatureCollection",
        "name": "relleno_sanitario_santa_maria_coapan",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32614"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "cuerpo_principal", "nombre": "Cuerpo principal de residuos (2025)", "area_ha": m_princ["area_ha"], "perim_m": m_princ["perimetro_m"], "fuente": "Esri Vivid 2025-08-24 (0.34 m)"},
                "geometry": {"type": "Polygon", "coordinates": [ring(POLY_PRINCIPAL)]},
            },
            {
                "type": "Feature",
                "properties": {"id": "huella_total", "nombre": "Huella operativa total perturbada (2025)", "area_ha": m_total["area_ha"], "perim_m": m_total["perimetro_m"], "fuente": "Esri Vivid 2025-08-24 + área auxiliar SO"},
                "geometry": {"type": "Polygon", "coordinates": [ring(POLY_TOTAL)]},
            },
            {
                "type": "Feature",
                "properties": {"id": "nucleo_2011", "nombre": "Núcleo histórico post-vida útil (2011)", "area_ha": m_2011["area_ha"], "perim_m": m_2011["perimetro_m"], "fuente": "Esri Wayback 2011-06-06 (0.5 m)"},
                "geometry": {"type": "Polygon", "coordinates": [ring(POLY_2011)]},
            },
            {
                "type": "Feature",
                "properties": {"id": "area_auxiliar_so", "nombre": "Zona auxiliar / préstamo / trincheras SO", "area_ha": m_aux["area_ha"], "perim_m": m_aux["perimetro_m"], "fuente": "Esri Wayback 2013-2025"},
                "geometry": {"type": "Polygon", "coordinates": [ring(POLY_AUX_SO)]},
            },
            {
                "type": "Feature",
                "properties": {"id": "laguna_lixiviados_no", "nombre": "Estanque/laguna de lixiviados flanco NO", "area_ha": m_laguna["area_ha"], "perim_m": m_laguna["perimetro_m"], "fuente": "Esri Vivid 2025-08-24"},
                "geometry": {"type": "Polygon", "coordinates": [ring(POLY_LAGUNA_NO)]},
            },
        ],
    }

    poly_utm_gj = os.path.join(SIG_DIR, "relleno_coapan_poligono_utm14n.geojson")
    poly_wgs_gj = os.path.join(SIG_DIR, "relleno_coapan_poligono_wgs84.geojson")
    poly_shp = os.path.join(SIG_DIR, "relleno_coapan_poligono.shp")
    poly_kml = os.path.join(SIG_DIR, "relleno_coapan_poligono.kml")

    with open(poly_utm_gj, "w", encoding="utf-8") as f:
        json.dump(fc_polys_utm, f, ensure_ascii=False, indent=2)

    for p_rm in (poly_wgs_gj, poly_kml):
        if os.path.exists(p_rm):
            os.remove(p_rm)
    subprocess.run(["ogr2ogr", "-overwrite", "-f", "GeoJSON", "-t_srs", "EPSG:4326", poly_wgs_gj, poly_utm_gj], check=True)
    subprocess.run(["ogr2ogr", "-overwrite", "-f", "ESRI Shapefile", "-s_srs", "EPSG:32614", "-t_srs", "EPSG:32614", poly_shp, poly_utm_gj], check=True)
    subprocess.run(["ogr2ogr", "-overwrite", "-f", "KML", "-t_srs", "EPSG:4326", poly_kml, poly_utm_gj], check=True)

    # GeoJSON y KML del diseño geofísico
    geof_feats = []
    for pf in profiles_geo:
        geof_feats.append({
            "type": "Feature",
            "properties": {"id": pf["id"], "tipo": pf["tipo"], "longitud_m": pf["longitud_m"], "electrodos": pf["electrodos"], "nota": pf["nota"]},
            "geometry": {"type": "LineString", "coordinates": pf["coords"]},
        })
    geof_feats.append({
        "type": "Feature",
        "properties": {"id": "Malla_EM_Mag", "tipo": "Malla EM y Magnetometría (predio + 50 m)", "longitud_m": 0, "electrodos": 0, "nota": "Estaciones EM cada 10 m en líneas cada 20 m; Magnetometría líneas 5 m"},
        "geometry": {"type": "Polygon", "coordinates": [em_poly]},
    })
    for pz in piezometros:
        geof_feats.append({
            "type": "Feature",
            "properties": {"id": pz["id"], "tipo": f"Piezómetro ({pz['rol']})", "longitud_m": 0, "electrodos": 0, "elev_m": pz["elev_m"], "nota": pz["nota"]},
            "geometry": {"type": "Point", "coordinates": [pz["E"], pz["N"]]},
        })
    fc_geof_utm = {
        "type": "FeatureCollection",
        "name": "diseno_geofisico_coapan",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32614"}},
        "features": geof_feats,
    }
    geof_utm_gj = os.path.join(SIG_DIR, "diseno_geofisico_georreferenciado_utm14n.geojson")
    geof_wgs_gj = os.path.join(SIG_DIR, "diseno_geofisico_georreferenciado.geojson")
    geof_kml = os.path.join(SIG_DIR, "diseno_geofisico_georreferenciado.kml")
    with open(geof_utm_gj, "w", encoding="utf-8") as f:
        json.dump(fc_geof_utm, f, ensure_ascii=False, indent=2)
    for p_rm in (geof_wgs_gj, geof_kml):
        if os.path.exists(p_rm):
            os.remove(p_rm)
    subprocess.run(["ogr2ogr", "-overwrite", "-f", "GeoJSON", "-t_srs", "EPSG:4326", geof_wgs_gj, geof_utm_gj], check=True)
    subprocess.run(["ogr2ogr", "-overwrite", "-f", "KML", "-t_srs", "EPSG:4326", geof_kml, geof_utm_gj], check=True)

    # GeoPackage multi-capa (para abrir directamente en QGIS)
    gpkg_path = os.path.join(SIG_DIR, "relleno_coapan_tehuacan.gpkg")
    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)

    # Capas separadas temporales para armar el GPKG limpio
    tmp_layers = {}
    def write_tmp_gj(name, feats):
        p = os.path.join(SIG_DIR, f"_tmp_{name}.geojson")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32614"}}, "features": feats}, f)
        tmp_layers[name] = p

    write_tmp_gj("cuerpo_principal", [fc_polys_utm["features"][0]])
    write_tmp_gj("huella_total", [fc_polys_utm["features"][1]])
    write_tmp_gj("nucleo_2011", [fc_polys_utm["features"][2]])
    write_tmp_gj("subzonas", fc_polys_utm["features"][3:])
    write_tmp_gj("puntos_profepa", [{
        "type": "Feature",
        "properties": {"id": p["id"], "coords_oficiales": p["desc"]},
        "geometry": {"type": "Point", "coordinates": [p["E"], p["N"]]}
    } for p in PROFEPA_PTS])
    write_tmp_gj("drenaje_d8", [{
        "type": "Feature",
        "properties": {"label": fp["label"]},
        "geometry": {"type": "LineString", "coordinates": fp["coords"]}
    } for fp in landfill_flow_paths])
    write_tmp_gj("perfiles_geofisicos", [ft for ft in geof_feats if ft["geometry"]["type"] in ("LineString", "Polygon")])
    write_tmp_gj("piezometros", [ft for ft in geof_feats if ft["geometry"]["type"] == "Point"])

    for idx_l, (lname, p_gj) in enumerate(tmp_layers.items()):
        cmd = ["ogr2ogr", "-f", "GPKG"]
        if idx_l > 0:
            cmd.append("-update")
        cmd.extend(["-nln", lname, "-s_srs", "EPSG:32614", "-t_srs", "EPSG:32614", gpkg_path, p_gj])
        subprocess.run(cmd, check=True)
        os.remove(p_gj)

    # CSVs de vértices y diseño geofísico
    csv_verts = os.path.join(SIG_DIR, "vertices_poligono_coapan.csv")
    with open(csv_verts, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["poligono", "vertice", "este_utm14n_m", "norte_utm14n_m", "latitud_wgs84", "longitud_wgs84"])
        for pname, plist in [("cuerpo_principal", POLY_PRINCIPAL), ("huella_total", POLY_TOTAL), ("nucleo_2011", POLY_2011)]:
            lls = utm_to_latlon(plist)
            for i, ((e, n), (lon, lat)) in enumerate(zip(plist, lls), 1):
                w.writerow([pname, f"V{i:02d}", f"{e:.2f}", f"{n:.2f}", f"{lat:.6f}", f"{lon:.6f}"])

    csv_geof = os.path.join(SIG_DIR, "coordenadas_diseno_geofisico.csv")
    with open(csv_geof, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["elemento", "tipo", "inicio_o_pt_E_m", "inicio_o_pt_N_m", "fin_E_m", "fin_N_m", "longitud_m", "electrodos_o_elev", "nota"])
        for pf in profiles_geo:
            (x0, y0), (x1, y1) = pf["coords"]
            w.writerow([pf["id"], pf["tipo"], f"{x0:.1f}", f"{y0:.1f}", f"{x1:.1f}", f"{y1:.1f}", pf["longitud_m"], pf["electrodos"], pf["nota"]])
        for pz in piezometros:
            w.writerow([pz["id"], f"Piezómetro ({pz['rol']})", f"{pz['E']:.1f}", f"{pz['N']:.1f}", "", "", "", f"{pz['elev_m']} m snm", pz["nota"]])

    # Guardar resumen_metricas.json (fuente única de verdad para Paso 4 y Paso 5)
    summary = {
        "poligonos": {
            "cuerpo_principal": m_princ,
            "huella_total": m_total,
            "nucleo_2011": m_2011,
            "area_auxiliar_so": m_aux,
            "laguna_lixiviados_no": m_laguna,
            "expansion_2011_2025_ha": exp_ha,
            "expansion_2011_2025_pct": exp_pct,
        },
        "geometria_listas": {
            "POLY_PRINCIPAL": POLY_PRINCIPAL,
            "POLY_TOTAL": POLY_TOTAL,
            "POLY_2011": POLY_2011,
            "POLY_LAGUNA_NO": POLY_LAGUNA_NO,
            "POLY_AUX_SO": POLY_AUX_SO,
            "EM_BBOX": em_bbox,
        },
        "referencias": {
            "profepa": PROFEPA_PTS,
            "santa_maria_coapan": COAPAN_IGLESIA,
            "distancias_m": {
                "mex_125": dist_mex125,
                "santa_maria_coapan": dist_coapan,
                "san_antonio_texcala": dist_texcala,
                "tehuacan_centro": dist_tehuacan,
            },
        },
        "serie_temporal_1989_2026": ts_records,
        "incendio_mayo_2022": {
            "pre_date": "2022-04-18",
            "active_smoke_date": "2022-05-08",
            "post_date": "2022-05-18",
            "area_dnbr_ge_010_ha": burn_ha_10,
            "area_dnbr_ge_027_ha": burn_ha_27,
            "pct_huella_quemada": round(burn_ha_10 / m_total["area_ha"] * 100.0, 1),
            "dnbr_max": dnbr_max,
            "dnbr_media_cicatriz": dnbr_mean_scar,
        },
        "estado_actual_2026_11_03": {
            "ndvi_mediana_relleno": round(float(np.median(ndvi_2026[mask_princ_10])), 3),
            "ndvi_mediana_testigo": round(float(np.median(ndvi_2026[mask_ctrl_10])), 3),
            "bsi_mediana_relleno": round(float(np.median(bsi_2026[mask_princ_10])), 3),
            "bsi_mediana_testigo": round(float(np.median(bsi_2026[mask_ctrl_10])), 3),
            "ndbi_mediana_relleno": round(float(np.median(ndbi_2026[mask_princ_10])), 3),
        },
        "sar_sentinel1_rel70": {
            "epocas": s1_stats,
            "delta_vv_2021_2026_db": round(dvv, 2),
            "delta_vh_2021_2026_db": round(dvh, 2),
        },
        "ml_kmeans_k5": ml_classes,
        "topografia_hidrologia": {
            "stats": topo_stats,
            "landfill_flow_paths": landfill_flow_paths,
            "stream_lines": stream_lines,
            "perfil_oe": {"e": [round(float(x), 1) for x in prof_oe_e], "z": [round(float(z), 1) for z in prof_oe_z], "n_const": 2035710.0},
            "perfil_ns": {"n": [round(float(x), 1) for x in prof_ns_n], "z": [round(float(z), 1) for z in prof_ns_z], "e_const": 666170.0},
        },
        "diseno_geofisico": {
            "perfiles": profiles_geo,
            "piezometros": piezometros,
            "em_bbox": em_bbox,
        },
    }

    res_json = os.path.join(SIG_DIR, "resumen_metricas.json")
    with open(res_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Resumen métrico guardado en: {res_json}")
    print(f"GeoPackage QGIS guardado en: {gpkg_path}")


if __name__ == "__main__":
    main()
