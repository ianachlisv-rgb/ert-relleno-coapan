#!/usr/bin/env python3
"""
Paso 1: Exploración visual de alta resolución y verificación de ubicación exacta
del relleno sanitario de Santa María Coapan (Tehuacán, Puebla).
Proyecto Final de Geofísica Ambiental (Otoño 2026) — Facultad de Ingeniería, BUAP.
Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale.
"""

import os
import json
import math
import subprocess
from datetime import datetime, timezone
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
RASTERS_DIR = os.path.join(BASE_DIR, "rasters")
SIG_DIR = os.path.join(BASE_DIR, "sig")
MAPAS_DIR = os.path.join(BASE_DIR, "mapas")

for d in [RASTERS_DIR, SIG_DIR, MAPAS_DIR]:
    os.makedirs(d, exist_ok=True)

# Coordenadas de anclaje PROFEPA (Resolución PFPA/03.2/2C27.1/0036/23/0059)
PROFEPA_PTS = [
    {"id": "PROFEPA-1", "desc": "18°24'12.3\"N, 97°25'41.8\"W", "lat": 18 + 24/60 + 12.3/3600, "lon": -(97 + 25/60 + 41.8/3600)},
    {"id": "PROFEPA-2", "desc": "18°24'05.88\"N, 97°25'30.03\"W", "lat": 18 + 24/60 + 5.88/3600, "lon": -(97 + 25/60 + 30.03/3600)},
]

CENTER_LAT = 18.4025
CENTER_LON = -97.4266
ORIGIN_SHIFT = 20037508.342789244


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def latlon_to_utm14n(points):
    """Convierte lista de (lon, lat) a (E, N) en EPSG:32614 vía gdaltransform."""
    inp = "\n".join(f"{lon} {lat}" for lon, lat in points) + "\n"
    res = subprocess.run(
        ["gdaltransform", "-s_srs", "EPSG:4326", "-t_srs", "EPSG:32614"],
        input=inp, text=True, capture_output=True, check=True
    )
    out = []
    for line in res.stdout.strip().splitlines():
        parts = line.strip().split()
        out.append((float(parts[0]), float(parts[1])))
    return out


def fetch_esri_metadata(lon, lat):
    url = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/0/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "SRC_DATE2,SRC_RES,NICE_NAME,SRC_DESC",
        "returnGeometry": "false",
        "f": "json",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    feats = r.json().get("features", [])
    results = []
    for f in feats:
        a = f.get("attributes", {})
        ts = a.get("SRC_DATE2")
        dt_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "N/A"
        results.append({
            "date": dt_str,
            "res_m": a.get("SRC_RES"),
            "source": a.get("NICE_NAME"),
            "desc": a.get("SRC_DESC"),
        })
    return results


def download_tile(args):
    url, tx, ty = args
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "BUAP-GeofisicaAmbiental-Coapan/1.0"})
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                return tx, ty, img
        except Exception:
            pass
    raise RuntimeError(f"Failed downloading tile {url}")


def download_esri_mosaic(lat, lon, zoom, radius_tiles, url_template, out_utm_tif):
    cx, cy = deg2num(lat, lon, zoom)
    xs = range(cx - radius_tiles, cx + radius_tiles + 1)
    ys = range(cy - radius_tiles, cy + radius_tiles + 1)

    tasks = []
    for ty in ys:
        for tx in xs:
            u = url_template.format(z=zoom, y=ty, x=tx)
            tasks.append((u, tx, ty))

    nx, ny = len(xs), len(ys)
    mosaic = Image.new("RGB", (nx * 256, ny * 256))
    with ThreadPoolExecutor(max_workers=12) as ex:
        for tx, ty, img in ex.map(download_tile, tasks):
            mosaic.paste(img, ((tx - xs.start) * 256, (ty - ys.start) * 256))

    tmp_png = out_utm_tif.replace(".tif", "_3857.png")
    tmp_3857 = out_utm_tif.replace(".tif", "_3857.tif")
    mosaic.save(tmp_png)

    n = 2.0 ** zoom
    tile_m = 2.0 * ORIGIN_SHIFT / n
    ulx = -ORIGIN_SHIFT + xs.start * tile_m
    uly = ORIGIN_SHIFT - ys.start * tile_m
    lrx = -ORIGIN_SHIFT + (xs.stop) * tile_m
    lry = ORIGIN_SHIFT - (ys.stop) * tile_m

    subprocess.run([
        "gdal_translate", "-of", "GTiff", "-a_srs", "EPSG:3857",
        "-a_ullr", str(ulx), str(uly), str(lrx), str(lry),
        tmp_png, tmp_3857
    ], check=True, capture_output=True)

    subprocess.run([
        "gdalwarp", "-overwrite", "-t_srs", "EPSG:32614", "-r", "cubic",
        "-co", "COMPRESS=DEFLATE", tmp_3857, out_utm_tif
    ], check=True, capture_output=True)

    for p in (tmp_png, tmp_3857):
        if os.path.exists(p):
            os.remove(p)

    return out_utm_tif


