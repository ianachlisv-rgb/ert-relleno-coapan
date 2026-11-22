#!/usr/bin/env python3
"""
Paso 4: Generación de las 5 figuras cartográficas (300 DPI PNG y PDF) con estética
cartográfica clásica académica / SIG (~2010: ArcGIS / INEGI / IEEE).
Proyecto Final de Geofísica Ambiental (Otoño 2026) — Facultad de Ingeniería, BUAP.
Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale.
"""

import os
import json
import subprocess

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.lines import Line2D

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
RASTERS_DIR = os.path.join(BASE_DIR, "rasters")
SIG_DIR = os.path.join(BASE_DIR, "sig")
MAPAS_DIR = os.path.join(BASE_DIR, "mapas")
os.makedirs(MAPAS_DIR, exist_ok=True)

with open(os.path.join(RASTERS_DIR, "manifesto_sensores.json"), "r", encoding="utf-8") as f:
    MANIFEST = json.load(f)
with open(os.path.join(SIG_DIR, "resumen_metricas.json"), "r", encoding="utf-8") as f:
    METRICS = json.load(f)

AUTORES = "Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale — Facultad de Ingeniería, BUAP"
PROY_TXT = "Geofísica Ambiental (Otoño 2026) | CRS: WGS 84 / UTM Zona 14N (EPSG:32614)"

