"""Boucles infinies : la dernière image est identique à la première.

TikTok enchaîne la vidéo en boucle et on ne voit pas la coupure : le spectateur attend
une fin qui n'arrive jamais, ce qui multiplie le temps de visionnage.
Principe : un zoom auto-similaire. Après une période, chaque niveau a pris exactement
la place (taille, position, couleur) du niveau précédent.
"""
import math

import numpy as np

from .core import FPS, W, Scene, background, bell, hook, hsv, note_freq, pop, whoosh

TAU = 2 * math.pi
COS30 = math.cos(math.pi / 6)
MELODY = [0, 4, 2, 5, 7, 4, 9, 5]  # 8 notes : la mélodie boucle avec la vidéo


def _crossed(t, period, at):
    """Vrai si la phase `at` (0-1) d'un cycle a été franchie pendant cette image."""
    t0 = t - 1 / FPS
    return math.floor(t / period - at) > math.floor(t0 / period - at)


class InfiniteCube(Scene):
    """Une boîte tombe dans une boîte, la caméra plonge dedans... pour toujours."""
    loop = True
    title = "Cette vidéo ne finit jamais"
    caption = "Essaie de trouver la fin..."
    tags = ["#illusion", "#satisfying", "#infiniteloop", "#oddlysatisfying", "#pourtoi"]
    K, S0, H0 = 3.0, 520.0, 9.0
    LAND, BOUNCE = 0.72, 0.86

    def __init__(self, rng):
        super().__init__(rng)
        self.period = float(rng.choice([3.0, 3.5, 4.0]))
        self.cycles = len(MELODY)
        self.max_duration = self.period * self.cycles
        self.hue0 = rng.random()
        self.base = (W / 2, 1300.0)
        self.sat = float(rng.uniform(0.6, 0.9))

    def fall(self, u):
        """Hauteur de la boîte qui tombe, en tailles de la boîte qui la reçoit."""
        if u < 0.3:
            return self.H0
        if u < self.LAND:
            return self.H0 * (1 - ((u - 0.3) / (self.LAND - 0.3)) ** 2)
        if u < self.BOUNCE:
            return 0.12 * math.sin(math.pi * (u - self.LAND) / (self.BOUNCE - self.LAND))
        return 0.0

    def _pt(self, b, s, X, Y, Z):
        return b[0] + (X - Y) * COS30 * s, b[1] + (X + Y) * 0.5 * s - Z * s

    def vis(self, s):
        """Opacité selon la taille seule (et pas le temps) : la boucle reste parfaite."""
        x = math.log(s / self.S0) / math.log(self.K)
        return 1.0 if x <= 0 else max(0.0, 1 - x) ** 2

    def _poly(self, ctx, b, s, pts, rgb, alpha):
        ctx.set_source_rgba(*rgb, alpha)
        for j, p in enumerate(pts):
            x, y = self._pt(b, s, *p)
            (ctx.move_to if j == 0 else ctx.line_to)(x, y)
        ctx.close_path()
        ctx.fill()

    def _edges(self, ctx, b, s, edges, rgb, vis):
        for width, alpha in ((min(18.0, max(4.0, s * 0.03)), 0.25), (min(6.0, max(1.5, s * 0.008)), 1.0)):
            ctx.set_source_rgba(*rgb, alpha * vis)
            ctx.set_line_width(width)
            for p, q in edges:
                ctx.move_to(*self._pt(b, s, *p))
                ctx.line_to(*self._pt(b, s, *q))
            ctx.stroke()

    def draw(self, ctx, t, frame):
        c = int(t // self.period)
        u = t / self.period - c
        if _crossed(t, self.period, 0.45):
            self.audio.add(t, whoosh(self.rng, 0.6), gain=0.35)
        if _crossed(t, self.period, self.LAND):
            self.audio.add(t, pop(110, 0.25), gain=0.8)
            self.audio.add(t, bell(note_freq(MELODY[(c + 1) % self.cycles] + 5), dur=2.0, decay=0.6), gain=0.45)
        if _crossed(t, self.period, self.BOUNCE):
            self.audio.add(t, pop(160, 0.15), gain=0.35)

        background(ctx)
        z = self.K ** u
        levels = []
        b = list(self.base)
        for i in range(-2, 3):
            s = self.S0 * z / self.K ** i
            if i == 2:
                b = [b[0], b[1] - self.fall(u) * self.S0 * z / self.K]
            hue = self.hue0 + (c + i) / self.cycles
            levels.append((tuple(b), s, hue))

        h = 0.5
        back = [((-h, -h, 0), (-h, h, 0), (-h, h, 1), (-h, -h, 1)),
                ((-h, -h, 0), (h, -h, 0), (h, -h, 1), (-h, -h, 1))]
        floor = ((-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0))
        front = [((h, -h, 0), (h, h, 0), (h, h, 1), (h, -h, 1)),
                 ((-h, h, 0), (h, h, 0), (h, h, 1), (-h, h, 1))]
        back_edges = [((-h, -h, 0), (-h, -h, 1)), ((-h, -h, 0), (h, -h, 0)), ((-h, -h, 0), (-h, h, 0)),
                      ((-h, -h, 1), (h, -h, 1)), ((-h, -h, 1), (-h, h, 1))]
        front_edges = [((h, h, 0), (h, h, 1)), ((h, -h, 0), (h, -h, 1)), ((-h, h, 0), (-h, h, 1)),
                       ((h, h, 0), (h, -h, 0)), ((h, h, 0), (-h, h, 0)),
                       ((h, h, 1), (h, -h, 1)), ((h, h, 1), (-h, h, 1))]

        # Verre : faces du fond de l'extérieur vers l'intérieur, puis faces avant en sens inverse.
        levels = [(b, s, hue, self.vis(s)) for b, s, hue in levels if self.vis(s) > 0]
        for b, s, hue, v in levels:
            self._poly(ctx, b, s, floor, hsv(hue, self.sat, 0.5), 0.5 * v)
            for face in back:
                self._poly(ctx, b, s, face, hsv(hue, self.sat, 0.35), 0.4 * v)
            self._edges(ctx, b, s, back_edges, hsv(hue, self.sat * 0.6, 1.0), v)
        for b, s, hue, v in reversed(levels):
            for face in front:
                self._poly(ctx, b, s, face, hsv(hue, self.sat, 0.9), 0.1 * v)
            self._edges(ctx, b, s, front_edges, hsv(hue, self.sat * 0.5, 1.0), v)

        hook(ctx, self.title, "Essaie de trouver la fin...")


class InfiniteSpiral(Scene):
    """Polygones emboîtés qui tournent en plongeant vers le centre, sans fin."""
    loop = True
    caption = "Fixe le centre 20 secondes puis regarde ta main"
    tags = ["#illusion", "#opticalillusion", "#satisfying", "#hypnotic", "#pourtoi"]

    def __init__(self, rng):
        super().__init__(rng)
        self.n = int(rng.choice([3, 4, 4, 5, 6]))
        self.theta = float(rng.uniform(0.15, 0.3)) * TAU / self.n
        # Un polygone tourné de theta et inscrit dans le précédent est réduit de ce rapport.
        self.ratio = math.cos(math.pi / self.n) / math.cos(math.pi / self.n - self.theta)
        self.period = float(rng.choice([1.2, 1.5]))
        self.cycles = 16
        self.palette = 8  # divise `cycles` : les couleurs bouclent aussi
        self.max_duration = self.period * self.cycles
        self.hue0 = rng.random()
        self.dir = 1 if rng.random() < 0.5 else -1
        self.title = "Fixe le centre..."
        self.center = (W / 2, 1060.0)

    def draw(self, ctx, t, frame):
        c = int(t // self.period)
        u = t / self.period - c
        if _crossed(t, self.period, 0.0) or frame == 0:
            step = MELODY[c % len(MELODY)]
            self.audio.add(t, bell(note_freq(step, 196.0), dur=2.5, decay=0.8), gain=0.3)

        background(ctx)
        zoom = self.ratio ** -u
        R0 = 2300.0
        i = 0
        while True:
            r = R0 * zoom * self.ratio ** i
            if r < 3:
                break
            rot = self.dir * self.theta * (i - u) - math.pi / 2
            a = c + i
            col = hsv(self.hue0 + (a % self.palette) / self.palette, 0.75, 1.0 if a % 2 else 0.8)
            ctx.set_source_rgb(*col)
            for j in range(self.n):
                ang = rot + j * TAU / self.n
                x, y = self.center[0] + r * math.cos(ang), self.center[1] + r * math.sin(ang)
                (ctx.move_to if j == 0 else ctx.line_to)(x, y)
            ctx.close_path()
            ctx.fill()
            i += 1

        hook(ctx, self.title, "20 secondes, puis regarde ta main")
