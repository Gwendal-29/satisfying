"""Les différents types de vidéos satisfaisantes.

Chaque scène est construite pour retenir le spectateur jusqu'au bout : une accroche en
haut, un compteur qui évolue, une tension qui monte et une fin marquée (remplissage,
réalignement, explosion) qui donne envie de revoir la boucle.
"""
import math

import cairo
import numpy as np

from .core import (FPS, H, W, Scene, background, beep, bell, circle, glow, hook, hsv,
                   marimba, note_freq, pop, ring, shatter, text, tick)

CX, CY = W / 2, 1080
TAU = 2 * math.pi


def _fade(ctx, amount):
    """Estompe une surface persistante (traînées).

    Arrondi vers le bas en numpy : avec DEST_OUT de cairo, les pixels très pâles ne
    tombent jamais à zéro et laissent un voile gris.
    """
    surface = ctx.get_target()
    surface.flush()
    px = np.ndarray((H, W, 4), np.uint8, surface.get_data())
    k = int(256 * (1 - amount))
    px[:] = (px.astype(np.uint16) * k) >> 8
    surface.mark_dirty()


def _layer():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    return s, cairo.Context(s)


def _final_chord(audio, t, base=0):
    for i, step in enumerate((0, 2, 4, 5, 7)):
        audio.add(t + i * 0.03, bell(note_freq(base + step), dur=3.0, decay=1.2), gain=0.5)


# ------------------------------------------------------------------ 1. balle qui grandit

class GrowingBall(Scene):
    title = "Chaque rebond, elle grandit"
    caption = "Elle finit par remplir le cercle... attends la fin"
    tags = ["#satisfying", "#oddlysatisfying", "#asmr", "#physics", "#pourtoi"]
    R, R0, G, SUB = 440.0, 22.0, 1800.0, 4

    def __init__(self, rng):
        super().__init__(rng)
        self.hue0 = rng.random()
        self.seed = int(rng.integers(1 << 30))
        target = rng.uniform(28, 40)
        # Calibre la croissance pour que le cercle soit rempli au bout de `target` secondes.
        lo, hi = 0.3, 40.0
        for _ in range(22):
            mid = (lo + hi) / 2
            if self._simulate(mid) > target:
                lo = mid
            else:
                hi = mid
        self.dr = (lo + hi) / 2
        self._reset()
        self.trail, self.tctx = _layer()
        self.flash = 0.0
        self.end_t = None

    def _reset(self):
        self.prng = np.random.default_rng(self.seed)
        a = self.prng.uniform(0, TAU)
        self.x, self.y = 0.0, -150.0
        self.vx, self.vy = 950 * math.cos(a), 950 * math.sin(a)
        self.r, self.bounces = self.R0, 0

    def _physics(self, dt, dr):
        self.vy += self.G * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        d = math.hypot(self.x, self.y) or 1e-9
        lim = self.R - self.r
        if d <= lim:
            return None
        nx, ny = self.x / d, self.y / d
        dot = self.vx * nx + self.vy * ny
        if dot > 0:
            self.vx -= 2 * dot * nx
            self.vy -= 2 * dot * ny
        self.x, self.y = nx * lim, ny * lim
        a = self.prng.normal(0, 0.06)
        c, s = math.cos(a), math.sin(a)
        self.vx, self.vy = self.vx * c - self.vy * s, self.vx * s + self.vy * c
        sp = math.hypot(self.vx, self.vy)
        k = min(max(sp, 1000), 1700) / sp
        self.vx, self.vy = self.vx * k, self.vy * k
        self.r = min(self.R, self.r + dr)
        self.bounces += 1
        return nx

    def _simulate(self, dr):
        self._reset()
        dt, t = 1 / (FPS * self.SUB), 0.0
        while self.r < self.R - 3 and t < 90:
            self._physics(dt, dr)
            t += dt
        return t

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * self.SUB)
        if not self.done:
            for sub in range(self.SUB):
                nx = self._physics(dt, self.dr)
                if nx is not None:
                    step = self.bounces % 15
                    self.audio.add(t + sub * dt, bell(note_freq(step)), gain=0.55, pan=nx * 0.6)
                    self.flash = 1.0
                if self.r >= self.R - 3:
                    self.done, self.end_t = True, t
                    self.r, self.x, self.y = self.R, 0.0, 0.0
                    _final_chord(self.audio, t)
                    break
        hue = self.hue0 + self.bounces * 0.025
        col = hsv(hue)

        background(ctx)
        _fade(self.tctx, 0.07)
        ring(self.tctx, CX + self.x, CY + self.y, self.r, col, 4, 0.9)
        ctx.set_source_surface(self.trail)
        ctx.paint()

        ring(ctx, CX, CY, self.R + 6, (1, 1, 1), 8, 0.9)
        glow(ctx, CX, CY, self.R, col, 0.06 + 0.15 * self.flash, 1.15)
        circle(ctx, CX + self.x, CY + self.y, self.r, col)
        ring(ctx, CX + self.x, CY + self.y, self.r, (1, 1, 1), 3, 0.8)
        self.flash *= 0.85

        hook(ctx, self.title, "Attends la fin...", t)
        pct = int(100 * (self.r - self.R0) / (self.R - self.R0))
        text(ctx, f"{pct} %", W / 2, 560, 64, col)
        text(ctx, f"Rebonds : {self.bounces}", W / 2, 1640, 52)
        if self.end_t is not None:
            a = max(0.0, 1 - (t - self.end_t) / 0.8)
            ctx.set_source_rgba(1, 1, 1, a * 0.8)
            ctx.paint()