# Estilo tipográfico clásico 2010 (equivalente Arial / Times)
plt.rcParams.update({
    "font.family": "Liberation Sans",
    "axes.edgecolor": "#000000",
    "axes.linewidth": 1.0,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

HALO_W = [pe.withStroke(linewidth=2.4, foreground="white")]
HALO_W_THIN = [pe.withStroke(linewidth=1.8, foreground="white")]


def read_tif(rel_or_abs, dtype=np.float32):
    p = rel_or_abs if os.path.isabs(rel_or_abs) else os.path.join(BASE_DIR, rel_or_abs)
    tmp = p + ".maptmp.tif"
    subprocess.run(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=NONE", p, tmp],
                   check=True, capture_output=True)
    arr = np.array(Image.open(tmp), dtype=dtype)
    os.remove(tmp)
    return arr


def draw_esri_north(ax, cx, cy, height=0.38):
    """Dibuja rosa de los vientos clásica estilo ArcGIS corrigiendo el aspecto físico del eje."""
    fig = ax.get_figure()
    pos = ax.get_position()
    w_in = max(1e-4, pos.width * fig.get_figwidth())
    h_in = max(1e-4, pos.height * fig.get_figheight())
    aspect = h_in / w_in  # escala x necesaria para que 1 unidad Y == 1 unidad X en pulgadas
    w = height * 0.24 * aspect
    y_top = cy + height * 0.44
    y_bot = cy - height * 0.44
    y_mid = cy - height * 0.22
    left_tri = MplPolygon([[cx, y_top], [cx - w, y_bot], [cx, y_mid]], closed=True,
                          facecolor="black", edgecolor="black", lw=0.8, transform=ax.transAxes)
    right_tri = MplPolygon([[cx, y_top], [cx + w, y_bot], [cx, y_mid]], closed=True,
                           facecolor="white", edgecolor="black", lw=0.8, transform=ax.transAxes)
    ax.add_patch(left_tri)
    ax.add_patch(right_tri)
    ax.text(cx, y_top + 0.04, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=10.5, fontweight="bold", fontfamily="Liberation Serif", color="black")


def draw_scale_bar_box(ax, x0, y0, width, height, labels, divisions=4):
    """Dibuja barra de escala alternada blanco/negro clásica dentro de un eje de cajetín (coords 0..1)."""
    seg_w = width / divisions
    for i in range(divisions):
        fc = "black" if i % 2 == 0 else "white"
        ax.add_patch(Rectangle((x0 + i * seg_w, y0), seg_w, height,
                               facecolor=fc, edgecolor="black", lw=0.8, transform=ax.transAxes))
    for i, lbl in enumerate(labels):
        lx = x0 + (i / (len(labels) - 1)) * width
        ax.plot([lx, lx], [y0, y0 + height * 1.4], color="black", lw=0.7, transform=ax.transAxes)
        ax.text(lx, y0 - 0.04, lbl, transform=ax.transAxes, ha="center", va="top", fontsize=7.5, color="black")


def setup_neatline_utm(ax, xlim, ylim, step_x=100, step_y=100, rot_y=True):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    xs = np.arange(np.ceil(xlim[0] / step_x) * step_x, xlim[1] + 1, step_x)
    ys = np.arange(np.ceil(ylim[0] / step_y) * step_y, ylim[1] + 1, step_y)
    ax.set_xticks(xs)
    ax.set_yticks(ys)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax.tick_params(axis="x", labelsize=7.5, pad=2)
    ax.tick_params(axis="y", labelsize=7.5, pad=2)
    if rot_y:
        for lbl in ax.get_yticklabels():
            lbl.set_rotation(90)
            lbl.set_va("center")
    ax.grid(color="#444444", linestyle=":", linewidth=0.45, alpha=0.4)


def save_both(fig, stem):
    png = os.path.join(MAPAS_DIR, f"{stem}.png")
    pdf = os.path.join(MAPAS_DIR, f"{stem}.pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Generado: {png} y .pdf")


# ==============================================================================
# FIGURA 1: LOCALIZACIÓN REGIONAL Y DELIMITACIÓN (ESTILO CLÁSICO 2010)
# ==============================================================================
def make_fig1():
    fig = plt.figure(figsize=(15.2, 9.6), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.6, 1.15], hspace=0.14)
    gs_maps = gs[0].subgridspec(1, 2, wspace=0.16, width_ratios=[1.0, 1.08])
    gs_caj = gs[1].subgridspec(1, 3, wspace=0.04, width_ratios=[1.05, 1.35, 1.0])

    ax1 = fig.add_subplot(gs_maps[0, 0])
    ax2 = fig.add_subplot(gs_maps[0, 1])

    # Panel (a): Contexto regional DEM + Hillshade + OSM + D8
    rx0, ry0, rx1, ry1 = MANIFEST["reg_bbox"]
    dem30 = read_tif(MANIFEST["dem"]["dem_30m"])
    hill30 = read_tif(MANIFEST["dem"]["hillshade_30m"])
    ax1.imshow(dem30, extent=[rx0, rx1, ry0, ry1], origin="upper", cmap="terrain", vmin=1500, vmax=2000, alpha=0.72)
    ax1.imshow(hill30, extent=[rx0, rx1, ry0, ry1], origin="upper", cmap="gray", alpha=0.32)

    for sl in METRICS["topografia_hidrologia"]["stream_lines"]:
        xs = [c[0] for c in sl["coords"]]
        ys = [c[1] for c in sl["coords"]]
        ax1.plot(xs, ys, color="#1976D2", lw=0.75, alpha=0.55)
    for fp in METRICS["topografia_hidrologia"]["landfill_flow_paths"]:
        xs = [c[0] for c in fp["coords"]]
        ys = [c[1] for c in fp["coords"]]
        ax1.plot(xs, ys, color="#0D47A1", lw=1.6, zorder=5)

    with open(os.path.join(SIG_DIR, "osm_contexto_utm14n.geojson"), "r", encoding="utf-8") as f:
        osm = json.load(f)
    for ft in osm["features"]:
        pr = ft["properties"]
        gm = ft["geometry"]
        if pr.get("layer") == "highway" and gm["type"] == "LineString":
            xs = [c[0] for c in gm["coordinates"]]
            ys = [c[1] for c in gm["coordinates"]]
            hw = pr.get("highway", "")
            if pr.get("ref") == "MEX 125" or hw in ("trunk", "primary"):
                ax1.plot(xs, ys, color="#8E0000", lw=2.8, zorder=6)
                ax1.plot(xs, ys, color="#FFB300", lw=1.2, zorder=7)
            elif hw in ("secondary", "tertiary"):
                ax1.plot(xs, ys, color="#555555", lw=0.9, alpha=0.65, zorder=4)
            else:
                ax1.plot(xs, ys, color="#777777", lw=0.45, alpha=0.45, zorder=3)
        elif pr.get("layer") == "place" and gm["type"] == "Point":
            name = pr.get("name", "")
            px, py = gm["coordinates"]
            if 663400 <= px <= 669000 and 2033000 <= py <= 2038600:
                ax1.plot(px, py, "o", color="black", markeredgecolor="white", ms=5, zorder=9)
                dx, dy = (100, -180) if "Texcala" in name else (90, 90)
                ax1.text(px + dx, py + dy, name, fontsize=8, fontweight="bold", color="black",
                         path_effects=HALO_W, zorder=10)

    coap = METRICS["referencias"]["santa_maria_coapan"]
    ax1.plot(coap["E"], coap["N"], "s", color="#1B5E20", markeredgecolor="white", ms=6, zorder=9)
    ax1.text(coap["E"] - 110, coap["N"] - 220, "Santa María Coapan\n(3.33 km NE)",
             fontsize=8, fontweight="bold", color="#1B5E20", ha="right", path_effects=HALO_W, zorder=10)

    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    ax1.add_patch(MplPolygon(poly_tot, closed=True, facecolor="#D32F2F", edgecolor="#7F0000", lw=1.3, alpha=0.8, zorder=8))
    b_x0, b_x1, b_y0, b_y1 = 665740, 666510, 2035260, 2036040
    ax1.add_patch(Rectangle((b_x0, b_y0), b_x1 - b_x0, b_y1 - b_y0, fill=False, edgecolor="black", lw=1.3, ls="--", zorder=11))
    ax1.text(666125, 2036120, "Área mapa (b)", fontsize=7.8, fontweight="bold", ha="center", color="black", path_effects=HALO_W, zorder=12)
    ax1.text(664750, 2035760, "Carr. Fed. MEX-125\n(723 m NO)", fontsize=7.8, fontweight="bold",
             color="#7F0000", ha="center", path_effects=HALO_W, zorder=10)

    setup_neatline_utm(ax1, (663400, 669100), (2033000, 2038700), step_x=1000, step_y=1000)
    ax1.set_xlabel("Este UTM (m)", fontsize=8.5, fontweight="bold")
    ax1.set_ylabel("Norte UTM (m)", fontsize=8.5, fontweight="bold")
    ax1.set_title("(a) Contexto regional, relieve y red hidrológica (Tehuacán, Pue.)", fontsize=10, fontweight="bold", pad=6)

    # Panel (b): Ortoimagen limpia SIN cajas flotantes
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    im25 = read_tif(MANIFEST["wayback"][-1]["file"], dtype=np.uint8)
    ax2.imshow(im25, extent=[fx0, fx1, fy0, fy1], origin="upper")

    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    poly_2011 = METRICS["geometria_listas"]["POLY_2011"]
    poly_lag = METRICS["geometria_listas"]["POLY_LAGUNA_NO"]

    # Contorno clásico con halo blanco fino para máxima legibilidad sin obstruir la imagen
    ax2.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=2.8, ls="--", zorder=5))
    ax2.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=1.8, ls="--", zorder=6))
    ax2.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=3.0, zorder=6))
    ax2.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#C62828", lw=2.0, zorder=7))
    ax2.add_patch(MplPolygon(poly_2011, closed=True, fill=False, edgecolor="#2E7D32", lw=1.8, ls=":", zorder=7))
    ax2.add_patch(MplPolygon(poly_lag, closed=True, facecolor="#1565C0", edgecolor="white", lw=1.0, alpha=0.55, zorder=8))

    for idx, (vx, vy) in enumerate(poly_p, 1):
        ax2.plot(vx, vy, "o", color="white", markeredgecolor="#C62828", ms=3.5, mew=0.9, zorder=9)
        if idx in (1, 5, 8, 12, 15, 20):
            if idx == 1:
                dx, dy = -16, 6
            elif idx == 5:
                dx, dy = 10, -10
            elif idx == 8:
                dx, dy = 0, 10
            else:
                dx, dy = 8, 4
            ax2.text(vx + dx, vy + dy, f"V{idx}", color="black", fontsize=7.5, fontweight="bold",
                     path_effects=HALO_W, zorder=10)

    for p in METRICS["referencias"]["profepa"]:
        ax2.plot(p["E"], p["N"], "^", color="#D32F2F", ms=8, markeredgecolor="white", mew=0.9, zorder=11)
        dx, dy, ha = (10, -14, "left") if "1" in p["id"] else (-10, 10, "right")
        ax2.text(p["E"] + dx, p["N"] + dy, p["id"], color="#8E0000", fontsize=7.8, fontweight="bold",
                 ha=ha, path_effects=HALO_W, zorder=12)

    ax2.text(665992, 2035802, "Laguna NO\n(315 m²)", color="#0D47A1", fontsize=7.2, fontweight="bold",
             ha="right", path_effects=HALO_W, zorder=11)
    ax2.text(665930, 2035630, "Área aux. SO\n(2.11 ha)", color="#4E342E", fontsize=7.2, fontweight="bold",
             ha="center", path_effects=HALO_W, zorder=11)

    setup_neatline_utm(ax2, (b_x0, b_x1), (b_y0, b_y1), step_x=100, step_y=100)
    ax2.set_xlabel("Este UTM (m)", fontsize=8.5, fontweight="bold")
    ax2.set_ylabel("Norte UTM (m)", fontsize=8.5, fontweight="bold")
    ax2.set_title("(b) Delimitación sobre ortoimagen satelital (2025-08-24, 0.34 m)", fontsize=10, fontweight="bold", pad=6)

    # Cajetín cartográfico blanco inferior en 3 celdas
    c1 = fig.add_subplot(gs_caj[0, 0])
    c2 = fig.add_subplot(gs_caj[0, 1])
    c3 = fig.add_subplot(gs_caj[0, 2])
    for ca in (c1, c2, c3):
        ca.set_xticks([]); ca.set_yticks([])
        for sp in ca.spines.values():
            sp.set_linewidth(0.9)
            sp.set_color("black")

    c1.text(0.04, 0.92, "SIMBOLOGÍA", fontsize=8.5, fontweight="bold", va="top", transform=c1.transAxes)
    leg_items = [
        Line2D([0], [0], color="#C62828", lw=2.0, label="Cuerpo principal de residuos (9.80 ha)"),
        Line2D([0], [0], color="#E65100", lw=1.8, ls="--", label="Huella operativa total (12.15 ha)"),
        Line2D([0], [0], color="#2E7D32", lw=1.8, ls=":", label="Núcleo histórico 2011 (6.75 ha)"),
        mpatches.Patch(facecolor="#1565C0", edgecolor="black", alpha=0.6, label="Laguna de lixiviados NO (315 m²)"),
        Line2D([0], [0], color="#8E0000", lw=2.4, label="Carretera Federal MEX-125"),
        Line2D([0], [0], color="#0D47A1", lw=1.6, label="Escurrimiento D8 desde el relleno"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#D32F2F", markeredgecolor="black", ms=6.5, lw=0, label="Puntos de inspección PROFEPA"),
    ]
    c1.legend(handles=leg_items, loc="lower left", bbox_to_anchor=(0.01, 0.02), frameon=False, fontsize=7.4, handlelength=2.2, labelspacing=0.35)

    mp = METRICS["poligonos"]["cuerpo_principal"]
    mt = METRICS["poligonos"]["huella_total"]
    m11 = METRICS["poligonos"]["nucleo_2011"]
    exp_ha = METRICS["poligonos"]["expansion_2011_2025_ha"]
    exp_pct = METRICS["poligonos"]["expansion_2011_2025_pct"]
    c2.text(0.03, 0.92, "MÉTRICAS GEODÉSICAS Y RECONCILIACIÓN DE SUPERFICIES", fontsize=8.5, fontweight="bold", va="top", transform=c2.transAxes)
    txt_c2 = (
        f"Centroide cuerpo principal:  {mp['centroide_dms']}  (E {mp['centroide_utm'][0]:,.2f} m, N {mp['centroide_utm'][1]:,.2f} m)\n"
        f"• Cuerpo principal (2025):    {mp['area_ha']:.3f} ha  (97,962 m²  |  Perímetro: {mp['perimetro_m']:,.1f} m)\n"
        f"• Huella operativa total:     {mt['area_ha']:.3f} ha  (121,536 m² |  Perímetro: {mt['perimetro_m']:,.1f} m)\n"
        f"• Núcleo histórico 2011:      {m11['area_ha']:.3f} ha  -> Expansión post-2010: +{exp_ha:.3f} ha (+{exp_pct}%)\n"
        f"• Subzona CONANP (DOF):       16.464 ha (polígono oficial RBTC con amortiguamiento)\n"
        f"• Distancias desde centroide: MEX-125 = 723.1 m (NO) | San A. Texcala = 2.08 km (OSO) | Coapan = 3.33 km (NE)"
    )
    c2.text(0.03, 0.77, txt_c2, fontsize=7.25, va="top", ha="left", transform=c2.transAxes, linespacing=1.42)

    c3.text(0.04, 0.92, "ORIENTACIÓN, ESCALA Y CRÉDITOS", fontsize=8.5, fontweight="bold", va="top", transform=c3.transAxes)
    draw_scale_bar_box(c3, 0.30, 0.68, 0.62, 0.06, ["0", "0.5", "1.0", "2.0 km (a)"], divisions=4)
    draw_scale_bar_box(c3, 0.30, 0.46, 0.62, 0.06, ["0", "50", "100", "200 m (b)"], divisions=4)
    c3.text(0.04, 0.28,
            f"Geofísica Ambiental (Otoño 2026) | CRS: EPSG:32614 (UTM 14N)\n"
            f"Fuentes: Esri Vivid (24/08/2025), Copernicus DEM, OSM, PROFEPA, CONANP.\n"
            f"Autores: Ian A. Sandoval-Valderrábano y Carlos E. Fernández Tepale\n"
            f"(Facultad de Ingeniería, BUAP).",
            fontsize=6.6, va="top", transform=c3.transAxes, linespacing=1.25)

    fig.suptitle(
        "Figura 1. Localización Geográfica y Delimitación Georreferenciada del Relleno Sanitario de Santa María Coapan (Tehuacán, Puebla)",
        fontsize=12.5, fontweight="bold", fontfamily="Liberation Serif", y=0.96
    )
    fig.subplots_adjust(top=0.895, bottom=0.04, left=0.055, right=0.98)
    fig.canvas.draw()
    draw_esri_north(c3, 0.14, 0.57, height=0.36)
    save_both(fig, "fig1_localizacion_delimitacion")


# ==============================================================================
# FIGURA 2: EVOLUCIÓN HISTÓRICA MULTITEMPORAL (ESTILO CLÁSICO 2010)
# ==============================================================================
def make_fig2():
    fig = plt.figure(figsize=(14.8, 15.2), dpi=300)
    gs = fig.add_gridspec(4, 3, height_ratios=[1, 1, 1, 0.92], hspace=0.23, wspace=0.08)

    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    rx0, ry0, rx1, ry1 = MANIFEST["reg_bbox"]
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    vx0, vx1, vy0, vy1 = 665790, 666440, 2035480, 2035945

    ls_map = {r["tag"]: r for r in MANIFEST["landsat"]}
    wb_map = {r["rid"]: r for r in MANIFEST["wayback"]}

    ls_panels = [
        ("1989_pre", "(a) 26/10/1989 — Landsat-4 TM (30 m)\nPre-operación: matorral natural intacto"),
        ("1993_ini", "(b) 15/02/1993 — Landsat-5 TM (30 m)\nTerreno aún sin desmonte visible"),
        ("1995_dic", "(c) 06/12/1995 — Landsat-5 TM (30 m)\nCamino y celda SE activos (inicio 1993–94)"),
    ]
    for c, (tag, title) in enumerate(ls_panels):
        ax = fig.add_subplot(gs[0, c])
        rec = ls_map[tag]
        b = rec["bands"]
        rgb = np.clip(np.dstack([
            np.clip(read_tif(b["red"]) * 0.0000275 - 0.2, 0, 1),
            np.clip(read_tif(b["green"]) * 0.0000275 - 0.2, 0, 1),
            np.clip(read_tif(b["blue"]) * 0.0000275 - 0.2, 0, 1),
        ]) / 0.28, 0, 1)
        ax.imshow(rgb, extent=[rx0, rx1, ry0, ry1], origin="upper", interpolation="nearest")
        ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=2.0, ls="--"))
        ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#D32F2F", lw=1.2, ls="--"))
        ax.set_xlim(vx0, vx1); ax.set_ylim(vy0, vy1)
        ax.set_title(title, fontsize=8.8, fontweight="bold", pad=4)
        ax.set_xticks([]); ax.set_yticks([])

    wb_panels = [
        ("10", "(d) 06/06/2011 — Alta res. (0.50 m)\nPost-vida útil 2010: núcleo 6.75 ha"),
        ("13770", "(e) 07/02/2013 — Alta res. (0.50 m)\nTrincheras SO y laguna NO"),
        ("13067", "(f) 30/11/2015 — Vivid (0.31 m)\nExpansión NO y desvío del camino"),
        ("42403", "(g) 25/04/2021 — Vivid (0.50 m)\nMáxima carga pre-cierre (oct 2021)"),
        ("1034", "(h) 18/11/2022 — Vivid (0.31 m)\nPost-incendio mayo 2022 y sellos Smadsot"),
        ("63116", "(i) 24/08/2025 — Vivid (0.34 m)\nPost-clausura PROFEPA: cubierta y laguna NO"),
    ]
    for idx, (rid, title) in enumerate(wb_panels):
        row = 1 + idx // 3
        col = idx % 3
        ax = fig.add_subplot(gs[row, col])
        im = read_tif(wb_map[rid]["file"], dtype=np.uint8)
        ax.imshow(im, extent=[fx0, fx1, fy0, fy1], origin="upper")
        ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=2.0, ls="--"))
        ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=1.2, ls="--"))
        ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=2.2))
        ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#C62828", lw=1.3))
        ax.set_xlim(vx0, vx1); ax.set_ylim(vy0, vy1)
        ax.set_title(title, fontsize=8.8, fontweight="bold", pad=4)
        ax.set_xticks([]); ax.set_yticks([])

    # Panel (j): Serie temporal clásica
    ax_ts = fig.add_subplot(gs[3, :])
    ts = METRICS["serie_temporal_1989_2026"]
    years = [int(r["date"][:4]) + (int(r["date"][5:7]) - 0.5) / 12.0 for r in ts]
    ndvi_r = [r["ndvi_relleno"] for r in ts]
    ndvi_c = [r["ndvi_testigo"] for r in ts]
    dndvi = [r["delta_ndvi"] for r in ts]

    ax_ts.axhline(0, color="black", lw=0.7)
    ax_ts.plot(years, ndvi_c, "o--", color="#1B5E20", lw=1.5, ms=4.5, label="NDVI matorral natural testigo")
    ax_ts.plot(years, ndvi_r, "s-", color="#B71C1C", lw=1.8, ms=5.0, label="NDVI cuerpo principal del relleno")
    ax_ts.plot(years, dndvi, "^-", color="#0D47A1", lw=1.6, ms=5.0, label="ΔNDVI = NDVI(relleno) − NDVI(testigo)")

    hitos = [
        (1994.0, "1993–94\nInicio real", "#B71C1C", 0.42, "left", 0.2),
        (2010.0, "2010\nFin vida útil", "#4A148C", 0.42, "left", 0.2),
        (2021.77, "Oct 2021\nCierre com.", "#00695C", 0.42, "right", -0.2),
        (2022.37, "May 2022\nIncendio", "#C62828", 0.30, "center", 0.0),
        (2023.49, "Jun 2023\nClausura PROFEPA", "#212121", 0.42, "left", 0.2),
    ]
    for yr, txt, col, y_pos, ha_mode, dx in hitos:
        ax_ts.axvline(yr, color=col, ls=":", lw=1.2)
        ax_ts.text(yr + dx, y_pos, txt, color=col, fontsize=7.5, fontweight="bold", va="top", ha=ha_mode,
                   path_effects=HALO_W_THIN)

    ax_ts.set_xlim(1988.5, 2027.8)
    ax_ts.set_ylim(-0.32, 0.45)
    ax_ts.grid(True, ls=":", color="#AAAAAA", lw=0.5)
    ax_ts.set_xlabel("Año de adquisición satelital (USGS Landsat 4/5/8 + ESA Sentinel-2)", fontsize=9.2, fontweight="bold")
    ax_ts.set_ylabel("Índice espectral", fontsize=9.2, fontweight="bold")
    ax_ts.set_title("(j) Evolución espectral multitemporal (1989–2026) respecto al matorral natural testigo", fontsize=9.8, fontweight="bold")
    ax_ts.legend(loc="lower left", fontsize=8, ncol=3, frameon=True, edgecolor="black", facecolor="white", fancybox=False)

    fig.suptitle(
        "Figura 2. Evolución Multitemporal del Relleno Sanitario de Santa María Coapan (1989–2026)",
        fontsize=12.8, fontweight="bold", fontfamily="Liberation Serif", y=0.962
    )
    fig.text(
        0.5, 0.015,
        f"Contorno rojo continuo: cuerpo principal (9.80 ha); naranja discontinuo: huella total (12.15 ha). Marco de cada cuadro: 650 × 465 m (EPSG:32614).\n"
        f"Fuentes: USGS Landsat C2 L2 y Esri World Imagery Wayback (fechas verificadas vía SRC_DATE2). Autores: {AUTORES}.",
        ha="center", fontsize=8, color="black",
        bbox=dict(boxstyle="square,pad=0.45", fc="white", ec="black", lw=0.8)
    )
    fig.subplots_adjust(top=0.915, bottom=0.085, left=0.06, right=0.97)
    save_both(fig, "fig2_evolucion_multitemporal")


