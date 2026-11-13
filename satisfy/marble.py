"""Bille musicale : une bille rebondit de tube en tube, chaque tube joue une note et s'allume.

Les rebonds sont calculés à partir des notes : la bille tombe pile au rythme de la mélodie.
« Top N des mélodies que tout le monde connaît », les titres se dévoilent un par un.
Toutes les mélodies sont dans le domaine public (aucun risque de droits d'auteur).
"""
import bisect
import math

import cairo
import numpy as np

from .core import FONT, W, Scene, bell, hsv, marimba, text

TAU = 2 * math.pi

# (note MIDI, durée en temps)
SONGS = {
    "Ode à la joie": [(64, 1), (64, 1), (65, 1), (67, 1), (67, 1), (65, 1), (64, 1), (62, 1), (60, 1), (60, 1),
                      (62, 1), (64, 1), (64, 1.5), (62, .5), (62, 2)],
    "Frère Jacques": [(60, 1), (62, 1), (64, 1), (60, 1)] * 2 + [(64, 1), (65, 1), (67, 2)] * 2,
    "Au clair de la lune": [(60, 1), (60, 1), (60, 1), (62, 1), (64, 2), (62, 2), (60, 1), (64, 1), (62, 1),
                            (62, 1), (60, 3)],
    "La Lettre à Élise": [(76, .5), (75, .5), (76, .5), (75, .5), (76, .5), (71, .5), (74, .5), (72, .5), (69, 1.5),
                          (60, .5), (64, .5), (69, .5), (71, 1.5), (64, .5), (68, .5), (71, .5), (72, 2)],
    "Le Roi de la montagne": [(59, .5), (61, .5), (62, .5), (64, .5), (66, .5), (62, .5), (66, 1), (65, .5),
                              (61, .5), (65, 1), (64, .5), (60, .5), (64, 1), (59, .5), (61, .5), (62, .5),
                              (64, .5), (66, .5), (62, .5), (66, .5), (71, .5), (69, .5), (66, .5), (62, .5),
                              (66, .5), (69, 2)],
    "Vive le vent": [(64, 1), (64, 1), (64, 2), (64, 1), (64, 1), (64, 2), (64, 1), (67, 1), (60, 1.5), (62, .5),
                     (64, 3)],
    "Ah ! vous dirai-je, maman": [(60, 1), (60, 1), (67, 1), (67, 1), (69, 1), (69, 1), (67, 2), (65, 1), (65, 1),
                                  (64, 1), (64, 1), (62, 1), (62, 1), (60, 2)],
    "Joyeux anniversaire": [(60, .75), (60, .25), (62, 1), (60, 1), (65, 1), (64, 2), (60, .75), (60, .25),
                            (62, 1), (60, 1), (67, 1), (65, 2)],
    "La Marseillaise": [(62, .75), (62, .25), (62, 1), (67, 1), (67, 1), (69, 1), (69, 1), (74, 1.5), (71, .5),
                        (67, .75), (67, .25), (71, .75), (67, .25), (64, 1), (72, 2), (69, .75), (66, .25), (67, 2)],
}

G = 3200.0          # gravité (px/s²) : petits sauts pour les notes courtes, grands pour les longues
ANGLE = math.radians(28)
TRANSITION = 1.3    # roulement sur rail entre deux mélodies (s)


def _freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


