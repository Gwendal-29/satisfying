"""Encore plus de scènes : fusions (planètes, slimes), balles qui se divisent, formes à
quitter (solo ou duel), nuage de particules 3D qui se transforme (boucle)."""
import math

import cairo
import numpy as np

from .core import (FPS, H, W, Scene, bell, hook, hsv, marimba, note_freq, pop, shatter, text,
                   tick, whoosh)
from .inspired import _chord, _want
from .merge import PotatoMerge, _blob, _crown, _eyes, _smile
from .physics import collide_balls, collide_segment, wall_circle

TAU = 2 * math.pi
CX, CY = W / 2, 1000
ALL = ("court", "moyen", "normal", "long")


# ------------------------------------------------------------------ fusion de planètes

_SPOTS = np.random.default_rng(42).uniform(-1, 1, (14, 3))


def _sphere_shade(ctx, r):
    g = cairo.RadialGradient(-0.35 * r, -0.4 * r, r * 0.05, 0, 0, r * 1.02)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.35)
    g.add_color_stop_rgba(0.45, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.8, 0, 0, 0, 0.25)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.7)
    ctx.set_source(g)
    ctx.paint()


def _bands(ctx, r, cols, tilt=0.0, wobble=0.0, t=0.0):
    ctx.save()
    ctx.rotate(tilt)
    n = len(cols)
    for i, c in enumerate(cols):
        y0 = -r + 2 * r * i / n
        ctx.set_source_rgb(*c)
        ctx.move_to(-r * 1.2, y0)
        for k in range(13):
            x = -r * 1.2 + k * r * 0.2
            ctx.line_to(x, y0 + wobble * r * math.sin(k * 0.9 + i * 1.7 + t))
        ctx.line_to(r * 1.2, y0 + 2 * r / n + 1)
        ctx.line_to(-r * 1.2, y0 + 2 * r / n + 1)
        ctx.close_path()
        ctx.fill()
    ctx.restore()