# ==============================================================================
# FIGURA 3: ESTADO ACTUAL MULTISENSOR (NOV 2026), INCENDIO 2022 Y ML (ESTILO 2010)
# ==============================================================================
def make_fig3():
    fig = plt.figure(figsize=(16.2, 11.4), dpi=300)
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 0.36], hspace=0.28, wspace=0.22)
    mx0, my0, mx1, my1 = MANIFEST["med_bbox"]
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    vx0, vx1, vy0, vy1 = 665680, 666540, 2035340, 2036040

    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    poly_lag = METRICS["geometria_listas"]["POLY_LAGUNA_NO"]

    axes = [fig.add_subplot(gs[r, c]) for r in range(2) for c in range(3)]

    # (a) RGB alta res + subzonas sin recuadros
    ax = axes[0]
    im25 = read_tif(MANIFEST["wayback"][-1]["file"], dtype=np.uint8)
    ax.imshow(im25, extent=[fx0, fx1, fy0, fy1], origin="upper")
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=2.4, ls="--"))
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=1.4, ls="--"))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=2.4))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#C62828", lw=1.5))
    ax.add_patch(MplPolygon(poly_lag, closed=True, facecolor="#1565C0", edgecolor="white", lw=0.9, alpha=0.55))
    ax.text(666190, 2035700, "Cuerpo principal\n(9.80 ha)", color="black", fontsize=7.5, fontweight="bold", ha="center", path_effects=HALO_W)
    ax.text(665925, 2035620, "Aux. SO\n(2.11 ha)", color="black", fontsize=7.2, fontweight="bold", ha="center", path_effects=HALO_W)
    ax.set_title("(a) Ortoimagen Vivid (24/08/2025, 0.34 m)\ny delimitación de subzonas", fontsize=9.2, fontweight="bold", pad=5)

    # Cargar S2 2026-11-03
    s2_cur = [r for r in MANIFEST["sentinel2"] if r["tag"] == "2026_cur_1103"][0]
    off, sc, b = s2_cur["boa_offset"], s2_cur["scale"], s2_cur["bands"]
    b12 = np.clip((read_tif(b["B12"]) + off) * sc, 0.001, 1.0)
    b8a = np.clip((read_tif(b["B8A"]) + off) * sc, 0.001, 1.0)
    b04 = np.clip((read_tif(b["B04"]) + off) * sc, 0.001, 1.0)

    # (b) Falso color SWIR
    ax = axes[1]
    fc = np.clip(np.dstack([b12 / 0.45, b8a / 0.45, b04 / 0.35]), 0, 1)
    ax.imshow(fc, extent=[mx0, mx1, my0, my1], origin="upper", interpolation="nearest")
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#B71C1C", lw=1.5, ls="--"))
    ax.set_title("(b) Sentinel-2 Falso Color SWIR (03/11/2026)\nB12–B8A–B04: mineral (blanco) / matorral (verde)", fontsize=9.2, fontweight="bold", pad=5)

    # (c) BSI actual
    ax = axes[2]
    bsi = read_tif(os.path.join(RASTERS_DIR, "s2_2026_bsi_utm14n.tif"))
    im_bsi = ax.imshow(bsi, extent=[mx0, mx1, my0, my1], origin="upper", cmap="YlOrBr", vmin=-0.10, vmax=0.28, interpolation="nearest")
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="black", lw=1.5))
    cb = plt.colorbar(im_bsi, ax=ax, fraction=0.045, pad=0.03, shrink=0.92)
    cb.set_label("BSI", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
    st_cur = METRICS["estado_actual_2026_11_03"]
    ax.set_title(f"(c) Índice de Suelo Desnudo BSI (03/11/2026)\nRelleno: BSI={st_cur['bsi_mediana_relleno']:+.3f} | NDVI={st_cur['ndvi_mediana_relleno']:+.3f}", fontsize=9.2, fontweight="bold", pad=5)

    # (d) dNBR incendio mayo 2022 (YlOrRd clásico)
    ax = axes[3]
    dnbr = read_tif(os.path.join(RASTERS_DIR, "s2_2022_dnbr_utm14n.tif"))
    im_d = ax.imshow(dnbr, extent=[mx0, mx1, my0, my1], origin="upper", cmap="YlOrRd", vmin=0.0, vmax=0.45, interpolation="nearest")
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="black", lw=1.4, ls="--"))
    cb_d = plt.colorbar(im_d, ax=ax, fraction=0.045, pad=0.03, shrink=0.92)
    cb_d.set_label("dNBR", fontsize=8)
    cb_d.ax.tick_params(labelsize=7.5)
    inc = METRICS["incendio_mayo_2022"]
    ax.set_title(f"(d) Severidad incendio mayo 2022 (dNBR)\nQuemado: {inc['area_dnbr_ge_010_ha']:.2f} ha ({inc['pct_huella_quemada']}%) | máx={inc['dnbr_max']:.2f}", fontsize=9.2, fontweight="bold", pad=5)

    # (e) Sentinel-1 SAR VV dB en escala de grises clásica (2010 IEEE TGRS style)
    ax = axes[4]
    vv26 = read_tif(os.path.join(RASTERS_DIR, "s1_2026_vv_db_utm14n.tif"))
    vv26 = np.where(vv26 < -100, np.nan, vv26)
    im_s1 = ax.imshow(vv26, extent=[mx0, mx1, my0, my1], origin="upper", cmap="gray", vmin=-15.0, vmax=-5.0, interpolation="nearest")
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#D32F2F", lw=1.6))
    cb_s1 = plt.colorbar(im_s1, ax=ax, fraction=0.045, pad=0.03, shrink=0.92)
    cb_s1.set_label(r"$\sigma^0$ VV (dB)", fontsize=8)
    cb_s1.ax.tick_params(labelsize=7.5)
    s1_ep = METRICS["sar_sentinel1_rel70"]["epocas"]
    dvv = METRICS["sar_sentinel1_rel70"]["delta_vv_2021_2026_db"]
    ax.set_title(f"(e) SAR Sentinel-1D RTC (19/11/2026, desc. rel=70)\nVV={s1_ep[-1]['vv_relleno_db']:.2f} dB, VH={s1_ep[-1]['vh_relleno_db']:.2f} dB (ΔVV={dvv:+.2f} dB)", fontsize=9.2, fontweight="bold", pad=5)

    # (f) Clasificación K-Means ML (k=5) paleta sobria Corine/INEGI
    ax = axes[5]
    ml = read_tif(os.path.join(RASTERS_DIR, "ml_kmeans_2026_utm14n.tif"))
    colors_ml = ["#D95F02", "#E6AB02", "#A6761D", "#A6D854", "#238B45"]
    cmap_ml = ListedColormap(colors_ml)
    norm_ml = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap_ml.N)
    ax.imshow(ml, extent=[mx0, mx1, my0, my1], origin="upper", cmap=cmap_ml, norm=norm_ml, interpolation="nearest")
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="black", lw=1.6, ls="--"))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="black", lw=1.2))
    ax.set_title("(f) Clasificación no supervisada K-Means (k=5)\nFusión Sentinel-2 + SAR Sentinel-1 + Pendiente", fontsize=9.2, fontweight="bold", pad=5)

    for ax in axes:
        setup_neatline_utm(ax, (vx0, vx1), (vy0, vy1), step_x=200, step_y=200, rot_y=True)

    # Cajetín inferior en 2 bloques limpios (Leyenda K-Means + Resumen & Autoría)
    gs_bot = gs[2, :].subgridspec(1, 2, wspace=0.05, width_ratios=[1.35, 1.0])
    cb1 = fig.add_subplot(gs_bot[0, 0])
    cb2 = fig.add_subplot(gs_bot[0, 1])
    for ca in (cb1, cb2):
        ca.set_xticks([]); ca.set_yticks([])
        for sp in ca.spines.values():
            sp.set_linewidth(0.9)
            sp.set_color("black")

    cb1.text(0.02, 0.90, "CLASES DE COBERTURA — APRENDIZAJE AUTOMÁTICO (K-MEANS, k=5) EN HUELLA OPERATIVA (12.15 ha)",
             fontsize=8.2, fontweight="bold", va="top", transform=cb1.transAxes)
    short_labels = [
        "Cubierta mineral / residuos compactados sin vegetación",
        "Taludes perturbados / suelo desnudo y caminos internos",
        "Escarpa de alta pendiente y rugosidad SAR (21.1°)",
        "Matorral ralo / vegetación pionera sobre suelo alterado",
        "Matorral xerófilo denso (entorno natural)",
    ]
    patches_ml = []
    for cl in METRICS["ml_kmeans_k5"]:
        cid = cl["class_id"]
        patches_ml.append(mpatches.Patch(
            facecolor=colors_ml[cid], edgecolor="black", linewidth=0.6,
            label=f"{short_labels[cid]}: {cl['ha_en_huella']:.2f} ha ({cl['pct_en_huella']:.1f}%)"
        ))
    cb1.legend(handles=patches_ml, loc="lower left", bbox_to_anchor=(0.01, 0.04), ncol=2, frameon=False, fontsize=7.5, columnspacing=1.2)

    cb2.text(0.03, 0.90, "RESUMEN MULTISENSOR Y REFERENCIA CARTOGRÁFICA", fontsize=8.0, fontweight="bold", va="top", transform=cb2.transAxes)
    draw_scale_bar_box(cb2, 0.67, 0.78, 0.28, 0.08, ["0", "100", "200 m"], divisions=2)
    cb2.text(0.03, 0.74,
             f"• Óptico (03/11/2026): NDVI={st_cur['ndvi_mediana_relleno']:+.3f} vs testigo={st_cur['ndvi_mediana_testigo']:+.3f}\n"
             f"• Incendio mayo 2022: 5–8 mayo (humo 08/05); dNBR≥0.27={inc['area_dnbr_ge_027_ha']:.2f} ha\n"
             f"• SAR 2021→2026: ΔVV={dvv:+.2f} dB; 87.5% de huella sin vegetación\n"
             f"• Geofísica Ambiental (Otoño 2026) | EPSG:32614 (UTM 14N)\n"
             f"• Autores: Ian A. Sandoval-Valderrábano y\n"
             f"  Carlos Enrique Fernández Tepale (FI, BUAP).",
             fontsize=6.7, va="top", transform=cb2.transAxes, linespacing=1.30)

    fig.suptitle(
        "Figura 3. Diagnóstico del Estado Actual del Terreno (Noviembre 2026) e Incendio Mayo 2022 (Fusión Óptica, SAR y ML)",
        fontsize=12.6, fontweight="bold", fontfamily="Liberation Serif", y=0.96
    )
    fig.subplots_adjust(top=0.90, bottom=0.04, left=0.055, right=0.98)
    fig.canvas.draw()
    draw_esri_north(cb2, 0.81, 0.24, height=0.32)
    save_both(fig, "fig3_estado_actual_multisensor_ml")


