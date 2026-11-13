"""Boîte qui s'ouvre : chaque bille qui s'échappe en fait naître deux nouvelles à l'intérieur.

La boîte tourne et s'ouvre en deux à intervalles réguliers. Les billes libérées remplissent
l'arène jusqu'à l'objectif annoncé dans l'accroche (« 2000 billes en 40 s ? »).
"""
import math

import numpy as np

from .core import FPS, W, Scene, background, bell, hook, hsv, note_freq, pop, text, tick

CX, CY = W / 2, 1080
TAU = 2 * math.pi


def _ball_pairs(p, r):
    """Paires de billes qui se touchent (grille de cellules, sans boucle Python sur les billes)."""
    cell = 2 * r
    ij = np.floor(p / cell).astype(np.int64)
    ij -= ij.min(axis=0)
    ny = int(ij[:, 1].max()) + 3
    key = (ij[:, 0] + 1) * ny + ij[:, 1] + 1
    order = np.argsort(key, kind="stable")
    sk = key[order]
    I, J = [], []
    for dx, dy in ((0, 0), (1, -1), (1, 0), (1, 1), (0, 1)):
        nk = key + dx * ny + dy
        lo = np.searchsorted(sk, nk, "left")
        hi = np.searchsorted(sk, nk, "right")
        cnt = hi - lo
        for k in range(int(cnt.max()) if len(cnt) else 0):
            m = cnt > k
            i = np.flatnonzero(m)
            j = order[lo[m] + k]
            keep = (j > i) if (dx, dy) == (0, 0) else np.ones(len(i), bool)
            I.append(i[keep])
            J.append(j[keep])
    if not I:
        return np.empty(0, int), np.empty(0, int)
    I, J = np.concatenate(I), np.concatenate(J)
    d = p[J] - p[I]
    close = (d * d).sum(1) < cell * cell
    return I[close], J[close]


