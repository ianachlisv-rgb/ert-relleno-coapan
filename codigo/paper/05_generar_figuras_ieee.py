#!/usr/bin/env python3
"""
Paso 5: Figuras cartográficas a escala nativa IEEE (7.16 in = 18.2 cm, dos columnas, 300 DPI)
para inserción directa en el reporte LaTeX (sin títulos ni créditos incrustados).
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
from matplotlib.lines import Line2D

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
RASTERS_DIR = os.path.join(BASE_DIR, "rasters")
SIG_DIR = os.path.join(BASE_DIR, "sig")
OUT_DIR = os.path.join(BASE_DIR, "mapas_paper_ieee")
os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(RASTERS_DIR, "manifesto_sensores.json"), "r", encoding="utf-8") as f:
    MANIFEST = json.load(f)
with open(os.path.join(SIG_DIR, "resumen_metricas.json"), "r", encoding="utf-8") as f:
    METRICS = json.load(f)

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "axes.edgecolor": "#000000",
    "axes.linewidth": 0.85,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

HALO = [pe.withStroke(linewidth=2.0, foreground="white")]
HALO_SM = [pe.withStroke(linewidth=1.6, foreground="white")]


def read_tif(rel_or_abs, dtype=np.float32):
    p = rel_or_abs if os.path.isabs(rel_or_abs) else os.path.join(BASE_DIR, rel_or_abs)
    tmp = p + ".ieetmp.tif"
    subprocess.run(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=NONE", p, tmp],
                   check=True, capture_output=True)
    arr = np.array(Image.open(tmp), dtype=dtype)
    os.remove(tmp)
    return arr


def draw_north_axes(ax, cx, cy, height=0.35):
    fig = ax.get_figure()
    pos = ax.get_position()
    aspect = max(1e-4, pos.height * fig.get_figheight()) / max(1e-4, pos.width * fig.get_figwidth())
    w = height * 0.25 * aspect
    yt = cy + height * 0.42
    yb = cy - height * 0.42
    ym = cy - height * 0.20
    ax.add_patch(MplPolygon([[cx, yt], [cx - w, yb], [cx, ym]], closed=True,
                            facecolor="black", edgecolor="black", lw=0.6, transform=ax.transAxes, zorder=20))
    ax.add_patch(MplPolygon([[cx, yt], [cx + w, yb], [cx, ym]], closed=True,
                            facecolor="white", edgecolor="black", lw=0.6, transform=ax.transAxes, zorder=20))
    ax.text(cx, yt + 0.04, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=8.0, fontweight="bold", fontfamily="Liberation Serif", color="black", zorder=21)


def draw_scale_in_data(ax, x0, y0, length_m, label_txt, divisions=2, pad_box=True, label_size=6.5):
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    dx_span = xlim[1] - xlim[0]
    dy_span = ylim[1] - ylim[0]
    h = 0.018 * dy_span
    if pad_box:
        px = 0.025 * dx_span
        py_b = 0.015 * dy_span
        py_t = 0.072 * dy_span if label_size < 6.0 else 0.055 * dy_span
        ax.add_patch(Rectangle((x0 - px, y0 - py_b), length_m + 2 * px, h + py_b + py_t,
                               facecolor="white", edgecolor="black", lw=0.6, alpha=0.90, zorder=19))
    seg = length_m / divisions
    for i in range(divisions):
        fc = "black" if i % 2 == 0 else "white"
        ax.add_patch(Rectangle((x0 + i * seg, y0), seg, h, facecolor=fc, edgecolor="black", lw=0.6, zorder=20))
    ax.text(x0 + length_m / 2.0, y0 + h + 0.008 * dy_span, label_txt,
            ha="center", va="bottom", fontsize=label_size, fontweight="bold", color="black", zorder=21)


def setup_utm(ax, xlim, ylim, step_x, step_y):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks(np.arange(np.ceil(xlim[0] / step_x) * step_x, xlim[1] + 1, step_x))
    ax.set_yticks(np.arange(np.ceil(ylim[0] / step_y) * step_y, ylim[1] + 1, step_y))
    # Mostrar km UTM para evitar amontonamiento a 7.16 pulgadas (ej. 664.0, 666.0)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.1f}"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.1f}"))
    ax.tick_params(axis="x", labelsize=6.5, pad=1.5)
    ax.tick_params(axis="y", labelsize=6.5, pad=1.5)
    for lbl in ax.get_yticklabels():
        lbl.set_rotation(90)
        lbl.set_va("center")
    ax.grid(color="#555555", ls=":", lw=0.35, alpha=0.38)


def save_ieee(fig, stem):
    png = os.path.join(OUT_DIR, f"{stem}.png")
    pdf = os.path.join(OUT_DIR, f"{stem}.pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.04)
    fig.savefig(pdf, bbox_inches="tight", facecolor="white", pad_inches=0.04)
    plt.close(fig)
    print(f"Generada figura IEEE: {png} y .pdf")


# ==============================================================================
# IEEE FIG. 2: DELIMITACIÓN LOCAL SOBRE ORTOIMAGEN + CONTEXTO VIAL/HIDROLÓGICO
# ==============================================================================
def make_ieee_fig2():
    fig = plt.figure(figsize=(7.16, 3.85), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.6, 0.72], hspace=0.22)
    gs_m = gs[0].subgridspec(1, 2, wspace=0.22, width_ratios=[1.0, 1.04])

    ax1 = fig.add_subplot(gs_m[0, 0])
    ax2 = fig.add_subplot(gs_m[0, 1])

    # Panel (a)
    rx0, ry0, rx1, ry1 = MANIFEST["reg_bbox"]
    dem30 = read_tif(MANIFEST["dem"]["dem_30m"])
    hill30 = read_tif(MANIFEST["dem"]["hillshade_30m"])
    ax1.imshow(dem30, extent=[rx0, rx1, ry0, ry1], origin="upper", cmap="terrain", vmin=1500, vmax=2000, alpha=0.72)
    ax1.imshow(hill30, extent=[rx0, rx1, ry0, ry1], origin="upper", cmap="gray", alpha=0.30)

    for sl in METRICS["topografia_hidrologia"]["stream_lines"]:
        xs = [c[0] for c in sl["coords"]]; ys = [c[1] for c in sl["coords"]]
        ax1.plot(xs, ys, color="#1976D2", lw=0.55, alpha=0.55)
    for fp in METRICS["topografia_hidrologia"]["landfill_flow_paths"]:
        xs = [c[0] for c in fp["coords"]]; ys = [c[1] for c in fp["coords"]]
        ax1.plot(xs, ys, color="#0D47A1", lw=1.2, zorder=5)

    with open(os.path.join(SIG_DIR, "osm_contexto_utm14n.geojson"), "r", encoding="utf-8") as f:
        osm = json.load(f)
    for ft in osm["features"]:
        pr, gm = ft["properties"], ft["geometry"]
        if pr.get("layer") == "highway" and gm["type"] == "LineString":
            xs = [c[0] for c in gm["coordinates"]]; ys = [c[1] for c in gm["coordinates"]]
            hw = pr.get("highway", "")
            if pr.get("ref") == "MEX 125" or hw in ("trunk", "primary"):
                ax1.plot(xs, ys, color="#8E0000", lw=1.9, zorder=6)
                ax1.plot(xs, ys, color="#FFB300", lw=0.8, zorder=7)
            elif hw in ("secondary", "tertiary"):
                ax1.plot(xs, ys, color="#555555", lw=0.6, alpha=0.6, zorder=4)
        elif pr.get("layer") == "place" and gm["type"] == "Point":
            name = pr.get("name", "")
            px, py = gm["coordinates"]
            if 663600 <= px <= 668900 and 2033200 <= py <= 2038500:
                ax1.plot(px, py, "o", color="black", markeredgecolor="white", ms=3.5, zorder=9)
                if "Texcala" in name:
                    ax1.text(px + 120, py - 240, "San Antonio\nTexcala", fontsize=6.0, fontweight="bold", path_effects=HALO_SM, zorder=10)
                elif "Arrealco" in name:
                    ax1.text(px + 80, py - 240, "San Andrés\nArrealco", fontsize=6.0, fontweight="bold", path_effects=HALO_SM, zorder=10)

    coap = METRICS["referencias"]["santa_maria_coapan"]
    ax1.plot(coap["E"], coap["N"], "s", color="#1B5E20", markeredgecolor="white", ms=4.0, zorder=9)
    ax1.text(coap["E"] - 100, coap["N"] - 320, "Santa María\nCoapan", fontsize=6.2, fontweight="bold",
             color="#1B5E20", ha="right", path_effects=HALO_SM, zorder=10)

    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    ax1.add_patch(MplPolygon(poly_tot, closed=True, facecolor="#D32F2F", edgecolor="#7F0000", lw=0.9, alpha=0.82, zorder=8))
    bx0, bx1, by0, by1 = 665740, 666510, 2035260, 2036040
    ax1.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fill=False, edgecolor="black", lw=0.9, ls="--", zorder=11))
    ax1.text(666125, 2036130, "(b)", fontsize=6.8, fontweight="bold", ha="center", path_effects=HALO_SM, zorder=12)
    ax1.text(664750, 2035900, "MEX-125", fontsize=6.2, fontweight="bold", color="#7F0000", ha="center", path_effects=HALO_SM, zorder=10)

    setup_utm(ax1, (663500, 668900), (2033100, 2038500), step_x=2000, step_y=2000)
    ax1.set_xlabel("Este UTM 14N (km)", fontsize=7.2, fontweight="bold", labelpad=2)
    ax1.set_ylabel("Norte UTM 14N (km)", fontsize=7.2, fontweight="bold", labelpad=2)
    ax1.set_title("(a) Entorno local y drenaje D8", fontsize=8.0, fontweight="bold", pad=4)
    draw_scale_in_data(ax1, 663700, 2033350, 1000, "1 km", divisions=2)

    # Panel (b)
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    im25 = read_tif(MANIFEST["wayback"][-1]["file"], dtype=np.uint8)
    ax2.imshow(im25, extent=[fx0, fx1, fy0, fy1], origin="upper")

    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    poly_2011 = METRICS["geometria_listas"]["POLY_2011"]
    poly_lag = METRICS["geometria_listas"]["POLY_LAGUNA_NO"]

    ax2.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=1.9, ls="--", zorder=5))
    ax2.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=1.2, ls="--", zorder=6))
    ax2.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=2.0, zorder=6))
    ax2.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#C62828", lw=1.3, zorder=7))
    ax2.add_patch(MplPolygon(poly_2011, closed=True, fill=False, edgecolor="#1B5E20", lw=1.2, ls=":", zorder=7))
    ax2.add_patch(MplPolygon(poly_lag, closed=True, facecolor="#1565C0", edgecolor="white", lw=0.7, alpha=0.65, zorder=8))

    for p in METRICS["referencias"]["profepa"]:
        ax2.plot(p["E"], p["N"], "^", color="#D32F2F", ms=5.0, markeredgecolor="white", mew=0.6, zorder=11)
        dx, dy, ha = (8, -14, "left") if "1" in p["id"] else (-8, 10, "right")
        ax2.text(p["E"] + dx, p["N"] + dy, p["id"], color="#8E0000", fontsize=5.9, fontweight="bold", ha=ha, path_effects=HALO_SM, zorder=12)

    ax2.text(665995, 2035805, "Laguna NO\n(315 m²)", color="#0D47A1", fontsize=5.8, fontweight="bold", ha="right", path_effects=HALO_SM, zorder=11)
    ax2.text(665930, 2035630, "Aux. SO\n(2.11 ha)", color="#3E2723", fontsize=5.8, fontweight="bold", ha="center", path_effects=HALO_SM, zorder=11)

    setup_utm(ax2, (bx0, bx1), (by0, by1), step_x=200, step_y=200)
    ax2.set_xlabel("Este UTM 14N (km)", fontsize=7.2, fontweight="bold", labelpad=2)
    ax2.set_ylabel("Norte UTM 14N (km)", fontsize=7.2, fontweight="bold", labelpad=2)
    ax2.set_title("(b) Delimitación (24/08/2025, 0.34 m)", fontsize=8.0, fontweight="bold", pad=4)
    draw_scale_in_data(ax2, 665775, 2035295, 100, "100 m", divisions=2)

    # Leyenda inferior compacta
    ax_leg = fig.add_subplot(gs[1, 0])
    ax_leg.set_xticks([]); ax_leg.set_yticks([])
    for sp in ax_leg.spines.values():
        sp.set_linewidth(0.75); sp.set_color("black")

    items = [
        Line2D([0], [0], color="#C62828", lw=1.4, label="Cuerpo principal (9.80 ha)"),
        Line2D([0], [0], color="#E65100", lw=1.3, ls="--", label="Huella total (12.15 ha)"),
        Line2D([0], [0], color="#1B5E20", lw=1.3, ls=":", label="Núcleo 2011 (6.75 ha)"),
        mpatches.Patch(facecolor="#1565C0", edgecolor="black", alpha=0.65, label="Laguna lixiviados (315 m²)"),
        Line2D([0], [0], color="#8E0000", lw=1.8, label="Carretera Fed. MEX-125"),
        Line2D([0], [0], color="#0D47A1", lw=1.3, label="Drenaje D8 (ENE)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#D32F2F", markeredgecolor="black", ms=5, lw=0, label="Inspección PROFEPA"),
    ]
    ax_leg.legend(handles=items, loc="center left", bbox_to_anchor=(0.01, 0.5), ncol=4,
                  frameon=False, fontsize=6.4, columnspacing=1.0, handlelength=1.7)

    fig.subplots_adjust(top=0.92, bottom=0.04, left=0.075, right=0.985)
    fig.canvas.draw()
    draw_north_axes(ax_leg, 0.96, 0.45, height=0.62)
    save_ieee(fig, "ieee_fig2_delimitacion_local")


# ==============================================================================
# IEEE FIG. 3: EVOLUCIÓN HISTÓRICA 2×2 EN 1 COLUMNA IEEE (3.50 IN)
# ==============================================================================
def make_ieee_fig3():
    fig = plt.figure(figsize=(3.50, 3.25), dpi=300)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.42], wspace=0.07, hspace=0.22)

    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    rx0, ry0, rx1, ry1 = MANIFEST["reg_bbox"]
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    vx0, vx1, vy0, vy1 = 665800, 666430, 2035490, 2035940

    ls_map = {r["tag"]: r for r in MANIFEST["landsat"]}
    wb_map = {r["rid"]: r for r in MANIFEST["wayback"]}

    # (a) Landsat 1993-02-15
    ax0 = fig.add_subplot(gs[0, 0])
    b = ls_map["1993_ini"]["bands"]
    rgb = np.clip(np.dstack([
        np.clip(read_tif(b["red"]) * 0.0000275 - 0.2, 0, 1),
        np.clip(read_tif(b["green"]) * 0.0000275 - 0.2, 0, 1),
        np.clip(read_tif(b["blue"]) * 0.0000275 - 0.2, 0, 1),
    ]) / 0.28, 0, 1)
    ax0.imshow(rgb, extent=[rx0, rx1, ry0, ry1], origin="upper", interpolation="nearest")
    ax0.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=1.3, ls="--"))
    ax0.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=0.85, ls="--"))
    ax0.set_title("(a) 02/1993 (L5, 30 m)", fontsize=6.8, fontweight="bold", pad=2.5)

    wb_sel = [
        ("10", gs[0, 1], "(b) 06/2011 (0.50 m)", False),
        ("1034", gs[1, 0], "(c) 11/2022 (0.31 m)", False),
        ("63116", gs[1, 1], "(d) 08/2025 (0.34 m)", True),
    ]
    panels = [ax0]
    for rid, slot, ttl, add_scale in wb_sel:
        ax = fig.add_subplot(slot)
        im = read_tif(wb_map[rid]["file"], dtype=np.uint8)
        ax.imshow(im, extent=[fx0, fx1, fy0, fy1], origin="upper")
        ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=1.3, ls="--"))
        ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=0.85, ls="--"))
        ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=1.3))
        ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#C62828", lw=0.85))
        ax.set_title(ttl, fontsize=6.8, fontweight="bold", pad=2.5)
        panels.append((ax, add_scale))

    ax0.set_xlim(vx0, vx1); ax0.set_ylim(vy0, vy1)
    ax0.set_xticks([]); ax0.set_yticks([])
    for ax, add_scale in panels[1:]:
        ax.set_xlim(vx0, vx1); ax.set_ylim(vy0, vy1)
        ax.set_xticks([]); ax.set_yticks([])
        if add_scale:
            draw_scale_in_data(ax, 665822, 2035872, 100, "100 m", divisions=2, label_size=5.4)

    ax_leg = fig.add_subplot(gs[2, :])
    ax_leg.set_xticks([]); ax_leg.set_yticks([])
    for sp in ax_leg.spines.values():
        sp.set_linewidth(0.75); sp.set_color("black")
    items = [
        Line2D([0], [0], color="#C62828", lw=1.3, label="Cuerpo principal 2025 (9.80 ha)"),
        Line2D([0], [0], color="#E65100", lw=1.3, ls="--", label="Huella operativa total 2025 (12.15 ha)"),
    ]
    ax_leg.legend(handles=items, loc="center left", bbox_to_anchor=(0.01, 0.5), ncol=1,
                  frameon=False, fontsize=5.9, labelspacing=0.3, handlelength=1.6)
    ax_leg.text(0.75, 0.5, "Marco: 630 × 450 m\n(EPSG:32614)", transform=ax_leg.transAxes,
                va="center", ha="center", fontsize=5.5, color="#333333")

    fig.subplots_adjust(top=0.93, bottom=0.03, left=0.02, right=0.98)
    fig.canvas.draw()
    draw_north_axes(ax_leg, 0.93, 0.44, height=0.58)
    save_ieee(fig, "ieee_fig3_evolucion_4fechas")


# ==============================================================================
# IEEE FIG. 4: DISEÑO GEOFÍSICO + CURVAS 20 M + DRENAJE D8 EN 1 COLUMNA (3.50 IN)
# ==============================================================================
def make_ieee_fig4():
    fig = plt.figure(figsize=(3.50, 4.35), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.15, 1.15], hspace=0.20)
    ax = fig.add_subplot(gs[0, 0])

    rx0, ry0, rx1, ry1 = MANIFEST["reg_bbox"]
    mx0, my0, mx1, my1 = MANIFEST["med_bbox"]
    fx0, fy0, fx1, fy1 = MANIFEST["fine_bbox"]
    dem30 = read_tif(MANIFEST["dem"]["dem_30m"])
    poly_tot = METRICS["geometria_listas"]["POLY_TOTAL"]
    poly_p = METRICS["geometria_listas"]["POLY_PRINCIPAL"]
    poly_lag = METRICS["geometria_listas"]["POLY_LAGUNA_NO"]

    im25 = read_tif(MANIFEST["wayback"][-1]["file"], dtype=np.uint8)
    ax.imshow(im25, extent=[fx0, fx1, fy0, fy1], origin="upper", alpha=0.84)

    # Curvas de nivel cada 20 m sobre el área del mapa
    xs30 = rx0 + (np.arange(dem30.shape[1]) + 0.5) * 30.0
    ys30 = ry1 - (np.arange(dem30.shape[0]) + 0.5) * 30.0
    levels = np.arange(1680, 1860, 20)
    cs = ax.contour(xs30, ys30, dem30, levels=levels, colors="#3E2723", linewidths=0.52, alpha=0.85, zorder=2.5)
    cs.set(path_effects=[pe.withStroke(linewidth=1.15, foreground=(1.0, 1.0, 1.0, 0.55))])
    clbls = ax.clabel(cs, inline=False, fontsize=4.9, fmt="%d")
    for txt in clbls:
        txt.set_path_effects(HALO_SM)
        txt.set_zorder(2.8)

    dnbr = read_tif(os.path.join(RASTERS_DIR, "s2_2022_dnbr_utm14n.tif"))
    xs10 = mx0 + (np.arange(dnbr.shape[1]) + 0.5) * 10.0
    ys10 = my1 - (np.arange(dnbr.shape[0]) + 0.5) * 10.0
    ax.contourf(xs10, ys10, dnbr, levels=[0.10, 1.0], colors=["#FFCC80"], hatches=["////"], alpha=0.24, zorder=3)
    ax.contour(xs10, ys10, dnbr, levels=[0.10], colors=["#E65100"], linewidths=0.75, zorder=4)

    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="white", lw=1.5, ls="--", zorder=4))
    ax.add_patch(MplPolygon(poly_tot, closed=True, fill=False, edgecolor="#E65100", lw=0.95, ls="--", zorder=5))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="white", lw=1.4, zorder=5))
    ax.add_patch(MplPolygon(poly_p, closed=True, fill=False, edgecolor="#424242", lw=0.75, zorder=6))
    ax.add_patch(MplPolygon(poly_lag, closed=True, facecolor="#1565C0", edgecolor="white", lw=0.55, alpha=0.68, zorder=6))

    eb = METRICS["diseno_geofisico"]["em_bbox"]
    ax.add_patch(Rectangle((eb[0], eb[1]), eb[2] - eb[0], eb[3] - eb[1],
                           fill=False, edgecolor="white", lw=1.35, ls=(0, (5, 3)), zorder=5))
    ax.add_patch(Rectangle((eb[0], eb[1]), eb[2] - eb[0], eb[3] - eb[1],
                           fill=False, edgecolor="#212121", lw=0.85, ls=(0, (5, 3)), zorder=6))

    for fp in METRICS["topografia_hidrologia"]["landfill_flow_paths"]:
        xs = [c[0] for c in fp["coords"]]; ys = [c[1] for c in fp["coords"]]
        ax.plot(xs, ys, color="white", lw=1.6, zorder=6)
        ax.plot(xs, ys, color="#0277BD", lw=0.95, zorder=7)
        if len(xs) > 9:
            ax.annotate("", xy=(xs[9], ys[9]), xytext=(xs[7], ys[7]),
                        arrowprops=dict(arrowstyle="-|>", color="#01579B", lw=1.05, mutation_scale=7.5), zorder=8)

    for pf in METRICS["diseno_geofisico"]["perfiles"]:
        (x0, y0), (x1, y1) = pf["coords"]
        pid = pf["id"]
        if pid.startswith("L"):
            ax.plot([x0, x1], [y0, y1], color="white", lw=1.8, zorder=8)
            ax.plot([x0, x1], [y0, y1], color="#0D47A1", lw=1.05, zorder=9)
            ax.text(x0 - 8, y0, pid, color="#0D47A1", fontsize=5.5, fontweight="bold", ha="right", va="center", path_effects=HALO_SM, zorder=13)
        elif pid.startswith("T"):
            ax.plot([x0, x1], [y0, y1], color="white", lw=1.8, zorder=8)
            ax.plot([x0, x1], [y0, y1], color="#B71C1C", lw=1.05, zorder=9)
            ax.text(x0, y1 + 10, pid, color="#B71C1C", fontsize=5.5, fontweight="bold", ha="center", va="bottom", path_effects=HALO_SM, zorder=13)
        else:
            ax.plot([x0, x1], [y0, y1], color="white", lw=1.9, zorder=8)
            ax.plot([x0, x1], [y0, y1], color="#1B5E20", lw=1.2, zorder=9)
            ax.text(x0, y0 - 12, "R1", color="#1B5E20", fontsize=5.7, fontweight="bold", ha="center", va="top", path_effects=HALO_SM, zorder=13)

    pzs = METRICS["diseno_geofisico"]["piezometros"]
    tri_x = [pzs[1]["E"], pzs[2]["E"], pzs[3]["E"], pzs[1]["E"]]
    tri_y = [pzs[1]["N"], pzs[2]["N"], pzs[3]["N"], pzs[1]["N"]]
    ax.plot(tri_x, tri_y, color="#4A148C", lw=0.85, ls=":", zorder=7)

    for pz in pzs:
        col = "#1B5E20" if pz["id"] == "P1" else "#6A1B9A"
        ax.plot(pz["E"], pz["N"], "s", color=col, ms=4.4, markeredgecolor="white", mew=0.6, zorder=11)
        if pz["id"] == "P1":
            dx, dy, ha = 0, 12, "center"
        elif pz["id"] == "P4":
            dx, dy, ha = -10, -14, "right"
        else:
            dx, dy, ha = 10, 8, "left"
        ax.text(pz["E"] + dx, pz["N"] + dy, pz["id"], color=col, fontsize=5.7, fontweight="bold", ha=ha, path_effects=HALO_SM, zorder=14)

    for p in METRICS["referencias"]["profepa"]:
        ax.plot(p["E"], p["N"], "^", color="#D32F2F", ms=4.2, markeredgecolor="white", mew=0.55, zorder=11)

    setup_utm(ax, (665570, 666650), (2035270, 2036120), step_x=200, step_y=200)
    ax.set_xlabel("Este UTM 14N (km)", fontsize=6.8, fontweight="bold", labelpad=2)
    ax.set_ylabel("Norte UTM 14N (km)", fontsize=6.8, fontweight="bold", labelpad=2)
    ax.set_title("Diseño geofísico y control topográfico (UTM 14N)", fontsize=7.3, fontweight="bold", pad=4)
    draw_scale_in_data(ax, 665605, 2035305, 100, "100 m", divisions=2, label_size=5.8)

    ax_leg = fig.add_subplot(gs[1, 0])
    ax_leg.set_xticks([]); ax_leg.set_yticks([])
    for sp in ax_leg.spines.values():
        sp.set_linewidth(0.75); sp.set_color("black")

    items = [
        Line2D([0], [0], color="#E65100", lw=1.1, ls="--", label="Huella total (12.15 ha)"),
        mpatches.Patch(facecolor="#FFCC80", edgecolor="#E65100", hatch="////", alpha=0.6, label="Incendio 05/2022 (dNBR≥0.10)"),
        Line2D([0], [0], color="#0D47A1", lw=1.2, label="ERT/IP L1–L6 (275–435 m)"),
        Line2D([0], [0], color="#B71C1C", lw=1.2, label="Transversales T1–T2"),
        Line2D([0], [0], color="#1B5E20", lw=1.3, label="Fondo R1 (235 m, oeste)"),
        Line2D([0], [0], color="#212121", lw=0.95, ls="--", label="Malla EM/Mag (+50 m)"),
        Line2D([0], [0], color="#0277BD", lw=1.2, label="Drenaje D8 (53.5° ENE)"),
        Line2D([0], [0], color="#3E2723", lw=0.75, label="Curvas de nivel (20 m)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#1B5E20", markeredgecolor="black", ms=4.2, lw=0, label="Piezóm. testigo (P1)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#6A1B9A", markeredgecolor="black", ms=4.2, lw=0, label="Piezóm. ENE (P2–P4)"),
    ]
    ax_leg.legend(handles=items, loc="center left", bbox_to_anchor=(0.01, 0.5), ncol=2,
                  frameon=False, fontsize=5.35, columnspacing=0.65, labelspacing=0.28, handlelength=1.35)

    fig.subplots_adjust(top=0.94, bottom=0.03, left=0.145, right=0.98)
    fig.canvas.draw()
    draw_north_axes(ax_leg, 0.945, 0.45, height=0.44)
    save_ieee(fig, "ieee_fig4_topografia_y_diseno_geofisico")


def plot_geojson_polys(ax, geom, facecolor="#EEEEEE", edgecolor="#444444", lw=0.5, alpha=1.0, zorder=2):
    gtype = geom.get("type")
    polys = [geom["coordinates"]] if gtype == "Polygon" else (geom["coordinates"] if gtype == "MultiPolygon" else [])
    for poly in polys:
        ext = poly[0]
        ax.add_patch(MplPolygon(ext, closed=True, facecolor=facecolor, edgecolor=edgecolor, lw=lw, alpha=alpha, zorder=zorder))


def make_ieee_fig1():
    """Localización regional (a) México, (b) Puebla, (c) Municipio de Tehuacán con Coapan y el relleno."""
    with open(os.path.join(SIG_DIR, "mexico_estados.geojson"), "r", encoding="utf-8") as f:
        mx_gj = json.load(f)
    with open(os.path.join(SIG_DIR, "puebla_municipios.geojson"), "r", encoding="utf-8") as f:
        pb_gj = json.load(f)

    fig = plt.figure(figsize=(7.16, 2.45), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 0.95, 1.15], wspace=0.28)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])

    # (a) República Mexicana
    for ft in mx_gj["features"]:
        is_pue = ft["properties"].get("state_name") == "Puebla"
        plot_geojson_polys(
            ax1, ft["geometry"],
            facecolor="#C62828" if is_pue else "#ECEFF1",
            edgecolor="#333333" if is_pue else "#78909C",
            lw=0.65 if is_pue else 0.35, zorder=4 if is_pue else 2
        )
    ax1.text(-102.5, 23.5, "MÉXICO", fontsize=7.5, fontweight="bold", ha="center", color="#263238")
    ax1.annotate("Puebla", xy=(-97.9, 18.8), xytext=(-104.5, 16.0),
                 fontsize=6.8, fontweight="bold", color="#B71C1C",
                 arrowprops=dict(arrowstyle="-|>", color="#B71C1C", lw=0.8, mutation_scale=7))
    ax1.set_xlim(-118.5, -86.2); ax1.set_ylim(14.0, 33.2)
    ax1.set_aspect("equal", adjustable="box")
    ax1.set_xticks([]); ax1.set_yticks([])
    ax1.set_title("(a) México y Puebla", fontsize=7.8, fontweight="bold", pad=4)

    # (b) Municipios de Puebla
    teh_geom = None
    for ft in pb_gj["features"]:
        is_teh = ft["properties"].get("NOM_MUN") == "Tehuacán"
        if is_teh:
            teh_geom = ft["geometry"]
        plot_geojson_polys(
            ax2, ft["geometry"],
            facecolor="#C62828" if is_teh else "#ECEFF1",
            edgecolor="#212121" if is_teh else "#90A4AE",
            lw=0.7 if is_teh else 0.25, zorder=4 if is_teh else 2
        )
    ax2.plot(-98.2063, 19.0414, "o", color="black", ms=2.6, zorder=6)
    ax2.text(-98.22, 19.12, "Puebla", fontsize=6.4, fontweight="bold", ha="center", path_effects=HALO_SM, zorder=7)
    ax2.text(-97.25, 18.22, "Tehuacán", fontsize=6.4, fontweight="bold", color="#B71C1C", ha="center", path_effects=HALO_SM, zorder=7)
    ax2.set_xlim(-99.15, -96.65); ax2.set_ylim(17.80, 20.88)
    ax2.set_aspect("equal", adjustable="box")
    ax2.set_xticks([-99.0, -98.0, -97.0]); ax2.set_yticks([18.0, 19.0, 20.0])
    ax2.tick_params(labelsize=6.0, pad=1.5)
    ax2.set_xlabel("Longitud (°O)", fontsize=6.8, fontweight="bold", labelpad=2)
    ax2.set_ylabel("Latitud (°N)", fontsize=6.8, fontweight="bold", labelpad=2)
    ax2.grid(color="#888888", ls=":", lw=0.3, alpha=0.4)
    ax2.set_title("(b) Estado de Puebla", fontsize=7.8, fontweight="bold", pad=4)

    # (c) Municipio de Tehuacán
    if teh_geom:
        plot_geojson_polys(ax3, teh_geom, facecolor="#F5EFE6", edgecolor="#4E342E", lw=0.85, zorder=2)
    # Tehuacán ciudad, Iglesia Coapan, Relleno sanitario
    ax3.plot(-97.3928, 18.4631, "o", color="#212121", ms=3.5, zorder=6)
    ax3.text(-97.385, 18.478, "Tehuacán", fontsize=6.4, fontweight="bold", ha="left", path_effects=HALO_SM, zorder=7)

    coap = METRICS["referencias"]["santa_maria_coapan"]
    ax3.plot(coap["lon"], coap["lat"], "^", color="#1B5E20", markeredgecolor="white", mew=0.5, ms=4.8, zorder=7)
    ax3.text(coap["lon"] + 0.012, coap["lat"] - 0.002, "Santa María\nCoapan", fontsize=6.0, fontweight="bold",
             color="#1B5E20", ha="left", va="center", path_effects=HALO_SM, zorder=8)

    clat, clon = METRICS["poligonos"]["cuerpo_principal"]["centroide_wgs84"]
    ax3.plot(clon, clat, "s", color="#C62828", markeredgecolor="white", mew=0.6, ms=5.0, zorder=8)
    ax3.text(clon - 0.014, clat - 0.032, "Relleno\nsanitario", fontsize=6.2, fontweight="bold",
             color="#B71C1C", ha="center", va="top", path_effects=HALO_SM, zorder=9)
    ax3.annotate("", xy=(clon, clat), xytext=(clon - 0.014, clat - 0.030),
                 arrowprops=dict(arrowstyle="-|>", color="#B71C1C", lw=0.7, mutation_scale=6), zorder=8)

    ax3.set_xlim(-97.68, -97.18); ax3.set_ylim(18.27, 18.67)
    ax3.set_aspect("equal", adjustable="box")
    ax3.set_xticks([-97.6, -97.4, -97.2]); ax3.set_yticks([18.3, 18.4, 18.5, 18.6])
    ax3.tick_params(labelsize=6.0, pad=1.5)
    ax3.set_xlabel("Longitud (°O)", fontsize=6.8, fontweight="bold", labelpad=2)
    ax3.grid(color="#888888", ls=":", lw=0.3, alpha=0.4)
    ax3.set_title("(c) Municipio de Tehuacán", fontsize=7.8, fontweight="bold", pad=4)

    fig.subplots_adjust(top=0.88, bottom=0.16, left=0.02, right=0.98)
    fig.canvas.draw()
    draw_north_axes(ax3, 0.12, 0.80, height=0.22)
    save_ieee(fig, "ieee_fig1_localizacion_regional")


def main():
    make_ieee_fig1()
    make_ieee_fig2()
    make_ieee_fig3()
    make_ieee_fig4()


if __name__ == "__main__":
    main()