# ------------------------------------------------------------------ 2. s'échapper des anneaux

class EscapeRings(Scene):
    caption = "Chaque anneau a une seule sortie..."
    tags = ["#satisfying", "#oddlysatisfying", "#asmr", "#simulation", "#pourtoi"]
    BR, SUB = 14.0, 4

    def __init__(self, rng):
        super().__init__(rng)
        self.n = int(rng.integers(8, 18))
        self.radii = np.linspace(110, 470, self.n)
        spin = rng.uniform(0.4, 0.8)
        alternate = rng.random() < 0.6
        self.speed = [(spin + 0.07 * i) * (1 if i % 2 or not alternate else -1) for i in range(self.n)]
        self.phase = rng.uniform(0, TAU, self.n) if rng.random() < 0.7 else np.full(self.n, rng.uniform(0, TAU))
        self.G = rng.uniform(1100, 1800)
        self.gap0 = rng.uniform(0.4, 0.7)
        self.hue0 = rng.random()
        self.k = 0
        nb = int(rng.choice([1, 1, 2, 3]))
        self.balls = []
        for j in range(nb):
            a = rng.uniform(0, TAU)
            col = (1, 1, 1) if nb == 1 else hsv(self.hue0 + 0.5 + j / nb, 0.5)
            self.balls.append([0.0, 0.0, 800 * math.cos(a), 800 * math.sin(a), col])
        self.title = "Va-t-elle s'échapper ?" if nb == 1 else "Vont-elles s'échapper ?"
        self.subtitle = f"{self.n} anneaux, {nb} balle{'s' if nb > 1 else ''}"
        self.parts = []
        self.hits = 0
        self.trail, self.tctx = _layer()
        self.shake = 0.0

    def gap(self, t):
        # La sortie s'élargit avec le temps : la vidéo finit toujours.
        return self.gap0 + max(0.0, t - 15) * 0.07

    def _step(self, b, t, dt):
        b[3] += self.G * dt
        b[0] += b[2] * dt
        b[1] += b[3] * dt
        if self.k >= self.n:
            return
        R = self.radii[self.k]
        d = math.hypot(b[0], b[1]) or 1e-9
        if d + self.BR < R:
            return
        rot = self.phase[self.k] + self.speed[self.k] * t
        local = (math.atan2(b[1], b[0]) - rot) % TAU
        if local < self.gap(t):
            self._destroy(t)
            return
        nx, ny = b[0] / d, b[1] / d
        dot = b[2] * nx + b[3] * ny
        if dot > 0:
            b[2] -= 2 * dot * nx
            b[3] -= 2 * dot * ny
        b[0], b[1] = nx * (R - self.BR), ny * (R - self.BR)
        a = self.rng.normal(0, 0.1)
        c, s = math.cos(a), math.sin(a)
        b[2], b[3] = b[2] * c - b[3] * s, b[2] * s + b[3] * c
        sp = math.hypot(b[2], b[3])
        k = min(max(sp, 750), 1300) / sp
        b[2], b[3] = b[2] * k, b[3] * k
        self.hits += 1
        self.audio.add(t, marimba(note_freq(self.hits % 10 + 5)), gain=0.5 / len(self.balls) ** 0.5, pan=nx * 0.6)

    def _destroy(self, t):
        R, i = self.radii[self.k], self.k
        col = hsv(self.hue0 + i / self.n)
        for a in self.rng.uniform(0, TAU, 70):
            sp = self.rng.uniform(150, 700)
            self.parts.append([CX + R * math.cos(a), CY + R * math.sin(a),
                               sp * math.cos(a), sp * math.sin(a), 1.0, col])
        self.audio.add(t, shatter(self.rng), gain=0.6)
        self.audio.add(t, bell(note_freq(i + 7), dur=1.5), gain=0.5)
        self.shake = 1.0
        self.k += 1
        if self.k >= self.n:
            self.done = True
            _final_chord(self.audio, t + 0.1, base=5)

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * self.SUB)
        for sub in range(self.SUB):
            for b in self.balls:
                self._step(b, t + sub * dt, dt)
        for p in self.parts:
            p[3] += 900 / FPS
            p[0] += p[2] / FPS
            p[1] += p[3] / FPS
            p[4] -= 1 / (FPS * 1.2)
        self.parts = [p for p in self.parts if p[4] > 0 and p[1] < H + 50]

        background(ctx)
        sx, sy = self.rng.normal(0, 12 * self.shake, 2)
        self.shake *= 0.85
        ctx.translate(sx, sy)
        g = self.gap(t)
        for i in range(self.k, self.n):
            rot = self.phase[i] + self.speed[i] * t
            col = hsv(self.hue0 + i / self.n)
            ring(ctx, CX, CY, self.radii[i], col, 9, 1.0, rot + g, rot + TAU)
        for x, y, _, _, life, col in self.parts:
            circle(ctx, x, y, 5 * life + 1, col, life)

        _fade(self.tctx, 0.12)
        for x, y, _, _, col in self.balls:
            circle(self.tctx, CX + x, CY + y, self.BR * 0.8, col, 0.5)
        ctx.set_source_surface(self.trail)
        ctx.paint()
        for x, y, _, _, col in self.balls:
            glow(ctx, CX + x, CY + y, self.BR, col, 0.5)
            circle(ctx, CX + x, CY + y, self.BR, col)
        ctx.identity_matrix()

        hook(ctx, self.title, self.subtitle, t)
        left = self.n - self.k
        text(ctx, "LIBRE !" if left == 0 else f"Anneaux restants : {left}", W / 2, 1640, 56,
             (0.4, 1, 0.5) if left == 0 else (1, 1, 1))