# ==============================================================================
# FIGURA 4: MODELADO TOPOGRÁFICO, HIDROLOGÍA D8 Y PERFILES (ESTILO 2010)
# ==============================================================================
def make_fig4():
    fig = plt.figure(figsize=(15.4, 11.4), dpi=300)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.45, 0.85, 0.42], hspace=0.30, wspace=0.20)

    rx0, ry0, rx1, ry1 = MANIFEST["reg_bbox"]
    mx0, my0, mx1, my1 = MANIFEST["med_bbox"]
    dem30 = read_tif(MANIFEST["dem"]["dem_30m"])
    hill30 = read_tif(MANIFEST["dem"]["hillshade_30m"])
    slope10 = read_tif(MANIFEST["dem"]["slope_10m"])
    dem10 = read_tif(MANIFEST["dem"]["dem_10m"])

    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]

    # (a) MDE + Curvas + D8
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(dem30, extent=[rx0, rx1, ry0, ry1], origin="upper", cmap="terrain", vmin=1550, vmax=1920, alpha=0.75)
    ax1.imshow(hill30, extent=[rx0, rx1, ry0, ry1], origin="upper", cmap="gray", alpha=0.30)

    xs30 = rx0 + (np.arange(dem30.shape[1]) + 0.5) * 30.0
    ys30 = ry1 - (np.arange(dem30.shape[0]) + 0.5) * 30.0
    cs = ax1.contour(xs30, ys30, dem30, levels=np.arange(1560, 1920, 20), colors="#5D4037", linewidths=0.55, alpha=0.75)
    ax1.clabel(cs, inline=True, fontsize=6.5, fmt="%d m")

    for sl in METRICS["topografia_hidrologia"]["stream_lines"]:
        xs = [c[0] for c in sl["coords"]]
        ys = [c[1] for c in sl["coords"]]
        ax1.plot(xs, ys, color="#1976D2", lw=0.85, alpha=0.65)
    for fp in METRICS["topografia_hidrologia"]["landfill_flow_paths"]:
        xs = [c[0] for c in fp["coords"]]
        ys = [c[1] for c in fp["coords"]]
        ax1.plot(xs, ys, color="#0D47A1", lw=2.0, zorder=8)
        if len(xs) > 12:
            ax1.annotate("", xy=(xs[12], ys[12]), xytext=(xs[10], ys[10]),
                         arrowprops=dict(arrowstyle="-|>", color="#0D47A1", lw=1.8, mutation_scale=12), zorder=9)

    ax1.add_patch(MplPolygon(poly_tot, closed=True, facecolor="#D32F2F", edgecolor="black", lw=1.2, alpha=0.72, zorder=7))
    for p in METRICS["referencias"]["profepa"]:
        ax1.plot(p["E"], p["N"], "^", color="black", markeredgecolor="white", ms=6.5, zorder=10)
        ax1.text(p["E"] + 35, p["N"] - 50, p["id"], fontsize=7.5, fontweight="bold", color="black", path_effects=HALO_W, zorder=11)

    setup_neatline_utm(ax1, (664900, 667600), (2034700, 2036700), step_x=500, step_y=500)
    ax1.set_xlabel("Este UTM (m)", fontsize=8.8, fontweight="bold")
    ax1.set_ylabel("Norte UTM (m)", fontsize=8.8, fontweight="bold")
    ax1.set_title("(a) Relieve (Copernicus DEM 30 m), curvas (20 m) y drenaje D8", fontsize=9.8, fontweight="bold", pad=5)

    # (b) Pendientes + vectores negros + perfiles A-A' y B-B'
    ax2 = fig.add_subplot(gs[0, 1])
    im_slp = ax2.imshow(slope10, extent=[mx0, mx1, my0, my1], origin="upper", cmap="YlOrRd", vmin=0, vmax=28)
    cb = plt.colorbar(im_slp, ax=ax2, fraction=0.044, pad=0.03)
    cb.set_label("Pendiente (°)", fontsize=8.5)
    cb.ax.tick_params(labelsize=7.5)

    gy, gx = np.gradient(dem10, 10.0)
    step = 7
    xs10 = mx0 + (np.arange(dem10.shape[1]) + 0.5) * 10.0
    ys10 = my1 - (np.arange(dem10.shape[0]) + 0.5) * 10.0
    qx, qy = np.meshgrid(xs10[::step], ys10[::step])
    u = -gx[::step, ::step]
    v = gy[::step, ::step]
    mag = np.hypot(u, v) + 1e-6
    ax2.quiver(qx, qy, u / mag, v / mag, color="#1A237E", alpha=0.7, scale=22, width=0.0038, zorder=6)

    ax2.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="black", lw=1.6, ls="--", zorder=7))
    ax2.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#1B5E20", lw=1.8, zorder=8))
    ax2.plot([665400, 666850], [2035710, 2035710], color="black", lw=1.3, ls="-.", zorder=9)
    ax2.text(665560, 2035728, "A (O–E)", color="black", fontsize=8, fontweight="bold", path_effects=HALO_W, zorder=10)
    ax2.plot([666170, 666170], [2035050, 2036300], color="black", lw=1.3, ls="-.", zorder=9)
    ax2.text(666185, 2035310, "B (S–N)", color="black", fontsize=8, fontweight="bold", path_effects=HALO_W, zorder=10)

    setup_neatline_utm(ax2, (665520, 666720), (2035250, 2036150), step_x=200, step_y=200)
    ax2.set_xlabel("Este UTM (m)", fontsize=8.8, fontweight="bold")
    ax2.set_ylabel("Norte UTM (m)", fontsize=8.8, fontweight="bold")
    ax2.set_title("(b) Mapa de pendientes (°), vectores de descenso y trazas A / B", fontsize=9.8, fontweight="bold", pad=5)

    # (c) Perfil A (O-E)
    ax3 = fig.add_subplot(gs[1, 0])
    poe = METRICS["topografia_hidrologia"]["perfil_oe"]
    e_arr = np.array(poe["e"]); z_arr = np.array(poe["z"])
    ax3.fill_between(e_arr, z_arr.min() - 15, z_arr, color="#E0E0E0")
    ax3.plot(e_arr, z_arr, color="black", lw=1.5)
    in_r = (e_arr >= 665980) & (e_arr <= 666345)
    ax3.fill_between(e_arr[in_r], z_arr.min() - 15, z_arr[in_r], color="#EF9A9A", hatch="///", edgecolor="#B71C1C", lw=0.6, label="Cuerpo de residuos (N = 2,035,710 m)")
    ax3.axvline(665680, color="#1B5E20", ls="--", lw=1.3, label="Perfil testigo aguas arriba (R1)")
    ax3.set_xlim(665400, 666840); ax3.set_ylim(z_arr.min() - 12, z_arr.max() + 18)
    ax3.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax3.tick_params(labelsize=8)
    ax3.grid(True, ls=":", color="#AAAAAA", lw=0.5)
    ax3.set_xlabel("Este UTM (m)", fontsize=8.8, fontweight="bold")
    ax3.set_ylabel("Elevación (m s.n.m.)", fontsize=8.8, fontweight="bold")
    ax3.set_title("(c) Perfil topográfico A: Oeste → Este (descenso hacia valle oriental)", fontsize=9.5, fontweight="bold")
    ax3.legend(loc="upper right", fontsize=7.6, frameon=True, edgecolor="black", facecolor="white", fancybox=False)

    # (d) Perfil B (S-N)
    ax4 = fig.add_subplot(gs[1, 1])
    pns = METRICS["topografia_hidrologia"]["perfil_ns"]
    n_arr = np.array(pns["n"]); zn_arr = np.array(pns["z"])
    ax4.fill_between(n_arr, zn_arr.min() - 15, zn_arr, color="#E0E0E0")
    ax4.plot(n_arr, zn_arr, color="black", lw=1.5)
    in_rn = (n_arr >= 2035555) & (n_arr <= 2035875)
    ax4.fill_between(n_arr[in_rn], zn_arr.min() - 15, zn_arr[in_rn], color="#EF9A9A", hatch="///", edgecolor="#B71C1C", lw=0.6, label="Cuerpo de residuos (E = 666,170 m)")
    ax4.set_xlim(2035050, 2036290); ax4.set_ylim(zn_arr.min() - 12, zn_arr.max() + 18)
    ax4.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax4.tick_params(labelsize=8)
    ax4.grid(True, ls=":", color="#AAAAAA", lw=0.5)
    ax4.set_xlabel("Norte UTM (m)", fontsize=8.8, fontweight="bold")
    ax4.set_ylabel("Elevación (m s.n.m.)", fontsize=8.8, fontweight="bold")
    ax4.set_title("(d) Perfil topográfico B: Sur → Norte (encajonamiento en cabecera)", fontsize=9.5, fontweight="bold")
    ax4.legend(loc="lower left", fontsize=7.6, frameon=True, edgecolor="black", facecolor="white", fancybox=False)

    # Cajetín inferior blanco
    caj = fig.add_subplot(gs[2, :])
    caj.set_xticks([]); caj.set_yticks([])
    for sp in caj.spines.values():
        sp.set_linewidth(0.9); sp.set_color("black")
    ts_t = METRICS["topografia_hidrologia"]["stats"]
    draw_scale_bar_box(caj, 0.70, 0.65, 0.17, 0.09, ["0", "250", "500 m (a)"], divisions=2)
    draw_scale_bar_box(caj, 0.70, 0.30, 0.17, 0.09, ["0", "150", "300 m (b)"], divisions=2)
    caj.text(0.015, 0.90, "PARÁMETROS TOPOGRÁFICOS, HIDROLOGÍA D8 Y REFERENCIA CARTOGRÁFICA", fontsize=8.3, fontweight="bold", va="top", transform=caj.transAxes)
    caj.text(0.015, 0.72,
             f"• Altitud en huella: {ts_t['elev_min_m']}–{ts_t['elev_max_m']} m s.n.m. (media {ts_t['elev_media_m']} m; desnivel {ts_t['desnivel_interno_m']} m) | Pendiente media: {ts_t['pendiente_media_deg']}° (máx {ts_t['pendiente_max_deg']}°).\n"
             f"• Dirección de drenaje D8 dominante: azimut {ts_t['azimut_descenso_deg']}° (ENE, hacia valle de Tehuacán) | Algoritmo: Wang & Liu + D8.\n"
             f"• Simbología: rojo = relleno; azul = drenaje D8; flechas en (a) = rutas de salida | Fuente: Copernicus DEM GLO-30 (EPSG:32614).\n"
             f"• Geofísica Ambiental (Otoño 2026) | Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale (FI, BUAP).",
             fontsize=7.0, va="top", transform=caj.transAxes, linespacing=1.36)

    fig.suptitle(
        "Figura 4. Modelado Topográfico, Drenaje Superficial D8 y Dirección de Riesgo de Migración de Lixiviados",
        fontsize=12.6, fontweight="bold", fontfamily="Liberation Serif", y=0.96
    )
    fig.subplots_adjust(top=0.90, bottom=0.04, left=0.055, right=0.98)
    fig.canvas.draw()
    draw_esri_north(caj, 0.935, 0.48, height=0.52)
    save_both(fig, "fig4_topografia_hidrologia_riesgo")


