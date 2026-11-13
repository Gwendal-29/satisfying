"""Scènes physiques : anneaux à briser, katana, aiguilles d'horloge, engrenage à arcs, plaque 3D."""
import math

import cairo
import numpy as np

from .core import (FPS, W, Scene, background, bell, hook, hsv, marimba, note_freq, pop,
                   shatter, text, tick, whoosh)
from .physics import collide_balls, collide_segment, wall_circle

CX, CY = W / 2, 1000
TAU = 2 * math.pi


def _want(t, target, cap, a=3.5):
    """Effectif visé : démarrage doux puis accélération, `cap` atteint à `target` secondes."""
    x = min(t, target) / target
    return 1 + (cap - 1) * (math.exp(a * x) - 1) / (math.exp(a) - 1)


def _chord(audio, t, base=0):
    for i, st in enumerate((0, 2, 4, 7, 9)):
        audio.add(t + i * 0.04, bell(note_freq(base + st), dur=3.0, decay=1.2), gain=0.5)


def _shing(freq):
    """Bruit de lame : cloche aiguë très courte."""
    return bell(freq, dur=0.5, decay=0.12)


# ------------------------------------------------------------------ anneaux à briser

class RingCountdown(Scene):
    caption = "Elle va sortir de tous les anneaux ?"
    tags = ["#satisfying", "#oddlysatisfying", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.5
    max_duration = 58.0
    lengths = ("court", "moyen", "normal", "long")

    def __init__(self, rng):
        super().__init__(rng)
        tgt = self.target(None)
        if tgt:
            self.T = float(tgt - 4)
            self.N = int(np.clip(round(self.T * 1.1 / 5) * 5, 20, 60))
            self.max_duration = self.T + 18
        else:
            self.N = int(rng.choice([30, 40, 50]))
            self.T = float(rng.choice([35, 40, 45]))
        self.r0, rmax = 70.0, 960.0
        self.sp = (rmax - self.r0) / self.N
        self.lw = self.sp * 0.42
        self.k = 0
        self.br = 9.0
        self.p = np.zeros(2)
        a = rng.uniform(0, TAU)
        self.dir = np.array([math.cos(a), math.sin(a)])
        self.phi = rng.uniform(0, TAU)
        self.omega = rng.choice([-1, 1]) * rng.uniform(0.8, 1.3)
        self.g = 0.3
        self.hue0 = rng.random()
        self.trail = []
        self.pp = np.zeros((0, 2))
        self.pv = np.zeros((0, 2))
        self.pl = np.zeros(0)
        self.ph = np.zeros(0)
        self.title = f"{self.N} anneaux... elle sort ?"

    def _inner(self, i):
        return self.r0 + i * self.sp - self.lw / 2

    def _break(self, t):
        i = self.k
        r = self.r0 + i * self.sp
        m = 90
        ang = self.phi + self.g + self.rng.uniform(0, TAU - 2 * self.g, m)
        dirs = np.stack([np.cos(ang), np.sin(ang)], 1)
        self.pp = np.vstack([self.pp, dirs * r])
        sp = self.rng.uniform(80, 420, m)[:, None]
        self.pv = np.vstack([self.pv, dirs * sp + self.rng.normal(0, 60, (m, 2))])
        self.pl = np.concatenate([self.pl, self.rng.uniform(0.6, 1.2, m)])
        self.ph = np.concatenate([self.ph, np.full(m, self._hue(i, t))])
        self.audio.add(t, shatter(self.rng, 0.4), gain=0.18)
        self.audio.add(t, bell(note_freq(i % 15), dur=1.2, decay=0.4), gain=0.35)
        self.k += 1
        if self.k >= self.N:
            self.done = True
            _chord(self.audio, t, 2)

    def _hue(self, i, t):
        return self.hue0 + 0.55 * i / self.N + 0.02 * t

    def _step(self, dt, t):
        if self.done:
            self.p += self.dir * 900 * dt
            return
        R = self._inner(self.k)
        speed = max(700.0, 3.4 * R)
        self.p += self.dir * speed * dt
        d = math.hypot(*self.p)
        if d > R - self.br:
            ang = math.atan2(self.p[1], self.p[0])
            diff = (ang - self.phi + math.pi) % TAU - math.pi
            n = self.p / d
            if abs(diff) < self.g:
                # l'anneau touché dans la brèche se brise et la balle rebondit :
                # un seul anneau à la fois, sinon elle traverserait toutes les brèches alignées
                self._break(t)
            v = self.dir - 2 * (self.dir @ n) * n
            j = self.rng.normal(0, 0.15)
            c, s = math.cos(j), math.sin(j)
            v = np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])
            if v @ n > -0.2:
                v = v - 1.2 * (v @ n + 0.2) * n
            self.dir = v / np.linalg.norm(v)
            self.p = n * (R - self.br)
            if self.k and abs(diff) < self.g:
                return
            self.audio.add(t, marimba(note_freq(int(self.rng.integers(5, 12))), 0.4), gain=0.12)

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        lag = self.N * min(t, self.T) / self.T - self.k + 1.5 * max(0.0, t - self.T)
        g_want = float(np.clip(0.3 * 1.5 ** lag, 0.15, 2.2))
        self.g += (g_want - self.g) * 0.05
        for _ in range(2):
            self.phi += self.omega * dt
            self._step(dt, t)
        self.trail.append(self.p.copy())
        self.trail = self.trail[-14:]
        # particules
        if len(self.pl):
            self.pp += self.pv / FPS
            self.pv *= 0.97
            self.pl -= 1 / FPS
            keep = self.pl > 0
            self.pp, self.pv, self.pl, self.ph = self.pp[keep], self.pv[keep], self.pl[keep], self.ph[keep]

        background(ctx, top=(0, 0, 0), bottom=(0, 0, 0))
        ctx.set_line_width(self.lw)
        for i in range(self.k, self.N):
            r = self.r0 + i * self.sp
            ctx.set_source_rgb(*hsv(self._hue(i, t), 0.85, 1.0))
            ctx.new_sub_path()
            ctx.arc(CX, CY, r, self.phi + self.g, self.phi - self.g + TAU)
            ctx.stroke()
        for (x, y), l, h in zip(self.pp, self.pl, self.ph):
            ctx.set_source_rgba(*hsv(h, 0.6, 1.0), min(1.0, l))
            ctx.arc(CX + x, CY + y, 3, 0, TAU)
            ctx.fill()
        for j, (x, y) in enumerate(self.trail):
            a = (j + 1) / len(self.trail)
            ctx.set_source_rgba(1, 1, 1, 0.35 * a)
            ctx.arc(CX + x, CY + y, self.br * a, 0, TAU)
            ctx.fill()
        ctx.set_source_rgb(1, 1, 1)
        ctx.arc(CX + self.p[0], CY + self.p[1], self.br, 0, TAU)
        ctx.fill()

        left = self.N - self.k
        R = self._inner(min(self.k, self.N - 1))
        size = float(np.clip(R * 0.8, 44, 230))
        text(ctx, f"{left}", CX, CY + size * 0.36, size, (1, 1, 1), 0.85)
        hook(ctx, self.title, None, t)
        if self.done:
            text(ctx, "LIBRE !", W / 2, 1700, 96, (0.4, 1, 0.5))