def draw_planet(ctx, x, y, r, tier, angle=0.0, look=(0, 0), t=0.0, seed=0.0, blink=False):
    ctx.save()
    ctx.translate(x, y)
    if tier == 7:  # soleil : couronne lumineuse et rayons qui tournent
        g = cairo.RadialGradient(0, 0, r * 0.8, 0, 0, r * 1.9)
        g.add_color_stop_rgba(0, 1, 0.75, 0.2, 0.7)
        g.add_color_stop_rgba(1, 1, 0.5, 0.1, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 1.9, 0, TAU)
        ctx.fill()
        ctx.set_source_rgba(1, 0.85, 0.3, 0.35)
        for k in range(16):
            a = k * TAU / 16 + t * 0.4
            ctx.move_to(math.cos(a - 0.08) * r, math.sin(a - 0.08) * r)
            ctx.line_to(math.cos(a) * r * 1.55, math.sin(a) * r * 1.55)
            ctx.line_to(math.cos(a + 0.08) * r, math.sin(a + 0.08) * r)
            ctx.fill()
    if tier == 5:  # anneau de Saturne, moitié arrière
        ctx.save()
        ctx.rotate(-0.35)
        ctx.scale(1, 0.28)
        ctx.set_source_rgba(0.85, 0.75, 0.55, 0.9)
        ctx.set_line_width(r * 0.35)
        ctx.arc(0, 0, r * 1.55, math.pi, TAU)
        ctx.stroke()
        ctx.restore()
    ctx.save()
    ctx.arc(0, 0, r, 0, TAU)
    ctx.clip()
    base = [(0.45, 0.42, 0.4), (0.78, 0.78, 0.8), (0.82, 0.35, 0.18), (0.15, 0.4, 0.85),
            (0.2, 0.35, 0.9), (0.88, 0.78, 0.55), (0.85, 0.6, 0.38), (1.0, 0.82, 0.25)][tier]
    ctx.set_source_rgb(*base)
    ctx.paint()
    rot = angle + seed
    if tier in (0, 1):  # astéroïde / lune : cratères
        for sx, sy, ss in _SPOTS[:9]:
            a = math.atan2(sy, sx) + rot
            d = math.hypot(sx, sy) * 0.75
            ctx.set_source_rgba(0, 0, 0, 0.22)
            ctx.arc(math.cos(a) * d * r, math.sin(a) * d * r, r * (0.1 + 0.08 * abs(ss)), 0, TAU)
            ctx.fill()
    elif tier == 2:  # Mars : taches sombres et calotte polaire
        for sx, sy, ss in _SPOTS[:6]:
            a = math.atan2(sy, sx) + rot
            ctx.set_source_rgba(0.45, 0.15, 0.05, 0.4)
            ctx.arc(math.cos(a) * 0.6 * r, math.sin(a) * 0.6 * r, r * (0.18 + 0.1 * abs(ss)), 0, TAU)
            ctx.fill()
        ctx.set_source_rgb(0.97, 0.95, 0.95)
        ctx.arc(0, -r * 1.05, r * 0.35, 0, TAU)
        ctx.fill()
    elif tier == 3:  # Terre : continents et nuages
        for sx, sy, ss in _SPOTS[:7]:
            a = math.atan2(sy, sx) + rot
            ctx.set_source_rgb(0.2, 0.65, 0.3)
            ctx.save()
            ctx.translate(math.cos(a) * 0.55 * r, math.sin(a) * 0.55 * r)
            ctx.rotate(a)
            ctx.scale(r * (0.32 + 0.1 * ss), r * 0.2)
            ctx.arc(0, 0, 1, 0, TAU)
            ctx.restore()
            ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.55)
        for sx, sy, ss in _SPOTS[7:12]:
            a = math.atan2(sy, sx) - rot * 1.3
            ctx.save()
            ctx.translate(math.cos(a) * 0.5 * r, math.sin(a) * 0.5 * r)
            ctx.scale(r * 0.3, r * 0.08)
            ctx.arc(0, 0, 1, 0, TAU)
            ctx.restore()
            ctx.fill()
    elif tier == 4:  # Neptune
        _bands(ctx, r, [(0.18, 0.32, 0.85), (0.3, 0.5, 0.95), (0.2, 0.35, 0.88), (0.35, 0.55, 1.0),
                        (0.2, 0.33, 0.86)], 0.15, 0.04, rot)
    elif tier == 5:  # Saturne
        _bands(ctx, r, [(0.9, 0.82, 0.6), (0.82, 0.7, 0.48), (0.93, 0.85, 0.65), (0.8, 0.66, 0.45),
                        (0.9, 0.8, 0.58)], -0.35, 0.03, rot)
    elif tier == 6:  # Jupiter et sa grande tache rouge
        _bands(ctx, r, [(0.9, 0.8, 0.65), (0.75, 0.5, 0.3), (0.95, 0.88, 0.75), (0.7, 0.45, 0.28),
                        (0.92, 0.82, 0.68), (0.78, 0.55, 0.35), (0.9, 0.8, 0.66)], 0.1, 0.05, rot)
        ctx.set_source_rgb(0.75, 0.25, 0.15)
        ctx.save()
        ctx.translate(r * 0.35 * math.cos(rot), r * 0.3)
        ctx.scale(r * 0.22, r * 0.13)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.fill()
    elif tier == 7:  # Soleil : granulation
        for sx, sy, ss in _SPOTS:
            a = math.atan2(sy, sx) + rot
            ctx.set_source_rgba(1, 0.55, 0.1, 0.35)
            ctx.arc(math.cos(a) * 0.6 * r, math.sin(a) * 0.6 * r, r * 0.15, 0, TAU)
            ctx.fill()
    _sphere_shade(ctx, r)
    ctx.restore()
    if tier == 5:  # anneau, moitié avant
        ctx.save()
        ctx.rotate(-0.35)
        ctx.scale(1, 0.28)
        ctx.set_source_rgba(0.9, 0.8, 0.6, 0.95)
        ctx.set_line_width(r * 0.35)
        ctx.arc(0, 0, r * 1.55, 0, math.pi)
        ctx.stroke()
        ctx.restore()
    ctx.restore()