# ------------------------------------------------------------------ 3. polyrythmie

class Polyrhythm(Scene):
    title = "Tout se réaligne à la fin"
    caption = "Chaque point joue sa note... écoute jusqu'au bout"
    tags = ["#satisfying", "#polyrhythm", "#asmr", "#music", "#pourtoi"]
    outro = 2.5

    def __init__(self, rng):
        super().__init__(rng)
        self.N = 16
        self.T = float(rng.choice([30, 35, 40]))
        top = int(rng.integers(22, 27))
        self.freq = [(top - i) / self.T for i in range(self.N)]  # aller-retours par seconde
        self.radii = np.linspace(470, 70, self.N)
        self.flash = np.zeros(self.N)
        self.hue0 = rng.random()
        self.cy = 1250
        self.trail, self.tctx = _layer()
        self.sound = rng.choice(["bell", "marimba"])

    def draw(self, ctx, t, frame):
        t0 = (frame - 1) / FPS
        for i, f in enumerate(self.freq):
            if t > self.T + 0.01:
                break
            m0, m1 = math.floor(2 * f * t0), math.floor(2 * f * t)
            for m in range(m0 + 1, m1 + 1):
                th = m / (2 * f)
                sig = bell(note_freq(i, 196.0)) if self.sound == "bell" else marimba(note_freq(i, 196.0))
                self.audio.add(th, sig, gain=0.35, pan=-0.7 if m % 2 == 0 else 0.7)
                self.flash[i] = 1.0
        if t >= self.T and not self.done:
            self.done = True
            _final_chord(self.audio, self.T + 0.05)

        background(ctx)
        ctx.set_source_rgba(1, 1, 1, 0.5)
        ctx.set_line_width(4)
        ctx.move_to(CX - 500, self.cy)
        ctx.line_to(CX + 500, self.cy)
        ctx.stroke()

        _fade(self.tctx, 0.15)
        tt = min(t, self.T)
        for i, (f, R) in enumerate(zip(self.freq, self.radii)):
            col = hsv(self.hue0 + i / self.N * 0.8)
            fl = self.flash[i]
            ring(ctx, CX, self.cy, R, col, 4 + 4 * fl, 0.35 + 0.65 * fl, math.pi, TAU)
            u = (f * tt) % 1.0
            th = math.pi * (1 - abs(1 - 2 * u))
            x, y = CX + R * math.cos(math.pi + th), self.cy + R * math.sin(math.pi + th)
            circle(self.tctx, x, y, 9, col, 0.6)
            glow(ctx, x, y, 12, col, 0.4 + 0.5 * fl)
            circle(ctx, x, y, 12, (1, 1, 1))
        ctx.set_source_surface(self.trail)
        ctx.paint()
        self.flash *= 0.9

        hook(ctx, self.title, "Écoute bien...", t)
        rest = max(0.0, self.T - t)
        if rest > 0:
            text(ctx, f"Réalignement dans {rest:0.1f} s", W / 2, 1450, 52)
        else:
            text(ctx, "Réalignés !", W / 2, 1450, 72, (0.4, 1, 0.5))


