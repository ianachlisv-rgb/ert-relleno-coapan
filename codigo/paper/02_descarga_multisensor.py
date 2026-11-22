#!/usr/bin/env python3
"""
Paso 2: Adquisición multitemporal y multisensor alineada a EPSG:32614 (UTM Zona 14N).
Fuentes:
  - Esri World Imagery Wayback (alta resolución 2011-2025, z=17/18)
  - USGS Landsat Collection 2 Level-2 (1989-2015, 30 m)
  - ESA Sentinel-2 L2A (2020-2026, 10 m, incl. evento de incendio mayo 2022)
  - ESA Sentinel-1 RTC SAR banda C (órbita descendente rel=70, VV/VH, 10 m)
  - Copernicus DEM GLO-30 (30 m y remuestreado a 10 m)

Proyecto Final de Geofísica Ambiental (Otoño 2026) — Facultad de Ingeniería, BUAP.
Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale.
"""

import os
import json
import math
import subprocess
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
RASTERS_DIR = os.path.join(BASE_DIR, "rasters")
WB_DIR = os.path.join(RASTERS_DIR, "wayback")
LS_DIR = os.path.join(RASTERS_DIR, "landsat")
S2_DIR = os.path.join(RASTERS_DIR, "sentinel2")
S1_DIR = os.path.join(RASTERS_DIR, "sentinel1")
DEM_DIR = os.path.join(RASTERS_DIR, "dem")

for d in [WB_DIR, LS_DIR, S2_DIR, S1_DIR, DEM_DIR]:
    os.makedirs(d, exist_ok=True)

# Grids maestros en EPSG:32614 (UTM Zona 14N)
FINE_BBOX = (665400.0, 2035050.0, 666850.0, 2036300.0)     # 1450 x 1250 m (0.6 m/px)
MED_BBOX = (664000.0, 2033600.0, 668500.0, 2038400.0)      # 4500 x 4800 m (10 m/px)
REG_BBOX = (663000.0, 2032600.0, 669300.0, 2038900.0)      # 6300 x 6300 m (30 m/px)

CENTER_UTM = (666140.0, 2035700.0)
ORIGIN_SHIFT = 20037508.342789244
PC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token"


def utm_to_latlon(pts):
    inp = "\n".join(f"{e} {n}" for e, n in pts) + "\n"
    res = subprocess.run(
        ["gdaltransform", "-s_srs", "EPSG:32614", "-t_srs", "EPSG:4326"],
        input=inp, text=True, capture_output=True, check=True
    )
    out = []
    for line in res.stdout.strip().splitlines():
        p = line.strip().split()
        out.append((float(p[0]), float(p[1])))  # lon, lat
    return out


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    return int((lon_deg + 180.0) / 360.0 * n), int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)


def get_sas_token(collection):
    r = requests.get(f"{PC_SAS}/{collection}", timeout=15)
    r.raise_for_status()
    return r.json()["token"]


def warp_vsicurl(href, sas_token, out_tif, bbox, tr, resampling="bilinear", dst_nodata=None):
    url = f"{href}?{sas_token}" if sas_token else href
    xmin, ymin, xmax, ymax = bbox
    cmd = [
        "gdalwarp", "-overwrite", "-t_srs", "EPSG:32614",
        "-te", str(xmin), str(ymin), str(xmax), str(ymax),
        "-tr", str(tr), str(tr), "-tap",
        "-r", resampling,
        "-co", "COMPRESS=DEFLATE",
    ]
    if dst_nodata is not None:
        cmd.extend(["-dstnodata", str(dst_nodata)])
    cmd.extend([f"/vsicurl/{url}", out_tif])
    subprocess.run(cmd, check=True, capture_output=True)


def read_band_array(tif_path):
    tmp = tif_path + ".raw.tif"
    subprocess.run(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=NONE", tif_path, tmp],
                   check=True, capture_output=True)
    arr = np.array(Image.open(tmp))
    os.remove(tmp)
    return arr


def download_tile(args):
    url, tx, ty = args
    for _ in range(3):
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "BUAP-GeofisicaAmbiental-Coapan/1.0"})
            if r.status_code == 200:
                return tx, ty, Image.open(BytesIO(r.content)).convert("RGB")
        except Exception:
            pass
    raise RuntimeError(f"Error descargando tile {url}")


