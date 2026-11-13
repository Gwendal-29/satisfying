"""Psytrance hypnotique : visuels psychédéliques calés sur une musique psytrance synthétisée.

Tout est généré : kick, basse roulante, ligne acide (filtre résonant façon 303), charlestons,
zaps électriques et montée avant le drop. La vidéo boucle parfaitement : 32 mesures dont
la durée tombe pile sur un nombre entier d'images, et chaque motif visuel fait un nombre
entier de cycles sur la boucle.
"""
import math

import cairo
import numpy as np

from .core import FPS, SR, H, W, Scene, text

TAU = 2 * math.pi
RW, RH = 360, 640  # résolution de calcul, agrandie ×3 avec lissage


# ------------------------------------------------------------------ synthèse audio

def _kick():
    n = int(SR * 0.42)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.035)
    phase = TAU * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t / 0.16)
    click = np.random.default_rng(1).normal(0, 1, n) * np.exp(-t / 0.002) * 0.3
    return np.tanh((body + click) * 1.6) * 0.95


def _lowpass_res(x, cutoff, res):
    """Filtre passe-bas résonant (state variable), cutoff par échantillon : le son « acide »."""
    low = band = 0.0
    out = np.empty_like(x)
    q = 1 - res
    for i in range(len(x)):
        f = 2 * math.sin(math.pi * min(cutoff[i], 8000) / SR)
        high = x[i] - low - q * band
        band += f * high
        low += f * band
        out[i] = low
    return out


def _saw(freq, n):
    t = np.arange(n) / SR
    return 2 * ((freq * t) % 1.0) - 1


def _bass_note(freq, step):
    """Note de basse roulante : saw filtrée, courte et ronde."""
    n = int(SR * step * 0.95)
    t = np.arange(n) / SR
    x = _saw(freq, n) * 0.6 + np.sin(TAU * freq * t) * 0.6
    env = np.minimum(1, t / 0.003) * np.exp(-t / (step * 0.45))
    cut = 180 + 900 * np.exp(-t / 0.02)
    return np.tanh(_lowpass_res(x, cut, 0.3) * 2.0) * env


def _acid_note(freq, step, accent, open_):
    n = int(SR * step * (1.6 if accent else 0.9))
    t = np.arange(n) / SR
    x = _saw(freq, n)
    cut = 300 + open_ * (2600 if accent else 1500) * np.exp(-t / (0.06 if accent else 0.04))
    env = np.minimum(1, t / 0.002) * np.exp(-t / (step * (0.9 if accent else 0.5)))
    return np.tanh(_lowpass_res(x, cut, 0.86) * (2.5 if accent else 1.6)) * env * 0.5


def _hat(rng, open_=False):
    n = int(SR * (0.16 if open_ else 0.045))
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    hp = np.diff(np.concatenate([[0], noise]))
    return hp * np.exp(-t / (0.05 if open_ else 0.012)) * 0.35


def _zap(rng, step):
    """Zap électrique : FM qui descend très vite."""
    n = int(SR * step * 2)
    t = np.arange(n) / SR
    f = rng.uniform(800, 2500) * np.exp(-t / 0.05) + 80
    mod = np.sin(TAU * np.cumsum(f * 2.01) / SR) * 4
    return np.sin(TAU * np.cumsum(f) / SR + mod) * np.exp(-t / 0.08) * 0.35


def _riser(n):
    t = np.arange(n) / SR
    u = t / t[-1]
    noise = np.random.default_rng(7).normal(0, 1, n)
    hp = np.diff(np.concatenate([[0], noise]))
    sweep = np.sin(TAU * np.cumsum(200 + 1800 * u ** 2) / SR)
    return (hp * 0.25 + sweep * 0.15) * u ** 2


def _place(track, sig, i, gain=1.0):
    """Ajoute sig dans la piste à l'échantillon i, en repartant au début s'il dépasse (boucle)."""
    n = len(track)
    i %= n
    end = min(n, i + len(sig))
    track[i:end] += sig[:end - i] * gain
    if i + len(sig) > n:
        rest = sig[end - i:]
        track[:len(rest)] += rest * gain