# ------------------------------------------------------------------ 4. algorithmes de tri

def _quick(a, ops, lo=0, hi=None):
    hi = len(a) - 1 if hi is None else hi
    while lo < hi:
        p = a[(lo + hi) // 2]
        i, j = lo, hi
        while i <= j:
            while a[i] < p:
                i += 1
            while a[j] > p:
                j -= 1
            if i <= j:
                a[i], a[j] = a[j], a[i]
                ops.append(("swap", i, j))
                i, j = i + 1, j - 1
        if j - lo < hi - i:
            _quick(a, ops, lo, j)
            lo = i
        else:
            _quick(a, ops, i, hi)
            hi = j


def _merge(a, ops, lo=0, hi=None):
    hi = len(a) if hi is None else hi
    if hi - lo < 2:
        return
    mid = (lo + hi) // 2
    _merge(a, ops, lo, mid)
    _merge(a, ops, mid, hi)
    merged, i, j = [], lo, mid
    while i < mid and j < hi:
        if a[i] <= a[j]:
            merged.append(a[i]); i += 1
        else:
            merged.append(a[j]); j += 1
    merged += a[i:mid] + a[j:hi]
    for k, v in enumerate(merged):
        a[lo + k] = v
        ops.append(("set", lo + k, v))


def _heap(a, ops):
    n = len(a)

    def sift(i, n):
        while 2 * i + 1 < n:
            c = 2 * i + 1
            if c + 1 < n and a[c + 1] > a[c]:
                c += 1
            if a[i] >= a[c]:
                return
            a[i], a[c] = a[c], a[i]
            ops.append(("swap", i, c))
            i = c

    for i in range(n // 2 - 1, -1, -1):
        sift(i, n)
    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        ops.append(("swap", 0, end))
        sift(0, end)


def _shell(a, ops):
    gap = len(a) // 2
    while gap:
        for i in range(gap, len(a)):
            j = i
            while j >= gap and a[j - gap] > a[j]:
                a[j - gap], a[j] = a[j], a[j - gap]
                ops.append(("swap", j - gap, j))
                j -= gap
        gap //= 2


def _radix(a, ops, base=4):
    m = 1
    while m <= max(a):
        buckets = [[] for _ in range(base)]
        for v in a:
            buckets[(v // m) % base].append(v)
        flat = [v for b in buckets for v in b]
        for k, v in enumerate(flat):
            a[k] = v
            ops.append(("set", k, v))
        m *= base


def _cocktail(a, ops):
    lo, hi, swapped = 0, len(a) - 1, True
    while swapped:
        swapped = False
        for i in range(lo, hi):
            if a[i] > a[i + 1]:
                a[i], a[i + 1] = a[i + 1], a[i]
                ops.append(("swap", i, i + 1)); swapped = True
        hi -= 1
        for i in range(hi, lo, -1):
            if a[i - 1] > a[i]:
                a[i - 1], a[i] = a[i], a[i - 1]
                ops.append(("swap", i - 1, i)); swapped = True
        lo += 1


SORTS = {
    "rapide": (_quick, 60), "fusion": (_merge, 100), "par tas": (_heap, 100),
    "de Shell": (_shell, 100), "radix": (_radix, 100), "cocktail": (_cocktail, 50),
}


class Sorting(Scene):
    caption = "Le son d'un algorithme qui trie... hypnotisant"
    tags = ["#satisfying", "#coding", "#algorithm", "#asmr", "#pourtoi"]

    def __init__(self, rng):
        super().__init__(rng)
        self.algo = str(rng.choice(list(SORTS)))
        fn, n = SORTS[self.algo]
        self.n = n
        self.title = f"Le son du tri {self.algo}"
        self.a = list(range(1, n + 1))
        self.hue0 = rng.random()
        shuffle_ops, b = [], list(self.a)
        for i in range(n - 1, 0, -1):
            j = int(rng.integers(0, i + 1))
            b[i], b[j] = b[j], b[i]
            shuffle_ops.append(("swap", i, j))
        sort_ops = []
        fn(list(b), sort_ops)
        sweep = [("green", i) for i in range(n)]
        dur = min(28.0, max(14.0, len(sort_ops) / 60))
        self.segments = []
        start = 0.8
        for ops, d in ((shuffle_ops, 1.5), ([], 0.6), (sort_ops, dur), (sweep, 1.8)):
            self.segments.append((start, d, ops, [0]))
            start += d
        self.end = start
        self.green = 0
        self.touched = set()

    def _apply(self, op):
        if op[0] == "swap":
            _, i, j = op
            self.a[i], self.a[j] = self.a[j], self.a[i]
            self.touched.update((i, j))
            return self.a[j]
        if op[0] == "set":
            _, i, v = op
            self.a[i] = v
            self.touched.add(i)
            return v
        self.green = op[1] + 1
        self.touched.add(op[1])
        return self.a[op[1]]

    def draw(self, ctx, t, frame):
        self.touched = set()
        last = None
        for start, d, ops, done in self.segments:
            if not ops or t < start:
                continue
            target = min(len(ops), int(len(ops) * (t - start) / d) + 1)
            while done[0] < target:
                last = self._apply(ops[done[0]])
                done[0] += 1
        if last is not None:
            self.audio.add(t, beep(180 + 1100 * last / self.n, dur=0.07), gain=0.6)
        if t >= self.end and not self.done:
            self.done = True
            _final_chord(self.audio, t)

        background(ctx)
        x0, x1, base, top = 40, W - 40, 1560, 640
        bw = (x1 - x0) / self.n
        for i, v in enumerate(self.a):
            h = (base - top) * v / self.n
            if i in self.touched:
                col = (1, 1, 1)
            elif i < self.green:
                col = (0.3, 1, 0.45)
            else:
                col = hsv(self.hue0 + v / self.n * 0.8)
            ctx.set_source_rgb(*col)
            ctx.rectangle(x0 + i * bw, base - h, bw - max(1, bw * 0.15), h)
            ctx.fill()

        hook(ctx, self.title, f"{self.n} barres mélangées", t)
        if self.done:
            text(ctx, "Trié !", W / 2, 1680, 64, (0.3, 1, 0.45))


# ------------------------------------------------------------------ 5. vague de pendules

class PendulumWave(Scene):
    title = "Regarde le motif changer"
    caption = "Des pendules de longueurs différentes... et ils se retrouvent"
    tags = ["#satisfying", "#physics", "#pendulum", "#asmr", "#pourtoi"]
    outro = 2.0

    def __init__(self, rng):
        super().__init__(rng)
        self.N = 18
        self.T = float(rng.choice([30, 36, 40]))
        n0 = int(self.T * rng.uniform(0.45, 0.6))
        self.counts = [n0 + k for k in range(self.N)]
        self.ys = np.linspace(650, 1500, self.N)
        self.A = 430
        self.hue0 = rng.random()
        self.trail, self.tctx = _layer()
        self.flash = np.zeros(self.N)

    def draw(self, ctx, t, frame):
        t0 = (frame - 1) / FPS
        if t <= self.T + 0.01:
            for k, c in enumerate(self.counts):
                f = c / self.T
                for m in range(math.floor(f * t0) + 1, math.floor(f * t) + 1):
                    self.audio.add(m / f, bell(note_freq(k, 130.81), dur=1.0), gain=0.3, pan=0.6)
                    self.flash[k] = 1.0
        if t >= self.T and not self.done:
            self.done = True
            _final_chord(self.audio, self.T + 0.05)

        background(ctx)
        _fade(self.tctx, 0.1)
        tt = min(t, self.T)
        for k, (c, y) in enumerate(zip(self.counts, self.ys)):
            col = hsv(self.hue0 + k / self.N * 0.8)
            x = CX + self.A * math.cos(TAU * c * tt / self.T)
            ctx.set_source_rgba(1, 1, 1, 0.08)
            ctx.set_line_width(2)
            ctx.move_to(CX - self.A, y)
            ctx.line_to(CX + self.A, y)
            ctx.stroke()
            circle(self.tctx, x, y, 14, col, 0.7)
            glow(ctx, x, y, 18, col, 0.3 + 0.5 * self.flash[k])
            circle(ctx, x, y, 18, col)
        ctx.set_source_surface(self.trail)
        ctx.paint()
        self.flash *= 0.88

        hook(ctx, self.title, f"{self.N} pendules", t)
        rest = max(0.0, self.T - t)
        text(ctx, f"Réalignement dans {rest:0.1f} s" if rest else "Réalignés !", W / 2, 1650, 52,
             (1, 1, 1) if rest else (0.4, 1, 0.5))


# ------------------------------------------------------------------ 6. planche de Galton

class Galton(Scene):
    title = "Toujours la même forme..."
    caption = "Des billes au hasard... et pourtant une courbe parfaite"
    tags = ["#satisfying", "#maths", "#science", "#asmr", "#pourtoi"]
    outro = 2.5
    ROWS, SP, BR, HOP = 13, 62, 7.0, 0.085

    def __init__(self, rng):
        super().__init__(rng)
        self.n = 360
        self.rate = 14.0
        self.top = 560
        self.dy = self.SP * 0.87
        self.floor = 1580
        self.paths = [np.concatenate([[0], np.cumsum(rng.integers(0, 2, self.ROWS))]) for _ in range(self.n)]
        self.landed = 0
        self.stack = [0] * (self.ROWS + 1)
        self.slots = {}
        self.static, self.sctx = _layer()
        self.peg_flash = {}
        self.hue0 = rng.random()

    def peg(self, j, m):
        return CX + (m - j / 2) * self.SP, self.top + j * self.dy

    def bin_x(self, b):
        return CX + (b - self.ROWS / 2) * self.SP

    def _slot(self, i):
        if i not in self.slots:
            b = int(self.paths[i][-1])
            s = self.stack[b]
            self.stack[b] += 1
            layer, col = divmod(s, 4)
            x = self.bin_x(b) + (col - 1.5) * self.BR * 2
            self.slots[i] = (x, self.floor - self.BR - layer * self.BR * 1.9)
        return self.slots[i]

    def draw(self, ctx, t, frame):
        background(ctx)
        hits, lands = [], []
        travel = (self.ROWS + 1) * self.HOP
        for b in range(self.ROWS + 2):
            x = CX + (b - (self.ROWS + 1) / 2) * self.SP
            ctx.set_source_rgba(1, 1, 1, 0.25)
            ctx.set_line_width(3)
            ctx.move_to(x, self.top + self.ROWS * self.dy)
            ctx.line_to(x, self.floor)
            ctx.stroke()
        for j in range(self.ROWS):
            for m in range(j + 1):
                x, y = self.peg(j, m)
                fl = self.peg_flash.get((j, m), 0.0)
                circle(ctx, x, y, 6 + 3 * fl, (1, 1, 1), 0.5 + 0.5 * fl)
        self.peg_flash = {k: v * 0.8 for k, v in self.peg_flash.items() if v > 0.05}

        ctx.set_source_surface(self.static)
        ctx.paint()

        spawned = min(self.n, int(t * self.rate) + 1)
        for i in range(self.landed, spawned):
            tau = t - i / self.rate
            path = self.paths[i]
            col = hsv(self.hue0 + path[-1] / self.ROWS * 0.8)
            if tau < travel - self.HOP:
                j = int(tau / self.HOP)
                u = tau / self.HOP - j
                if j == 0:
                    x0, y0 = CX, self.top - 80
                else:
                    x0, y0 = self.peg(j - 1, path[j - 1])
                x1, y1 = self.peg(j, path[j])
                x = x0 + (x1 - x0) * u
                y = y0 + (y1 - y0) * u - 22 * 4 * u * (1 - u) - self.BR - 6
                if int((tau - 1 / FPS) / self.HOP) != j or tau < 1 / FPS:
                    hits.append((j, path[j], x))
                circle(ctx, x, y, self.BR, col)
            else:
                sx, sy = self._slot(i)
                fall = tau - (travel - self.HOP)
                x0, y0 = self.peg(self.ROWS - 1, path[self.ROWS - 1])
                u = min(1.0, fall / 0.35)
                x = x0 + (sx - x0) * min(1.0, u * 2)
                y = y0 + (sy - y0) * u * u
                if u >= 1.0:
                    # Toutes les billes ont le même trajet en durée : elles atterrissent dans l'ordre.
                    circle(self.sctx, sx, sy, self.BR, col)
                    self.landed = i + 1
                    lands.append(sx)
                else:
                    circle(ctx, x, y, self.BR, col)

        for j, m, x in hits:
            self.peg_flash[(j, m)] = 1.0
        for j, m, x in hits[:2]:
            self.audio.add(t, marimba(note_freq(12 - j % 10, 523.25)), gain=0.12, pan=(x - CX) / 500)
        for x in lands[:2]:
            self.audio.add(t, pop(300 + self.rng.uniform(0, 200)), gain=0.25, pan=(x - CX) / 500)

        if self.landed >= self.n and not self.done:
            self.done, self.end_t = True, t
            _final_chord(self.audio, t)
        if self.done:
            self._curve(ctx, min(1.0, (t - self.end_t) / 1.2))

        hook(ctx, self.title, "Regarde la courbe apparaître", t)
        text(ctx, f"Billes : {min(self.landed, self.n)} / {self.n}", W / 2, 1700, 50)

    def _curve(self, ctx, progress):
        mu, sigma = self.ROWS / 2, math.sqrt(self.ROWS) / 2
        peak = self.n / (sigma * math.sqrt(TAU))
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(6)
        steps = int(200 * progress)
        for s in range(steps + 1):
            b = -0.5 + (self.ROWS + 1) * s / 200
            h = peak * math.exp(-((b - mu) ** 2) / (2 * sigma ** 2))
            y = self.floor - h / 4 * self.BR * 1.9
            x = self.bin_x(b)
            (ctx.move_to if s == 0 else ctx.line_to)(x, y)
        ctx.stroke()


# ------------------------------------------------------------------ 7. balles qui se multiplient

class Multiply(Scene):
    title = "Elles se multiplient..."
    caption = "Devine combien il y en a à la fin"
    tags = ["#satisfying", "#oddlysatisfying", "#simulation", "#asmr", "#pourtoi"]
    R, BR, G, CAP = 450.0, 9.0, 1400.0, 1000
    outro = 2.0

    def __init__(self, rng):
        super().__init__(rng)
        a = rng.uniform(0, TAU)
        self.p = np.array([[0.0, -100.0]])
        self.v = np.array([[900 * math.cos(a), 900 * math.sin(a)]])
        self.hue = np.array([rng.random()])
        self.chance = 0.12

    def _step(self, dt):
        self.v[:, 1] += self.G * dt
        self.p += self.v * dt
        d = np.hypot(self.p[:, 0], self.p[:, 1])
        hit = d > self.R - self.BR
        if not hit.any():
            return 0, None
        n = self.p[hit] / d[hit, None]
        dot = np.einsum("ij,ij->i", self.v[hit], n)
        v = self.v[hit] - 2 * np.maximum(dot, 0)[:, None] * n
        sp = np.hypot(v[:, 0], v[:, 1])
        v *= (np.clip(sp, 900, 1400) / sp)[:, None]
        self.v[hit] = v
        self.p[hit] = n * (self.R - self.BR)
        count = int(hit.sum())
        if not self.done:
            spawn = hit.copy()
            # Démarrage rapide (il faut de l'action dès les premières secondes), puis croissance régulière.
            chance = 1.0 if len(self.p) < 6 else 0.45 if len(self.p) < 40 else self.chance
            spawn[hit] = self.rng.random(count) < chance
            k = int(spawn.sum())
            if k:
                k = min(k, self.CAP - len(self.p))
                idx = np.flatnonzero(spawn)[:k]
                ang = self.rng.normal(0, 0.4, k)
                c, s = np.cos(ang), np.sin(ang)
                vv = self.v[idx]
                nv = np.stack([vv[:, 0] * c - vv[:, 1] * s, vv[:, 0] * s + vv[:, 1] * c], axis=1)
                self.p = np.vstack([self.p, self.p[idx]])
                self.v = np.vstack([self.v, nv])
                self.hue = np.concatenate([self.hue, self.hue[idx] + 0.03])
                if len(self.p) >= self.CAP:
                    self.done = True
        return count, n[:, 0]

    def draw(self, ctx, t, frame):
        was_done = self.done
        sounds = []
        for sub in range(2):
            c, pans = self._step(1 / (FPS * 2))
            if c:
                sounds += list(pans[:2])
        n = len(self.p)
        for pan in sounds[:3]:
            self.audio.add(t, pop(note_freq(int(self.rng.integers(5, 15)))), gain=0.5 / (1 + n / 150), pan=pan * 0.6)
        if self.done and not was_done:
            self.end_t = t
            _final_chord(self.audio, t)

        background(ctx)
        ring(ctx, CX, CY, self.R + 5, (1, 1, 1), 8, 0.9)
        for (x, y), h in zip(self.p, self.hue):
            circle(ctx, CX + x, CY + y, self.BR, hsv(h))
        hook(ctx, self.title, "Devine le total final", t)
        text(ctx, f"{n}", W / 2, 560, 90, (1, 0.85, 0.3))
        if self.done:
            text(ctx, "MAX !", W / 2, 1650, 72, (0.4, 1, 0.5))


from .illusions import InfiniteCube, InfiniteSpiral  # noqa: E402

SCENES = [GrowingBall, EscapeRings, Polyrhythm, Sorting, PendulumWave, Galton, Multiply,
          InfiniteCube, InfiniteSpiral]