def fetch_osm_context():
    """Consulta vías, localidades y uso de suelo en entorno amplio vía Overpass."""
    query = """[out:json][timeout:25];
(
  way["highway"~"trunk|primary|secondary|tertiary|unclassified|track"](18.36,-97.47,18.46,-97.37);
  way["landuse"="landfill"](18.36,-97.47,18.46,-97.37);
  relation["landuse"="landfill"](18.36,-97.47,18.46,-97.37);
  node["place"~"city|town|village|hamlet|suburb"](18.35,-97.49,18.48,-97.35);
  way["waterway"](18.37,-97.46,18.44,-97.38);
);
out body;
>;
out skel qt;"""
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    data = None
    for ep in endpoints:
        try:
            r = requests.post(
                ep, data={"data": query},
                headers={"User-Agent": "BUAP-GeofisicaAmbiental-Coapan/1.0"},
                timeout=30
            )
            if r.status_code == 200:
                data = r.json()
                print(f"Overpass OK desde {ep}: {len(data.get('elements', []))} elementos")
                break
            else:
                print(f"Overpass {ep} -> HTTP {r.status_code}")
        except Exception as e:
            print(f"Overpass {ep} error: {e}")

    if data is None:
        print("ADVERTENCIA: No se pudo descargar contexto OSM; se continuará sin capa OSM.")
        return None

    nodes = {}
    features = []
    for el in data.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
            if "tags" in el and "place" in el["tags"]:
                features.append({
                    "type": "Feature",
                    "properties": {"osm_id": el["id"], "layer": "place", **el["tags"]},
                    "geometry": {"type": "Point", "coordinates": [el["lon"], el["lat"]]},
                })
    for el in data.get("elements", []):
        if el["type"] == "way" and "nodes" in el:
            coords = [list(nodes[nid]) for nid in el["nodes"] if nid in nodes]
            if len(coords) < 2:
                continue
            tags = el.get("tags", {})
            is_poly = (tags.get("landuse") == "landfill") and (coords[0] == coords[-1]) and len(coords) >= 4
            geom = {"type": "Polygon", "coordinates": [coords]} if is_poly else {"type": "LineString", "coordinates": coords}
            layer = "landfill" if tags.get("landuse") == "landfill" else ("waterway" if "waterway" in tags else "highway")
            features.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "layer": layer, **tags},
                "geometry": geom,
            })

    fc = {"type": "FeatureCollection", "features": features}
    out_gj = os.path.join(SIG_DIR, "osm_contexto_wgs84.geojson")
    with open(out_gj, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)

    out_utm = os.path.join(SIG_DIR, "osm_contexto_utm14n.geojson")
    subprocess.run([
        "ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:32614", out_utm, out_gj
    ], check=True)
    return out_utm


def read_geotiff_rgb(tif_path):
    """Lee un GeoTIFF RGB sin depender de rasterio usando gdalinfo + PIL/raw."""
    info = json.loads(subprocess.check_output(["gdalinfo", "-json", tif_path], text=True))
    w, h = info["size"]
    gt = info["geoTransform"]
    xmin = gt[0]
    ymax = gt[3]
    px_w = gt[1]
    px_h = gt[5]
    xmax = xmin + w * px_w
    ymin = ymax + h * px_h

    raw_tif = tif_path + ".tmp_uncomp.tif"
    subprocess.run(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=NONE", tif_path, raw_tif],
                   check=True, capture_output=True)
    img = np.array(Image.open(raw_tif))
    os.remove(raw_tif)
    return img, (xmin, xmax, ymin, ymax), info


