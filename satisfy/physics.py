"""Petits outils de physique 2D vectorisés (numpy), partagés par les scènes à billes."""
import numpy as np

from .escape_box import _ball_pairs


def collide_balls(p, v, r, e=1.0):
    """Chocs entre billes (rayons éventuellement différents, masse ∝ surface)."""
    if len(p) < 2:
        return 0
    rr = np.full(len(p), float(r)) if np.ndim(r) == 0 else np.asarray(r, float)
    I, J = _ball_pairs(p, float(rr.max()))
    if not len(I):
        return 0
    d = p[J] - p[I]
    dist = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
    lim = rr[I] + rr[J]
    m = dist < lim
    if not m.any():
        return 0
    I, J, d, dist, lim = I[m], J[m], d[m], dist[m], lim[m]
    n = d / dist[:, None]
    mi, mj = rr[I] ** 2, rr[J] ** 2
    over = lim - dist
    np.add.at(p, I, -n * (over * mj / (mi + mj))[:, None])
    np.add.at(p, J, n * (over * mi / (mi + mj))[:, None])
    rel = np.einsum("ij,ij->i", v[J] - v[I], n)
    j = np.minimum(rel, 0) * (1 + e) / (1 / mi + 1 / mj)
    np.add.at(v, I, n * (j / mi)[:, None])
    np.add.at(v, J, -n * (j / mj)[:, None])
    return len(I)


def wall_circle(p, v, R, r, e=1.0):
    """Paroi circulaire de rayon R centrée en 0. Renvoie le masque des billes qui l'ont touchée."""
    d = np.maximum(np.hypot(p[:, 0], p[:, 1]), 1e-6)
    m = d > R - r
    if m.any():
        rm = r[m] if np.ndim(r) else r
        n = p[m] / d[m, None]
        p[m] = n * (R - rm)[:, None] if np.ndim(r) else n * (R - rm)
        dot = np.einsum("ij,ij->i", v[m], n)
        v[m] -= ((1 + e) * np.maximum(dot, 0))[:, None] * n
    return m


def collide_segment(p, v, r, A, B, half, pivot=(0.0, 0.0), omega=0.0, e=1.0):
    """Segment épais [A, B] (demi-épaisseur `half`) tournant à `omega` autour de `pivot`.

    Renvoie (masque des billes touchées, vitesse relative d'impact).
    """
    A, B = np.asarray(A, float), np.asarray(B, float)
    ab = B - A
    u = np.clip(((p - A) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    q = A + u[:, None] * ab
    d = p - q
    dist = np.hypot(d[:, 0], d[:, 1])
    reach = (r if np.ndim(r) == 0 else np.asarray(r)) + half
    m = dist < reach
    if not m.any():
        return m, np.zeros(0)
    n = d[m] / np.maximum(dist[m], 1e-6)[:, None]
    rm = reach if np.ndim(reach) == 0 else reach[m]
    p[m] = q[m] + n * (rm if np.ndim(rm) == 0 else rm[:, None])
    qq = q[m] - np.asarray(pivot, float)
    vs = omega * np.stack([-qq[:, 1], qq[:, 0]], 1)
    rel = np.einsum("ij,ij->i", v[m] - vs, n)
    v[m] -= ((1 + e) * np.minimum(rel, 0))[:, None] * n
    return m, -np.minimum(rel, 0)