def download_wayback_all():
    print("\n--- 1. Esri World Imagery Wayback (z=17/18 -> 0.6 m/px) ---")
    (lon_min, lat_min), (lon_max, lat_max) = utm_to_latlon([
        (FINE_BBOX[0], FINE_BBOX[1]),
        (FINE_BBOX[2], FINE_BBOX[3]),
    ])
    (lon_c, lat_c) = utm_to_latlon([CENTER_UTM])[0]

    wb = requests.get("https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json", timeout=20).json()
    # Las 9 versiones únicas identificadas vía tilemap (orden cronológico)
    target_rids = [
        ("10", "2014-02-20"),
        ("13770", "2016-10-12"),
        ("13067", "2018-02-23"),
        ("42403", "2021-11-03"),
        ("47471", "2022-09-21"),
        ("1034", "2023-10-11"),
        ("56450", "2024-10-10"),
        ("58924", "2025-09-25"),
        ("63116", "2026-09-24"),
    ]

    wb_records = []
    for rid, wb_date in target_rids:
        info = wb[rid]
        tpl = info["itemURL"]
        # Detectar zoom máximo disponible (18 si existe, si no 17)
        cx18, cy18 = deg2num(lat_c, lon_c, 18)
        test_url = tpl.replace("{level}", "18").replace("{row}", str(cy18)).replace("{col}", str(cx18))
        try:
            tr = requests.get(test_url, timeout=8)
            z = 18 if (tr.status_code == 200 and "image" in tr.headers.get("Content-Type", "")) else 17
        except Exception:
            z = 17
        x0, y1 = deg2num(lat_min, lon_min, z)
        x1, y0 = deg2num(lat_max, lon_max, z)
        xs = range(x0 - 1, x1 + 2)
        ys = range(y0 - 1, y1 + 2)

        # Consultar metadata real (SRC_DATE2, SRC_RES, NICE_NAME)
        meta_url = info.get("metadataLayerUrl", "")
        src_date, src_res, src_name = "N/D", "N/D", "N/D"
        if meta_url:
            for attempt in range(2):
                try:
                    mr = requests.get(f"{meta_url}/identify", params={
                        "geometry": f"{lon_c},{lat_c}",
                        "geometryType": "esriGeometryPoint",
                        "sr": "4326",
                        "layers": "all",
                        "tolerance": "1",
                        "mapExtent": f"{lon_c-0.01},{lat_c-0.01},{lon_c+0.01},{lat_c+0.01}",
                        "imageDisplay": "400,400,96",
                        "returnGeometry": "false",
                        "f": "json",
                    }, timeout=25).json()
                    results = mr.get("results", [])
                    if results:
                        attrs = results[0].get("attributes", {})
                        src_date = str(attrs.get("SRC_DATE2", "N/D")).strip()
                        src_res = str(attrs.get("SRC_RES", "N/D")).strip()
                        src_name = str(attrs.get("NICE_NAME", "N/D")).strip() or "Esri Archive"
                        break
                except Exception:
                    pass

        out_tif = os.path.join(WB_DIR, f"wayback_rid{rid}_{wb_date}.tif")
        if not os.path.exists(out_tif):
            tasks = [(tpl.replace("{level}", str(z)).replace("{row}", str(ty)).replace("{col}", str(tx)), tx, ty)
                     for ty in ys for tx in xs]
            mosaic = Image.new("RGB", (len(xs) * 256, len(ys) * 256))
            with ThreadPoolExecutor(max_workers=16) as ex:
                for tx, ty, im in ex.map(download_tile, tasks):
                    mosaic.paste(im, ((tx - xs.start) * 256, (ty - ys.start) * 256))

            tmp_png = out_tif.replace(".tif", "_3857.png")
            tmp_3857 = out_tif.replace(".tif", "_3857.tif")
            mosaic.save(tmp_png)
            n = 2.0 ** z
            tile_m = 2.0 * ORIGIN_SHIFT / n
            ulx = -ORIGIN_SHIFT + xs.start * tile_m
            uly = ORIGIN_SHIFT - ys.start * tile_m
            lrx = -ORIGIN_SHIFT + xs.stop * tile_m
            lry = ORIGIN_SHIFT - ys.stop * tile_m
            subprocess.run([
                "gdal_translate", "-of", "GTiff", "-a_srs", "EPSG:3857",
                "-a_ullr", str(ulx), str(uly), str(lrx), str(lry), tmp_png, tmp_3857
            ], check=True, capture_output=True)
            xmin, ymin, xmax, ymax = FINE_BBOX
            subprocess.run([
                "gdalwarp", "-overwrite", "-t_srs", "EPSG:32614",
                "-te", str(xmin), str(ymin), str(xmax), str(ymax),
                "-tr", "0.6", "0.6", "-r", "cubic", "-co", "COMPRESS=DEFLATE",
                tmp_3857, out_tif
            ], check=True, capture_output=True)
            for p in (tmp_png, tmp_3857):
                if os.path.exists(p):
                    os.remove(p)

        print(f"  Wayback {wb_date} (rid={rid}, z={z}) -> captura real={src_date}, res={src_res} m, fuente={src_name}")
        wb_records.append({
            "rid": rid, "wayback_release": wb_date, "zoom": z,
            "capture_date": src_date, "res_m": src_res, "source": src_name,
            "file": os.path.relpath(out_tif, BASE_DIR),
        })

    # Crear mosaico rápido de inspección 3x3 centrado en el relleno (665750..666550, 2035400..2036000)
    fig, axes = plt.subplots(3, 3, figsize=(15, 12.5), dpi=150)
    for ax, rec in zip(axes.flat, wb_records):
        tif = os.path.join(BASE_DIR, rec["file"])
        im = read_band_array(tif)
        # Recorte interno para ver bien el relleno
        xmin, ymin, xmax, ymax = FINE_BBOX
        ax.imshow(im, extent=[xmin, xmax, ymin, ymax], origin="upper")
        ax.set_xlim(665750, 666500)
        ax.set_ylim(2035400, 2036000)
        ax.set_title(f"Release {rec['wayback_release']} (rid={rec['rid']})\nCaptura real: {rec['capture_date']} ({rec['res_m']}m)", fontsize=9.5, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Inspección de capturas históricas únicas — Esri Wayback (Santa María Coapan)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    insp_wb = os.path.join(RASTERS_DIR, "_inspeccion_wayback.png")
    fig.savefig(insp_wb, dpi=150)
    plt.close(fig)
    print(f"Guardada inspección Wayback: {insp_wb}")
    return wb_records


def download_landsat():
    print("\n--- 2. USGS Landsat Collection 2 Level-2 (30 m, 1989-2015) ---")
    sas = get_sas_token("landsat-c2-l2")
    target_ids = [
        ("1989_pre", "LT04_L2SP_025047_19891026_02_T1"),
        ("1993_ini", "LT05_L2SP_025047_19930215_02_T1"),
        ("1994_dic", "LT05_L2SP_025047_19941203_02_T1"),
        ("1995_mar", "LT05_L2SP_025047_19950325_02_T1"),
        ("1995_dic", "LT05_L2SP_025047_19951206_02_T1"),
        ("1996_abr", "LT05_L2SP_025047_19960412_02_T1"),
        ("1998_tem", "LT05_L2SP_025047_19980317_02_T1"),
        ("2001_op1", "LT05_L2SP_025047_20010221_02_T1"),
        ("2011_fin", "LT05_L2SP_025047_20110217_02_T1"),
        ("2015_op2", "LC08_L2SP_025047_20150519_02_T1"),
    ]
    bands = ["blue", "green", "red", "nir08", "swir16", "swir22", "qa_pixel"]
    records = []

    for tag, item_id in target_ids:
        r = requests.post(PC_SEARCH, json={"collections": ["landsat-c2-l2"], "ids": [item_id]}, timeout=15).json()
        feat = r["features"][0]
        props = feat["properties"]
        dt = props["datetime"][:10]
        plat = props.get("platform")
        cc = props.get("eo:cloud_cover")
        sub = os.path.join(LS_DIR, f"{tag}_{dt}_{plat}")
        os.makedirs(sub, exist_ok=True)
        files = {}
        for b in bands:
            out_tif = os.path.join(sub, f"{b}.tif")
            if not os.path.exists(out_tif):
                resamp = "near" if b == "qa_pixel" else "bilinear"
                warp_vsicurl(feat["assets"][b]["href"], sas, out_tif, REG_BBOX, 30, resampling=resamp)
            files[b] = os.path.relpath(out_tif, BASE_DIR)

        # Verificar qa_pixel libre de nubes/sombras sobre el relleno (bits 1=dilated cloud, 3=cloud, 4=shadow)
        qa = read_band_array(os.path.join(BASE_DIR, files["qa_pixel"]))
        # Ventana central alrededor del relleno en REG_BBOX (6300x6300 @30m -> 210x210; relleno ~px 95..120)
        qa_sub = qa[95:125, 90:120]
        bad_mask = (qa_sub & ((1 << 1) | (1 << 3) | (1 << 4))) != 0
        pct_bad = float(np.mean(bad_mask) * 100.0)
        print(f"  {tag} ({item_id}, {dt}, {plat}): escena cc={cc}%, AOI nube/sombra={pct_bad:.1f}%")
        records.append({
            "tag": tag, "id": item_id, "date": dt, "platform": plat,
            "scene_cc": cc, "aoi_cloud_pct": pct_bad, "bands": files
        })
    return records


def download_sentinel2():
    print("\n--- 3. ESA Sentinel-2 L2A (10 m, 2020-2026) ---")
    sas = get_sas_token("sentinel-2-l2a")
    target_ids = [
        ("2020_op", "S2B_MSIL2A_20200223T165309_R026_T14QPF_20200928T011305"),
        ("2022_prefire_0418", "S2A_MSIL2A_20220418T164851_R026_T14QPF_20220419T005937"),
        ("2022_prefire_0428", "S2A_MSIL2A_20220428T164851_R026_T14QPF_20220429T110631"),
        ("2022_fire_0508", "S2A_MSIL2A_20220508T164851_R026_T14QPF_20240614T144944"),
        ("2022_fire_0513", "S2B_MSIL2A_20220513T164839_R026_T14QPF_20220516T045527"),
        ("2022_postfire_0518", "S2A_MSIL2A_20220518T164851_R026_T14QPF_20220520T130607"),
        ("2022_postfire_0523", "S2B_MSIL2A_20220523T164839_R026_T14QPF_20220524T073704"),
        ("2026_cur_1103", "S2C_MSIL2A_20261103T165451_R026_T14QPF_20261103T194307"),
        ("2026_cur_1115", "S2A_MSIL2A_20261115T165701_R026_T14QPF_20261115T232507"),
    ]
    bands = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12", "SCL"]
    records = []

    for tag, item_id in target_ids:
        r = requests.post(PC_SEARCH, json={"collections": ["sentinel-2-l2a"], "ids": [item_id]}, timeout=15).json()
        feat = r["features"][0]
        props = feat["properties"]
        dt = props["datetime"][:10]
        baseline = props.get("s2:processing_baseline", "00.00")
        offset = -1000.0 if float(baseline) >= 4.0 else 0.0
        sub = os.path.join(S2_DIR, f"{tag}_{dt}")
        os.makedirs(sub, exist_ok=True)
        files = {}
        for b in bands:
            out_tif = os.path.join(sub, f"{b}.tif")
            if not os.path.exists(out_tif):
                resamp = "near" if b == "SCL" else "bilinear"
                warp_vsicurl(feat["assets"][b]["href"], sas, out_tif, MED_BBOX, 10, resampling=resamp)
            files[b] = os.path.relpath(out_tif, BASE_DIR)

        scl = read_band_array(os.path.join(BASE_DIR, files["SCL"]))
        # MED_BBOX: E 664000..668500 (450 px), N 2033600..2038400 (480 px).
        # Relleno ~ E 665800..666450 (col 180..245), N 2035500..2035950 (row 245..290)
        scl_sub = scl[245:290, 180:245]
        # SCL clouds/shadow/cirrus: 3=shadow, 8=med cloud, 9=high cloud, 10=cirrus
        bad = np.isin(scl_sub, [0, 1, 3, 8, 9, 10])
        pct_bad = float(np.mean(bad) * 100.0)
        print(f"  {tag} ({dt}, baseline={baseline}, offset={offset}): escena cc={props.get('eo:cloud_cover'):.1f}%, relleno nube/sombra={pct_bad:.1f}%")
        records.append({
            "tag": tag, "id": item_id, "date": dt, "baseline": baseline,
            "boa_offset": offset, "scale": 0.0001, "scene_cc": props.get("eo:cloud_cover"),
            "landfill_cloud_pct": pct_bad, "bands": files
        })
    return records


def download_sentinel1():
    print("\n--- 4. ESA Sentinel-1 RTC SAR banda C (10 m, órbita descendente rel=70) ---")
    sas = get_sas_token("sentinel-1-rtc")
    pt = {"type": "Point", "coordinates": list(utm_to_latlon([CENTER_UTM])[0])}
    epochs = [
        ("2021_pre_cierre", "2021-01-01/2021-10-05"),
        ("2023_post_clausura", "2023-07-01/2023-12-31"),
        ("2026_actual", "2026-10-01/2026-11-21"),
    ]
    records = []
    for tag, dr in epochs:
        r = requests.post(PC_SEARCH, json={
            "collections": ["sentinel-1-rtc"],
            "intersects": pt,
            "datetime": dr,
            "query": {"sat:orbit_state": {"eq": "descending"}, "sat:relative_orbit": {"eq": 70}},
            "limit": 20,
        }, timeout=15).json()
        feats = sorted(r.get("features", []), key=lambda x: x["properties"]["datetime"])
        if not feats:
            print(f"  ADVERTENCIA: sin escenas descendente rel=70 para {tag}")
            continue
        # Elegir última escena dentro de la ventana (en 2021-09, 2023-11/12, 2026-11)
        feat = feats[-1]
        props = feat["properties"]
        dt = props["datetime"][:10]
        plat = props.get("platform")
        sub = os.path.join(S1_DIR, f"{tag}_{dt}")
        os.makedirs(sub, exist_ok=True)
        files = {}
        for pol in ["vv", "vh"]:
            out_tif = os.path.join(sub, f"{pol}.tif")
            if not os.path.exists(out_tif):
                warp_vsicurl(feat["assets"][pol]["href"], sas, out_tif, MED_BBOX, 10, resampling="bilinear")
            files[pol] = os.path.relpath(out_tif, BASE_DIR)
        print(f"  {tag} ({feat['id']}, {dt}, {plat}, orbit={props.get('sat:orbit_state')} rel={props.get('sat:relative_orbit')})")
        records.append({
            "tag": tag, "id": feat["id"], "date": dt, "platform": plat,
            "orbit_state": props.get("sat:orbit_state"),
            "relative_orbit": props.get("sat:relative_orbit"),
            "pols": files,
        })
    return records


def download_dem():
    print("\n--- 5. Copernicus DEM GLO-30 (30 m y 10 m) ---")
    sas = get_sas_token("cop-dem-glo-30")
    pt = {"type": "Point", "coordinates": list(utm_to_latlon([CENTER_UTM])[0])}
    r = requests.post(PC_SEARCH, json={"collections": ["cop-dem-glo-30"], "intersects": pt, "limit": 2}, timeout=15).json()
    feat = r["features"][0]
    href = feat["assets"]["data"]["href"]

    dem_30 = os.path.join(DEM_DIR, "cop_dem_30m_utm14n.tif")
    dem_10 = os.path.join(DEM_DIR, "cop_dem_10m_utm14n.tif")
    hill_30 = os.path.join(DEM_DIR, "cop_dem_30m_hillshade.tif")
    slope_30 = os.path.join(DEM_DIR, "cop_dem_30m_slope_deg.tif")
    slope_10 = os.path.join(DEM_DIR, "cop_dem_10m_slope_deg.tif")

    if not os.path.exists(dem_30):
        warp_vsicurl(href, sas, dem_30, REG_BBOX, 30, resampling="bilinear")
    if not os.path.exists(dem_10):
        warp_vsicurl(href, sas, dem_10, MED_BBOX, 10, resampling="bilinear")

    subprocess.run(["gdaldem", "hillshade", dem_30, hill_30, "-z", "1.5", "-az", "315", "-alt", "45", "-co", "COMPRESS=DEFLATE"], check=True, capture_output=True)
    subprocess.run(["gdaldem", "slope", dem_30, slope_30, "-co", "COMPRESS=DEFLATE"], check=True, capture_output=True)
    subprocess.run(["gdaldem", "slope", dem_10, slope_10, "-co", "COMPRESS=DEFLATE"], check=True, capture_output=True)

    print(f"  DEM 30m y 10m generados con hillshade y pendiente: {feat['id']}")
    return {
        "id": feat["id"],
        "dem_30m": os.path.relpath(dem_30, BASE_DIR),
        "dem_10m": os.path.relpath(dem_10, BASE_DIR),
        "hillshade_30m": os.path.relpath(hill_30, BASE_DIR),
        "slope_30m": os.path.relpath(slope_30, BASE_DIR),
        "slope_10m": os.path.relpath(slope_10, BASE_DIR),
    }


def main():
    manifest = {
        "crs": "EPSG:32614",
        "fine_bbox": FINE_BBOX,
        "med_bbox": MED_BBOX,
        "reg_bbox": REG_BBOX,
        "wayback": download_wayback_all(),
        "landsat": download_landsat(),
        "sentinel2": download_sentinel2(),
        "sentinel1": download_sentinel1(),
        "dem": download_dem(),
    }
    out_json = os.path.join(RASTERS_DIR, "manifesto_sensores.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nManifiesto completo guardado en: {out_json}")


if __name__ == "__main__":
    main()