# ==============================================================================
# FIGURA 5: DISEÑO GEOFÍSICO GEORREFERENCIADO (CARTA CLÁSICA ARCMAP 2010)
# ==============================================================================
def make_fig5():
    fig = plt.figure(figsize=(15.8, 9.6), dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.35, 1.0], wspace=0.05)

    ax = fig.add_subplot(gs[0, 0])
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    mx0, my0, mx1, my1 = MANIFEST["med_bbox"]

    im25 = read_tif(MANIFEST["wayback"][-1]["file"], dtype=np.uint8)
    ax.imshow(im25, extent=[fx0, fx1, fy0, fy1], origin="upper", alpha=0.92)

    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    poly_lag = METRICS["geometria_listas"]["POLY_LAGUNA_NO"]

    # Cicatriz dNBR en achurado clásico naranja-rojo semitransparente
    dnbr = read_tif(os.path.join(RASTERS_DIR, "s2_2022_dnbr_utm14n.tif"))
    xs10 = mx0 + (np.arange(dnbr.shape[1]) + 0.5) * 10.0
    ys10 = my1 - (np.arange(dnbr.shape[0]) + 0.5) * 10.0
    ax.contourf(xs10, ys10, dnbr, levels=[0.12, 1.0], colors=["#FFCC80"], hatches=["///"], alpha=0.25, zorder=3)
    ax.contour(xs10, ys10, dnbr, levels=[0.12], colors=["#E65100"], linewidths=1.2, linestyles="-", zorder=4)

    # Polígonos
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=2.4, ls="--", zorder=4))
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=1.5, ls="--", zorder=5))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=2.4, zorder=5))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#424242", lw=1.3, zorder=6))
    ax.add_patch(MplPolygon(poly_lag, closed=True, facecolor="#1565C0", edgecolor="white", lw=0.9, alpha=0.6, zorder=6))

    # Malla EM y magnetometría (+50 m buffer)
    eb = METRICS["diseno_geofisico"]["em_bbox"]
    ax.add_patch(Rectangle((eb[0], eb[1]), eb[2] - eb[0], eb[3] - eb[1],
                           fill=False, edgecolor="white", lw=2.2, ls=(0, (6, 3)), zorder=5))
    ax.add_patch(Rectangle((eb[0], eb[1]), eb[2] - eb[0], eb[3] - eb[1],
                           fill=False, edgecolor="#212121", lw=1.4, ls=(0, (6, 3)), zorder=6))

    # Rutas D8
    for fp in METRICS["topografia_hidrologia"]["landfill_flow_paths"]:
        xs = [c[0] for c in fp["coords"]]
        ys = [c[1] for c in fp["coords"]]
        ax.plot(xs, ys, color="white", lw=2.6, zorder=6)
        ax.plot(xs, ys, color="#0277BD", lw=1.6, zorder=7)
        if len(xs) > 9:
            ax.annotate("", xy=(xs[9], ys[9]), xytext=(xs[7], ys[7]),
                        arrowprops=dict(arrowstyle="-|>", color="#01579B", lw=1.8, mutation_scale=12), zorder=8)

    # Perfiles geofísicos con halo blanco clásico (SIN recuadros oscuros)
    for pf in METRICS["diseno_geofisico"]["perfiles"]:
        (x0, y0), (x1, y1) = pf["coords"]
        pid = pf["id"]
        if pid.startswith("L"):
            ax.plot([x0, x1], [y0, y1], color="white", lw=3.0, zorder=8)
            ax.plot([x0, x1], [y0, y1], color="#0D47A1", lw=1.8, zorder=9)
            ax.text(x0 - 8, y0, f"{pid} ({pf['longitud_m']} m)", color="#0D47A1", fontsize=7.6,
                    fontweight="bold", ha="right", va="center", path_effects=HALO_W, zorder=13)
        elif pid.startswith("T"):
            ax.plot([x0, x1], [y0, y1], color="white", lw=3.0, zorder=8)
            ax.plot([x0, x1], [y0, y1], color="#B71C1C", lw=1.8, zorder=9)
            ax.text(x0, y1 + 10, f"{pid} ({pf['longitud_m']} m)", color="#B71C1C", fontsize=7.6,
                    fontweight="bold", ha="center", va="bottom", path_effects=HALO_W, zorder=13)
        else:
            ax.plot([x0, x1], [y0, y1], color="white", lw=3.2, zorder=8)
            ax.plot([x0, x1], [y0, y1], color="#1B5E20", lw=2.0, zorder=9)
            ax.text(x0, y0 - 12, f"{pid} ({pf['longitud_m']} m)\n[Testigo aguas arriba]", color="#1B5E20",
                    fontsize=7.6, fontweight="bold", ha="center", va="top", path_effects=HALO_W, zorder=13)

    # Piezómetros P1-P4 + triángulo
    pzs = METRICS["diseno_geofisico"]["piezometros"]
    tri_x = [pzs[1]["E"], pzs[2]["E"], pzs[3]["E"], pzs[1]["E"]]
    tri_y = [pzs[1]["N"], pzs[2]["N"], pzs[3]["N"], pzs[1]["N"]]
    ax.plot(tri_x, tri_y, color="#4A148C", lw=1.2, ls=":", zorder=7)

    for pz in pzs:
        col = "#1B5E20" if pz["id"] == "P1" else "#6A1B9A"
        ax.plot(pz["E"], pz["N"], "s", color=col, ms=7.5, markeredgecolor="white", mew=1.0, zorder=11)
        if pz["id"] == "P1":
            dx, dy, ha = 0, 12, "center"
        elif pz["id"] == "P4":
            dx, dy, ha = -10, -14, "right"
        else:
            dx, dy, ha = 10, 8, "left"
        ax.text(pz["E"] + dx, pz["N"] + dy, f"{pz['id']} ({pz['elev_m']} m)",
                color=col, fontsize=7.6, fontweight="bold", ha=ha, path_effects=HALO_W, zorder=14)

    for p in METRICS["referencias"]["profepa"]:
        ax.plot(p["E"], p["N"], "^", color="#D32F2F", ms=7.5, markeredgecolor="white", mew=0.9, zorder=11)
        dx, dy, ha = (10, -14, "left") if "1" in p["id"] else (-10, 10, "right")
        ax.text(p["E"] + dx, p["N"] + dy, p["id"], color="#8E0000", fontsize=7.2, fontweight="bold",
                ha=ha, path_effects=HALO_W, zorder=12)

    ax.text(eb[2], eb[1] - 12, "Límite malla EM (10×20 m) y Magnetometría (1×5 m)",
            color="#212121", fontsize=7.3, fontweight="bold", ha="right", va="top", path_effects=HALO_W, zorder=12)

    setup_neatline_utm(ax, (665560, 666660), (2035260, 2036130), step_x=100, step_y=100)
    ax.set_xlabel("Este UTM Zona 14N (m)", fontsize=9.2, fontweight="bold")
    ax.set_ylabel("Norte UTM Zona 14N (m)", fontsize=9.2, fontweight="bold")

    # Panel derecho: Cajetín Cartográfico Clásico en 5 compartimentos
    gs_side = gs[0, 1].subgridspec(5, 1, height_ratios=[0.65, 0.72, 1.38, 1.05, 0.65], hspace=0.06)
    s_boxes = [fig.add_subplot(gs_side[i, 0]) for i in range(5)]
    for sb in s_boxes:
        sb.set_xticks([]); sb.set_yticks([])
        for sp in sb.spines.values():
            sp.set_linewidth(0.95); sp.set_color("black")

    # 1. Título del mapa
    s_boxes[0].text(0.5, 0.56,
                    "DISEÑO DE ADQUISICIÓN GEOFÍSICA\nGEORREFERENCIADO (FIG. 5)\n\n"
                    "Relleno Sanitario de Santa María Coapan\nTehuacán, Puebla, México",
                    ha="center", va="center", fontsize=8.8, fontweight="bold",
                    fontfamily="Liberation Serif", transform=s_boxes[0].transAxes, linespacing=1.28)

    # 2. Norte y escala gráfica
    s_boxes[1].text(0.5, 0.90, "ORIENTACIÓN Y ESCALA GRÁFICA", ha="center", va="top",
                    fontsize=7.8, fontweight="bold", transform=s_boxes[1].transAxes)
    draw_scale_bar_box(s_boxes[1], 0.33, 0.42, 0.58, 0.10, ["0", "50", "100", "200 m"], divisions=4)
    s_boxes[1].text(0.62, 0.12, "Malla reticular: 100 × 100 m (EPSG:32614)", ha="center", va="bottom",
                    fontsize=6.9, transform=s_boxes[1].transAxes)

    # 3. Simbología
    s_boxes[2].text(0.04, 0.94, "SIMBOLOGÍA", va="top", fontsize=8.0, fontweight="bold", transform=s_boxes[2].transAxes)
    leg_5 = [
        Line2D([0], [0], color="#424242", lw=1.5, label="Cuerpo principal de residuos (9.80 ha)"),
        Line2D([0], [0], color="#E65100", lw=1.6, ls="--", label="Huella operativa total (12.15 ha)"),
        mpatches.Patch(facecolor="#FFCC80", edgecolor="#E65100", hatch="///", alpha=0.6, label="Cicatriz incendio mayo 2022 (dNBR ≥ 0.12)"),
        Line2D([0], [0], color="#0D47A1", lw=1.8, label="Perfiles ERT/IP E–O (L1–L6; @ 5 m roll-along)"),
        Line2D([0], [0], color="#B71C1C", lw=1.8, label="Perfiles transversales N–S (T1–T2)"),
        Line2D([0], [0], color="#1B5E20", lw=2.0, label="Perfil de fondo aguas arriba (R1, 235 m)"),
        Line2D([0], [0], color="#212121", lw=1.4, ls="--", label="Malla EM y Magnetometría (+50 m)"),
        Line2D([0], [0], color="#0277BD", lw=1.6, label="Trayectorias escurrimiento D8 (ENE)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#1B5E20", markeredgecolor="black", ms=6, lw=0, label="Piezómetro testigo aguas arriba (P1)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#6A1B9A", markeredgecolor="black", ms=6, lw=0, label="Piezómetros aguas abajo (P2–P4)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#D32F2F", markeredgecolor="black", ms=6, lw=0, label="Puntos de inspección PROFEPA"),
    ]
    s_boxes[2].legend(handles=leg_5, loc="lower left", bbox_to_anchor=(0.01, 0.02), frameon=False,
                      fontsize=7.0, labelspacing=0.33, handlelength=2.0)

    # 4. Tabla de coordenadas UTM
    s_boxes[3].text(0.04, 0.93, "COORDENADAS CLAVE (UTM 14N — EPSG:32614)", va="top",
                    fontsize=7.6, fontweight="bold", transform=s_boxes[3].transAxes)
    rows_txt = ["Elem.   Este (m)   Norte (m)   Cota / Long."]
    for pz in pzs:
        rows_txt.append(f"{pz['id']:<5s}  {pz['E']:8.1f}  {pz['N']:9.1f}  {pz['elev_m']:6.1f} m snm")
    r1 = [x for x in METRICS["diseno_geofisico"]["perfiles"] if x["id"] == "R1"][0]
    rows_txt.append(f"R1-S   {r1['coords'][0][0]:8.1f}  {r1['coords'][0][1]:9.1f}   235 m (48 el.)")
    rows_txt.append(f"R1-N   {r1['coords'][1][0]:8.1f}  {r1['coords'][1][1]:9.1f}   Testigo natural")
    for p in METRICS["referencias"]["profepa"]:
        rows_txt.append(f"{p['id'][-1]:<1s}-PRO  {p['E']:8.1f}  {p['N']:9.1f}   Ref. oficial")
    s_boxes[3].text(0.04, 0.80, "\n".join(rows_txt), va="top", ha="left",
                    fontsize=6.8, fontfamily="Liberation Mono", transform=s_boxes[3].transAxes, linespacing=1.35)

    # 5. Autoría y fuente
    s_boxes[4].text(0.04, 0.88, "REFERENCIA Y AUTORÍA", va="top", fontsize=7.6, fontweight="bold", transform=s_boxes[4].transAxes)
    s_boxes[4].text(0.04, 0.68,
                    f"Sistema: WGS 84 / UTM Zona 14N (EPSG:32614)\n"
                    f"Base: Ortoimagen Esri Vivid (24/08/2025, 0.34 m)\n"
                    f"MDE: Copernicus GLO-30 (flujo D8 Wang & Liu)\n"
                    f"Proyecto: Geofísica Ambiental — Otoño 2026\n"
                    f"Autores: Ian A. Sandoval-Valderrábano y\n"
                    f"Carlos Enrique Fernández Tepale (FI, BUAP)",
                    va="top", fontsize=6.8, transform=s_boxes[4].transAxes, linespacing=1.28)

    fig.subplots_adjust(top=0.96, bottom=0.06, left=0.055, right=0.98)
    fig.canvas.draw()
    draw_esri_north(s_boxes[1], 0.16, 0.40, height=0.48)
    save_both(fig, "fig5_diseno_geofisico_georreferenciado")


def main():
    print("=== Paso 4 (Rediseño clásico 2010): Generación de mapas cartográficos (300 DPI PNG y PDF) ===")
    make_fig1()
    make_fig2()
    make_fig3()
    make_fig4()
    make_fig5()
    print("Todas las figuras rediseñadas generadas exitosamente.")


if __name__ == "__main__":
    main()