def psytrance(rng, bpm, bars, root_midi, break_start):
    beat = 60 / bpm
    step = beat / 4
    n = int(round(SR * bars * 4 * beat))
    L = np.zeros(n)
    R = np.zeros(n)
    root = 440 * 2 ** ((root_midi - 69) / 12)
    kick = _kick()
    bass_cache = {}
    acid_cache = {}
    # motif acide : 16 pas, degrés de la gamme phrygienne (très « psy »)
    scale = [0, 1, 3, 5, 7, 8, 10, 12]
    pattern = [(int(rng.choice(scale)) + 12 * int(rng.random() < 0.25), rng.random() < 0.3, rng.random() < 0.75)
               for _ in range(16)]
    pattern2 = [(p if rng.random() < 0.6 else int(rng.choice(scale)), a, on) for p, a, on in pattern]
    hat_c, hat_o = _hat(rng), _hat(rng, True)
    drop = break_start + 4  # 4 mesures de pause avec montée, puis le drop
    for bar in range(bars):
        brk = break_start <= bar < drop
        for b in range(4):
            for s in range(4):
                k = (bar * 16 + b * 4 + s)
                i = int(round(k * step * SR))
                if not brk:
                    if s == 0:
                        _place(L, kick, i)
                        _place(R, kick, i)
                    else:
                        # basse roulante sur les 3 doubles-croches après le kick
                        f = root / 2 * (2 if (bar % 4 == 3 and b == 3 and s == 3) else 1)
                        if f not in bass_cache:
                            bass_cache[f] = _bass_note(f, step)
                        _place(L, bass_cache[f], i, 0.55)
                        _place(R, bass_cache[f], i, 0.55)
                    if s == 2:
                        _place(L, hat_o, i, 0.5)
                        _place(R, hat_o, i, 0.6)
                    else:
                        _place(L, hat_c, i, 0.25)
                        _place(R, hat_c, i, 0.2)
                # ligne acide : entre à la mesure 5, tourne en permanence, filtre qui s'ouvre
                if bar >= 4:
                    deg, acc, on = (pattern2 if (bar // 8) % 2 else pattern)[b * 4 + s]
                    if on:
                        open_ = 0.35 + 0.65 * ((bar % 8) * 16 + b * 4 + s) / 128
                        key = (deg, acc, round(open_, 1))
                        if key not in acid_cache:
                            acid_cache[key] = _acid_note(root * 2 ** (deg / 12), step, acc, key[2])
                        pan = 0.5 + 0.35 * math.sin(k * 0.37)
                        _place(L, acid_cache[key], i, 0.55 * (1 - pan) * 2)
                        _place(R, acid_cache[key], i, 0.55 * pan * 2)
                if not brk and s == 3 and b == 3 and bar % 2 == 1 and rng.random() < 0.7:
                    z = _zap(rng, step)
                    _place(L, z, i, 0.6 if bar % 4 == 1 else 0.2)
                    _place(R, z, i, 0.2 if bar % 4 == 1 else 0.6)
    # montée avant le drop
    i0 = int(round(break_start * 16 * step * SR))
    rs = _riser(int(round((drop - break_start) * 16 * step * SR)))
    _place(L, rs, i0, 0.8)
    _place(R, rs, i0, 0.8)
    out = np.stack([L, R], 1)
    return out / (np.abs(out).max() + 1e-9) * 0.95


# ------------------------------------------------------------------ visuels

def _palette(x, a, b, c, d):
    """Palette cosinus : couleurs saturées qui glissent en continu."""
    return [a[k] + b[k] * np.cos(TAU * (c[k] * x + d[k])) for k in range(3)]


PALETTES = [
    ((0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1.0, 1.0, 1.0), (0.0, 0.33, 0.67)),
    ((0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1.0, 1.0, 0.5), (0.8, 0.9, 0.3)),
    ((0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (2.0, 1.0, 0.0), (0.5, 0.2, 0.25)),
    ((0.6, 0.4, 0.6), (0.5, 0.5, 0.4), (1.0, 1.0, 1.0), (0.3, 0.2, 0.6)),
]


class PsyTrance(Scene):
    loop = True
    tags = ["#psytrance", "#trippy", "#psychedelic", "#hypnotic", "#pourtoi"]
    bed_freqs = (55.0,)
    lengths = ("court", "moyen", "normal", "long")

    def __init__(self, rng):
        super().__init__(rng)
        self.bpm = float(rng.choice([144, 150]))
        self.bars = 32
        if self.LENGTH:
            self.bars = int(np.clip(round(self.LENGTH * self.bpm / 240 / 8) * 8, 16, 40))
            if self.LENGTH >= 61:
                self.bars = 40
        self.brk = self.bars // 2
        self.max_duration = self.bars * 4 * 60 / self.bpm  # tombe pile sur un nombre entier d'images
        self.mode = str(rng.choice(["tunnel", "mandala", "spirale"]))
        self.fold = int(rng.choice([6, 8, 10, 12]))
        self.pal = PALETTES[int(rng.integers(len(PALETTES)))]
        self.dir = int(rng.choice([-1, 1]))
        self.title = str(rng.choice(["Monte le son et fixe le centre", "Ne cligne pas des yeux",
                                     "Regarde au centre jusqu'au drop"]))
        self.caption = "Mets le son à fond et fixe le centre jusqu'au drop..."
        root = int(rng.choice([40, 41, 42, 43]))  # mi, fa, fa#, sol : tonalités typiques
        track = psytrance(rng, self.bpm, self.bars, root, self.brk)
        self._add_stereo(track)
        # grille polaire précalculée
        ys, xs = np.mgrid[0:RH, 0:RW].astype(np.float32)
        x = (xs - RW / 2) / (RW / 2)
        y = (ys - RH * 0.52) / (RW / 2)
        self.R = np.hypot(x, y) + 1e-3
        self.A = np.arctan2(y, x)
        self.logR = np.log(self.R)
        self.small = cairo.ImageSurface(cairo.FORMAT_RGB24, RW, RH)
        self.buf = np.ndarray((RH, RW, 4), np.uint8, self.small.get_data())

    def _add_stereo(self, track):
        # Audio.add ne gère que le mono + panoramique : on dépose les deux canaux séparément.
        self.audio.add(0.0, track[:, 0], gain=1.0, pan=-1.0)
        self.audio.add(0.0, track[:, 1], gain=1.0, pan=1.0)

    def _kick_env(self, t):
        beat = 60 / self.bpm
        bar = int(t / (4 * beat))
        if self.brk <= bar < self.brk + 4:
            return 0.0
        ph = (t % beat) / beat
        return math.exp(-ph * 7)

    def _field(self, ph, kick):
        """Motif en niveaux (float) ; ph = position dans la boucle (0..1)."""
        n = self.fold
        R = self.R * (1 - 0.07 * kick)
        A = self.A
        if self.mode == "tunnel":
            depth = 0.42 / R + self.dir * 16 * ph
            a = np.abs(((A * n / TAU + 2 * ph) % 1.0) - 0.5)
            v = np.sin(TAU * 2 * depth) + np.sin(TAU * (a * 3 + depth)) * 0.8
            v += 0.5 * np.sin(TAU * (a * 6 - 3 * ph) + 4 * np.sin(TAU * depth))
            return v * 0.25 + depth * 0.25, np.clip(R * 2.2, 0, 1)
        if self.mode == "mandala":
            a = np.abs(((A * n / TAU) % 1.0) - 0.5)
            w = np.sin(TAU * (R * 3 - 4 * ph * self.dir)) * 0.6
            v = np.sin(TAU * (R * 5 + a * 2 + w - 8 * ph * self.dir))
            v += np.sin(TAU * (a * 4 + R * 2 + 2 * ph)) * 0.7
            return v * 0.3 + R * 0.6 - 4 * ph, np.clip(1.3 - R * 0.55, 0, 1)
        # spirale logarithmique : zoom infini
        s = A * n / TAU + 1.8 * self.logR - self.dir * 12 * ph
        v = np.sin(TAU * s) + 0.6 * np.sin(TAU * (2 * s + 0.5 * np.sin(TAU * (self.logR - 3 * ph))))
        return v * 0.22 + self.logR * 0.35 - 3 * ph, np.clip(self.R * 3, 0, 1)

    def draw(self, ctx, t, frame):
        ph = t / self.max_duration
        kick = self._kick_env(t)
        field, mask = self._field(ph, kick)
        a, b, c, d = self.pal
        cols = _palette(field + 2 * ph, a, b, c, d)
        bright = mask * (0.85 + 0.3 * kick)
        # léger décalage de canal (aberration chromatique) pour l'effet « trip »
        r = np.clip(np.roll(cols[0], 2, axis=1) * bright, 0, 1)
        g = np.clip(cols[1] * bright, 0, 1)
        bl = np.clip(np.roll(cols[2], -2, axis=1) * bright, 0, 1)
        self.small.flush()
        self.buf[..., 2] = (r * 255).astype(np.uint8)
        self.buf[..., 1] = (g * 255).astype(np.uint8)
        self.buf[..., 0] = (bl * 255).astype(np.uint8)
        self.small.mark_dirty()
        ctx.save()
        ctx.scale(W / RW, H / RH)
        ctx.set_source_surface(self.small, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
        ctx.paint()
        ctx.restore()
        # point central à fixer, qui bat avec le kick
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.arc(W / 2, H * 0.52, 7 + 6 * kick, 0, TAU)
        ctx.fill()
        text(ctx, self.title, W / 2, 290, 64)