class EscapeBox(Scene):
    title = "2000 billes en 40 s ?"
    caption = "Elle s'ouvre, elles se multiplient..."
    tags = ["#satisfying", "#physics", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.0
    max_duration = 58.0
    lengths = ("court", "moyen", "normal", "long")
    HALF = 480.0        # demi-côté de l'arène
    WALL = 14.0         # épaisseur des parois de la boîte

    def __init__(self, rng):
        super().__init__(rng)
        tgt = self.target(None)
        self.target_s = int(round(tgt - 1)) if tgt else int(rng.choice([30, 40, 45]))
        self.cap = int(rng.choice([500, 800, 1000] if self.target_s < 30 else [1000, 1500, 2000]))
        self.max_duration = self.target_s + 15
        self.title = f"{self.cap} billes en {self.target_s} s ?"
        # Rayon choisi pour que l'arène soit bien pleine (~55 %) à la fin.
        self.r = math.sqrt(0.55 * (2 * self.HALF) ** 2 / (self.cap * math.pi))
        self.bw = rng.uniform(150, 200)                      # demi-largeur de la boîte
        self.bh = self.bw * rng.choice([1.0, 1.0, 0.6, 0.45])  # parfois une boîte allongée
        self.spin = rng.choice([-1, 1]) * rng.uniform(0.35, 0.7)
        self.period = rng.uniform(2.6, 3.4)
        self.hue0 = rng.random()
        self.p = np.zeros((1, 2))
        a = rng.uniform(0, TAU)
        self.v = np.array([[math.cos(a), math.sin(a)]]) * 520
        self.inside = np.array([True])
        self.hue = np.array([self.hue0])
        self.flash = np.array([1.0])
        self.angle = 0.0
        self.open = 0.0
        self.end_t = None
        self.room_in = int(0.4 * 4 * self.bw * self.bh / (math.pi * self.r ** 2))

    # -- boîte : deux « U » qui s'écartent ------------------------------------------
    def _opening(self, t):
        if t < 1.2:
            return 0.0
        u = ((t - 1.2) / self.period) % 1.0
        if u < 0.35:
            return 0.0
        if u < 0.5:
            x = (u - 0.35) / 0.15
        elif u < 0.8:
            x = 1.0
        else:
            x = 1 - (u - 0.8) / 0.2
        return 0.5 - 0.5 * math.cos(math.pi * x)

    def _segments(self):
        bw, bh = self.bw, self.bh
        s = self.open * bh * 0.95
        segs = []
        for sign in (-1, 1):
            y0 = sign * (bh + s)
            ym = sign * s
            segs += [((-bw, y0), (bw, y0)), ((-bw, y0), (-bw, ym)), ((bw, y0), (bw, ym))]
        c, sn = math.cos(self.angle), math.sin(self.angle)
        a = np.array([[x * c - y * sn, x * sn + y * c] for (x, y), _ in segs])
        b = np.array([[x * c - y * sn, x * sn + y * c] for _, (x, y) in segs])
        return a, b

    # -- physique ----------------------------------------------------------------------
    def _step(self, dt, t):
        p, v, r = self.p, self.v, self.r
        p += v * dt
        # parois de l'arène
        lim = self.HALF - r
        for k in range(2):
            lo, hi = p[:, k] < -lim, p[:, k] > lim
            v[lo, k] = np.abs(v[lo, k])
            v[hi, k] = -np.abs(v[hi, k])
            np.clip(p[:, k], -lim, lim, out=p[:, k])
        # parois de la boîte
        a, b = self._segments()
        reach = r + self.WALL / 2
        hits = 0
        for A, B in zip(a, b):
            ab = B - A
            u = np.clip(((p - A) @ ab) / (ab @ ab), 0, 1)
            q = A + u[:, None] * ab
            d = p - q
            dist = np.hypot(d[:, 0], d[:, 1])
            m = dist < reach
            if m.any():
                n = d[m] / np.maximum(dist[m], 1e-6)[:, None]
                p[m] = q[m] + n * reach
                dot = np.einsum("ij,ij->i", v[m], n)
                v[m] -= 2 * np.minimum(dot, 0)[:, None] * n
                hits += int((dot < 0).sum())
        # chocs entre billes (élastiques, masses égales)
        if len(p) > 1:
            I, J = _ball_pairs(p, r)
            if len(I):
                d = p[J] - p[I]
                dist = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
                n = d / dist[:, None]
                over = (2 * r - dist) * 0.5
                np.add.at(p, I, -n * over[:, None])
                np.add.at(p, J, n * over[:, None])
                rel = np.einsum("ij,ij->i", v[J] - v[I], n)
                imp = np.minimum(rel, 0)[:, None] * n
                np.add.at(v, I, imp)
                np.add.at(v, J, -imp)
        # vitesse vivante mais pas folle
        sp = np.maximum(np.hypot(v[:, 0], v[:, 1]), 1e-6)
        v *= (np.clip(sp, 260, 760) / sp)[:, None]
        return hits

    def _want(self, t):
        """Nombre de billes visé à l'instant t : démarrage doux puis accélération."""
        a = 3.5
        x = min(t, self.target_s) / self.target_s
        return 1 + (self.cap - 1) * (math.exp(a * x) - 1) / (math.exp(a) - 1)

    def _escapes(self, t):
        """Billes sorties de la boîte : chacune en fait naître au moins une au centre."""
        c, s = math.cos(-self.angle), math.sin(-self.angle)
        qx = self.p[:, 0] * c - self.p[:, 1] * s
        qy = self.p[:, 0] * s + self.p[:, 1] * c
        out = self.inside & ((np.abs(qx) > self.bw + self.r) | (np.abs(qy) > self.bh + self.r))
        k = int(out.sum())
        if not k:
            return 0
        self.inside[out] = False
        n = len(self.p)
        births = max(k, int(round(self._want(t) - n)))
        # pas plus que ce que la boîte peut contenir, sinon les billes traversent les parois
        births = min(births, self.cap - n, max(0, self.room_in - int(self.inside.sum())))
        if births > 0:
            ang = self.rng.uniform(0, TAU, births)
            rad = np.sqrt(self.rng.uniform(0, 1, births)) * 0.8
            ca, sa = math.cos(self.angle), math.sin(self.angle)
            lx, ly = rad * np.cos(ang) * self.bw, rad * np.sin(ang) * self.bh
            pos = np.stack([lx * ca - ly * sa, lx * sa + ly * ca], 1)
            va = self.rng.uniform(0, TAU, births)
            vel = np.stack([np.cos(va), np.sin(va)], 1) * 520
            wave = max(0, int((t - 1.2) / self.period))  # une couleur par ouverture
            self.p = np.vstack([self.p, pos])
            self.v = np.vstack([self.v, vel])
            self.inside = np.concatenate([self.inside, np.ones(births, bool)])
            self.hue = np.concatenate([self.hue, np.full(births, self.hue0 + 0.17 * wave)])
            self.flash = np.concatenate([self.flash, np.ones(births)])
        if len(self.p) >= self.cap:
            self.done = True
            self.end_t = t
        return k

    # -- rendu -------------------------------------------------------------------------
    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        was_done = self.done
        self.open = self._opening(t)
        hits = esc = 0
        for _ in range(2):
            self.angle += self.spin * dt
            hits += self._step(dt, t)
            esc += self._escapes(t)
        n = len(self.p)
        if esc:
            step = 4 + int(self.rng.integers(0, 8))
            self.audio.add(t, pop(note_freq(step)), gain=0.45 / (1 + n / 400))
        if hits and frame % 2 == 0 and n < 300:
            self.audio.add(t, tick(self.rng, bright=0.4), gain=0.12)
        if self.done and not was_done:
            for i, st in enumerate((0, 2, 4, 7, 9)):
                self.audio.add(t + i * 0.04, bell(note_freq(st), dur=3.0, decay=1.2), gain=0.5)

        background(ctx, top=(0, 0, 0), bottom=(0, 0, 0))
        # arène
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.set_line_width(3)
        ctx.rectangle(CX - self.HALF, CY - self.HALF, 2 * self.HALF, 2 * self.HALF)
        ctx.stroke()
        # billes (les nouvelles brillent un instant)
        self.flash *= 0.94
        r = self.r
        for (x, y), h, f in zip(self.p, self.hue, self.flash):
            ctx.set_source_rgb(*hsv(h, 0.85 - 0.6 * f, 1.0))
            ctx.arc(CX + x, CY + y, r, 0, TAU)
            ctx.fill()
        # boîte : traits blancs avec un dégradé vers les extrémités
        a, b = self._segments()
        ctx.set_line_cap(1)  # ROUND
        ctx.set_line_width(self.WALL)
        ctx.set_source_rgb(0.95, 0.95, 1.0)
        for A, B in zip(a, b):
            ctx.move_to(CX + A[0], CY + A[1])
            ctx.line_to(CX + B[0], CY + B[1])
        ctx.stroke()

        hook(ctx, self.title, None, t)
        shown = min(n, self.cap)
        text(ctx, f"{shown}", W / 2, 1720, 96, (1, 1, 1))
        text(ctx, f"{(self.end_t or t):0.1f} s", W / 2, 1810, 48, (0.7, 0.7, 0.75), outline=False)
        if self.done:
            text(ctx, "PLEIN !", W / 2, 470, 80, (0.4, 1, 0.5))