def main():
    print("=== Paso 1: Exploración visual de alta resolución ===")
    meta = fetch_esri_metadata(CENTER_LON, CENTER_LAT)
    print("Metadatos Esri World Imagery actuales:", json.dumps(meta, indent=2, ensure_ascii=False))
    with open(os.path.join(RASTERS_DIR, "esri_2026_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Descargar mosaico z=17, radio 4 -> 9x9 tiles (~2.6 km x 2.6 km, ~1.1 m/px)
    out_tif = os.path.join(RASTERS_DIR, "esri_2026_utm14n.tif")
    url_tpl = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    print("Descargando mosaico Esri World Imagery z=17 (9x9 tiles)...")
    download_esri_mosaic(CENTER_LAT, CENTER_LON, zoom=17, radius_tiles=4, url_template=url_tpl, out_utm_tif=out_tif)

    # Descargar contexto OSM
    osm_utm_gj = fetch_osm_context()

    # Transformar puntos PROFEPA a UTM 14N
    utm_coords = latlon_to_utm14n([(p["lon"], p["lat"]) for p in PROFEPA_PTS])
    for p, (e, n) in zip(PROFEPA_PTS, utm_coords):
        p["E"] = e
        p["N"] = n
        print(f"  {p['id']}: E={e:.2f} m, N={n:.2f} m ({p['desc']})")

    # Leer imagen y generar figura de inspección con grilla de 100 m y 50 m
    img, (xmin, xmax, ymin, ymax), info = read_geotiff_rgb(out_tif)
    print(f"Raster UTM14N shape={img.shape}, extent=({xmin:.1f}, {xmax:.1f}, {ymin:.1f}, {ymax:.1f})")

    # Enfocar vista de inspección en +-900 m alrededor del promedio de los puntos PROFEPA
    e_c = np.mean([p["E"] for p in PROFEPA_PTS])
    n_c = np.mean([p["N"] for p in PROFEPA_PTS])
    vx0, vx1 = e_c - 800, e_c + 800
    vy0, vy1 = n_c - 800, n_c + 800

    fig, ax = plt.subplots(figsize=(14, 14), dpi=180)
    ax.imshow(img, extent=[xmin, xmax, ymin, ymax], origin="upper")

    # Superponer carreteras OSM y eventual polígono landfill
    if osm_utm_gj and os.path.exists(osm_utm_gj):
        with open(osm_utm_gj, "r", encoding="utf-8") as f:
            gj = json.load(f)
        for feat in gj.get("features", []):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            gtype = geom.get("type")
            if props.get("layer") == "highway" and gtype == "LineString":
                xs = [c[0] for c in geom["coordinates"]]
                ys = [c[1] for c in geom["coordinates"]]
                hw = props.get("highway", "")
                lw = 2.0 if hw in ("trunk", "primary") else 1.0
                col = "#FFD54F" if hw in ("trunk", "primary") else "#90CAF9"
                ax.plot(xs, ys, color=col, linewidth=lw, alpha=0.85)
            elif props.get("layer") == "landfill" and gtype == "Polygon":
                xs = [c[0] for c in geom["coordinates"][0]]
                ys = [c[1] for c in geom["coordinates"][0]]
                ax.plot(xs, ys, color="#00E676", linewidth=2.5, linestyle="--", label="OSM landuse=landfill")

    # Grilla UTM cada 100 m (principal) y 50 m (secundaria)
    e_start = math.floor(vx0 / 100) * 100
    e_end = math.ceil(vx1 / 100) * 100
    n_start = math.floor(vy0 / 100) * 100
    n_end = math.ceil(vy1 / 100) * 100

    ax.set_xticks(np.arange(e_start, e_end + 1, 100))
    ax.set_yticks(np.arange(n_start, n_end + 1, 100))
    ax.set_xticks(np.arange(e_start, e_end + 1, 50), minor=True)
    ax.set_yticks(np.arange(n_start, n_end + 1, 50), minor=True)
    ax.grid(which="major", color="cyan", linestyle="-", linewidth=0.8, alpha=0.65)
    ax.grid(which="minor", color="white", linestyle=":", linewidth=0.5, alpha=0.4)

    # Puntos PROFEPA
    for p in PROFEPA_PTS:
        ax.plot(p["E"], p["N"], marker="o", markersize=10, color="#FF1744", markeredgecolor="white", markeredgewidth=1.5, zorder=10)
        ax.text(p["E"] + 15, p["N"] + 15, f"{p['id']}\n({p['E']:.0f}, {p['N']:.0f})",
                color="yellow", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="black", alpha=0.7), zorder=11)

    ax.set_xlim(vx0, vx1)
    ax.set_ylim(vy0, vy1)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    plt.xticks(rotation=30, fontsize=8)
    plt.yticks(fontsize=8)
    ax.set_xlabel("Este UTM Zona 14N (m) — EPSG:32614", fontsize=11, fontweight="bold")
    ax.set_ylabel("Norte UTM Zona 14N (m) — EPSG:32614", fontsize=11, fontweight="bold")
    date_lbl = meta[0]["date"] if meta else "Actual"
    ax.set_title(
        f"Inspección visual de alta resolución — Relleno Sanitario Santa María Coapan\n"
        f"Esri World Imagery (captura {date_lbl}) | Grilla métrica 100 m / 50 m (EPSG:32614)",
        fontsize=13, fontweight="bold"
    )

    out_png = os.path.join(RASTERS_DIR, "_inspeccion_grid_2026.png")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    print(f"Guardada imagen de inspección: {out_png}")


if __name__ == "__main__":
    main()
