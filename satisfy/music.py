"""Vidéos « musique connue » (mélodies du domaine public, arrangées en synthé + basse + batterie).

SongBounce : une bille file en diagonale et creuse son chemin dans la roche ; elle rebondit
             pile sur chaque note de la mélodie. Le nom du morceau se dévoile en cours de route.
SongRing   : des billes dans un anneau arc-en-ciel. La musique n'avance QUE quand une bille
             touche l'anneau : au début elle est hachée, puis le jeton « x2 » multiplie les
             billes et le morceau finit par jouer en entier, sans coupure.
"""
import bisect
import math

import cairo
import numpy as np

from .core import SR, W, Scene, hsv, text
from .physics import wall_circle
from .songs import SONGS, render_track, song_beats

TAU = 2 * math.pi


def _pick_songs(rng, seconds, beat, gap_beats):
    """Mélodies au hasard jusqu'à remplir `seconds` ; la dernière est raccourcie si besoin."""
    names = [str(n) for n in rng.permutation(list(SONGS))]
    picked, total, cut = [], 0.0, None
    for name in names:
        d = (song_beats(name) + gap_beats) * beat
        if total + d <= seconds:
            picked.append(name)
            total += d
    left = seconds - total
    if left > 4 or not picked:
        # on complète avec le début d'une autre mélodie (toujours reconnaissable)
        for name in names:
            if name in picked:
                continue
            notes, acc = 0, gap_beats * beat
            for _, b in SONGS[name]:
                if acc + b * beat > left:
                    break
                acc += b * beat
                notes += 1
            if notes >= 6:
                return picked, name, notes
    return picked, None, cut


def _track(rng, seconds, beat, gap_beats):
    picked, extra, n_extra = _pick_songs(rng, seconds, beat, gap_beats)
    track, notes, sections = render_track(picked, beat, rng, gap_beats)
    if extra:
        t2, n2, s2 = render_track([extra], beat, rng, gap_beats, cut=n_extra)
        off = sections[-1][1] + gap_beats * beat if sections else 0.0
        i = int(off * SR)
        full = np.zeros(max(len(track), i + len(t2)))
        full[:len(track)] += track
        full[i:i + len(t2)] += t2
        track = full
        ns = len(sections)
        notes += [(t + off, m, s + ns, last) for t, m, s, last in n2]
        sections += [(a + off, b + off, nm) for a, b, nm in s2]
    return track, notes, sections


# ====================================================================== SongBounce