class PlanetMerge(PotatoMerge):
    caption = "Deux planètes identiques fusionnent... jusqu'au Soleil ?"
    tags = ["#espace", "#planetes", "#merge", "#satisfying", "#pourtoi"]
    names = ["L'astéroïde", "La Lune", "Mars", "La Terre", "Neptune", "Saturne", "Jupiter", "LE SOLEIL"]
    draw_item = staticmethod(draw_planet)
    titles = ["Attends le Soleil...", "Jusqu'où ça va grossir ?", "Tu tiens jusqu'au Soleil ?"]
    final_text = "LE SOLEIL !"
    final_voice = "le soleil"


# ------------------------------------------------------------------ fusion de slimes

SLIME_HUES = [0.33, 0.5, 0.6, 0.76, 0.9, 0.03, 0.12, None]


def draw_slime(ctx, x, y, r, tier, angle=0.0, look=(0, 0), t=0.0, seed=0.0, blink=False):
    ctx.save()
    ctx.translate(x, y)
    squash = 1 + 0.06 * math.sin(t * 7 + seed * 3)
    ctx.scale(1 / squash, squash)
    hue = SLIME_HUES[tier]
    rainbow = hue is None
    if rainbow:
        hue = (t * 0.2) % 1.0
    _blob(ctx, r, seed)
    g = cairo.RadialGradient(-0.3 * r, -0.4 * r, r * 0.1, 0, 0, r * 1.05)
    g.add_color_stop_rgba(0, *hsv(hue, 0.35, 1.0), 0.95)
    g.add_color_stop_rgba(0.7, *hsv(hue + (0.15 if rainbow else 0), 0.8, 0.95), 0.92)
    g.add_color_stop_rgba(1, *hsv(hue + (0.3 if rainbow else 0), 0.9, 0.65), 0.95)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(*hsv(hue, 0.9, 0.4), 0.9)
    ctx.set_line_width(max(1.5, r * 0.05))
    ctx.stroke()
    # reflet brillant
    ctx.set_source_rgba(1, 1, 1, 0.55)
    ctx.save()
    ctx.translate(-0.38 * r, -0.5 * r)
    ctx.rotate(-0.6)
    ctx.scale(r * 0.22, r * 0.1)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.fill()
    _eyes(ctx, r, look, closed=blink)
    _smile(ctx, r, big=tier >= 6)
    if tier == 7:
        _crown(ctx, r)
    ctx.restore()


class SlimeMerge(PotatoMerge):
    caption = "Deux slimes identiques fusionnent... jusqu'au roi ?"
    tags = ["#slime", "#merge", "#satisfying", "#asmr", "#pourtoi"]
    names = ["Le mini slime", "Le slime vert", "Le slime bleu", "Le slime violet", "Le slime rose",
             "Le slime de feu", "Le slime doré", "LE ROI DES SLIMES"]
    draw_item = staticmethod(draw_slime)
    titles = ["Attends le roi des slimes...", "Lequel sera le plus gros ?", "Tu tiens jusqu'au roi ?"]
    final_text = "LE ROI DES SLIMES !"
    final_voice = "le roi des slimes"


# ------------------------------------------------------------------ balles qui se divisent

def _polygon(n, R, rot):
    a = rot + np.arange(n) * TAU / n
    return np.stack([R * np.cos(a), R * np.sin(a)], 1)


