#!/usr/bin/env python3
"""
Paso 6: Simulación sintética ERT 2.5D por diferencias finitas e inversión suavizada
(Loke-Barker) sobre malla independiente para el perfil base de 48 electrodos (235 m).
Proyecto Final de Geofísica Ambiental (Otoño 2026) — Facultad de Ingeniería, BUAP.
Autores: Ian A. Sandoval-Valderrábano y Carlos Enrique Fernández Tepale.
"""

import os
import json
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.optimize import nnls
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle

BASE_DIR = "/home/carlos-enrique/proyectos/Carolina/Ambiental final"
OUT_DIR = os.path.join(BASE_DIR, "mapas_paper_ieee")
SIG_DIR = os.path.join(BASE_DIR, "sig")
os.makedirs(OUT_DIR, exist_ok=True)


def build_mesh_1d(core_start, core_end, core_dx, pad_widths):
    left_pads = [core_start - np.sum(pad_widths[:i+1]) for i in range(len(pad_widths))][::-1]
    core = np.arange(core_start, core_end + 1e-9, core_dx)
    right_pads = [core_end + np.sum(pad_widths[:i+1]) for i in range(len(pad_widths))]
    return np.concatenate([left_pads, core, right_pads])


def assemble_25d_operators(xs, zs, sigma_cells):
    """
    Discretización FVM simétrica en nodos (nx * nz) para conductividad por celda (nx-1, nz-1).
    Retorna matrices dispersas base para conductancia K_sig y masa M_sig (A(k) = K_sig + k^2 M_sig),
    más arreglos de bordes para derivadas analíticas rápidas del jacobiano.
    """
    nx = len(xs)
    nz = len(zs)
    dx = np.diff(xs)
    dz = np.diff(zs)
    # Conductancia horizontal entre (ix, iz) y (ix+1, iz): [nx-1, nz]
    sig_pad_z = np.zeros((nx - 1, nz), dtype=np.float64)
    sig_pad_z[:, 0] = sigma_cells[:, 0] * dz[0] * 0.5
    sig_pad_z[:, 1:-1] = (sigma_cells[:, :-1] * dz[:-1][None, :] + sigma_cells[:, 1:] * dz[1:][None, :]) * 0.5
    sig_pad_z[:, -1] = sigma_cells[:, -1] * dz[-1] * 0.5
    gx = sig_pad_z / dx[:, None]

    # Conductancia vertical entre (ix, iz) y (ix, iz+1): [nx, nz-1]
    sig_pad_x = np.zeros((nx, nz - 1), dtype=np.float64)
    sig_pad_x[0, :] = sigma_cells[0, :] * dx[0] * 0.5
    sig_pad_x[1:-1, :] = (sigma_cells[:-1, :] * dx[:-1][:, None] + sigma_cells[1:, :] * dx[1:][:, None]) * 0.5
    sig_pad_x[-1, :] = sigma_cells[-1, :] * dx[-1] * 0.5
    gz = sig_pad_x / dz[None, :]

    # Masa por nodo: 1/4 de área * sigma de cada celda adyacente
    area_sig = sigma_cells * (dx[:, None] * dz[None, :]) * 0.25
    m_node = np.zeros((nx, nz), dtype=np.float64)
    m_node[:-1, :-1] += area_sig
    m_node[1:, :-1] += area_sig
    m_node[:-1, 1:] += area_sig
    m_node[1:, 1:] += area_sig

    # Índices de nodos: node(ix, iz) = ix * nz + iz (coincide con .ravel() de arreglos (nx, nz))
    ix_h, iz_h = np.meshgrid(np.arange(nx - 1), np.arange(nz), indexing="ij")
    u_h = (ix_h * nz + iz_h).ravel()
    v_h = ((ix_h + 1) * nz + iz_h).ravel()
    w_h = gx.ravel()

    ix_v, iz_v = np.meshgrid(np.arange(nx), np.arange(nz - 1), indexing="ij")
    u_v = (ix_v * nz + iz_v).ravel()
    v_v = (ix_v * nz + (iz_v + 1)).ravel()
    w_v = gz.ravel()

    rows = np.concatenate([u_h, v_h, u_v, v_v])
    cols = np.concatenate([v_h, u_h, v_v, u_v])
    vals = np.concatenate([-w_h, -w_h, -w_v, -w_v])

    diag_k = np.zeros(nx * nz, dtype=np.float64)
    np.add.at(diag_k, u_h, w_h)
    np.add.at(diag_k, v_h, w_h)
    np.add.at(diag_k, u_v, w_v)
    np.add.at(diag_k, v_v, w_v)

    all_idx = np.arange(nx * nz)
    K = sp.csc_matrix(
        (np.concatenate([vals, diag_k]), (np.concatenate([rows, all_idx]), np.concatenate([cols, all_idx]))),
        shape=(nx * nz, nx * nz)
    )
    M = sp.diags(m_node.ravel(), format="csc")

    # Aplicar Dirichlet homogéneo (phi=0) en bordes exteriores (ix=0, ix=nx-1, iz=nz-1)
    bmask = np.zeros((nx, nz), dtype=bool)
    bmask[0, :] = True
    bmask[-1, :] = True
    bmask[:, -1] = True
    bfree = ~bmask.ravel()
    return K, M, bfree