class SongBounce(Scene):
    """La bille rebondit sur chaque note : on « voit » la mélodie."""
    tags = ["#satisfying", "#music", "#musique", "#bouncingball", "#pourtoi"]
    lengths = ("court", "moyen", "normal", "long")
    outro = 2.0
    bed_freqs = ()   # pas de nappe : la musique suffit
    BR = 20          # rayon de la bille
    SPEED = 640.0    # px/s, constante : la distance entre deux rebonds = la durée de la note

    def __init__(self, rng):
        super().__init__(rng)
        self.beat = 60 / float(rng.choice([108, 116, 124]))
        self.t0 = 1.0
        limit = self.target(50) - self.t0 - 0.8
        self.track, self.notes, self.sections = _track(rng, limit, self.beat, 2)
        self.audio.add(self.t0, self.track, gain=0.9)
        self.n = len(self.sections)
        self.title = "Musiques que tu connais"
        self.caption = (f"{self.n} musiques que tout le monde connaît... tu les as toutes reconnues ?"
                        if self.n > 1 else "Une musique que tout le monde connaît... tu l'as reconnue ?")
        self.hue0 = rng.random()
        self.hues = [(self.hue0 + 0.37 * s) % 1 for s in range(self.n + 1)]
        self.max_duration = self.t0 + self.sections[-1][1] + 1.2 + self.outro
        self._build()
        self.played = 0
        self.flash = np.zeros(len(self.hits))
        self.parts = []  # étincelles : [x, y, vx, vy, r, né, teinte]
        self.cam = np.array(self.verts[0], float)

    def _build(self):
        """Sommets du trajet : un rebond par note, toujours à 45°, en zigzag vers le bas."""
        rng, v = self.rng, self.SPEED
        arcs = [v * (self.t0 + n[0]) for n in self.notes]
        P = np.array([0.0, 0.0])
        d = np.array([1.0, 1.0]) / math.sqrt(2)
        self.verts, self.arc = [P.copy()], [0.0]
        self.hits = []  # (instant, midi, mélodie, point de contact, normale du mur)
        prev = 0.0
        for k, (tn, midi, s, last) in enumerate(self.notes):
            P = P + d * (arcs[k] - prev)
            prev = arcs[k]
            nxt = (arcs[k + 1] - arcs[k]) if k + 1 < len(arcs) else 3 * v
            # rebond : mur vertical (on inverse x) ou horizontal (on inverse y)
            options = []
            for axis in (0, 1):
                nd = d.copy()
                nd[axis] = -nd[axis]
                end = P + nd * nxt
                score = abs(end[0]) / 900  # ne pas trop dériver sur le côté (la caméra suit)
                score += 0.0 if nd[1] > 0 else (0.6 if d[1] > 0 else 0.15)  # descendre surtout
                score += rng.random() * 0.5
                options.append((score, axis, nd))
            _, axis, nd = min(options, key=lambda o: o[0])
            normal = np.zeros(2)
            normal[axis] = -np.sign(d[axis])  # le mur est du côté où l'on allait
            self.hits.append((self.t0 + tn, midi, s, P.copy(), normal))
            d = nd
            self.verts.append(P.copy())
            self.arc.append(arcs[k])
        P = P + d * 4 * v
        self.verts.append(P)
        self.arc.append(prev + 4 * v)
        self.verts = np.array(self.verts)
        self.arc = np.array(self.arc)
        self.times = [h[0] for h in self.hits]

    def _pos(self, s):
        k = min(max(0, bisect.bisect_right(self.arc, s) - 1), len(self.arc) - 2)
        u = (s - self.arc[k]) / max(1e-9, self.arc[k + 1] - self.arc[k])
        return self.verts[k] + (self.verts[k + 1] - self.verts[k]) * u, k

    def _scr(self, x, y):
        return W / 2 + (x - self.cam[0]), 1050 + (y - self.cam[1])

    def draw(self, ctx, t, frame):
        s_ball = self.SPEED * t
        (bx, by), kseg = self._pos(s_ball)
        self.cam += (np.array([bx, by]) - self.cam) * 0.15
        while self.played < len(self.hits) and self.hits[self.played][0] <= t:
            th, midi, s, P, nrm = self.hits[self.played]
            self.flash[self.played] = 1.0
            hue = self.hues[s]
            for _ in range(9):
                a = math.atan2(nrm[1], nrm[0]) + self.rng.uniform(-1.2, 1.2)
                sp = self.rng.uniform(150, 520)
                self.parts.append([P[0] - nrm[0] * self.BR, P[1] - nrm[1] * self.BR,
                                   math.cos(a) * sp, math.sin(a) * sp, self.rng.uniform(5, 14), t, hue])
            self.played += 1
        if self.played == len(self.hits) and t > self.hits[-1][0] + 1.0:
            self.done = True
        self.flash *= 0.9

        # roche grise, puis les « salles » creusées par la bille (rectangles autour de chaque trajet)
        ctx.set_source_rgb(0.72, 0.72, 0.74)
        ctx.paint()
        pad = self.BR + 16
        ctx.set_source_rgb(0.04, 0.04, 0.06)
        for k in range(max(0, kseg - 220), kseg + 1):
            a = self.verts[k]
            b = self.verts[k + 1] if k < kseg else np.array([bx, by])
            x0, y0 = self._scr(min(a[0], b[0]), min(a[1], b[1]))
            x1, y1 = self._scr(max(a[0], b[0]), max(a[1], b[1]))
            if y1 + pad < -50 or y0 - pad > 1970:
                continue
            ctx.rectangle(x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
        ctx.fill()

        # marques de rebond sur les murs
        lo = max(0, self.played - 120)
        for k in range(lo, self.played):
            th, midi, s, P, nrm = self.hits[k]
            x, y = self._scr(P[0] - nrm[0] * (self.BR + 10), P[1] - nrm[1] * (self.BR + 10))
            if not -40 < y < 1960:
                continue
            f = self.flash[k]
            c = np.array(hsv(self.hues[s], 0.8, 1.0)) * (1 - f) + f
            w, h = (14, 30) if nrm[0] else (30, 14)
            ctx.set_source_rgb(*c)
            ctx.rectangle(x - w / 2, y - h / 2, w, h)
            ctx.fill()

        # étincelles
        alive = []
        for p in self.parts:
            age = t - p[5]
            if age > 0.9:
                continue
            alive.append(p)
            x = p[0] + p[2] * age
            y = p[1] + p[3] * age + 300 * age * age
            sx, sy = self._scr(x, y)
            ctx.set_source_rgba(*hsv(p[6], 0.75, 1.0), 1 - age / 0.9)
            ctx.arc(sx, sy, p[4] * (1 - age / 1.5), 0, TAU)
            ctx.fill()
        self.parts = alive[-300:]

        # traînée : anneaux espacés le long du chemin déjà parcouru
        cur = self.played - 1
        hue = self.hues[self.hits[cur][2]] if cur >= 0 else self.hues[0]
        n_tr = 46
        for j in range(n_tr, 0, -1):
            s = s_ball - j * self.BR * 1.5
            if s < 0:
                continue
            (x, y), _ = self._pos(s)
            sx, sy = self._scr(x, y)
            ctx.arc(sx, sy, self.BR * 0.95, 0, TAU)
            ctx.set_source_rgb(0.02, 0.02, 0.03)
            ctx.fill_preserve()
            ctx.set_source_rgba(*hsv(hue + j * 0.004, 0.8, 1.0), 1 - j / (n_tr + 6))
            ctx.set_line_width(4)
            ctx.stroke()
        sx, sy = self._scr(bx, by)
        ctx.arc(sx, sy, self.BR, 0, TAU)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()

        # titres : le nom de la mélodie se dévoile aux deux tiers
        text(ctx, self.title, W / 2, 230, 66)
        st = t - self.t0
        sec = max(0, min(self.n - 1, bisect.bisect_right([a for a, _, _ in self.sections], st) - 1))
        a, b, name = self.sections[sec]
        shown = name if st > a + (b - a) * 0.6 else "???"
        text(ctx, f"{sec + 1}/{self.n} : {shown}" if self.n > 1 else shown, W / 2, 305, 46, (1, 0.85, 0.3))
        if self.done:
            text(ctx, "Tu les as toutes reconnues ?" if self.n > 1 else "Tu l'as reconnue ?",
                 W / 2, 1650, 62, (1, 0.85, 0.3))


# ====================================================================== SongRing

class SongRing(Scene):
    """La musique ne joue que quand une bille touche l'anneau, puis finit par jouer en entier."""
    tags = ["#satisfying", "#music", "#musique", "#asmr", "#pourtoi"]
    lengths = ("court", "moyen", "normal", "long")
    outro = 2.5
    bed_freqs = ()   # pas de nappe : les coupures de la musique doivent s'entendre
    R = 330.0
    BR = 13.0
    SPEED = 820.0
    GATE = 0.07      # chaque contact fait jouer 0,07 s de musique
    CAP = 160
    CX, CY = W / 2, 1000

    def __init__(self, rng):
        super().__init__(rng)
        self.beat = 60 / float(rng.choice([112, 120, 128]))
        T = self.target(48)
        self.T = T
        self.track, notes, self.sections = _track(rng, T * 0.56, self.beat, 1)
        self.L = self.sections[-1][1] + 0.3
        self.n = len(self.sections)
        self.title = "Devine la musique"
        self.caption = "La musique ne joue que quand une bille touche l'anneau... tu l'as reconnue avant la fin ?"
        self.max_duration = T * 1.6 + 6
        a = rng.uniform(0, TAU)
        self.p = np.array([[math.cos(a) * 60, math.sin(a) * 60]])
        b = a + rng.uniform(-1, 1) + math.pi / 2
        self.v = np.array([[math.cos(b), math.sin(b)]]) * self.SPEED
        self.hue = np.array([rng.random()])
        self.tok = rng.uniform(0, TAU)       # angle du jeton x2
        self.rot = 0.0
        self.head = 0.0                       # position dans la piste (s)
        self.gate_end = -1.0
        self.seg_start = None
        self.seg_head = 0.0
        self.rate = 1.4                       # contacts / s / bille (estimé en continu)
        self.hits_total = 0
        self.sparks, self.dots = [], []
        self.revealed = 0

    # -- musique hachée ------------------------------------------------------------------
    def _emit(self, end):
        """Joue le morceau de piste correspondant au créneau [seg_start, end]."""
        dur = end - self.seg_start
        i0 = int(self.seg_head * SR)
        n = int(dur * SR)
        seg = self.track[i0:i0 + n].copy()
        if len(seg) > 8:
            f = min(len(seg) // 2, int(0.006 * SR))
            seg[:f] *= np.linspace(0, 1, f)
            seg[-f:] *= np.linspace(1, 0, f)
            self.audio.add(self.seg_start, seg, gain=0.9)

    def _hit(self, th):
        if th > self.gate_end:
            if self.seg_start is not None:
                self._emit(self.gate_end)
            self.seg_start, self.seg_head = th, self.head
        self.gate_end = max(self.gate_end, th + self.GATE)

    # -- simulation ----------------------------------------------------------------------
    def _need(self, t):
        """Billes nécessaires pour tenir le planning du morceau (fin à T)."""
        T, L = self.T, self.L
        x = min(t / T, 1.0)
        want = L * x ** 1.9
        rate = 1.9 * L * max(x, 0.02) ** 0.9 / T + (want - self.head) * 0.35
        rate = min(max(rate, 0.0), 0.985)
        return max(1.0, -math.log(1 - rate) / (self.rate * self.GATE))

    def step(self, t, dt):
        self.rot += dt * 0.9
        self.tok += dt * 1.25
        # la tête de lecture avance tant que la musique joue
        if t < self.gate_end:
            self.head += dt
        steps = 2
        h = dt / steps
        hit_angles = []
        for k in range(steps):
            self.p += self.v * h
            m = wall_circle(self.p, self.v, self.R, self.BR)
            if m.any():
                idx = np.nonzero(m)[0]
                for i in idx:
                    hit_angles.append((i, math.atan2(self.p[i, 1], self.p[i, 0]), t + k * h))
        need = self._need(t)
        n = len(self.p)
        lag = math.log2(need / n)
        width = float(np.clip(0.22 * 1.8 ** lag, 0.05, 1.6))
        self.tok_w = width
        new_p, new_v, new_h = [], [], []
        for i, ang, th in hit_angles:
            self._hit(th)
            self.hits_total += 1
            diff = abs((ang - self.tok + math.pi) % TAU - math.pi)
            if diff < width and n + len(new_p) < min(self.CAP, need * 1.3 + 1):
                c, s = math.cos(0.45), math.sin(0.45)
                vx, vy = self.v[i]
                new_p.append(self.p[i] * 0.97)
                new_v.append([vx * c - vy * s, vx * s + vy * c])
                new_h.append((self.hue[i] + 0.13) % 1)
                self._fx_double = (th, ang)
            yield_ = (i, ang, th)
            self._fx(*yield_)
        if new_p:
            self.p = np.vstack([self.p, new_p])
            self.v = np.vstack([self.v, new_v])
            self.hue = np.concatenate([self.hue, new_h])
        # estimation du rythme de contacts par bille
        if t > 0.5:
            self.rate = 0.98 * self.rate + 0.02 * (len(hit_angles) / dt / max(1, n))
            self.rate = min(max(self.rate, 0.6), 3.0)
        if self.head >= self.L and not self.done:
            self.done = True
            if self.seg_start is not None:
                self._emit(self.gate_end)
                self.seg_start = None

    def _fx(self, i, ang, th):
        if len(self.sparks) < 220:
            self.sparks.append((th, ang, float(self.hue[i])))
        if self.rng.random() < 0.35 and len(self.dots) < 140:
            sp = self.rng.uniform(60, 220)
            a = ang + self.rng.uniform(-0.4, 0.4)
            self.dots.append([ang, self.R + 30, math.cos(a) * sp, math.sin(a) * sp, th,
                              float(self.hue[i]), self.rng.uniform(10, 26)])

    # -- dessin --------------------------------------------------------------------------
    def draw(self, ctx, t, frame):
        if not self.done:
            self.step(t, 1 / 60)
        cx, cy, R = self.CX, self.CY, self.R
        g = cairo.RadialGradient(cx, cy, 50, cx, cy, 1300)
        g.add_color_stop_rgb(0, 0.07, 0.04, 0.12)
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()

        # bulles colorées qui flottent autour (souvenir de chaque contact)
        alive = []
        for d in self.dots:
            age = t - d[4]
            if age > 5:
                continue
            alive.append(d)
            k = 1 - math.exp(-age * 2.2)
            x = cx + math.cos(d[0]) * d[1] + d[2] * k / 2.2
            y = cy + math.sin(d[0]) * d[1] + d[3] * k / 2.2
            a = min(1, age * 6) * (1 - age / 5)
            col = hsv(d[5], 0.7, 1.0)
            ctx.set_source_rgba(*col, 0.25 * a)
            ctx.arc(x, y, d[6] * 1.5, 0, TAU)
            ctx.fill()
            ctx.set_source_rgba(*col, 0.85 * a)
            ctx.arc(x, y, d[6], 0, TAU)
            ctx.fill()
        self.dots = alive

        # anneau arc-en-ciel qui tourne, plus épais et lumineux quand la musique joue
        playing = t < self.gate_end or self.done
        thick = 26 + (8 if playing else 0)
        for glow_w, alpha in ((thick * 3.2, 0.10), (thick * 1.9, 0.18)):
            ctx.set_line_width(glow_w)
            for k in range(48):
                a0 = k / 48 * TAU
                ctx.set_source_rgba(*hsv(k / 48 + self.rot / TAU, 0.9, 1.0), alpha * (1.6 if playing else 1))
                ctx.arc(cx, cy, R + 6, a0, a0 + TAU / 48 + 0.01)
                ctx.stroke()
        ctx.set_line_width(thick)
        for k in range(96):
            a0 = k / 96 * TAU
            ctx.set_source_rgb(*hsv(k / 96 + self.rot / TAU, 0.85, 1.0))
            ctx.arc(cx, cy, R + thick / 2 - 2, a0, a0 + TAU / 96 + 0.01)
            ctx.stroke()

        # éclairs aux points de contact
        keep = []
        ctx.set_line_width(4)
        for th, ang, hue in self.sparks:
            age = t - th
            if age > 0.35 or age < 0:
                continue
            keep.append((th, ang, hue))
            r0 = R + 30 + age * 500
            ctx.set_source_rgba(*hsv(hue, 0.6, 1.0), 1 - age / 0.35)
            ctx.move_to(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0)
            ctx.line_to(cx + math.cos(ang) * (r0 + 40), cy + math.sin(ang) * (r0 + 40))
            ctx.stroke()
        self.sparks = keep

        # billes
        for (x, y), hu in zip(self.p, self.hue):
            col = hsv(hu, 0.75, 1.0)
            ctx.set_source_rgba(*col, 0.25)
            ctx.arc(cx + x, cy + y, self.BR * 1.8, 0, TAU)
            ctx.fill()
            ctx.set_source_rgb(*col)
            ctx.arc(cx + x, cy + y, self.BR, 0, TAU)
            ctx.fill()

        # jeton x2 qui glisse sur l'anneau
        if not self.done:
            tx, ty = cx + math.cos(self.tok) * (R - 4), cy + math.sin(self.tok) * (R - 4)
            ctx.set_source_rgba(1, 0.2, 0.25, 0.3)
            ctx.arc(tx, ty, 40, 0, TAU)
            ctx.fill()
            ctx.set_source_rgb(0.9, 0.12, 0.18)
            ctx.arc(tx, ty, 30, 0, TAU)
            ctx.fill_preserve()
            ctx.set_source_rgb(1, 1, 1)
            ctx.set_line_width(3)
            ctx.stroke()
            text(ctx, "x2", tx, ty + 11, 30, outline=False)

        # textes : titre, nom révélé à la fin de chaque morceau, barre de progression
        while self.revealed < self.n and self.head >= self.sections[self.revealed][1]:
            self.revealed += 1
        text(ctx, self.title, W / 2, 250, 72)
        if self.revealed:
            names = " / ".join(nm for _, _, nm in self.sections[:self.revealed])
            text(ctx, names, W / 2, 330, 40 if len(names) < 34 else 30, (1, 0.85, 0.3))
        else:
            text(ctx, "???", W / 2, 330, 48, (1, 0.85, 0.3))
        text(ctx, f"{len(self.p)} bille{'s' if len(self.p) > 1 else ''}", W / 2, cy + R + 150, 46)
        x0, wbar, ybar = 190, W - 380, cy + R + 200
        ctx.set_source_rgba(1, 1, 1, 0.15)
        ctx.rectangle(x0, ybar, wbar, 12)
        ctx.fill()
        ctx.set_source_rgb(*hsv(self.rot / TAU, 0.8, 1.0))
        ctx.rectangle(x0, ybar, wbar * min(1, self.head / self.L), 12)
        ctx.fill()
        if self.done:
            text(ctx, "Musique complète !", W / 2, 1620, 64, (0.4, 1, 0.5))