class SplitBalls(Scene):
    caption = "Elle se divise à chaque rebond..."
    tags = ["#satisfying", "#physics", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.5
    lengths = ALL
    R, G = 470.0, 1100.0

    def __init__(self, rng):
        super().__init__(rng)
        self.target = self.target(float(rng.choice([30, 38, 45]))) - 1
        self.cap = int(rng.choice([128, 256] if self.target < 28 else [256, 512, 1024]))
        self.max_duration = self.target + 15
        self.sides = int(rng.choice([0, 4, 5, 6, 8]))
        self.spin = rng.choice([-1, 1]) * rng.uniform(0.3, 0.8)
        self.rot = rng.uniform(0, TAU)
        self.r0 = 55.0
        self.rmin = math.sqrt(0.42 * self.R ** 2 / self.cap)
        self.p = np.array([[0.0, -150.0]])
        a = rng.uniform(0, TAU)
        self.v = np.array([[math.cos(a), math.sin(a)]]) * 700
        self.gen = np.array([0])
        self.cool = np.array([0.0])
        self.hue0 = rng.random()
        self.title = f"1 balle → {self.cap} ?"
        self.wave = []

    def _rad(self, gen):
        return np.maximum(self.rmin, self.r0 * 0.78 ** gen)

    def _step(self, dt, t):
        self.v[:, 1] += self.G * dt
        self.p += self.v * dt
        self.cool -= dt
        r = self._rad(self.gen)
        collide_balls(self.p, self.v, r, e=0.95)
        if self.sides:
            self.rot += self.spin * dt
            pts = _polygon(self.sides, self.R, self.rot)
            hit = np.zeros(len(self.p), bool)
            for i in range(self.sides):
                m, _ = collide_segment(self.p, self.v, r, pts[i], pts[(i + 1) % self.sides], 5.0,
                                       omega=self.spin, e=1.0)
                hit |= m
            wall_circle(self.p, self.v, self.R, r, e=1.0)  # sécurité : personne ne sort
        else:
            hit = wall_circle(self.p, self.v, self.R, r, e=1.0)
        sp = np.maximum(np.hypot(*self.v.T), 1e-6)
        self.v *= (np.clip(sp, 450, 1500) / sp)[:, None]
        idx = np.flatnonzero(hit & (self.cool <= 0))
        room = int(_want(t, self.target, self.cap) - len(self.p))
        idx = idx[:max(0, min(room, self.cap - len(self.p)))]
        if len(idx):
            v = self.v[idx]
            c, s = math.cos(0.5), math.sin(0.5)
            v1 = np.stack([v[:, 0] * c - v[:, 1] * s, v[:, 0] * s + v[:, 1] * c], 1)
            v2 = np.stack([v[:, 0] * c + v[:, 1] * s, -v[:, 0] * s + v[:, 1] * c], 1)
            self.v[idx] = v1
            self.gen[idx] += 1
            self.cool[idx] = 0.25
            self.p = np.vstack([self.p, self.p[idx]])
            self.v = np.vstack([self.v, v2])
            self.gen = np.concatenate([self.gen, self.gen[idx]])
            self.cool = np.concatenate([self.cool, np.full(len(idx), 0.25)])
            for i in idx[:3]:
                self.wave.append((*self.p[i], t))
            if len(self.p) >= self.cap:
                self.done = True
                _chord(self.audio, t, 0)
        return len(idx), int(hit.sum())

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        born = hits = 0
        for _ in range(2):
            b, h = self._step(dt, t)
            born += b
            hits += h
        n = len(self.p)
        if born:
            g = int(self.gen.max())
            self.audio.add(t, pop(note_freq(4 + g % 10)), gain=0.45 / (1 + n / 200))
        elif hits and n < 30:
            self.audio.add(t, tick(self.rng, bright=0.4), gain=0.12)

        ctx.set_source_rgb(0.02, 0.02, 0.05)
        ctx.paint()
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(6)
        if self.sides:
            pts = _polygon(self.sides, self.R + 3, self.rot)
            for i, (x, y) in enumerate(pts):
                (ctx.move_to if i == 0 else ctx.line_to)(CX + x, CY + y)
            ctx.close_path()
        else:
            ctx.arc(CX, CY, self.R + 3, 0, TAU)
        ctx.stroke()
        alive = []
        for x, y, t0 in self.wave:
            age = t - t0
            if age < 0.4:
                alive.append((x, y, t0))
                ctx.set_source_rgba(1, 1, 1, 0.6 * (1 - age / 0.4))
                ctx.set_line_width(3)
                ctx.arc(CX + x, CY + y, 20 + 120 * age, 0, TAU)
                ctx.stroke()
        self.wave = alive[-30:]
        r = self._rad(self.gen)
        for (x, y), rr, g in zip(self.p, r, self.gen):
            ctx.set_source_rgb(*hsv(self.hue0 + 0.09 * g, 0.8, 1.0))
            ctx.arc(CX + x, CY + y, rr, 0, TAU)
            ctx.fill()
        hook(ctx, self.title, None, t)
        text(ctx, f"{n}", W / 2, 1640, 96, (1, 1, 1))
        if self.done:
            text(ctx, "OBJECTIF !", W / 2, 1740, 64, (0.4, 1, 0.5))


# ------------------------------------------------------------------ formes à quitter (solo / duel)

class ShapeEscape(Scene):
    caption = "Chaque forme a une seule sortie..."
    tags = ["#satisfying", "#oddlysatisfying", "#simulation", "#asmr", "#pourtoi"]
    outro = 2.5
    lengths = ALL
    BR, G = 11.0, 1300.0

    def __init__(self, rng):
        super().__init__(rng)
        self.T = self.target(float(rng.choice([30, 38, 45]))) - 4
        self.max_duration = self.T + 20
        seq = [3, 4, 5, 6, 8]
        mode = rng.choice(["suite", "pareil", "hasard"])
        pick = {"suite": lambda i: [4, 5, 6, 8][min(i, 3)],
                "pareil": lambda i, c=int(rng.choice([6, 8])): c,
                "hasard": lambda i: int(rng.choice([5, 6, 8, 8]))}[mode]
        # Chaque forme doit contenir entièrement la précédente (sinon la balle les traverse
        # toutes d'un coup) : rayon suivant = (rayon + marge) / cos(pi / côtés).
        gapr = 16.0 if self.T > 40 else 20.0
        self.sides, radii, R = [], [], 85.0
        i = 0
        while True:
            n = pick(i) if i else (4 if mode == "suite" else pick(0))
            R = R if i == 0 else (R + gapr) / math.cos(math.pi / n)
            if R > 525:
                break
            self.sides.append(n)
            radii.append(R)
            i += 1
        self.radii = np.array(radii)
        self.n = len(radii)
        base = rng.uniform(0.5, 0.9)
        alt = rng.random() < 0.6
        self.w = [(base + 0.05 * i) * (-1 if alt and i % 2 else 1) for i in range(self.n)]
        self.rot = list(rng.uniform(0, TAU, self.n))
        self.hue0 = rng.random()
        self.duel = rng.random() < 0.45
        if self.duel:
            self.cols = [(1.0, 0.25, 0.25), (0.25, 0.55, 1.0)]
            self.names = ["ROUGE", "BLEU"]
            self.title = "Rouge ou Bleu ?"
            self.caption = "Rouge ou Bleu : qui casse le plus de formes ? Dis-le en commentaire"
        else:
            self.cols = [(1, 1, 1)]
            self.names = [""]
            self.title = "Elle va s'échapper ?"
        nb = len(self.cols)
        self.p = np.array([[(-30 if nb == 2 else 0) + 60 * i, 0.0] for i in range(nb)])
        a = rng.uniform(0, TAU, nb)
        self.v = np.stack([np.cos(a), np.sin(a)], 1) * 800
        self.score = [0] * nb
        self.k = 0
        self.g = 0.35
        self.assist = 0.0
        self.parts = []
        self.trail = [[] for _ in range(nb)]

    def _edges(self, i):
        """Segments du polygone i, avec une ouverture au milieu du premier côté."""
        n = self.sides[i]
        pts = _polygon(n, self.radii[i], self.rot[i])
        segs = []
        for e in range(n):
            a, b = pts[e], pts[(e + 1) % n]
            if e == 0:
                m = (a + b) / 2
                half = self.g / 2
                segs.append((a, m + (a - m) * half))
                segs.append((m + (b - m) * half, b))
            else:
                segs.append((a, b))
        return segs

    def _break(self, who, t):
        i = self.k
        col = hsv(self.hue0 + i / self.n)
        pts = _polygon(self.sides[i], self.radii[i], self.rot[i])
        for e in range(self.sides[i]):
            a, b = pts[e], pts[(e + 1) % self.sides[i]]
            for u in self.rng.uniform(0, 1, 14):
                q = a + (b - a) * u
                d = q / (np.linalg.norm(q) + 1e-6)
                sp = self.rng.uniform(100, 500)
                self.parts.append([q[0], q[1], d[0] * sp, d[1] * sp, 1.0, col])
        self.audio.add(t, shatter(self.rng, 0.5), gain=0.4)
        self.audio.add(t, bell(note_freq(i % 15 + 5), dur=1.4), gain=0.45)
        self.score[who] += 1
        self.k += 1
        if self.k >= self.n:
            self.done = True
            _chord(self.audio, t + 0.1, 5)

    def _step(self, dt, t):
        self.v[:, 1] += self.G * dt
        self.p += self.v * dt
        for i in range(self.k, self.n):
            self.rot[i] += self.w[i] * dt
        if self.k >= self.n:
            return
        segs = self._edges(self.k)
        hit = np.zeros(len(self.p), bool)
        for A, B in segs:
            m, rel = collide_segment(self.p, self.v, self.BR, A, B, 4.0, omega=self.w[self.k], e=1.0)
            if m.any() and (rel > 50).any():
                hit |= m
                self.audio.add(t, marimba(note_freq(int(self.rng.integers(5, 13))), 0.5), gain=0.25)
        # coup de pouce discret quand la vidéo prend du retard : le rebond part vers la sortie
        if hit.any() and self.assist > 0:
            pts = _polygon(self.sides[self.k], self.radii[self.k], self.rot[self.k])
            gap = (pts[0] + pts[1]) / 2
            for j in np.flatnonzero(hit):
                if self.rng.random() < self.assist:
                    d = gap - self.p[j]
                    self.v[j] = d / (np.linalg.norm(d) + 1e-6) * np.linalg.norm(self.v[j])
        sp = np.maximum(np.hypot(*self.v.T), 1e-6)
        self.v *= (np.clip(sp, 650, 1250) / sp)[:, None]
        if len(self.p) > 1:
            collide_balls(self.p, self.v, self.BR, e=1.0)
        inside = self._inside(self.k)
        out = np.flatnonzero(inside < -(self.BR + 4))
        if len(out):
            self._break(int(out[0]), t)

    def _inside(self, i):
        """Distance signée des billes au polygone i (positive = dedans)."""
        n = self.sides[i]
        pts = _polygon(n, self.radii[i], self.rot[i])
        best = np.full(len(self.p), np.inf)
        for e in range(n):
            a, b = pts[e], pts[(e + 1) % n]
            mid = (a + b) / 2
            nin = -mid / (np.linalg.norm(mid) + 1e-9)
            best = np.minimum(best, (self.p - a) @ nin)
        return best

    def draw(self, ctx, t, frame):
        lag = self.n * min(t, self.T) / self.T - self.k + 1.5 * max(0.0, t - self.T)
        g_want = float(np.clip(0.3 * 1.45 ** lag, 0.1, 0.92))
        self.g += (g_want - self.g) * 0.05
        self.assist = float(np.clip((lag - 1.0) * 0.12, 0, 0.5))
        dt = 1 / (FPS * 4)
        for _ in range(4):
            self._step(dt, t)
        for p in self.parts:
            p[3] += 700 / FPS
            p[0] += p[2] / FPS
            p[1] += p[3] / FPS
            p[4] -= 1 / (FPS * 1.1)
        self.parts = [p for p in self.parts if p[4] > 0]
        for j, (x, y) in enumerate(self.p):
            self.trail[j] = (self.trail[j] + [(x, y)])[-12:]

        ctx.set_source_rgb(0.03, 0.03, 0.06)
        ctx.paint()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for i in range(self.k, self.n):
            col = hsv(self.hue0 + i / self.n)
            if i == self.k:
                ctx.set_source_rgba(*col, 0.25)
                ctx.set_line_width(22)
                for A, B in self._edges(i):
                    ctx.move_to(CX + A[0], CY + A[1])
                    ctx.line_to(CX + B[0], CY + B[1])
                ctx.stroke()
            ctx.set_source_rgb(*col)
            ctx.set_line_width(8)
            for A, B in self._edges(i):
                ctx.move_to(CX + A[0], CY + A[1])
                ctx.line_to(CX + B[0], CY + B[1])
            ctx.stroke()
        for x, y, _, _, life, col in self.parts:
            ctx.set_source_rgba(*col, life)
            ctx.arc(CX + x, CY + y, 2 + 4 * life, 0, TAU)
            ctx.fill()
        for j, col in enumerate(self.cols):
            for k, (x, y) in enumerate(self.trail[j]):
                a = (k + 1) / len(self.trail[j])
                ctx.set_source_rgba(*col, 0.3 * a)
                ctx.arc(CX + x, CY + y, self.BR * a, 0, TAU)
                ctx.fill()
            ctx.set_source_rgb(*col)
            ctx.arc(CX + self.p[j, 0], CY + self.p[j, 1], self.BR, 0, TAU)
            ctx.fill()

        hook(ctx, self.title, None, t)
        if self.duel:
            text(ctx, f"{self.score[0]}", W / 2 - 200, 1680, 110, self.cols[0])
            text(ctx, "-", W / 2, 1670, 90, (1, 1, 1))
            text(ctx, f"{self.score[1]}", W / 2 + 200, 1680, 110, self.cols[1])
            if self.done:
                a, b = self.score
                msg = "ÉGALITÉ !" if a == b else f"{self.names[0 if a > b else 1]} GAGNE !"
                text(ctx, msg, W / 2, 1800, 72, self.cols[0] if a > b else self.cols[1] if b > a else (1, 1, 1))
        else:
            left = self.n - self.k
            text(ctx, "LIBRE !" if left == 0 else f"Formes restantes : {left}", W / 2, 1680, 60,
                 (0.4, 1, 0.5) if left == 0 else (1, 1, 1))


# ------------------------------------------------------------------ nuage de particules 3D (boucle)

def _fib_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], 1)


