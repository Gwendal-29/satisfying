"""Fusion de patates : deux patates identiques qui se touchent deviennent une patate plus grosse.

Les patates tombent par le goulot d'une fiole ronde. À chaque nouveau niveau, une bannière
« NOUVEAU : ... » s'affiche et une voix annonce son nom, de plus en plus grave, jusqu'à la
patate suprême. Les personnages sont dessinés entièrement au code (aucune image externe).
"""
import math

import cairo
import numpy as np

from .core import FONT, FPS, W, Scene, bell, hsv, note_freq, pop, text
from .escape_box import _ball_pairs
from .physics import collide_balls
from .voice import speak

TAU = 2 * math.pi
CX, CY = W / 2, 1060
R_FLASK = 440.0
NECK = 80.0
NECK_TOP = 450.0  # haut du goulot (pixels écran), sous le titre

NAMES = ["La patatine", "La patate moustachue", "La patate à lunettes", "La patate en béret",
         "La patate pirate", "La patate viking", "La patate magicienne", "LA PATATE SUPRÊME"]
TIERS = len(NAMES)


def _radius(tier):
    return 26 * 1.36 ** tier


# ------------------------------------------------------------------ dessin des personnages

def _blob(ctx, r, seed):
    pts = 28
    a = np.linspace(0, TAU, pts, endpoint=False)
    rr = r * (1 + 0.05 * np.sin(3 * a + seed) + 0.03 * np.sin(5 * a + 2 * seed))
    xs, ys = rr * np.cos(a) * 0.9, rr * np.sin(a) * 1.0
    ctx.move_to(xs[0], ys[0])
    for i in range(pts):
        x0, y0 = xs[i], ys[i]
        x1, y1 = xs[(i + 1) % pts], ys[(i + 1) % pts]
        ctx.curve_to(x0 + (x1 - xs[i - 1]) / 6, y0 + (y1 - ys[i - 1]) / 6,
                     x1 - (xs[(i + 2) % pts] - x0) / 6, y1 - (ys[(i + 2) % pts] - y0) / 6, x1, y1)
    ctx.close_path()