class MarbleMelody(Scene):
    tags = ["#satisfying", "#music", "#marble", "#asmr", "#pourtoi"]
    outro = 2.5

    def __init__(self, rng):
        super().__init__(rng)
        self.beat = 60 / float(rng.choice([120, 132, 144]))
        names = list(rng.permutation(list(SONGS)))
        picked, total = [], 1.2
        for name in names:
            d = sum(b for _, b in SONGS[name]) * self.beat + TRANSITION
            if len(picked) < 6 and total + d < 53:
                picked.append(name)
                total += d
        self.songs = picked
        self.n = len(picked)
        self.title = f"Top {self.n} des mélodies"
        self.subtitle = "que tout le monde connaît"
        self.caption = f"Top {self.n} des mélodies que tout le monde connaît... tu les as toutes reconnues ?"
        self.hue0 = rng.random()
        self.tube_len = rng.uniform(150, 200)
        self._build()
        self.max_duration = self.hits[-1][0] + 1.5 + self.outro
        self.played = 0
        self.revealed = 0
        self.cam = np.array(self.points[0], float)
        self.spin = 0.0
        self.bg = None

    # -- trajectoire --------------------------------------------------------------------
    def _build(self):
        """Calcule l'instant et la position de chaque impact, et le type de trajet entre deux impacts."""
        t, x, y = 1.2, 0.0, 0.0
        self.hits = []      # (t, midi, numéro de mélodie, est-ce la dernière note)
        self.points = []    # position monde de chaque impact
        self.kinds = []     # trajet APRÈS l'impact : "hop" ou "rail"
        self.song_end = []  # instant de la dernière note de chaque mélodie
        for s, name in enumerate(self.songs):
            notes = SONGS[name]
            for k, (midi, dur) in enumerate(notes):
                last = k == len(notes) - 1
                self.hits.append((t, midi, s, last))
                self.points.append((x, y))
                dt = dur * self.beat
                if last:
                    self.song_end.append(t)
                    dt += TRANSITION
                    self.kinds.append("rail")
                    x += 420 + 120 * dt
                    y += 90
                else:
                    self.kinds.append("hop")
                    x += 110 + 230 * dt
                    y += 22
                t += dt
        self.times = [h[0] for h in self.hits]
        self.end_point = (x, y)
        self.lit = np.zeros(len(self.hits))

    def _ball(self, t):
        """Position monde de la bille à l'instant t (y vers le bas)."""
        if t < self.times[0]:
            x0, y0 = self.points[0]
            h = 0.5 * G * (self.times[0] - t) ** 2
            return x0, y0 - min(h, 2500)
        k = bisect.bisect_right(self.times, t) - 1
        t0 = self.times[k]
        x0, y0 = self.points[k]
        if k + 1 < len(self.points):
            t1 = self.times[k + 1]
            x1, y1 = self.points[k + 1]
        else:
            t1, (x1, y1) = t0 + 1.5, self.end_point
        dt = t1 - t0
        u = min(1.0, (t - t0) / dt)
        if self.kinds[k] == "hop" or k + 1 >= len(self.points):
            vy = ((y1 - y0) - 0.5 * G * dt * dt) / dt
            s = t - t0
            return x0 + (x1 - x0) * u, y0 + vy * s + 0.5 * G * s * s
        # rail : petit saut pour monter sur le rail, roulement, puis chute sur le tube suivant
        e = u * u * (3 - 2 * u)
        bump = -60 * math.sin(math.pi * min(1, u * 4)) if u < 0.25 else 0
        return x0 + (x1 - x0) * e, y0 + (y1 - y0) * e + bump

    def _screen(self, x, y):
        cx, cy = self.cam
        dx, dy = x - cx, y - cy
        return W / 2 - dx * math.cos(ANGLE) + 60, 1150 + dx * math.sin(ANGLE) + dy

    # -- dessin -----------------------------------------------------------------------
    def _tube(self, ctx, x, y, midi, lit):
        sx, sy = self._screen(x, y)
        L = self.tube_len + (72 - midi) * 9  # plus grave = plus long, comme un carillon
        ax, ay = math.cos(math.radians(62)), math.sin(math.radians(62))  # axe du tube vers le spectateur
        r = 30.0
        ex, ey = sx + ax * L, sy + ay * L
        nx, ny = -ay * r, ax * r
        hue = self.hue0 + (midi % 12) / 12
        base = np.array(hsv(hue, 0.75, 1.0))
        dark = np.array([0.13, 0.13, 0.15])
        col = dark * (1 - lit) + base * lit
        # lueur
        if lit > 0.05:
            mx, my = (sx + ex) / 2, (sy + ey) / 2
            g = cairo.RadialGradient(mx, my, 10, mx, my, L * 0.75)
            g.add_color_stop_rgba(0, *base, 0.3 * lit)
            g.add_color_stop_rgba(1, *base, 0)
            ctx.set_source(g)
            ctx.rectangle(mx - L * 0.75, my - L * 0.75, L * 1.5, L * 1.5)
            ctx.fill()
        # ombre portée sur le sol
        ctx.set_source_rgba(0, 0, 0, 0.18)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(2 * r)
        ctx.move_to(sx + 45, sy + 12)
        ctx.line_to(ex + 45, ey + 12)
        ctx.stroke()
        # corps du cylindre : dégradé en travers pour le volume
        g = cairo.LinearGradient(sx + nx, sy + ny, sx - nx, sy - ny)
        g.add_color_stop_rgb(0, *(col * 0.55))
        g.add_color_stop_rgb(0.35, *np.minimum(1, col * 1.25 + 0.12))
        g.add_color_stop_rgb(1, *(col * 0.35))
        ctx.set_source(g)
        ctx.move_to(sx + nx, sy + ny)
        ctx.line_to(ex + nx, ey + ny)
        ctx.arc(ex, ey, r, math.atan2(ny, nx), math.atan2(ny, nx) + math.pi)
        ctx.line_to(sx - nx, sy - ny)
        ctx.close_path()
        ctx.fill()
        # embouchure (ellipse ouverte, intérieur sombre)
        ctx.save()
        ctx.translate(sx, sy)
        ctx.rotate(math.atan2(ny, nx))
        ctx.scale(r, r * 0.45)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgb(*np.minimum(1, col * 1.1 + 0.15))
        ctx.fill()
        ctx.save()
        ctx.translate(sx + ax * 3, sy + ay * 3)
        ctx.rotate(math.atan2(ny, nx))
        ctx.scale(r * 0.78, r * 0.33)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgb(*(col * 0.25 + 0.02))
        ctx.fill()

    def _rail(self, ctx, p0, p1):
        (x0, y0), (x1, y1) = p0, p1
        pts = []
        for k in range(25):
            u = k / 24
            e = u * u * (3 - 2 * u)
            pts.append(self._screen(x0 + (x1 - x0) * e, y0 + (y1 - y0) * e + 14))
        for off in (-9, 9):
            ctx.set_source_rgba(0.75, 0.78, 0.85, 0.8)
            ctx.set_line_width(3)
            for k, (x, y) in enumerate(pts):
                (ctx.move_to if k == 0 else ctx.line_to)(x + off * 0.5, y + off)
            ctx.stroke()
        ctx.set_source_rgba(0.6, 0.62, 0.7, 0.6)
        ctx.set_line_width(2)
        for x, y in pts[::3]:
            ctx.move_to(x - 6, y - 12)
            ctx.line_to(x + 6, y + 12)
            ctx.stroke()

    def _marble(self, ctx, x, y, r=34):
        ctx.save()
        ctx.translate(x, y)
        ctx.arc(0, 0, r, 0, TAU)
        ctx.clip()
        g = cairo.RadialGradient(-r * 0.35, -r * 0.4, r * 0.1, 0, 0, r * 1.1)
        g.add_color_stop_rgb(0, 1, 0.45, 0.45)
        g.add_color_stop_rgb(0.6, 0.85, 0.08, 0.1)
        g.add_color_stop_rgb(1, 0.4, 0.02, 0.04)
        ctx.set_source(g)
        ctx.paint()
        ctx.rotate(self.spin)
        ctx.set_source_rgba(0.97, 0.97, 0.97, 0.95)
        ctx.save()
        ctx.scale(1, 0.32)
        ctx.arc(0, 0, r * 1.05, 0, TAU)
        ctx.restore()
        ctx.fill()
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, 0.7)
        ctx.arc(x - r * 0.35, y - r * 0.4, r * 0.18, 0, TAU)
        ctx.fill()

    def _panel(self, ctx, t):
        text(ctx, self.title, W / 2, 250, 64)
        text(ctx, self.subtitle, W / 2, 320, 46, (1, 0.85, 0.3))
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        half = (self.n + 1) // 2
        for i in range(self.n):
            rank = i + 1
            col, row = (0, i) if i < half else (1, i - half)
            x, y = 70 + col * 500, 400 + row * 52
            # on joue du dernier (n) au premier (1) : la mélodie jouée en s-ième position est le rang n - s
            s = self.n - rank
            name = self.songs[s] if s < self.revealed else ""
            ctx.set_font_size(36 if len(name) < 20 else 30)
            ctx.move_to(x, y)
            ctx.text_path(f"{rank}: {name}")
            ctx.set_source_rgba(0, 0, 0, 0.8)
            ctx.set_line_width(5)
            ctx.stroke_preserve()
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

    def draw(self, ctx, t, frame):
        # sons et allumages au moment exact des impacts
        while self.played < len(self.hits) and self.hits[self.played][0] <= t:
            th, midi, s, last = self.hits[self.played]
            f = _freq(midi)
            self.audio.add(th, bell(f, dur=1.8, decay=0.7), gain=0.32)
            self.audio.add(th, marimba(f, 0.9), gain=0.38)
            self.lit[self.played] = 1.0
            self.played += 1
        while self.revealed < self.n and t >= self.song_end[self.revealed] + 0.4:
            self.revealed += 1
            self.audio.add(t, bell(_freq(84), dur=1.2, decay=0.3), gain=0.12)
        if self.played == len(self.hits) and t > self.hits[-1][0] + 1.2:
            self.done = True
        self.lit = np.maximum(self.lit * 0.985, np.where(self.lit > 0, 0.45, 0))

        bx, by = self._ball(t)
        self.cam += (np.array([bx, by]) - self.cam) * 0.12
        self.spin += 0.12

        # fond : gris sombre avec vignettage
        if self.bg is None:
            self.bg = cairo.ImageSurface(cairo.FORMAT_RGB24, W, 1920)
            bc = cairo.Context(self.bg)
            g = cairo.RadialGradient(W / 2, 1100, 100, W / 2, 1100, 1300)
            g.add_color_stop_rgb(0, 0.26, 0.26, 0.29)
            g.add_color_stop_rgb(1, 0.05, 0.05, 0.06)
            bc.set_source(g)
            bc.paint()
        ctx.set_source_surface(self.bg, 0, 0)
        ctx.paint()

        # tubes visibles (de l'arrière vers l'avant) et rails
        k_now = max(0, bisect.bisect_right(self.times, t) - 1)
        lo, hi = max(0, k_now - 14), min(len(self.points), k_now + 18)
        for k in range(lo, hi):
            if self.kinds[k] == "rail" and k + 1 < len(self.points):
                self._rail(ctx, self.points[k], self.points[k + 1])
        for k in range(lo, hi):
            x, y = self.points[k]
            self._tube(ctx, x, y, self.hits[k][1], self.lit[k])

        # ombre de la bille sur le tube visé
        k_next = min(len(self.points) - 1, bisect.bisect_right(self.times, t))
        tx, ty = self.points[k_next]
        sx, sy = self._screen(tx, ty)
        h = max(0.0, ty - by)
        a = 0.4 / (1 + h / 150)
        ctx.set_source_rgba(0, 0, 0, a)
        ctx.save()
        ctx.translate(sx, sy)
        ctx.scale(28, 11)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.fill()
        mx, my = self._screen(bx, by)
        self._marble(ctx, mx, my - 30)

        self._panel(ctx, t)
        if self.done:
            text(ctx, "Tu les avais toutes ?", W / 2, 1750, 70, (1, 0.85, 0.3))