def _shapes3d(n, rng):
    u = rng.uniform(0, 1, n)
    v = rng.uniform(0, 1, n)
    out = {}
    out["Sphère"] = _fib_sphere(n)
    face = rng.integers(0, 6, n)
    a, b = rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)
    cube = np.zeros((n, 3))
    ax = face % 3
    sgn = np.where(face < 3, 1.0, -1.0)
    for k in range(3):
        m = ax == k
        cube[m, k] = sgn[m]
        cube[m, (k + 1) % 3] = a[m]
        cube[m, (k + 2) % 3] = b[m]
    out["Cube"] = cube * 0.72
    th, ph = u * TAU, v * TAU
    out["Tore"] = np.stack([(0.75 + 0.3 * np.cos(ph)) * np.cos(th), 0.3 * np.sin(ph),
                            (0.75 + 0.3 * np.cos(ph)) * np.sin(th)], 1)
    s = u * 2 - 1
    strand = np.where(v < 0.5, 0, math.pi)
    out["Hélice"] = np.stack([0.5 * np.cos(s * 3 * math.pi + strand), s * 1.0, 0.5 * np.sin(s * 3 * math.pi + strand)], 1)
    t = u * TAU
    z = v * 2 - 1
    sc = np.sqrt(1 - z ** 2) * 0.06
    hx = 16 * np.sin(t) ** 3
    hy = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    out["Cœur"] = np.stack([hx * sc, hy * sc + 0.1, z * 0.35], 1)
    arm = rng.integers(0, 3, n)
    rr = np.sqrt(u) * 1.0
    ang = arm * TAU / 3 + rr * 4.5 + rng.normal(0, 0.18, n)
    out["Galaxie"] = np.stack([rr * np.cos(ang), rng.normal(0, 0.04, n) * (1.2 - rr), rr * np.sin(ang)], 1)
    cone_h = u * 2 - 1
    cr = (1 - (cone_h + 1) / 2) * 0.8
    out["Pyramide"] = np.stack([cr * np.cos(v * TAU), cone_h * 0.85, cr * np.sin(v * TAU)], 1)
    gx, gz = rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)
    out["Vague"] = np.stack([gx, 0.25 * np.sin(gx * 4) * np.cos(gz * 3), gz], 1)
    # on trie chaque forme de haut en bas : chaque point voyage vers un endroit « logique »
    for k in out:
        P = out[k]
        out[k] = P[np.lexsort((np.arctan2(P[:, 2], P[:, 0]), P[:, 1]))]
    return out