def _eyes(ctx, r, look, closed=False):
    for s in (-1, 1):
        x, y = s * 0.3 * r, -0.15 * r
        if closed:
            ctx.set_source_rgb(0.15, 0.08, 0.03)
            ctx.set_line_width(r * 0.06)
            ctx.arc(x, y, r * 0.12, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()
            continue
        ctx.set_source_rgb(1, 1, 1)
        ctx.arc(x, y, r * 0.17, 0, TAU)
        ctx.fill()
        ctx.set_source_rgb(0.05, 0.03, 0.02)
        ctx.arc(x + look[0] * r * 0.06, y + look[1] * r * 0.06, r * 0.095, 0, TAU)
        ctx.fill()
        ctx.set_source_rgb(1, 1, 1)
        ctx.arc(x + look[0] * r * 0.06 - r * 0.03, y + look[1] * r * 0.06 - r * 0.03, r * 0.03, 0, TAU)
        ctx.fill()


def _smile(ctx, r, big=False):
    ctx.set_source_rgb(0.3, 0.1, 0.05)
    ctx.set_line_width(r * 0.06)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.arc(0, 0.12 * r, r * (0.3 if big else 0.22), math.pi * 0.2, math.pi * 0.8)
    ctx.stroke()
    ctx.set_source_rgba(1, 0.45, 0.45, 0.35)
    for s in (-1, 1):
        ctx.arc(s * 0.52 * r, 0.12 * r, r * 0.11, 0, TAU)
        ctx.fill()


def _mustache(ctx, r):
    ctx.set_source_rgb(0.28, 0.15, 0.07)
    for s in (-1, 1):
        ctx.save()
        ctx.translate(s * 0.17 * r, 0.12 * r)
        ctx.rotate(s * -0.25)
        ctx.scale(0.24 * r, 0.1 * r)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.fill()
        ctx.arc(s * 0.4 * r, 0.03 * r, 0.07 * r, 0, TAU)
        ctx.fill()


def _glasses(ctx, r):
    ctx.set_source_rgb(0.08, 0.08, 0.1)
    ctx.set_line_width(r * 0.05)
    for s in (-1, 1):
        ctx.arc(s * 0.3 * r, -0.15 * r, r * 0.23, 0, TAU)
        ctx.stroke()
    ctx.move_to(-0.07 * r, -0.17 * r)
    ctx.line_to(0.07 * r, -0.17 * r)
    ctx.stroke()


def _beret(ctx, r):
    ctx.save()
    ctx.translate(-0.08 * r, -0.86 * r)
    ctx.rotate(-0.2)
    ctx.scale(0.72 * r, 0.26 * r)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.set_source_rgb(0.12, 0.14, 0.35)
    ctx.fill()
    ctx.set_line_width(r * 0.06)
    ctx.move_to(0, -1.1 * r)
    ctx.line_to(0.05 * r, -1.22 * r)
    ctx.stroke()


def _pirate(ctx, r):
    ctx.set_source_rgb(0.82, 0.1, 0.12)
    ctx.arc(0, -0.2 * r, r * 0.86, math.pi * 1.12, math.pi * 1.88)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    for x in (-0.3, 0.05, 0.4):
        ctx.arc(x * r, -0.78 * r, r * 0.05, 0, TAU)
        ctx.fill()
    ctx.set_source_rgb(0.05, 0.05, 0.05)
    ctx.set_line_width(r * 0.04)
    ctx.move_to(-0.85 * r, -0.45 * r)
    ctx.line_to(0.85 * r, 0.05 * r)
    ctx.stroke()
    ctx.arc(0.3 * r, -0.15 * r, r * 0.2, 0, TAU)
    ctx.fill()


def _viking(ctx, r):
    for s in (-1, 1):
        ctx.move_to(s * 0.55 * r, -0.62 * r)
        ctx.curve_to(s * 1.0 * r, -0.75 * r, s * 1.1 * r, -1.1 * r, s * 0.95 * r, -1.35 * r)
        ctx.curve_to(s * 0.85 * r, -1.05 * r, s * 0.7 * r, -0.9 * r, s * 0.4 * r, -0.8 * r)
        ctx.close_path()
        ctx.set_source_rgb(0.95, 0.92, 0.82)
        ctx.fill()
    ctx.set_source_rgb(0.62, 0.64, 0.7)
    ctx.arc(0, -0.45 * r, r * 0.68, math.pi, TAU)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(0.45, 0.47, 0.52)
    ctx.rectangle(-0.7 * r, -0.5 * r, 1.4 * r, 0.12 * r)
    ctx.fill()


def _wizard(ctx, r):
    ctx.move_to(-0.75 * r, -0.62 * r)
    ctx.line_to(0.75 * r, -0.62 * r)
    ctx.line_to(0.25 * r, -1.75 * r)
    ctx.close_path()
    ctx.set_source_rgb(0.35, 0.15, 0.6)
    ctx.fill()
    ctx.set_source_rgb(1, 0.85, 0.2)
    for x, y in ((-0.2, -0.85), (0.25, -1.15), (0.05, -1.45)):
        _star(ctx, x * r, y * r, r * 0.09)
    ctx.set_source_rgb(0.95, 0.95, 0.97)
    ctx.move_to(-0.35 * r, 0.3 * r)
    ctx.curve_to(-0.3 * r, 0.9 * r, 0.3 * r, 0.9 * r, 0.35 * r, 0.3 * r)
    ctx.curve_to(0.15 * r, 0.4 * r, -0.15 * r, 0.4 * r, -0.35 * r, 0.3 * r)
    ctx.fill()


def _star(ctx, x, y, s):
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = s if k % 2 == 0 else s * 0.45
        (ctx.move_to if k == 0 else ctx.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    ctx.close_path()
    ctx.fill()


def _crown(ctx, r):
    ctx.move_to(-0.55 * r, -0.62 * r)
    for k, (x, y) in enumerate([(-0.6, -1.15), (-0.3, -0.85), (0, -1.25), (0.3, -0.85), (0.6, -1.15), (0.55, -0.62)]):
        ctx.line_to(x * r, y * r)
    ctx.close_path()
    ctx.set_source_rgb(1, 0.8, 0.15)
    ctx.fill()
    for x, y, c in ((-0.6, -1.15, (0.9, 0.1, 0.2)), (0, -1.25, (0.2, 0.5, 1)), (0.6, -1.15, (0.1, 0.8, 0.3))):
        ctx.set_source_rgb(*c)
        ctx.arc(x * r, y * r, r * 0.07, 0, TAU)
        ctx.fill()


def _arms(ctx, r, t):
    wave = 0.25 * math.sin(t * 6)
    for s in (-1, 1):
        ctx.save()
        ctx.translate(s * 0.85 * r, 0.05 * r)
        ctx.rotate(s * (-0.9 + wave))
        ctx.scale(0.4 * r, 0.16 * r)
        ctx.arc(s * 0.8, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgb(0.95, 0.72, 0.32)
        ctx.fill()


ACCESSORY = {1: _mustache, 2: _glasses, 3: _beret, 4: _pirate, 5: _viking, 6: _wizard, 7: _crown}


def draw_potato(ctx, x, y, r, tier, angle=0.0, look=(0, 0), t=0.0, seed=0.0, blink=False):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    if tier == TIERS - 1:
        g = cairo.RadialGradient(0, 0, r * 0.6, 0, 0, r * 1.6)
        g.add_color_stop_rgba(0, 1, 0.85, 0.3, 0.5)
        g.add_color_stop_rgba(1, 1, 0.85, 0.3, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 1.6, 0, TAU)
        ctx.fill()
        _arms(ctx, r, t)
    _blob(ctx, r, seed)
    g = cairo.RadialGradient(-0.3 * r, -0.35 * r, r * 0.1, 0, 0, r * 1.05)
    g.add_color_stop_rgb(0, 1.0, 0.9, 0.55)
    g.add_color_stop_rgb(0.6, 0.96, 0.72, 0.32)
    g.add_color_stop_rgb(1, 0.78, 0.5, 0.2)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.45, 0.25, 0.08)
    ctx.set_line_width(max(1.5, r * 0.05))
    ctx.stroke()
    ctx.set_source_rgba(0.55, 0.32, 0.1, 0.35)
    for sx, sy, sr in ((0.45, 0.45, 0.06), (-0.5, 0.4, 0.05), (0.15, 0.7, 0.04), (-0.2, -0.6, 0.045)):
        ctx.arc(sx * r, sy * r, sr * r, 0, TAU)
        ctx.fill()
    _eyes(ctx, r, look, closed=blink)
    if tier != 1:
        _smile(ctx, r, big=tier == TIERS - 1)
    if tier in ACCESSORY:
        ACCESSORY[tier](ctx, r)
    ctx.restore()


# ------------------------------------------------------------------ la scène

class PotatoMerge(Scene):
    caption = "Attends la dernière patate..."
    tags = ["#patate", "#merge", "#satisfying", "#asmr", "#pourtoi"]
    outro = 4.0
    max_duration = 75.0

    def __init__(self, rng):
        super().__init__(rng)
        self.gravity = float(rng.choice([0.0, 0.0, 700.0]))  # le plus souvent en apesanteur
        self.title = str(rng.choice(["Attends la dernière patate...", "Qui sera la plus grosse ?",
                                     "Tu tiens jusqu'à la patate suprême ?"]))
        self.p = np.zeros((0, 2))
        self.v = np.zeros((0, 2))
        self.tier = np.zeros(0, int)
        self.ang = np.zeros(0)
        self.spin = np.zeros(0)
        self.seed = np.zeros(0)
        self.grow = np.zeros(0)
        self.next_spawn = 0.3
        self.score = 0
        self.found = {0}
        self.banner = None  # (texte, t0)
        self.rings = []     # (x, y, r, t0)
        self.dust = []      # particules [x, y, vx, vy, vie]
        self.hue_shift = rng.random()
        self.end_t = None
        self.last_voice = -10.0
        self._announce(0, 0.0)

    # -- voix et annonces ------------------------------------------------------------
    def _announce(self, tier, t):
        self.banner = (f"NOUVEAU : {NAMES[tier]}", t)
        start = max(t, self.last_voice + 0.2)
        sig = speak(NAMES[tier].lower() if tier < TIERS - 1 else "la patate suprême",
                    deep=-2.2 * tier, rng=self.rng)
        self.audio.add(start, sig, gain=0.85)
        self.last_voice = start + len(sig) / 44100

    # -- physique --------------------------------------------------------------------
    def _r(self):
        return _radius(self.tier) * np.minimum(1, 0.55 + 0.45 * self.grow)

    def _spawn(self, t):
        if t < self.next_spawn or self.done:
            return
        area = float((math.pi * _radius(self.tier) ** 2).sum()) if len(self.tier) else 0.0
        if area > 0.5 * math.pi * R_FLASK ** 2:
            return
        top = min(3, int(t / 12))  # plus tard, des patates déjà un peu grosses tombent aussi
        tier = int(self.rng.integers(0, top + 1)) if self.rng.random() < 0.35 else 0
        self.p = np.vstack([self.p, [[self.rng.uniform(-NECK * 0.4, NECK * 0.4), NECK_TOP - CY + 30]]])
        self.v = np.vstack([self.v, [[self.rng.normal(0, 40), 420.0]]])
        self.tier = np.append(self.tier, tier)
        self.ang = np.append(self.ang, self.rng.uniform(-0.3, 0.3))
        self.spin = np.append(self.spin, self.rng.normal(0, 1.2))
        self.seed = np.append(self.seed, self.rng.uniform(0, 6))
        self.grow = np.append(self.grow, 1.0)
        if tier not in self.found:
            self.found.add(tier)
        self.next_spawn = t + float(self.rng.uniform(0.28, 0.45))

    def _walls(self, r):
        p, v = self.p, self.v
        d = np.maximum(np.hypot(p[:, 0], p[:, 1]), 1e-6)
        neck_y = -math.sqrt(R_FLASK ** 2 - NECK ** 2)
        in_neck = (p[:, 1] < neck_y + 10) & (np.abs(p[:, 0]) < NECK - r * 0.5)
        out = (d > R_FLASK - r) & ~in_neck
        if out.any():
            n = p[out] / d[out, None]
            p[out] = n * (R_FLASK - r[out])[:, None]
            dot = np.einsum("ij,ij->i", v[out], n)
            v[out] -= (2 * np.maximum(dot, 0))[:, None] * n
        neck = p[:, 1] < neck_y
        for s in (-1, 1):
            m = neck & (s * p[:, 0] > NECK - r)
            p[m, 0] = s * (NECK - r[m])
            v[m, 0] = -s * np.abs(v[m, 0])
        top = p[:, 1] < NECK_TOP - CY + r
        p[top, 1] = NECK_TOP - CY + r[top]
        v[top, 1] = np.abs(v[top, 1])

    def _merge(self, t, r):
        if len(self.p) < 2:
            return
        I, J = _ball_pairs(self.p, float(r.max()))
        if not len(I):
            return
        same = self.tier[I] == self.tier[J]
        I, J = I[same], J[same]
        d = np.hypot(*(self.p[J] - self.p[I]).T)
        close = d < (r[I] + r[J]) + 2
        I, J = I[close], J[close]
        used = set()
        kill = []
        for i, j in zip(I, J):
            if i in used or j in used or self.tier[i] >= TIERS - 1:
                continue
            used.update((i, j))
            nt = self.tier[i] + 1
            mid = (self.p[i] + self.p[j]) / 2
            self.p[i] = mid
            self.v[i] = (self.v[i] + self.v[j]) / 2
            self.tier[i] = nt
            self.grow[i] = 0.0
            self.spin[i] = self.rng.normal(0, 0.8)
            kill.append(j)
            self.score += 2 ** nt
            self.rings.append((mid[0], mid[1], _radius(nt), t))
            for _ in range(14):
                a = self.rng.uniform(0, TAU)
                s = self.rng.uniform(80, 300)
                self.dust.append([mid[0], mid[1], math.cos(a) * s, math.sin(a) * s, 0.7])
            # le son descend avec le niveau : de plus en plus grave
            self.audio.add(t, pop(note_freq(14 - 2 * nt, 196.0), dur=0.18), gain=0.45)
            self.audio.add(t, bell(note_freq(10 - nt, 130.81), dur=0.8, decay=0.3), gain=0.18)
            if nt not in self.found:
                self.found.add(nt)
                self._announce(nt, t)
            if nt == TIERS - 1:
                self.done = True
                self.end_t = t
                for k, st in enumerate((0, 4, 7, 12)):
                    self.audio.add(t + 0.6 + k * 0.1, bell(note_freq(st, 65.41), dur=3.5, decay=1.5), gain=0.5)
        if kill:
            keep = np.ones(len(self.p), bool)
            keep[kill] = False
            for name in ("p", "v", "tier", "ang", "spin", "seed", "grow"):
                setattr(self, name, getattr(self, name)[keep])

    def _attract(self, t, dt):
        """Les patates identiques s'attirent doucement (et de plus en plus) pour que ça fusionne."""
        strength = 160 + 12 * t
        for tier in np.unique(self.tier):
            idx = np.flatnonzero(self.tier == tier)
            if len(idx) < 2:
                continue
            P = self.p[idx]
            D = P[None, :, :] - P[:, None, :]
            dist = np.hypot(D[..., 0], D[..., 1]) + np.eye(len(idx)) * 1e9
            nearest = dist.argmin(1)
            dirv = D[np.arange(len(idx)), nearest]
            dn = dist[np.arange(len(idx)), nearest][:, None]
            self.v[idx] += dirv / dn * strength * dt

    def _step(self, dt, t):
        if not len(self.p):
            return
        self.v[:, 1] += self.gravity * dt
        self._attract(t, dt)
        self.p += self.v * dt
        r = self._r()
        collide_balls(self.p, self.v, r, e=0.85)
        self._walls(r)
        if self.gravity == 0:
            sp = np.maximum(np.hypot(*self.v.T), 1e-6)
            self.v *= (np.clip(sp, 90, 420) / sp)[:, None]
        else:
            sp = np.maximum(np.hypot(*self.v.T), 1e-6)
            self.v *= (np.minimum(sp, 900) / sp)[:, None]
        if not self.done:
            self._merge(t, r)

    # -- rendu -----------------------------------------------------------------------
    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        self._spawn(t)
        for _ in range(2):
            self._step(dt, t)
        self.ang += self.spin / FPS
        self.grow = np.minimum(1, self.grow + 1 / (0.2 * FPS))

        ctx.set_source_rgb(0.03, 0.03, 0.08)
        ctx.paint()
        # rayons de fond qui tournent doucement
        ctx.save()
        ctx.translate(CX, CY)
        ctx.rotate(t * 0.1)
        ctx.set_source_rgba(1, 1, 1, 0.025)
        for k in range(16):
            a = k * TAU / 16
            ctx.move_to(0, 0)
            ctx.arc(0, 0, 1400, a, a + TAU / 40)
            ctx.close_path()
        ctx.fill()
        ctx.restore()
        # fiole : cercle arc-en-ciel lumineux + goulot
        a_neck = math.asin(NECK / R_FLASK)
        a0, a1 = -math.pi / 2 + a_neck, 1.5 * math.pi - a_neck
        segs = 72
        for glow_w, alpha in ((26, 0.12), (10, 1.0)):
            ctx.set_line_width(glow_w)
            for k in range(segs):
                b0 = a0 + (a1 - a0) * k / segs
                b1 = a0 + (a1 - a0) * (k + 1.05) / segs
                ctx.set_source_rgba(*hsv(self.hue_shift + k / segs + t * 0.08, 0.85, 1.0), alpha)
                ctx.arc(CX, CY, R_FLASK + 5, b0, b1)
                ctx.stroke()
        neck_y = CY - math.sqrt(R_FLASK ** 2 - NECK ** 2)
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(6)
        for s in (-1, 1):
            ctx.move_to(CX + s * (NECK + 5), NECK_TOP)
            ctx.line_to(CX + s * (NECK + 5), neck_y)
            ctx.stroke()
        # anneaux de fusion
        alive = []
        for x, y, rr, t0 in self.rings:
            age = t - t0
            if age < 0.5:
                alive.append((x, y, rr, t0))
                ctx.set_source_rgba(0.85, 1, 0.85, 0.7 * (1 - age / 0.5))
                ctx.set_line_width(5)
                ctx.arc(CX + x, CY + y, rr * (1 + age * 0.8), 0, TAU)
                ctx.stroke()
        self.rings = alive
        # patates (les petites devant les grosses)
        r = self._r()
        order = np.argsort(-self.tier, kind="stable")
        blink = (t % 3.7) < 0.12
        for i in order:
            sp = np.hypot(*self.v[i]) + 1e-6
            look = (self.v[i, 0] / sp, self.v[i, 1] / sp)
            draw_potato(ctx, CX + self.p[i, 0], CY + self.p[i, 1], r[i], int(self.tier[i]),
                        0.35 * math.sin(self.ang[i]), look, t, self.seed[i], blink and i % 3 == 0)
        # poussière d'étoiles
        keep = []
        for d in self.dust:
            d[0] += d[2] / FPS
            d[1] += d[3] / FPS
            d[4] -= 1 / FPS
            if d[4] > 0:
                keep.append(d)
                ctx.set_source_rgba(1, 0.95, 0.7, min(1, d[4] * 1.5))
                ctx.arc(CX + d[0], CY + d[1], 3, 0, TAU)
                ctx.fill()
        self.dust = keep

        # textes
        text(ctx, self.title, W / 2, 300, 66)
        if self.banner and t - self.banner[1] < 2.5:
            a = min(1, (2.5 - (t - self.banner[1])) * 2)
            text(ctx, self.banner[0], W / 2, 400, 50, (1, 0.85, 0.2), a)
        text(ctx, f"SCORE : {self.score:,}".replace(",", " "), W / 2, 1610, 80)
        # barre des niveaux découverts
        n = TIERS
        gap = 96
        x0 = W / 2 - gap * (n - 1) / 2
        for k in range(n):
            x, y = x0 + k * gap, 1700
            ctx.set_source_rgba(1, 1, 1, 0.12)
            ctx.arc(x, y, 38, 0, TAU)
            ctx.fill()
            ctx.set_source_rgba(1, 1, 1, 0.6)
            ctx.set_line_width(2.5)
            ctx.arc(x, y, 38, 0, TAU)
            ctx.stroke()
            if k in self.found:
                draw_potato(ctx, x, y + 4, 26, k, 0, (0, 0), t, 1.0)
            else:
                ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                ctx.set_font_size(34)
                ctx.set_source_rgba(1, 1, 1, 0.7)
                ext = ctx.text_extents("?")
                ctx.move_to(x - ext.width / 2 - ext.x_bearing, y + ext.height / 2)
                ctx.show_text("?")
        if self.done:
            pulse = 1 + 0.06 * math.sin(t * 8)
            text(ctx, "LA PATATE SUPRÊME !", W / 2, 1830, 64 * pulse, (1, 0.85, 0.2))