# ------------------------------------------------------------------ katana

class Katana(Scene):
    title = "KATANA"
    lengths = ("court", "moyen", "normal")
    caption = "1 balle, combien de morceaux à la fin ?"
    tags = ["#satisfying", "#katana", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.5
    max_duration = 55.0
    R, G = 470.0, 1300.0

    def __init__(self, rng):
        super().__init__(rng)
        tgt = self.target(None)
        self.gens = (6 if tgt < 30 else 7) if tgt else int(rng.choice([6, 7]))
        r0 = float(rng.choice([75, 85]))
        self.p = np.array([[0.0, -180.0]])
        a = rng.uniform(0, TAU)
        self.v = np.array([[math.cos(a), math.sin(a)]]) * 500
        self.r = np.array([r0])
        self.gen = np.array([0])
        self.cool = np.array([0.0])
        self.hue0 = rng.random()
        self.hue = np.array([self.hue0])
        self.theta = rng.uniform(0, TAU)
        self.omega = rng.choice([-1, 1]) * 1.5
        self.L = self.R * 0.94
        self.ghost = []
        self.slashes = []  # (x, y, angle, taille, âge)
        self.cuts = 0

    def _slice(self, idx, t):
        n = np.array([-math.sin(self.theta), math.cos(self.theta)])
        new_p, new_v, new_r, new_g, new_h = [], [], [], [], []
        for i in idx:
            r2 = self.r[i] / math.sqrt(2)
            g = self.gen[i] + 1
            h = self.hue0 + 0.13 * g
            for s in (-1, 1):
                new_p.append(self.p[i] + s * n * r2 * 0.75)
                new_v.append(self.v[i] * 0.6 + s * n * 380)
                new_r.append(r2)
                new_g.append(g)
                new_h.append(h)
            self.slashes.append((*self.p[i], self.theta, self.r[i] * 2.4, 0.0))
        keep = np.ones(len(self.p), bool)
        keep[idx] = False
        self.p = np.vstack([self.p[keep], new_p])
        self.v = np.vstack([self.v[keep], new_v])
        self.r = np.concatenate([self.r[keep], new_r])
        self.gen = np.concatenate([self.gen[keep], new_g])
        self.hue = np.concatenate([self.hue[keep], new_h])
        self.cool = np.concatenate([self.cool[keep], np.full(len(new_r), 0.35)])
        self.cuts += len(idx)
        self.omega = math.copysign(min(abs(self.omega) * 1.004, 3.2), self.omega)
        for k, i in enumerate(idx[:3]):
            self.audio.add(t + 0.01 * k, _shing(note_freq(8 + int(new_g[2 * k]))), gain=0.4)
        self.audio.add(t, whoosh(self.rng, 0.25), gain=0.12)

    def _step(self, dt, t):
        self.v[:, 1] += self.G * dt
        self.p += self.v * dt
        self.cool -= dt
        hit = wall_circle(self.p, self.v, self.R, self.r, e=0.9)
        collide_balls(self.p, self.v, self.r, e=0.9)
        A = (0.0, 0.0)
        B = (self.L * math.cos(self.theta), self.L * math.sin(self.theta))
        # 1) les billes qui peuvent encore être coupées
        ab = np.array(B)
        u = np.clip((self.p @ ab) / (ab @ ab), 0, 1)
        dist = np.hypot(*(self.p - u[:, None] * ab).T)
        can = (dist < self.r + 5.0) & (self.gen < self.gens) & (self.cool <= 0)
        idx = np.flatnonzero(can)
        if len(idx):
            self._slice(idx, t)
        # 2) les autres rebondissent sur la lame
        collide_segment(self.p, self.v, self.r, A, B, 4.0, omega=self.omega, e=0.6)
        sp = np.maximum(np.hypot(*self.v.T), 1e-6)
        self.v *= (np.minimum(sp, 1600) / sp)[:, None]
        self.theta += self.omega * dt
        return int(hit.sum())

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        hits = 0
        for _ in range(2):
            hits += self._step(dt, t)
        if hits and frame % 3 == 0 and len(self.p) < 60:
            self.audio.add(t, tick(self.rng, bright=0.3), gain=0.1)
        if not self.done and (self.gen >= self.gens).all():
            self.done = True
            _chord(self.audio, t, 0)
        self.ghost.append(self.theta)
        self.ghost = self.ghost[-7:]

        background(ctx, top=(0.07, 0.03, 0.04), bottom=(0.02, 0.01, 0.02))
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(4)
        ctx.arc(CX, CY, self.R + 2, 0, TAU)
        ctx.stroke()
        for (x, y), r, h in zip(self.p, self.r, self.hue):
            ctx.set_source_rgb(*hsv(h, 0.8, 1.0))
            ctx.arc(CX + x, CY + y, r, 0, TAU)
            ctx.fill()
        # traces de coupe
        alive = []
        for x, y, a, s, age in self.slashes:
            age += 1 / FPS
            if age < 0.3:
                alive.append((x, y, a, s, age))
                ctx.set_source_rgba(1, 1, 1, 1 - age / 0.3)
                ctx.set_line_width(5)
                dx, dy = math.cos(a) * s / 2, math.sin(a) * s / 2
                ctx.move_to(CX + x - dx, CY + y - dy)
                ctx.line_to(CX + x + dx, CY + y + dy)
                ctx.stroke()
        self.slashes = alive
        # lame : traînées puis lame nette, poignée rouge au centre
        ctx.set_line_cap(1)
        for j, a in enumerate(self.ghost[:-1]):
            ctx.set_source_rgba(1, 1, 1, 0.06 * (j + 1))
            ctx.set_line_width(4)
            ctx.move_to(CX + 60 * math.cos(a), CY + 60 * math.sin(a))
            ctx.line_to(CX + self.L * math.cos(a), CY + self.L * math.sin(a))
            ctx.stroke()
        c, s = math.cos(self.theta), math.sin(self.theta)
        ctx.set_source_rgb(0.96, 0.96, 1.0)
        ctx.set_line_width(8)
        ctx.move_to(CX + 60 * c, CY + 60 * s)
        ctx.line_to(CX + self.L * c, CY + self.L * s)
        ctx.stroke()
        ctx.set_source_rgb(0.85, 0.1, 0.12)
        ctx.set_line_width(10)
        ctx.set_dash([7, 4])
        ctx.move_to(CX - 10 * c, CY - 10 * s)
        ctx.line_to(CX + 58 * c, CY + 58 * s)
        ctx.stroke()
        ctx.set_dash([])

        hook(ctx, self.title, "Combien de morceaux à la fin ?", t)
        text(ctx, f"{len(self.p)}", W / 2, 1640, 96, (1, 1, 1))
        if self.done:
            text(ctx, "TOUT COUPÉ !", W / 2, 1740, 64, (1, 0.4, 0.4))


# ------------------------------------------------------------------ aiguilles d'horloge

class ClockSweep(Scene):
    title = "Tu dis combien à la fin ?"
    lengths = ("court", "moyen", "normal", "long")
    caption = "Les aiguilles mélangent tout... ton pronostic ?"
    tags = ["#satisfying", "#physics", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.5
    max_duration = 55.0
    R, G = 470.0, 900.0

    def __init__(self, rng):
        super().__init__(rng)
        tgt = self.target(None)
        self.target = float(tgt - 2) if tgt else float(rng.choice([30, 35, 40]))
        self.cap = int(rng.choice([500, 800] if self.target < 28 else [800, 1200, 1600]))
        self.max_duration = self.target + 15
        self.r = self.R * math.sqrt(0.5 / self.cap)
        sign = rng.choice([-1, 1])
        w1 = sign * rng.uniform(0.9, 1.4)
        w2 = w1 * rng.choice([-1, 1]) * rng.uniform(0.45, 0.75)
        self.hands = [[rng.uniform(0, TAU), w1, self.R * 0.97], [rng.uniform(0, TAU), w2, self.R * 0.78]]
        self.p = np.array([[0.0, -200.0]])
        a = rng.uniform(0, TAU)
        self.v = np.array([[math.cos(a), math.sin(a)]]) * 600
        self.hue0 = rng.random()
        self.hue = np.array([self.hue0])
        self.flash = np.array([1.0])

    def _hand_segments(self, theta, L):
        c, s = math.cos(theta), math.sin(theta)
        return [((0, 0), (0.55 * L * c, 0.55 * L * s), 4.0),
                ((0.55 * L * c, 0.55 * L * s), (L * c, L * s), 14.0)]

    def _spawn(self, idx, t):
        room = int(_want(t, self.target, self.cap) - len(self.p))
        idx = idx[:max(0, min(room, self.cap - len(self.p)))]
        if not len(idx):
            return 0
        k = len(idx)
        a = self.rng.uniform(0, TAU, k)
        off = np.stack([np.cos(a), np.sin(a)], 1)
        wave = int(t / 5.0)
        self.p = np.vstack([self.p, self.p[idx] + off * self.r * 1.5])
        self.v = np.vstack([self.v, off * 500])
        self.hue = np.concatenate([self.hue, np.full(k, self.hue0 + 0.17 * wave)])
        self.flash = np.concatenate([self.flash, np.ones(k)])
        if len(self.p) >= self.cap:
            self.done = True
            _chord(self.audio, t, 4)
        return k

    def _step(self, dt, t):
        self.v[:, 1] += self.G * dt
        self.p += self.v * dt
        touched = wall_circle(self.p, self.v, self.R, self.r, e=0.9)
        collide_balls(self.p, self.v, self.r, e=0.8)
        for h in self.hands:
            h[0] += h[1] * dt
            for A, B, half in self._hand_segments(h[0], h[2]):
                m, _ = collide_segment(self.p, self.v, self.r, A, B, half, omega=h[1], e=0.7)
                touched |= m
        sp = np.maximum(np.hypot(*self.v.T), 1e-6)
        self.v *= (np.minimum(sp, 1400) / sp)[:, None]
        wall_circle(self.p, self.v, self.R, self.r, e=0.9)
        return self._spawn(np.flatnonzero(touched), t) if not self.done else 0

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        born = sum(self._step(dt, t) for _ in range(2))
        if born:
            self.audio.add(t, pop(note_freq(int(self.rng.integers(4, 13)))), gain=0.45 / (1 + len(self.p) / 300))
        self.flash *= 0.95

        background(ctx, top=(0, 0, 0), bottom=(0, 0, 0))
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(3)
        ctx.arc(CX, CY, self.R + 1.5, 0, TAU)
        ctx.stroke()
        r = self.r
        for (x, y), h, f in zip(self.p, self.hue, self.flash):
            if f > 0.15:
                ctx.set_source_rgba(*hsv(h, 0.5, 1.0), 0.25 * f)
                ctx.arc(CX + x, CY + y, r * 2.2, 0, TAU)
                ctx.fill()
            ctx.set_source_rgb(*hsv(h, 0.8 - 0.5 * f, 1.0))
            ctx.arc(CX + x, CY + y, r, 0, TAU)
            ctx.fill()
        for theta, _, L in self.hands:
            c, s = math.cos(theta), math.sin(theta)
            ctx.set_source_rgb(0.35, 0.35, 0.38)
            ctx.set_line_width(6)
            ctx.move_to(CX, CY)
            ctx.line_to(CX + 0.6 * L * c, CY + 0.6 * L * s)
            ctx.stroke()
            # palette : dégradé blanc vers gris, comme une lame
            nx, ny = -s * 14, c * 14
            x0, y0 = CX + 0.55 * L * c, CY + 0.55 * L * s
            x1, y1 = CX + L * c, CY + L * s
            g = cairo.LinearGradient(x0 - nx, y0 - ny, x0 + nx, y0 + ny)
            g.add_color_stop_rgb(0, 0.55, 0.55, 0.6)
            g.add_color_stop_rgb(0.5, 1, 1, 1)
            g.add_color_stop_rgb(1, 0.6, 0.6, 0.65)
            ctx.set_source(g)
            ctx.move_to(x0 - nx * 0.6, y0 - ny * 0.6)
            ctx.line_to(x1 - nx, y1 - ny)
            ctx.line_to(x1 + nx, y1 + ny)
            ctx.line_to(x0 + nx * 0.6, y0 + ny * 0.6)
            ctx.close_path()
            ctx.fill()
        circle_r = 9
        ctx.set_source_rgb(0.5, 0.5, 0.55)
        ctx.arc(CX, CY, circle_r, 0, TAU)
        ctx.fill()

        hook(ctx, self.title, None, t)
        text(ctx, f"{len(self.p)}", W / 2, 1640, 96, (1, 1, 1))
        if self.done:
            text(ctx, "PLEIN !", W / 2, 1740, 64, (0.4, 1, 0.5))


# ------------------------------------------------------------------ engrenage à arcs

class GearArcs(Scene):
    caption = "Chaque coup d'arc la dédouble..."
    lengths = ("court", "moyen", "normal", "long")
    tags = ["#satisfying", "#physics", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.5
    max_duration = 55.0
    R, G = 470.0, 1000.0
    HALF = 13.0

    def __init__(self, rng):
        super().__init__(rng)
        tgt = self.target(None)
        self.target = float(tgt - 2) if tgt else float(rng.choice([30, 35, 40]))
        self.cap = int(rng.choice([64, 100] if self.target < 28 else [100, 150, 250]))
        self.max_duration = self.target + 15
        self.br = float(np.clip(self.R * math.sqrt(0.18 / self.cap), 9, 18))
        self.title = f"1 balle → {self.cap} ?"
        self.orbit = rng.uniform(40, 130)
        self.orbit_w = rng.choice([-1, 1]) * rng.uniform(0.25, 0.5)
        self.orbit_a = rng.uniform(0, TAU)
        self.rho = rng.uniform(125, 165)
        self.span = rng.uniform(3.1, 3.7)
        self.theta = rng.uniform(0, TAU)
        self.omega = rng.choice([-1, 1]) * rng.uniform(1.3, 2.0)
        self.p = np.array([[0.0, -250.0]])
        a = rng.uniform(0, TAU)
        self.v = np.array([[math.cos(a), math.sin(a)]]) * 500
        self.cool = np.array([0.0])
        self.hue0 = rng.random()
        self.level = 0
        self.flash = 0.0

    def _gear(self):
        return np.array([self.orbit * math.cos(self.orbit_a), self.orbit * math.sin(self.orbit_a)])

    def _arcs(self):
        g = self._gear()
        out = []
        for i in range(2):
            th = self.theta + i * math.pi
            c = g + self.rho * np.array([math.cos(th), math.sin(th)])
            out.append((c, th + math.pi))  # l'arc démarre au niveau de l'engrenage
        return g, out

    def _collide_arc(self, c, a0, g):
        d = self.p - c
        dist = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
        ang = np.arctan2(d[:, 1], d[:, 0])
        rel = (ang - a0) % TAU
        on = rel <= self.span
        e0 = c + self.rho * np.array([math.cos(a0), math.sin(a0)])
        e1 = c + self.rho * np.array([math.cos(a0 + self.span), math.sin(a0 + self.span)])
        radial = d / dist[:, None]
        q = np.where(on[:, None], c + radial * self.rho, 0)
        d0, d1 = self.p - e0, self.p - e1
        n0, n1 = np.hypot(*d0.T), np.hypot(*d1.T)
        q = np.where(on[:, None], q, np.where((n0 < n1)[:, None], e0, e1))
        dv = self.p - q
        dd = np.maximum(np.hypot(*dv.T), 1e-6)
        reach = self.br + self.HALF
        m = dd < reach
        if not m.any():
            return m, np.zeros(0)
        n = dv[m] / dd[m, None]
        self.p[m] = q[m] + n * reach
        qq = q[m] - g
        vs = self.omega * np.stack([-qq[:, 1], qq[:, 0]], 1)
        rel_v = np.einsum("ij,ij->i", self.v[m] - vs, n)
        self.v[m] -= (2 * np.minimum(rel_v, 0))[:, None] * n
        return m, -np.minimum(rel_v, 0)

    def _step(self, dt, t):
        self.v[:, 1] += self.G * dt
        self.p += self.v * dt
        self.cool -= dt
        wall_circle(self.p, self.v, self.R, self.br, e=1.0)
        collide_balls(self.p, self.v, self.br, e=1.0)
        self.theta += self.omega * dt
        self.orbit_a += self.orbit_w * dt
        g, arcs = self._arcs()
        hits = np.zeros(len(self.p), bool)
        for c, a0 in arcs:
            m, _ = self._collide_arc(c, a0, g)
            hits |= m
        # un peu d'énergie en plus pour que ça ne s'endorme jamais
        sp = np.maximum(np.hypot(*self.v.T), 1e-6)
        self.v *= (np.clip(sp, 350, 1500) / sp)[:, None]
        idx = np.flatnonzero(hits & (self.cool <= 0))
        room = int(_want(t, self.target, self.cap) - len(self.p))
        idx = idx[:max(0, min(room, self.cap - len(self.p)))]
        if len(idx):
            nv = self.v[idx] * np.array([-1, 1])
            self.p = np.vstack([self.p, self.p[idx] + self.rng.normal(0, 2, (len(idx), 2))])
            self.v = np.vstack([self.v, nv])
            self.cool[idx] = 0.6
            self.cool = np.concatenate([self.cool, np.full(len(idx), 0.6)])
            if len(self.p) >= self.cap:
                self.done = True
                _chord(self.audio, t, 2)
        return len(idx), int(hits.sum())

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        born = hits = 0
        for _ in range(2):
            b, h = self._step(dt, t)
            born += b
            hits += h
        n = len(self.p)
        level = int(math.log2(max(n, 1)))
        if level != self.level:
            self.level = level
            self.flash = 1.0
            self.audio.add(t, bell(note_freq(level + 3), dur=1.5, decay=0.5), gain=0.35)
        if born:
            self.audio.add(t, pop(note_freq(int(self.rng.integers(6, 14)))), gain=0.4 / (1 + n / 80))
        elif hits and n < 40:
            self.audio.add(t, tick(self.rng, bright=0.4), gain=0.12)
        self.flash *= 0.93

        background(ctx, top=(0, 0, 0), bottom=(0, 0, 0))
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(4)
        ctx.arc(CX, CY, self.R + 2, 0, TAU)
        ctx.stroke()
        col = hsv(self.hue0 + 0.15 * self.level, 0.85 - 0.6 * self.flash, 1.0)
        ctx.set_source_rgb(*col)
        for x, y in self.p:
            ctx.new_sub_path()
            ctx.arc(CX + x, CY + y, self.br, 0, TAU)
        ctx.fill()
        g, arcs = self._arcs()
        ctx.set_line_cap(1)
        for c, a0 in arcs:
            ctx.set_source_rgb(0.62, 0.62, 0.66)
            ctx.set_line_width(2 * self.HALF)
            ctx.new_sub_path()
            ctx.arc(CX + c[0], CY + c[1], self.rho, a0, a0 + self.span)
            ctx.stroke()
            ctx.set_source_rgba(1, 1, 1, 0.35)
            ctx.set_line_width(3)
            ctx.new_sub_path()
            ctx.arc(CX + c[0], CY + c[1], self.rho - 5, a0, a0 + self.span)
            ctx.stroke()
        # engrenage
        gx, gy = CX + g[0], CY + g[1]
        teeth, r1, r2 = 12, 22, 30
        ctx.set_source_rgb(0.85, 0.85, 0.9)
        for k in range(2 * teeth):
            a = self.theta * 1.5 + k * math.pi / teeth
            rr = r2 if k % 2 == 0 else r1
            for da in (-0.12, 0.12):
                x, y = gx + rr * math.cos(a + da), gy + rr * math.sin(a + da)
                if k == 0 and da < 0:
                    ctx.move_to(x, y)
                else:
                    ctx.line_to(x, y)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgb(0, 0, 0)
        ctx.arc(gx, gy, 9, 0, TAU)
        ctx.fill()

        hook(ctx, self.title, None, t)
        text(ctx, f"{n}", W / 2, 1640, 96, (1, 1, 1))
        if self.done:
            text(ctx, "OBJECTIF !", W / 2, 1740, 64, (0.4, 1, 0.5))


# ------------------------------------------------------------------ plaque 3D (boucle)

def _shapes(u, v):
    r = np.sqrt(u * u + v * v)
    return {
        "plat": np.zeros_like(u),
        "dome": 1 - r * r,
        "cone": 1 - 1.3 * r,
        "pyramide": 1 - 1.6 * np.maximum(np.abs(u), np.abs(v)),
        "selle": u * v * 1.6,
        "vague": np.sin(u * math.pi * 1.5) * 0.8,
        "ondes": np.cos(r * math.pi * 3) * 0.6,
        "creux": -(1 - r * r),
        "pente": (u + v) * 0.7,
        "bosses": np.sin(u * math.pi * 2) * np.sin(v * math.pi * 2) * 0.7,
    }


class PinArt(Scene):
    loop = True
    caption = "La plaque ne s'arrête jamais de changer de forme"
    lengths = ("court", "moyen", "normal", "long")
    tags = ["#satisfying", "#3d", "#asmr", "#oddlysatisfying", "#pourtoi"]
    N = 34

    def __init__(self, rng):
        super().__init__(rng)
        lin = np.linspace(-1, 1, self.N)
        self.u, self.v = np.meshgrid(lin, lin, indexing="ij")
        shapes = _shapes(self.u, self.v)
        others = [k for k in shapes if k != "plat"]
        self.seg = float(rng.choice([4.0, 4.5, 5.0]))
        m = 6
        if self.LENGTH:
            m = int(np.clip(round(self.LENGTH / self.seg), 3, len(others) + 1))
            self.seg = max(self.seg, (61.5 / m) if self.LENGTH >= 61 else 0, self.LENGTH * 0.8 / m)
        pick = list(rng.choice(others, size=m - 1, replace=False))
        self.seq = [shapes["plat"]] + [shapes[k] for k in pick]
        self.max_duration = self.seg * len(self.seq)
        self.hue0 = float(rng.choice([0.42, 0.5, 0.58, 0.75, 0.9, 0.08]))
        self.title = str(rng.choice(["Tu peux pas arrêter de regarder", "Attends la forme suivante...",
                                     "Cette plaque est vivante"]))
        self.A, self.B, self.HS = 330.0, 190.0, 230.0
        self.Y0 = 1000.0
        ii, jj = np.meshgrid(np.arange(self.N), np.arange(self.N), indexing="ij")
        self.order = np.argsort((ii + jj).ravel(), kind="stable")
        self.du = 1.0 / (self.N - 1)

    def _height(self, t):
        m = len(self.seq)
        x = t / self.seg
        k = int(x) % m
        f = x - int(x)
        s = float(np.clip((f - 0.35) / 0.65, 0, 1))
        s = s * s * (3 - 2 * s)
        Z = (1 - s) * self.seq[k] + s * self.seq[(k + 1) % m]
        bob = 0.06 * math.sin(TAU * t / self.seg)
        return 1.0 + bob + 0.5 * Z, k, f

    def _proj(self, u, v, z):
        return CX + (u - v) * self.A, self.Y0 + (u + v) * self.B * 0.5 - z * self.HS

    def draw(self, ctx, t, frame):
        Z, k, f = self._height(t)
        c_now = math.floor(t / self.seg - 0.35)
        if c_now != math.floor((t - 1 / FPS) / self.seg - 0.35):
            self.audio.add(t, whoosh(self.rng, 1.2), gain=0.12)
            self.audio.add(t, marimba(note_freq([0, 4, 2, 5, 7, 9][k % 6]), 1.2), gain=0.3)

        background(ctx, top=(0, 0, 0), bottom=(0, 0, 0))
        d = self.du
        corners = [(-d, -d), (d, -d), (d, d), (-d, d)]
        # reflet sous le socle
        ctx.save()
        for idx in self.order[::2]:
            i, j = divmod(idx, self.N)
            u, v, z = self.u[i, j], self.v[i, j], Z[i, j]
            ctx.set_source_rgba(*hsv(self.hue0 + 0.08 * (u + v), 0.8, 0.8), 0.07)
            for c, (a, b) in enumerate(corners):
                x, y = self._proj(u + a * 1.4, v + b * 1.4, -0.35 - z * 0.6)
                (ctx.move_to if c == 0 else ctx.line_to)(x, y)
            ctx.fill()
        ctx.restore()
        # socle sombre avec l'empreinte lumineuse là où la plaque est proche
        for c, (a, b) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
            x, y = self._proj(a * 1.04, b * 1.04, 0)
            (ctx.move_to if c == 0 else ctx.line_to)(x, y)
        ctx.close_path()
        ctx.set_source_rgb(0.13, 0.13, 0.15)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.25, 0.25, 0.28)
        ctx.set_line_width(2)
        ctx.stroke()
        step = 2
        for i in range(0, self.N, step):
            for j in range(0, self.N, step):
                close = max(0.0, 1 - (Z[i, j] - 0.4) / 0.8)
                if close < 0.05:
                    continue
                ctx.set_source_rgba(*hsv(self.hue0, 0.6, 1.0), 0.35 * close)
                for c, (a, b) in enumerate(corners):
                    x, y = self._proj(self.u[i, j] + a * step, self.v[i, j] + b * step, 0.0)
                    (ctx.move_to if c == 0 else ctx.line_to)(x, y)
                ctx.fill()
        # plaque en pixels, de l'arrière vers l'avant
        zmin, zmax = float(Z.min()), float(Z.max())
        span = max(zmax - zmin, 1e-3)
        side = 0.035
        for idx in self.order:
            i, j = divmod(idx, self.N)
            u, v, z = self.u[i, j], self.v[i, j], Z[i, j]
            hgt = (z - zmin) / span
            top = hsv(self.hue0 - 0.12 * hgt + 0.05, 0.75 - 0.35 * hgt, 0.55 + 0.45 * hgt)
            p = [self._proj(u + a, v + b, z) for a, b in corners]
            q = [self._proj(u + a, v + b, z - side) for a, b in corners]
            # faces avant (droite et gauche)
            ctx.set_source_rgb(*[c * 0.55 for c in top])
            ctx.move_to(*p[1]); ctx.line_to(*p[2]); ctx.line_to(*q[2]); ctx.line_to(*q[1]); ctx.fill()  # noqa: E702
            ctx.set_source_rgb(*[c * 0.4 for c in top])
            ctx.move_to(*p[2]); ctx.line_to(*p[3]); ctx.line_to(*q[3]); ctx.line_to(*q[2]); ctx.fill()  # noqa: E702
            ctx.set_source_rgb(*top)
            ctx.move_to(*p[0]); ctx.line_to(*p[1]); ctx.line_to(*p[2]); ctx.line_to(*p[3]); ctx.fill()  # noqa: E702

        text(ctx, self.title, W / 2, 300, 70)