class ParticleMorph(Scene):
    loop = True
    caption = "Laquelle est la plus satisfaisante ?"
    tags = ["#satisfying", "#3d", "#particles", "#hypnotic", "#pourtoi"]
    lengths = ALL
    N = 2400
    MELO = [0, 4, 7, 9, 7, 4, 2, 5, 9, 12, 11, 7]

    def __init__(self, rng):
        super().__init__(rng)
        shapes = _shapes3d(self.N, rng)
        self.seg = float(rng.choice([3.5, 4.0, 4.5]))
        m = 6
        if self.LENGTH:
            m = int(np.clip(round(self.LENGTH / self.seg), 3, len(shapes)))
            self.seg = max(self.seg, (61.5 / m) if self.LENGTH >= 61 else 0, self.LENGTH * 0.85 / m)
        names = list(rng.choice(list(shapes), size=m, replace=False))
        self.names = names
        self.seq = [shapes[k] for k in names]
        self.max_duration = self.seg * m
        self.turns = int(rng.choice([1, 2])) * (1 if m < 6 else 2)
        self.hue0 = rng.random()
        self.pitch = rng.uniform(0.25, 0.45)
        self.title = str(rng.choice(["Laquelle tu préfères ?", "Regarde-les se transformer...",
                                     "Fixe le centre..."]))
        self.order = np.arange(self.N)

    def draw(self, ctx, t, frame):
        m = len(self.seq)
        x = t / self.seg
        k = int(x) % m
        f = x - int(x)
        s = float(np.clip((f - 0.45) / 0.55, 0, 1))
        s = s * s * (3 - 2 * s)
        P = (1 - s) * self.seq[k] + s * self.seq[(k + 1) % m]
        if math.floor(t / self.seg - 0.45) != math.floor((t - 1 / FPS) / self.seg - 0.45):
            self.audio.add(t, whoosh(self.rng, 1.0), gain=0.1)
            self.audio.add(t, bell(note_freq(self.MELO[k % len(self.MELO)], 196.0), dur=2.2, decay=0.8), gain=0.3)
        if math.floor(t / self.seg) != math.floor((t - 1 / FPS) / self.seg) or frame == 0:
            self.audio.add(t, marimba(note_freq(self.MELO[(k + 3) % len(self.MELO)] + 7), 1.0), gain=0.2)
        ph = t / self.max_duration
        yaw = TAU * self.turns * ph
        breathe = 1 + 0.03 * math.sin(TAU * m * 2 * ph)
        c, sn = math.cos(yaw), math.sin(yaw)
        X = P[:, 0] * c + P[:, 2] * sn
        Z = -P[:, 0] * sn + P[:, 2] * c
        Y = P[:, 1]
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        Y, Z = Y * cp - Z * sp, Y * sp + Z * cp
        persp = 3.2 / (Z + 3.4)
        sx = CX + X * persp * 360 * breathe
        sy = 1040 - Y * persp * 360 * breathe
        order = np.argsort(-Z)
        depth = (Z - Z.min()) / (np.ptp(Z) + 1e-6)

        g = cairo.RadialGradient(W / 2, 1040, 50, W / 2, 1040, 1100)
        g.add_color_stop_rgb(0, 0.07, 0.06, 0.12)
        g.add_color_stop_rgb(1, 0.0, 0.0, 0.02)
        ctx.set_source(g)
        ctx.paint()
        hues = self.hue0 + 0.45 * self.order / self.N + 0.15 * math.sin(TAU * ph)
        for i in order:
            b = 1 - 0.65 * depth[i]
            ctx.set_source_rgb(*hsv(hues[i], 0.7, b))
            ctx.arc(sx[i], sy[i], 2.0 + 3.2 * persp[i] * (1 - 0.5 * depth[i]), 0, TAU)
            ctx.fill()
        text(ctx, self.title, W / 2, 300, 66)
        name = self.names[k] if f < 0.55 else self.names[(k + 1) % m]
        text(ctx, name, W / 2, 1680, 80, (1, 0.85, 0.3))