def calibrate_k_weights(xs, zs, elec_nodes, k_vals):
    """Calibra pesos de cuadratura de Fourier contra semiespacio homogéneo exacto 1/(2*pi*r)."""
    nx = len(xs)
    nc = (nx - 1) * (len(zs) - 1)
    sig_hom = np.ones((nx - 1, len(zs) - 1), dtype=np.float64)
    K, M, bfree = assemble_25d_operators(xs, zs, sig_hom)
    K_ff = K[bfree, :][:, bfree]
    M_ff = M[bfree, :][:, bfree]

    # Mapa de índice global a libre
    free_map = np.full(nx * len(zs), -1, dtype=int)
    free_map[bfree] = np.arange(np.sum(bfree))
    efree = free_map[elec_nodes]

    RHS = np.zeros((np.sum(bfree), len(elec_nodes)), dtype=np.float64)
    for j, nf in enumerate(efree):
        RHS[nf, j] = 1.0

    # Resolver para cada k_m y guardar potencial entre pares de electrodos
    P_k = np.zeros((len(elec_nodes), len(elec_nodes), len(k_vals)), dtype=np.float64)
    for m, kv in enumerate(k_vals):
        A = (K_ff + (kv * kv) * M_ff).tocsc()
        sol = spla.spsolve(A, RHS)
        P_k[:, :, m] = sol[efree, :]

    # Construir pares únicos de distancia r = |x_i - x_j| (elec_nodes = elec_ix * nz)
    ex = xs[elec_nodes // len(zs)]
    rows_A = []
    rows_b = []
    for i in range(len(elec_nodes)):
        for j in range(i + 1, len(elec_nodes)):
            r = abs(ex[j] - ex[i])
            rows_A.append(P_k[i, j, :])
            rows_b.append(1.0 / (2.0 * np.pi * r))
    A_ls = np.array(rows_A)
    b_ls = np.array(rows_b)
    # Ridge mínimo ponderado por 1/b_ls para minimizar error relativo en todos los espaciamientos
    scale = 1.0 / b_ls
    w, _ = nnls(A_ls * scale[:, None], np.ones_like(b_ls))
    pred = A_ls @ w
    rel_err = np.max(np.abs(pred - b_ls) / b_ls) * 100.0
    med_err = np.median(np.abs(pred - b_ls) / b_ls) * 100.0
    print(f"Calibración 2.5D NNLS (M={len(k_vals)} k): err mediana={med_err:.2f}%, máx={rel_err:.2f}%")
    return w


def generate_ws_schedule(n_elec=48, dx=5.0):
    """Genera secuencia Wenner-Schlumberger clásica sobre 48 electrodos @ 5 m."""
    quads = []
    # a = m*5m, n <= 8 (estándar Wenner-Schlumberger para buena razón señal/ruido)
    for a_step in [1, 2, 3, 4, 5, 6]:
        for n in range(1, 9):
            span = (2 * n + 1) * a_step
            if span >= n_elec:
                break
            for iA in range(0, n_elec - span):
                iM = iA + n * a_step
                iN = iM + a_step
                iB = iN + n * a_step
                xA, xM, xN, xB = iA * dx, iM * dx, iN * dx, iB * dx
                k_geom = 2.0 * np.pi / (1.0/abs(xA-xM) - 1.0/abs(xA-xN) - 1.0/abs(xB-xM) + 1.0/abs(xB-xN))
                x_mid = 0.5 * (xM + xN)
                # Pseudoprofundidad efectiva (Edwards, 1977)
                L_ab2 = 0.5 * (xB - xA)
                z_ps = 0.38 * L_ab2  # Edwards ~0.19*L_AB = 0.38*(L_AB/2)
                quads.append((iA, iB, iM, iN, k_geom, x_mid, -z_ps))
    return quads


def forward_and_jacobian(xs, zs, sigma_cells, elec_nodes, k_vals, k_weights, quads, need_jac=False, k_g_override=None):
    """Calcula resistividades aparentes (y opcionalmente jacobiano ∂ln(ρ_a)/∂ln(σ))."""
    nx = len(xs)
    nz = len(zs)
    K, M, bfree = assemble_25d_operators(xs, zs, sigma_cells)
    K_ff = K[bfree, :][:, bfree]
    M_ff = M[bfree, :][:, bfree]

    free_map = np.full(nx * nz, -1, dtype=int)
    free_map[bfree] = np.arange(np.sum(bfree))
    efree = free_map[elec_nodes]

    n_e = len(elec_nodes)
    RHS = np.zeros((np.sum(bfree), n_e), dtype=np.float64)
    for j, nf in enumerate(efree):
        RHS[nf, j] = 1.0

    # Almacenar potenciales completos para todos los electrodos y k_m
    Phi_full = np.zeros((len(k_vals), nx * nz, n_e), dtype=np.float64)
    for m, kv in enumerate(k_vals):
        A = (K_ff + (kv * kv) * M_ff).tocsc()
        sol = spla.spsolve(A, RHS)
        Phi_full[m, bfree, :] = sol

    # Potencial ensamblado por par de electrodos: V[i_src, i_rec] = sum_m w_m * Phi[m, node_rec, i_src]
    V_mat = np.tensordot(k_weights, Phi_full[:, elec_nodes, :], axes=(0, 0))  # (n_e, n_e)

    iA = np.array([q[0] for q in quads])
    iB = np.array([q[1] for q in quads])
    iM = np.array([q[2] for q in quads])
    iN = np.array([q[3] for q in quads])
    k_g = np.array([q[4] for q in quads]) if k_g_override is None else k_g_override

    dV = V_mat[iM, iA] - V_mat[iN, iA] - V_mat[iM, iB] + V_mat[iN, iB]
    rho_a = np.maximum(1e-3, k_g * dV)

    if not need_jac:
        return rho_a

    # Jacobiano exacto por celdas: J[q, c] = (sigma_c / dV_q) * ∂dV_q/∂σ_c = ∂ln(ρ_a)/∂ln(σ_c)
    dx = np.diff(xs)
    dz = np.diff(zs)
    n_cx, n_cz = nx - 1, nz - 1
    n_c = n_cx * n_cz
    n_q = len(quads)

    Phi_grid = Phi_full.reshape(len(k_vals), nx, nz, n_e)  # axis1=ix, axis2=iz

    U = Phi_grid[:, :, :, iA] - Phi_grid[:, :, :, iB]  # (nk, nx, nz, n_q)
    W = Phi_grid[:, :, :, iM] - Phi_grid[:, :, :, iN]  # (nk, nx, nz, n_q)

    # 4 esquinas de cada celda (nk, n_cx, n_cz, n_q)
    u00, u10 = U[:, :-1, :-1, :], U[:, 1:, :-1, :]
    u01, u11 = U[:, :-1, 1:, :], U[:, 1:, 1:, :]
    w00, w10 = W[:, :-1, :-1, :], W[:, 1:, :-1, :]
    w01, w11 = W[:, :-1, 1:, :], W[:, 1:, 1:, :]

    # Factores geométricos (1, n_cx, n_cz, 1)
    cx_h = (dz[None, :] / (2.0 * dx[:, None]))[None, :, :, None]
    cx_v = (dx[:, None] / (2.0 * dz[None, :]))[None, :, :, None]
    cm = (0.25 * dx[:, None] * dz[None, :])[None, :, :, None]

    term_k = cx_h * ((u10 - u00) * (w10 - w00) + (u11 - u01) * (w11 - w01)) + \
             cx_v * ((u01 - u00) * (w01 - w00) + (u11 - u10) * (w11 - w10))
    term_m = (k_vals[:, None, None, None] ** 2) * cm * (u00 * w00 + u10 * w10 + u01 * w01 + u11 * w11)

    dA_term = term_k + term_m  # (nk, n_cx, n_cz, n_q)
    dV_dsig = -np.tensordot(k_weights, dA_term, axes=(0, 0))  # (n_cx, n_cz, n_q)
    dV_dsig = np.transpose(dV_dsig, (2, 0, 1)).reshape(n_q, n_c)

    J = dV_dsig * (sigma_cells.ravel()[None, :] / dV[:, None])
    return rho_a, J


def build_true_model(xc, zc):
    """Construye el modelo geológico sintético de Santa María Coapan en malla dada."""
    XX, ZZ = np.meshgrid(xc, zc, indexing="ij")
    rho = np.full_like(XX, 90.0)             # Terreno natural (90 Ohm.m)
    rho[ZZ < 1.5] = 120.0                    # Cubierta seca (120 Ohm.m)
    rho[ZZ >= 28.0] = 300.0                  # Roca basal (> 28 m, 300 Ohm.m)
    # Residuos: x 55..165 m, z 1.5..14 m (30 Ohm.m)
    m_res = (XX >= 55.0) & (XX <= 165.0) & (ZZ >= 1.5) & (ZZ <= 14.0)
    rho[m_res] = 30.0
    # Lixiviado debajo y al este: x 115..205 m, z 14..24 m (6 Ohm.m)
    m_lix = (XX >= 115.0) & (XX <= 205.0) & (ZZ >= 14.0) & (ZZ <= 24.0)
    rho[m_lix] = 6.0
    # Bolsa de lodos salinos (20 x 4 m): x 85..105 m, z 3..7 m (8 Ohm.m)
    m_lod = (XX >= 85.0) & (XX <= 105.0) & (ZZ >= 3.0) & (ZZ <= 7.0)
    rho[m_lod] = 8.0
    return rho


def build_smoothness_matrix(nx_c, nz_c, dx_c, dz_c):
    """Operador Laplaciano / primeras diferencias ponderado por escala de celda."""
    rows, cols, vals = [], [], []
    r_idx = 0
    # Horizontal
    for ix in range(nx_c - 1):
        for iz in range(nz_c):
            c1 = ix * nz_c + iz
            c2 = (ix + 1) * nz_c + iz
            w = 1.0
            rows.extend([r_idx, r_idx]); cols.extend([c1, c2]); vals.extend([-w, w])
            r_idx += 1
    # Vertical (suavidad vertical ligeramente menor para no aplastar capas)
    for ix in range(nx_c):
        for iz in range(nz_c - 1):
            c1 = ix * nz_c + iz
            c2 = ix * nz_c + (iz + 1)
            w = 0.85
            rows.extend([r_idx, r_idx]); cols.extend([c1, c2]); vals.extend([-w, w])
            r_idx += 1
    return sp.csc_matrix((vals, (rows, cols)), shape=(r_idx, nx_c * nz_c))


def main():
    print("=== Paso 6: Simulación sintética ERT 2.5D (modelado directo + inversión independiente) ===")
    quads = generate_ws_schedule(n_elec=48, dx=5.0)
    print(f"Mediciones Wenner-Schlumberger generadas: N = {len(quads)}")

    # Malla directa fina (dx=2.5 m en el núcleo [0..235], paddings amplios hasta +-380 m)
    pad_x = [5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0]
    xs_f = build_mesh_1d(0.0, 235.0, 2.5, pad_x)
    zs_f = np.concatenate([
        np.arange(0.0, 16.0, 1.0),
        np.arange(16.0, 36.0, 2.0),
        [36.0, 40.0, 46.0, 55.0, 70.0, 95.0, 135.0, 200.0, 300.0, 450.0]
    ])
    elec_x = np.arange(0.0, 235.1, 5.0)
    elec_ix_f = np.array([int(np.argmin(np.abs(xs_f - ex))) for ex in elec_x])
    elec_nodes_f = elec_ix_f * len(zs_f)

    k_vals = np.geomspace(0.0015, 0.45, 10)
    k_weights_f = calibrate_k_weights(xs_f, zs_f, elec_nodes_f, k_vals)
    # Normalización geométrica por malla (elimina error de singularidad nodal en ambos mallados)
    rho_hom_f = forward_and_jacobian(
        xs_f, zs_f, np.ones((len(xs_f) - 1, len(zs_f) - 1)),
        elec_nodes_f, k_vals, k_weights_f, quads, need_jac=False
    )
    k_g_arr = np.array([q[4] for q in quads])
    k_g_f = k_g_arr / rho_hom_f

    xc_f = 0.5 * (xs_f[:-1] + xs_f[1:])
    zc_f = 0.5 * (zs_f[:-1] + zs_f[1:])
    rho_true_f = build_true_model(xc_f, zc_f)

    rho_a_clean = forward_and_jacobian(
        xs_f, zs_f, 1.0 / rho_true_f, elec_nodes_f, k_vals, k_weights_f, quads,
        need_jac=False, k_g_override=k_g_f
    )
    rng = np.random.default_rng(2026)
    noise = rng.normal(0.0, 0.03, size=len(rho_a_clean))
    rho_a_obs = np.maximum(0.5, rho_a_clean * (1.0 + noise))

    # Malla de inversión INDEPENDIENTE (dx=5.0 m en núcleo, profundidades distintas)
    xs_i = build_mesh_1d(0.0, 235.0, 5.0, [10.0, 20.0, 40.0, 80.0, 160.0, 320.0])
    zs_i = np.array([0.0, 1.2, 2.6, 4.2, 6.0, 8.0, 10.3, 13.0, 16.0, 19.5, 23.5, 28.0, 33.5, 40.0, 48.0, 60.0, 80.0, 115.0, 175.0, 260.0, 400.0])
    elec_ix_i = np.array([int(np.argmin(np.abs(xs_i - ex))) for ex in elec_x])
    elec_nodes_i = elec_ix_i * len(zs_i)
    k_weights_i = calibrate_k_weights(xs_i, zs_i, elec_nodes_i, k_vals)
    rho_hom_i = forward_and_jacobian(
        xs_i, zs_i, np.ones((len(xs_i) - 1, len(zs_i) - 1)),
        elec_nodes_i, k_vals, k_weights_i, quads, need_jac=False
    )
    k_g_i = k_g_arr / rho_hom_i

    nx_ci, nz_ci = len(xs_i) - 1, len(zs_i) - 1
    xc_i = 0.5 * (xs_i[:-1] + xs_i[1:])
    zc_i = 0.5 * (zs_i[:-1] + zs_i[1:])

    L_reg = build_smoothness_matrix(nx_ci, nz_ci, np.diff(xs_i), np.diff(zs_i))
    LtL = (L_reg.T @ L_reg).toarray()
    I_ref = np.eye(nx_ci * nz_ci)

    # Inversión en espacio m = ln(sigma) (y = ln(rho_a))
    y_obs = np.log(rho_a_obs)
    rho_0 = float(np.median(rho_a_obs))
    m_ref = np.full(nx_ci * nz_ci, np.log(1.0 / rho_0), dtype=np.float64)
    m = m_ref.copy()

    # Ponderación de datos: uniforme en espacio logarítmico (equivale a error relativo constante 3%)
    rms_hist = []
    lam = 1.5
    for it in range(14):
        sig_cur = np.exp(m).reshape(nx_ci, nz_ci)
        rho_pred, J_sig = forward_and_jacobian(
            xs_i, zs_i, sig_cur, elec_nodes_i, k_vals, k_weights_i, quads,
            need_jac=True, k_g_override=k_g_i
        )
        # d(ln rho_a)/d(ln sigma) = J_sig
        r = y_obs - np.log(rho_pred)
        rms_log = float(np.sqrt(np.mean(r ** 2)) * 100.0)
        rms_hist.append(rms_log)
        print(f"  Iter {it:2d}: lambda={lam:5.3f} -> RMS={rms_log:.2f}%")
        if rms_log <= 3.05 and it >= 3:
            break

        H = J_sig.T @ J_sig + lam * (LtL + 0.005 * I_ref)
        g = J_sig.T @ r - lam * (LtL @ m + 0.005 * (m - m_ref))
        dm = np.linalg.solve(H, g)
        # Búsqueda de paso simple para evitar sobrepasos
        step = 1.0
        for _ in range(5):
            m_try = np.clip(m + step * dm, np.log(1.0 / 2000.0), np.log(1.0 / 0.5))
            sig_try = np.exp(m_try).reshape(nx_ci, nz_ci)
            rp_try = forward_and_jacobian(
                xs_i, zs_i, sig_try, elec_nodes_i, k_vals, k_weights_i, quads,
                need_jac=False, k_g_override=k_g_i
            )
            rms_try = float(np.sqrt(np.mean((y_obs - np.log(rp_try)) ** 2)) * 100.0)
            if rms_try < rms_log or step < 0.1:
                m = m_try
                break
            step *= 0.5
        lam = max(0.03, lam * 0.45)

    rho_inv = (1.0 / np.exp(m)).reshape(nx_ci, nz_ci)
    final_rms = round(rms_hist[-1], 1)

    # Calcular medianas recuperadas en las zonas del modelo (restringido al dominio [0..235])
    XXi, ZZi = np.meshgrid(xc_i, zc_i, indexing="ij")
    zones = {
        "Residuos (1.5–14 m)": (30, (XXi >= 55) & (XXi <= 165) & (ZZi >= 1.5) & (ZZi <= 14)),
        "Lixiviado (14–24 m)": (6, (XXi >= 115) & (XXi <= 205) & (ZZi >= 14) & (ZZi <= 24)),
        "Bolsa de lodos (3–7 m)": (8, (XXi >= 85) & (XXi <= 105) & (ZZi >= 3) & (ZZi <= 7)),
        "Terreno natural, borde": (90, ((XXi >= 10) & (XXi <= 45) & (ZZi >= 2) & (ZZi <= 16))),
        "Debajo del lixiviado (26–35 m)": (90, (XXi >= 120) & (XXi <= 195) & (ZZi >= 26) & (ZZi <= 35)),
        "Roca basal (> 28 m, centro)": (300, (XXi >= 55) & (XXi <= 180) & (ZZi >= 29) & (ZZi <= 38)),
    }
    rec_table = []
    print("\n--- Recuperación de zonas (mediana del modelo invertido) ---")
    for zname, (v_true, mask) in zones.items():
        v_inv = float(np.median(rho_inv[mask]))
        rec_table.append({"zona": zname, "verdadero_ohm_m": v_true, "invertido_ohm_m": round(v_inv)})
        print(f"  {zname:32s}: verdadero={v_true:3d} Ohm.m | invertido={v_inv:6.1f} Ohm.m")

    res_out = {
        "n_electrodos": 48,
        "espaciado_m": 5.0,
        "longitud_m": 235.0,
        "arreglo": "Wenner-Schlumberger",
        "n_mediciones": len(quads),
        "ruido_pct": 3.0,
        "rms_final_pct": final_rms,
        "tabla_recuperacion": rec_table,
    }
    with open(os.path.join(SIG_DIR, "simulacion_ert_resultados.json"), "w", encoding="utf-8") as f:
        json.dump(res_out, f, indent=2, ensure_ascii=False)

    # Graficar figura a escala IEEE 1 columna (3.50 x 4.95 in, 300 DPI)
    plt.rcParams.update({
        "font.family": "Liberation Sans",
        "axes.edgecolor": "black",
        "axes.linewidth": 0.8,
        "figure.facecolor": "white",
    })
    fig = plt.figure(figsize=(3.50, 4.95), dpi=300)
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 1, 1.05], hspace=0.28, top=0.95, bottom=0.19, left=0.15, right=0.96)
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[2, 0]),
    ]
    norm = LogNorm(vmin=4.0, vmax=350.0)
    cmap = "turbo"

    # (a) Modelo verdadero
    ax = axes[0]
    m_x = (xs_f >= -2) & (xs_f <= 237)
    m_z = zs_f <= 40
    x_sub = xs_f[m_x]; z_sub = zs_f[m_z]
    ix0 = int(np.where(m_x)[0][0]); ix1 = int(np.where(m_x)[0][-1])
    iz1 = int(np.where(m_z)[0][-1])
    ax.pcolormesh(x_sub, -z_sub, rho_true_f[ix0:ix1, :iz1].T, cmap=cmap, norm=norm, shading="flat")
    ax.text(132, -8.5, "residuos\n(30)", fontsize=5.8, fontweight="bold", ha="center", va="center", color="#111111")
    ax.text(160, -19.0, "lixiviado\n(6)", fontsize=5.8, fontweight="bold", ha="center", va="center", color="white")
    ax.text(95, -5.0, "lodos", fontsize=5.0, fontweight="bold", ha="center", va="center", color="white")
    ax.set_xlim(0, 235); ax.set_ylim(-35, 0)
    ax.set_ylabel("Prof. (m)", fontsize=6.8)
    ax.set_title("(a) Modelo verdadero (sintético)", fontsize=7.2, fontweight="bold", pad=3)
    ax.tick_params(labelsize=6.2, labelbottom=False)

    # (b) Seudosección aparente simulada (+3 % ruido)
    ax = axes[1]
    px = np.array([q[5] for q in quads])
    pz = np.array([q[6] for q in quads])
    ax.scatter(px, pz, c=rho_a_obs, cmap=cmap, norm=norm, s=5.5, marker="s", edgecolors="none")
    ax.set_xlim(0, 235); ax.set_ylim(-42, 0)
    ax.set_ylabel("Seudoprof. (m)", fontsize=6.8)
    ax.set_title(f"(b) Seudosección aparente (+3 % ruido, N={len(quads)})", fontsize=7.2, fontweight="bold", pad=3)
    ax.tick_params(labelsize=6.2, labelbottom=False)

    # (c) Modelo invertido + contornos punteados
    ax = axes[2]
    m_xi = (xs_i >= -2) & (xs_i <= 237)
    m_zi = zs_i <= 40.5
    x_si = xs_i[m_xi]; z_si = zs_i[m_zi]
    ixi0 = int(np.where(m_xi)[0][0]); ixi1 = int(np.where(m_xi)[0][-1])
    izi1 = int(np.where(m_zi)[0][-1])
    pcm = ax.pcolormesh(x_si, -z_si, rho_inv[ixi0:ixi1, :izi1].T, cmap=cmap, norm=norm, shading="flat")
    # Contornos punteados de los cuerpos verdaderos
    ax.add_patch(Rectangle((55, -14), 110, 12.5, fill=False, edgecolor="black", ls="--", lw=0.85))
    ax.add_patch(Rectangle((115, -24), 90, 10.0, fill=False, edgecolor="white", ls="--", lw=0.85))
    ax.add_patch(Rectangle((85, -7), 20, 4.0, fill=False, edgecolor="black", ls=":", lw=0.8))
    ax.set_xlim(0, 235); ax.set_ylim(-35, 0)
    ax.set_xlabel("Distancia a lo largo del perfil (m)", fontsize=6.8, fontweight="bold", labelpad=2)
    ax.set_ylabel("Prof. (m)", fontsize=6.8)
    ax.set_title(f"(c) Modelo invertido (RMS = {final_rms:.1f} %); punteado: cuerpos reales", fontsize=7.2, fontweight="bold", pad=3)
    ax.tick_params(labelsize=6.2)

    # Eje explícito y separado para colorbar en la franja inferior [0.075..0.105]
    cax = fig.add_axes([0.18, 0.080, 0.75, 0.024])
    cbar = fig.colorbar(pcm, cax=cax, orientation="horizontal")
    cbar.set_label("Resistividad aparente / invertida (Ω·m)", fontsize=6.8, fontweight="bold", labelpad=2)
    cbar.ax.tick_params(labelsize=6.0)
    cbar.set_ticks([5, 10, 20, 50, 100, 200, 350])
    cbar.set_ticklabels(["5", "10", "20", "50", "100", "200", "350"])

    png = os.path.join(OUT_DIR, "ieee_fig5_simulacion_ert.png")
    pdf = os.path.join(OUT_DIR, "ieee_fig5_simulacion_ert.pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.03)
    fig.savefig(pdf, bbox_inches="tight", facecolor="white", pad_inches=0.03)
    plt.close(fig)
    print(f"Generada figura IEEE 5: {png} y .pdf")


if __name__ == "__main__":
    main()
