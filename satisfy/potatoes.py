"""L'univers des patates : une grande bibliothèque de personnages et 4 jeux.

Personnages : peau (dorée, rouge, violette, zombie, alien...), yeux, bouche, accessoires du
visage, chapeau et extras (cape, bras, halo...). Chaque vidéo tire sa propre distribution.

Jeux : PotatoRace (course pour sortir des anneaux), PotatoSplit (la patate géante se divise),
PotatoEscape (sortir des formes, solo ou duel), PotatoDuel (deux équipes qui fusionnent).
"""
import math

import cairo
import numpy as np

from .core import FPS, H, W, Scene, bell, hook, hsv, marimba, note_freq, pop, shatter, text, tick
from .escape_box import _ball_pairs
from .merge import _blob, _beret, _crown, _glasses, _mustache, _pirate, _star, _viking, _wizard
from .more import ShapeEscape, SplitBalls
from .physics import collide_balls
from .voice import speak

TAU = 2 * math.pi
CX, CY = W / 2, 1000
ALL = ("court", "moyen", "normal", "long")

# ------------------------------------------------------------------ peaux

SKINS = {  # clair, moyen, sombre, contour
    "doree": ((1.0, 0.9, 0.55), (0.96, 0.72, 0.32), (0.78, 0.5, 0.2), (0.45, 0.25, 0.08)),
    "rouge": ((1.0, 0.72, 0.66), (0.86, 0.36, 0.3), (0.6, 0.18, 0.15), (0.35, 0.08, 0.06)),
    "violette": ((0.86, 0.72, 1.0), (0.6, 0.36, 0.78), (0.38, 0.18, 0.5), (0.2, 0.08, 0.28)),
    "douce": ((1.0, 0.82, 0.55), (0.96, 0.56, 0.25), (0.75, 0.35, 0.12), (0.42, 0.18, 0.05)),
    "pale": ((1.0, 1.0, 0.97), (0.92, 0.9, 0.86), (0.74, 0.72, 0.68), (0.4, 0.38, 0.35)),
    "zombie": ((0.78, 0.96, 0.66), (0.5, 0.76, 0.4), (0.32, 0.5, 0.25), (0.15, 0.28, 0.1)),
    "alien": ((0.72, 0.96, 1.0), (0.36, 0.72, 0.96), (0.18, 0.45, 0.75), (0.08, 0.2, 0.4)),
    "brune": ((0.86, 0.66, 0.46), (0.66, 0.46, 0.28), (0.46, 0.3, 0.18), (0.25, 0.15, 0.07)),
    "or": ((1.0, 1.0, 0.72), (1.0, 0.83, 0.22), (0.85, 0.6, 0.05), (0.5, 0.32, 0.0)),
    "cosmique": ((0.82, 0.72, 1.0), (0.46, 0.3, 0.9), (0.2, 0.1, 0.5), (0.1, 0.05, 0.3)),
}


def _fill_ellipse(ctx, x, y, rx, ry, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(max(rx, 0.01), max(ry, 0.01))
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.fill()


# ------------------------------------------------------------------ yeux, bouches

def _eye_white(ctx, x, y, r, look):
    ctx.set_source_rgb(1, 1, 1)
    ctx.arc(x, y, r * 0.17, 0, TAU)
    ctx.fill()
    ctx.set_source_rgb(0.05, 0.03, 0.02)
    ctx.arc(x + look[0] * r * 0.06, y + look[1] * r * 0.06, r * 0.095, 0, TAU)
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.arc(x + look[0] * r * 0.06 - r * 0.03, y + look[1] * r * 0.06 - r * 0.03, r * 0.03, 0, TAU)
    ctx.fill()


def _closed(ctx, x, y, r):
    ctx.set_source_rgb(0.15, 0.08, 0.03)
    ctx.set_line_width(r * 0.06)
    ctx.arc(x, y, r * 0.12, math.pi * 1.1, math.pi * 1.9)
    ctx.stroke()


def _heart(ctx, x, y, s):
    ctx.move_to(x, y + s * 0.9)
    ctx.curve_to(x - s * 1.6, y - s * 0.2, x - s * 0.6, y - s * 1.3, x, y - s * 0.4)
    ctx.curve_to(x + s * 0.6, y - s * 1.3, x + s * 1.6, y - s * 0.2, x, y + s * 0.9)
    ctx.fill()


def draw_eyes(ctx, r, style, look, blink, skin):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k, s in enumerate((-1, 1)):
        x, y = s * 0.3 * r, -0.15 * r
        if blink and style not in ("hearts", "stars"):
            _closed(ctx, x, y, r)
            continue
        if style == "hearts":
            ctx.set_source_rgb(0.95, 0.15, 0.3)
            _heart(ctx, x, y, r * 0.15)
        elif style == "stars":
            ctx.set_source_rgb(1, 0.85, 0.15)
            _star(ctx, x, y, r * 0.2)
        elif style == "wink" and s == 1:
            _closed(ctx, x, y, r)
        elif style == "sleepy":
            _eye_white(ctx, x, y, r, (0, 0.5))
            ctx.set_source_rgb(*SKINS[skin][1])
            ctx.rectangle(x - r * 0.2, y - r * 0.2, r * 0.4, r * 0.19)
            ctx.fill()
            ctx.set_source_rgb(*SKINS[skin][3])
            ctx.set_line_width(r * 0.04)
            ctx.move_to(x - r * 0.18, y - r * 0.01)
            ctx.line_to(x + r * 0.18, y - r * 0.01)
            ctx.stroke()
        else:
            _eye_white(ctx, x, y, r, look)
        if style == "angry":
            ctx.set_source_rgb(0.15, 0.08, 0.03)
            ctx.set_line_width(r * 0.07)
            ctx.move_to(x - s * r * 0.2, y - r * 0.3)
            ctx.line_to(x + s * r * 0.15, y - r * 0.2)
            ctx.stroke()


def draw_mouth(ctx, r, style):
    dark = (0.3, 0.1, 0.05)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(r * 0.06)
    if style == "grin":
        ctx.set_source_rgb(0.45, 0.08, 0.08)
        ctx.move_to(-0.3 * r, 0.12 * r)
        ctx.curve_to(-0.25 * r, 0.5 * r, 0.25 * r, 0.5 * r, 0.3 * r, 0.12 * r)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgb(1, 1, 1)
        ctx.rectangle(-0.24 * r, 0.12 * r, 0.48 * r, 0.08 * r)
        ctx.fill()
    elif style == "o":
        ctx.set_source_rgb(*dark)
        _fill_ellipse(ctx, 0, 0.25 * r, 0.1 * r, 0.13 * r)
    elif style == "cat":
        ctx.set_source_rgb(*dark)
        for s in (-1, 1):
            ctx.arc(s * 0.09 * r, 0.18 * r, 0.09 * r, 0, math.pi)
            ctx.stroke()
    elif style == "flat":
        ctx.set_source_rgb(*dark)
        ctx.move_to(-0.15 * r, 0.25 * r)
        ctx.line_to(0.15 * r, 0.25 * r)
        ctx.stroke()
    else:  # smile, tongue, fangs
        ctx.set_source_rgb(*dark)
        ctx.arc(0, 0.12 * r, r * 0.22, math.pi * 0.2, math.pi * 0.8)
        ctx.stroke()
        if style == "tongue":
            ctx.set_source_rgb(1, 0.45, 0.55)
            _fill_ellipse(ctx, 0.04 * r, 0.36 * r, 0.09 * r, 0.11 * r)
        if style == "fangs":
            ctx.set_source_rgb(1, 1, 1)
            for s in (-1, 1):
                ctx.move_to(s * 0.12 * r, 0.32 * r)
                ctx.line_to(s * 0.07 * r, 0.32 * r)
                ctx.line_to(s * 0.095 * r, 0.45 * r)
                ctx.close_path()
                ctx.fill()


def _cheeks(ctx, r):
    ctx.set_source_rgba(1, 0.45, 0.45, 0.35)
    for s in (-1, 1):
        ctx.arc(s * 0.52 * r, 0.12 * r, r * 0.11, 0, TAU)
        ctx.fill()


# ------------------------------------------------------------------ accessoires du visage

def f_sunglasses(ctx, r, t):
    ctx.set_source_rgb(0.05, 0.05, 0.08)
    for s in (-1, 1):
        ctx.move_to(s * 0.08 * r, -0.28 * r)
        ctx.line_to(s * 0.52 * r, -0.28 * r)
        ctx.line_to(s * 0.46 * r, -0.02 * r)
        ctx.line_to(s * 0.12 * r, -0.02 * r)
        ctx.close_path()
        ctx.fill()
    ctx.set_line_width(r * 0.05)
    ctx.move_to(-0.1 * r, -0.25 * r)
    ctx.line_to(0.1 * r, -0.25 * r)
    ctx.stroke()
    ctx.set_source_rgba(1, 1, 1, 0.5)
    for s in (-1, 1):
        ctx.move_to(s * 0.4 * r, -0.24 * r)
        ctx.line_to(s * 0.3 * r, -0.08 * r)
        ctx.set_line_width(r * 0.03)
        ctx.stroke()


def f_monocle(ctx, r, t):
    ctx.set_source_rgb(0.85, 0.7, 0.2)
    ctx.set_line_width(r * 0.04)
    ctx.arc(0.3 * r, -0.15 * r, r * 0.22, 0, TAU)
    ctx.stroke()
    ctx.move_to(0.45 * r, 0.02 * r)
    ctx.curve_to(0.55 * r, 0.3 * r, 0.4 * r, 0.5 * r, 0.5 * r, 0.7 * r)
    ctx.stroke()


def f_beard(ctx, r, t):
    ctx.set_source_rgb(0.95, 0.95, 0.95)
    ctx.move_to(-0.5 * r, 0.1 * r)
    ctx.curve_to(-0.55 * r, 0.75 * r, -0.15 * r, 1.05 * r, 0, 1.0 * r)
    ctx.curve_to(0.15 * r, 1.05 * r, 0.55 * r, 0.75 * r, 0.5 * r, 0.1 * r)
    ctx.curve_to(0.25 * r, 0.35 * r, -0.25 * r, 0.35 * r, -0.5 * r, 0.1 * r)
    ctx.fill()


def f_clown(ctx, r, t):
    ctx.set_source_rgb(0.95, 0.1, 0.12)
    ctx.arc(0, 0.04 * r, r * 0.13, 0, TAU)
    ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.6)
    ctx.arc(-0.04 * r, 0.0, r * 0.04, 0, TAU)
    ctx.fill()


def f_freckles(ctx, r, t):
    ctx.set_source_rgba(0.5, 0.25, 0.1, 0.6)
    for x, y in ((-0.5, 0.05), (-0.42, 0.12), (-0.56, 0.16), (0.5, 0.05), (0.42, 0.12), (0.56, 0.16)):
        ctx.arc(x * r, y * r, r * 0.025, 0, TAU)
        ctx.fill()


def f_chain(ctx, r, t):
    ctx.set_source_rgb(1, 0.82, 0.2)
    ctx.set_line_width(r * 0.05)
    ctx.arc(0, 0.2 * r, r * 0.6, math.pi * 0.25, math.pi * 0.75)
    ctx.stroke()
    _fill_ellipse(ctx, 0, 0.82 * r, 0.1 * r, 0.12 * r)


def f_pacifier(ctx, r, t):
    ctx.set_source_rgb(0.4, 0.75, 1)
    _fill_ellipse(ctx, 0, 0.28 * r, 0.2 * r, 0.1 * r)
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(r * 0.04)
    ctx.arc(0, 0.4 * r, r * 0.08, 0, TAU)
    ctx.stroke()


def f_eyepatch(ctx, r, t):
    ctx.set_source_rgb(0.05, 0.05, 0.05)
    ctx.set_line_width(r * 0.04)
    ctx.move_to(-0.85 * r, -0.45 * r)
    ctx.line_to(0.85 * r, 0.05 * r)
    ctx.stroke()
    ctx.arc(0.3 * r, -0.15 * r, r * 0.2, 0, TAU)
    ctx.fill()


def f_mask(ctx, r, t):  # loup de super-héros
    ctx.set_source_rgb(0.1, 0.1, 0.12)
    ctx.move_to(-0.62 * r, -0.2 * r)
    ctx.curve_to(-0.5 * r, -0.42 * r, 0.5 * r, -0.42 * r, 0.62 * r, -0.2 * r)
    ctx.curve_to(0.5 * r, 0.05 * r, -0.5 * r, 0.05 * r, -0.62 * r, -0.2 * r)
    ctx.fill()
    for s in (-1, 1):
        ctx.set_source_rgb(1, 1, 1)
        ctx.arc(s * 0.3 * r, -0.16 * r, r * 0.1, 0, TAU)
        ctx.fill()


FACE = {"mustache": lambda c, r, t: _mustache(c, r), "glasses": lambda c, r, t: _glasses(c, r),
        "sunglasses": f_sunglasses, "monocle": f_monocle, "beard": f_beard, "clown": f_clown,
        "freckles": f_freckles, "chain": f_chain, "pacifier": f_pacifier, "eyepatch": f_eyepatch,
        "mask": f_mask}


# ------------------------------------------------------------------ chapeaux et coiffes

def h_top(ctx, r, t):
    ctx.set_source_rgb(0.08, 0.08, 0.1)
    ctx.rectangle(-0.42 * r, -1.6 * r, 0.84 * r, 0.82 * r)
    ctx.fill()
    _fill_ellipse(ctx, 0, -0.8 * r, 0.72 * r, 0.14 * r)
    ctx.set_source_rgb(0.75, 0.1, 0.15)
    ctx.rectangle(-0.42 * r, -1.0 * r, 0.84 * r, 0.12 * r)
    ctx.fill()


def h_cowboy(ctx, r, t):
    ctx.set_source_rgb(0.55, 0.33, 0.15)
    ctx.move_to(-0.42 * r, -0.78 * r)
    ctx.curve_to(-0.45 * r, -1.45 * r, -0.1 * r, -1.3 * r, 0, -1.2 * r)
    ctx.curve_to(0.1 * r, -1.3 * r, 0.45 * r, -1.45 * r, 0.42 * r, -0.78 * r)
    ctx.close_path()
    ctx.fill()
    ctx.move_to(-1.0 * r, -0.95 * r)
    ctx.curve_to(-0.6 * r, -0.6 * r, 0.6 * r, -0.6 * r, 1.0 * r, -0.95 * r)
    ctx.curve_to(0.6 * r, -0.72 * r, -0.6 * r, -0.72 * r, -1.0 * r, -0.95 * r)
    ctx.fill()
    ctx.set_source_rgb(0.3, 0.17, 0.07)
    ctx.rectangle(-0.42 * r, -0.92 * r, 0.84 * r, 0.1 * r)
    ctx.fill()


def h_chef(ctx, r, t):
    ctx.set_source_rgb(0.98, 0.98, 0.98)
    for x, y, s in ((-0.32, -1.25, 0.32), (0.0, -1.42, 0.36), (0.32, -1.25, 0.32)):
        ctx.arc(x * r, y * r, s * r, 0, TAU)
        ctx.fill()
    ctx.rectangle(-0.5 * r, -1.2 * r, 1.0 * r, 0.45 * r)
    ctx.fill()
    ctx.set_source_rgb(0.85, 0.85, 0.85)
    ctx.rectangle(-0.5 * r, -0.86 * r, 1.0 * r, 0.1 * r)
    ctx.fill()


def h_ninja(ctx, r, t):
    ctx.set_source_rgb(0.12, 0.12, 0.14)
    ctx.rectangle(-0.9 * r, -0.62 * r, 1.8 * r, 0.22 * r)
    ctx.fill()
    for k in (0, 1):
        w = math.sin(t * 9 + k) * 0.12 * r
        ctx.move_to(0.8 * r, -0.55 * r)
        ctx.curve_to(1.05 * r, -0.6 * r + w, 1.25 * r, -0.4 * r - w, 1.45 * r, -0.45 * r + k * 0.2 * r + w)
        ctx.line_to(1.4 * r, -0.35 * r + k * 0.2 * r + w)
        ctx.curve_to(1.2 * r, -0.3 * r, 1.0 * r, -0.4 * r, 0.8 * r, -0.42 * r)
        ctx.close_path()
        ctx.fill()
    ctx.set_source_rgb(0.75, 0.77, 0.82)
    ctx.rectangle(-0.22 * r, -0.6 * r, 0.44 * r, 0.18 * r)
    ctx.fill()


def h_astronaut(ctx, r, t):
    ctx.set_source_rgba(0.75, 0.9, 1.0, 0.18)
    ctx.arc(0, -0.05 * r, r * 1.18, 0, TAU)
    ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.set_line_width(r * 0.08)
    ctx.arc(0, -0.05 * r, r * 1.18, 0, TAU)
    ctx.stroke()
    ctx.set_source_rgba(1, 1, 1, 0.5)
    ctx.set_line_width(r * 0.06)
    ctx.arc(0, -0.05 * r, r * 0.95, math.pi * 1.1, math.pi * 1.4)
    ctx.stroke()


def h_cap(ctx, r, t, color=(0.85, 0.15, 0.2), back=False):
    ctx.set_source_rgb(*color)
    ctx.arc(0, -0.55 * r, r * 0.6, math.pi, TAU)
    ctx.close_path()
    ctx.fill()
    s = -1 if back else 1
    _fill_ellipse(ctx, s * 0.55 * r, -0.58 * r, 0.42 * r, 0.1 * r)
    ctx.set_source_rgb(1, 1, 1)
    ctx.arc(0, -1.12 * r, r * 0.07, 0, TAU)
    ctx.fill()


def h_santa(ctx, r, t):
    ctx.set_source_rgb(0.85, 0.1, 0.12)
    ctx.move_to(-0.6 * r, -0.7 * r)
    ctx.curve_to(-0.4 * r, -1.6 * r, 0.6 * r, -1.7 * r, 0.95 * r, -1.1 * r)
    ctx.line_to(0.6 * r, -0.7 * r)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.rectangle(-0.65 * r, -0.8 * r, 1.3 * r, 0.18 * r)
    ctx.fill()
    ctx.arc(0.95 * r, -1.1 * r, r * 0.14, 0, TAU)
    ctx.fill()


def h_party(ctx, r, t):
    ctx.move_to(-0.32 * r, -0.78 * r)
    ctx.line_to(0.32 * r, -0.78 * r)
    ctx.line_to(0.05 * r, -1.6 * r)
    ctx.close_path()
    ctx.set_source_rgb(0.2, 0.75, 0.95)
    ctx.fill()
    for k, c in enumerate(((1, 0.3, 0.5), (1, 0.85, 0.2), (0.4, 1, 0.5))):
        ctx.set_source_rgb(*c)
        ctx.arc(0.05 * r - 0.1 * r * (k - 1), -0.95 * r - k * 0.2 * r, r * 0.05, 0, TAU)
        ctx.fill()
    ctx.set_source_rgb(1, 0.4, 0.6)
    ctx.arc(0.05 * r, -1.62 * r, r * 0.1, 0, TAU)
    ctx.fill()


def h_grad(ctx, r, t):
    ctx.set_source_rgb(0.1, 0.1, 0.12)
    ctx.rectangle(-0.42 * r, -1.0 * r, 0.84 * r, 0.25 * r)
    ctx.fill()
    ctx.move_to(-0.95 * r, -1.08 * r)
    ctx.line_to(0, -1.35 * r)
    ctx.line_to(0.95 * r, -1.08 * r)
    ctx.line_to(0, -0.85 * r)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(1, 0.8, 0.2)
    ctx.set_line_width(r * 0.04)
    ctx.move_to(0, -1.1 * r)
    ctx.line_to(0.7 * r, -1.0 * r)
    ctx.line_to(0.72 * r, -0.62 * r)
    ctx.stroke()


def h_headphones(ctx, r, t):
    ctx.set_source_rgb(0.15, 0.15, 0.18)
    ctx.set_line_width(r * 0.1)
    ctx.arc(0, -0.2 * r, r * 0.9, math.pi * 1.05, math.pi * 1.95)
    ctx.stroke()
    for s in (-1, 1):
        ctx.set_source_rgb(0.95, 0.2, 0.45)
        _fill_ellipse(ctx, s * 0.88 * r, -0.12 * r, 0.16 * r, 0.26 * r)


def h_flower(ctx, r, t):
    x, y = 0.45 * r, -0.75 * r
    ctx.set_source_rgb(1, 0.5, 0.75)
    for k in range(5):
        a = k * TAU / 5 + t * 0.5
        ctx.arc(x + math.cos(a) * r * 0.14, y + math.sin(a) * r * 0.14, r * 0.11, 0, TAU)
        ctx.fill()
    ctx.set_source_rgb(1, 0.85, 0.2)
    ctx.arc(x, y, r * 0.09, 0, TAU)
    ctx.fill()


def h_bow(ctx, r, t):
    ctx.set_source_rgb(1, 0.35, 0.6)
    for s in (-1, 1):
        ctx.move_to(0, -0.9 * r)
        ctx.line_to(s * 0.38 * r, -1.12 * r)
        ctx.line_to(s * 0.38 * r, -0.7 * r)
        ctx.close_path()
        ctx.fill()
    ctx.arc(0, -0.9 * r, r * 0.09, 0, TAU)
    ctx.fill()


def h_helmet(ctx, r, t, color=(1, 0.8, 0.1)):
    ctx.set_source_rgb(*color)
    ctx.arc(0, -0.55 * r, r * 0.68, math.pi, TAU)
    ctx.close_path()
    ctx.fill()
    _fill_ellipse(ctx, 0, -0.55 * r, 0.85 * r, 0.1 * r)
    ctx.set_source_rgba(1, 1, 1, 0.4)
    ctx.rectangle(-0.06 * r, -1.22 * r, 0.12 * r, 0.6 * r)
    ctx.fill()


def h_fire(ctx, r, t):
    h_helmet(ctx, r, t, (0.85, 0.12, 0.1))
    ctx.set_source_rgb(1, 0.85, 0.2)
    ctx.arc(0, -0.85 * r, r * 0.13, 0, TAU)
    ctx.fill()


def h_police(ctx, r, t):
    ctx.set_source_rgb(0.1, 0.18, 0.45)
    ctx.move_to(-0.6 * r, -0.72 * r)
    ctx.line_to(-0.7 * r, -1.1 * r)
    ctx.line_to(0.7 * r, -1.1 * r)
    ctx.line_to(0.6 * r, -0.72 * r)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(0.05, 0.05, 0.08)
    _fill_ellipse(ctx, 0, -0.68 * r, 0.62 * r, 0.1 * r)
    ctx.set_source_rgb(1, 0.82, 0.2)
    _star(ctx, 0, -0.92 * r, r * 0.13)


def h_nightcap(ctx, r, t):
    ctx.set_source_rgb(0.3, 0.4, 0.85)
    ctx.move_to(-0.6 * r, -0.72 * r)
    ctx.curve_to(-0.3 * r, -1.5 * r, 0.8 * r, -1.4 * r, 1.0 * r, -0.6 * r)
    ctx.line_to(0.6 * r, -0.72 * r)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.arc(1.0 * r, -0.6 * r, r * 0.13, 0, TAU)
    ctx.fill()


def h_halo(ctx, r, t):
    ctx.set_source_rgba(1, 0.9, 0.3, 0.95)
    ctx.set_line_width(r * 0.09)
    ctx.save()
    ctx.translate(0, -1.25 * r + 0.05 * r * math.sin(t * 3))
    ctx.scale(0.55 * r, 0.14 * r)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.stroke()


def h_horns(ctx, r, t):
    ctx.set_source_rgb(0.75, 0.05, 0.08)
    for s in (-1, 1):
        ctx.move_to(s * 0.25 * r, -0.85 * r)
        ctx.curve_to(s * 0.35 * r, -1.2 * r, s * 0.55 * r, -1.25 * r, s * 0.6 * r, -1.35 * r)
        ctx.curve_to(s * 0.6 * r, -1.1 * r, s * 0.55 * r, -0.9 * r, s * 0.48 * r, -0.75 * r)
        ctx.close_path()
        ctx.fill()


def h_cat(ctx, r, t, skin="doree"):
    for s in (-1, 1):
        ctx.set_source_rgb(*SKINS[skin][1])
        ctx.move_to(s * 0.2 * r, -0.88 * r)
        ctx.line_to(s * 0.55 * r, -1.35 * r)
        ctx.line_to(s * 0.68 * r, -0.65 * r)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgb(1, 0.6, 0.7)
        ctx.move_to(s * 0.3 * r, -0.85 * r)
        ctx.line_to(s * 0.53 * r, -1.18 * r)
        ctx.line_to(s * 0.6 * r, -0.75 * r)
        ctx.close_path()
        ctx.fill()


def h_bunny(ctx, r, t):
    for s in (-1, 1):
        a = s * 0.2 + 0.08 * math.sin(t * 4 + s)
        ctx.set_source_rgb(1, 1, 1)
        _fill_ellipse(ctx, s * 0.3 * r, -1.35 * r, 0.16 * r, 0.55 * r, a)
        ctx.set_source_rgb(1, 0.65, 0.75)
        _fill_ellipse(ctx, s * 0.3 * r, -1.35 * r, 0.08 * r, 0.4 * r, a)


def h_propeller(ctx, r, t):
    ctx.set_source_rgb(0.2, 0.6, 1)
    ctx.arc(0, -0.62 * r, r * 0.55, math.pi, TAU)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(1, 0.85, 0.2)
    ctx.arc(0, -0.62 * r, r * 0.55, math.pi * 1.33, math.pi * 1.66)
    ctx.line_to(0, -0.62 * r)
    ctx.close_path()
    ctx.fill()
    ctx.set_source_rgb(0.3, 0.3, 0.3)
    ctx.rectangle(-0.03 * r, -1.35 * r, 0.06 * r, 0.2 * r)
    ctx.fill()
    w = math.cos(t * 20) * 0.6 * r
    ctx.set_source_rgb(0.95, 0.2, 0.25)
    _fill_ellipse(ctx, 0, -1.35 * r, abs(w) + 0.05 * r, 0.06 * r)


def h_antennas(ctx, r, t):
    ctx.set_source_rgb(0.2, 0.35, 0.6)
    ctx.set_line_width(r * 0.05)
    for s in (-1, 1):
        ctx.move_to(s * 0.2 * r, -0.85 * r)
        ctx.line_to(s * 0.45 * r, -1.35 * r)
        ctx.stroke()
        ctx.set_source_rgb(0.5, 1, 0.5)
        ctx.arc(s * 0.45 * r, -1.35 * r, r * 0.1, 0, TAU)
        ctx.fill()
        ctx.set_source_rgb(0.2, 0.35, 0.6)


def h_laurel(ctx, r, t):
    ctx.set_source_rgb(0.25, 0.65, 0.25)
    for s in (-1, 1):
        for k in range(5):
            a = math.pi * (1.15 + 0.08 * k) if s < 0 else math.pi * (1.85 - 0.08 * k)
            x, y = math.cos(a) * 0.82 * r, math.sin(a) * 0.82 * r - 0.1 * r
            _fill_ellipse(ctx, x, y, 0.13 * r, 0.06 * r, a + math.pi / 2)


def h_sportband(ctx, r, t):
    ctx.set_source_rgb(0.9, 0.15, 0.2)
    ctx.rectangle(-0.88 * r, -0.66 * r, 1.76 * r, 0.2 * r)
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.rectangle(-0.88 * r, -0.58 * r, 1.76 * r, 0.04 * r)
    ctx.fill()


def h_sombrero_mini(ctx, r, t):  # petit chapeau de paille
    ctx.set_source_rgb(0.95, 0.82, 0.45)
    _fill_ellipse(ctx, 0, -0.78 * r, 0.95 * r, 0.16 * r)
    ctx.arc(0, -0.78 * r, r * 0.45, math.pi, TAU)
    ctx.fill()
    ctx.set_source_rgb(0.85, 0.2, 0.2)
    ctx.rectangle(-0.45 * r, -0.92 * r, 0.9 * r, 0.08 * r)
    ctx.fill()


HATS = {
    "top": h_top, "cowboy": h_cowboy, "chef": h_chef, "ninja": h_ninja, "astronaut": h_astronaut,
    "cap": h_cap, "capback": lambda c, r, t: h_cap(c, r, t, (0.15, 0.4, 0.9), back=True),
    "santa": h_santa, "party": h_party, "grad": h_grad, "headphones": h_headphones, "flower": h_flower,
    "bow": h_bow, "helmet": h_helmet, "fire": h_fire, "police": h_police, "nightcap": h_nightcap,
    "halo": h_halo, "horns": h_horns, "cat": h_cat, "bunny": h_bunny, "propeller": h_propeller,
    "antennas": h_antennas, "laurel": h_laurel, "sport": h_sportband, "straw": h_sombrero_mini,
    "crown": lambda c, r, t: _crown(c, r), "viking": lambda c, r, t: _viking(c, r),
    "wizard": lambda c, r, t: _wizard(c, r), "beret": lambda c, r, t: _beret(c, r),
    "pirate": lambda c, r, t: _pirate(c, r),
}


# ------------------------------------------------------------------ arrière-plan (cape, bras, aura)

def _cape(ctx, r, color):
    ctx.set_source_rgb(*color)
    ctx.move_to(-0.7 * r, -0.2 * r)
    ctx.curve_to(-1.2 * r, 0.6 * r, -0.9 * r, 1.2 * r, -0.6 * r, 1.15 * r)
    ctx.line_to(0.6 * r, 1.15 * r)
    ctx.curve_to(0.9 * r, 1.2 * r, 1.2 * r, 0.6 * r, 0.7 * r, -0.2 * r)
    ctx.close_path()
    ctx.fill()


def _arms(ctx, r, t, skin):
    wave = 0.25 * math.sin(t * 6)
    for s in (-1, 1):
        ctx.set_source_rgb(*SKINS[skin][1])
        _fill_ellipse(ctx, s * 1.05 * r, -0.2 * r, 0.4 * r, 0.16 * r, s * (-0.9 + wave))


def _aura(ctx, r, color):
    g = cairo.RadialGradient(0, 0, r * 0.6, 0, 0, r * 1.7)
    g.add_color_stop_rgba(0, *color, 0.5)
    g.add_color_stop_rgba(1, *color, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, r * 1.7, 0, TAU)
    ctx.fill()


# ------------------------------------------------------------------ personnages

def P(skin="doree", eyes="normal", mouth="smile", face=(), hat=None, back=(), cheeks=True, cape=(0.75, 0.1, 0.15), aura=None):
    return {"skin": skin, "eyes": eyes, "mouth": mouth, "face": list(face), "hat": hat, "back": list(back),
            "cheeks": cheeks, "cape": cape, "aura": aura}


PATATINE = ("La patatine", P())
CHARACTERS = [
    ("La patate moustachue", P(mouth="flat", face=["mustache"])),
    ("La patate à lunettes", P(face=["glasses"])),
    ("La patate en béret", P(hat="beret", face=["mustache"], mouth="flat")),
    ("La patate pirate", P(hat="pirate", mouth="grin")),
    ("La patate viking", P(hat="viking", eyes="angry", mouth="grin")),
    ("La patate magicienne", P(hat="wizard")),
    ("La patate cowboy", P(hat="cowboy", mouth="grin", face=["mustache"])),
    ("La patate ninja", P(hat="ninja", eyes="angry", mouth="flat")),
    ("La patate chef", P(hat="chef", face=["mustache"], mouth="flat")),
    ("La patate astronaute", P(hat="astronaut", mouth="o")),
    ("La patate DJ", P(hat="headphones", eyes="sleepy", mouth="smile")),
    ("La patate rappeuse", P(hat="capback", face=["sunglasses", "chain"], mouth="grin")),
    ("La patate bébé", P(hat="bow", face=["pacifier"], cheeks=True)),
    ("Le papy patate", P(face=["glasses", "beard"], skin="brune")),
    ("La patate diplômée", P(hat="grad", face=["glasses"], mouth="grin")),
    ("La patate pompière", P(hat="fire", mouth="grin")),
    ("La patate policière", P(hat="police", eyes="angry", mouth="flat")),
    ("La patate ouvrière", P(hat="helmet", mouth="smile", face=["freckles"])),
    ("La patate du Père Noël", P(hat="santa", face=["beard"], mouth="smile")),
    ("La patate fêtarde", P(hat="party", eyes="wink", mouth="tongue")),
    ("La patate amoureuse", P(eyes="hearts", mouth="smile")),
    ("La patate star", P(eyes="stars", mouth="grin", hat="flower")),
    ("La patate endormie", P(hat="nightcap", eyes="sleepy", mouth="o")),
    ("La patate en colère", P(eyes="angry", mouth="flat", skin="rouge", cheeks=False)),
    ("La patate vampire", P(skin="pale", mouth="fangs", eyes="angry", back=["cape"], cape=(0.12, 0.05, 0.15))),
    ("La patate zombie", P(skin="zombie", eyes="sleepy", mouth="o", cheeks=False)),
    ("La patate extraterrestre", P(skin="alien", hat="antennas", mouth="o", cheeks=False)),
    ("La patate ange", P(hat="halo", mouth="smile", skin="pale")),
    ("La patate diablotine", P(hat="horns", skin="rouge", mouth="fangs", eyes="wink")),
    ("La patate chat", P(hat="cat", mouth="cat")),
    ("La patate lapin", P(hat="bunny", mouth="cat", skin="pale")),
    ("La patate hélicoptère", P(hat="propeller", mouth="grin", face=["freckles"])),
    ("La patate clown", P(hat="party", face=["clown"], mouth="grin")),
    ("La patate gentleman", P(hat="top", face=["monocle", "mustache"], mouth="flat")),
    ("La patate douce", P(skin="douce", hat="bow")),
    ("La patate violette", P(skin="violette", eyes="wink", mouth="tongue")),
    ("La patate rouge", P(skin="rouge", face=["freckles"], mouth="grin")),
    ("La patate fleurie", P(hat="flower", eyes="hearts")),
    ("La patate geek", P(hat="headphones", face=["glasses"], mouth="o")),
    ("La patate sportive", P(hat="sport", mouth="grin", eyes="angry")),
    ("La patate super-héros", P(face=["mask"], back=["cape"], cape=(0.15, 0.35, 0.95), mouth="grin")),
    ("La patate vacancière", P(hat="straw", face=["sunglasses"], mouth="smile")),
    ("La patate rockeuse", P(face=["sunglasses"], mouth="tongue", skin="brune", hat="horns")),
    ("La patate casquette", P(hat="cap", mouth="smile")),
]
BOSSES = [
    ("LA PATATE SUPRÊME", P(hat="crown", mouth="grin", back=["arms"], aura=(1, 0.85, 0.3))),
    ("LE ROI DES PATATES", P(hat="crown", face=["beard"], back=["cape", "arms"], cape=(0.6, 0.05, 0.1), aura=(1, 0.8, 0.3))),
    ("L'EMPEREUR PATATE", P(hat="laurel", eyes="angry", mouth="grin", back=["cape"], cape=(0.45, 0.1, 0.55), aura=(0.9, 0.7, 1))),
    ("LA PATATE GÉANTE", P(mouth="grin", eyes="stars", back=["arms"], aura=(1, 0.6, 0.3))),
    ("LA PATATE COSMIQUE", P(skin="cosmique", eyes="stars", mouth="o", hat="halo", aura=(0.6, 0.5, 1))),
    ("LA PATATE EN OR", P(skin="or", hat="crown", face=["sunglasses"], mouth="grin", back=["arms"], aura=(1, 0.9, 0.3))),
]


def draw_character(ctx, x, y, r, spec, angle=0.0, look=(0, 0), t=0.0, seed=0.0, blink=False):
    skin = spec["skin"]
    light, mid, dark, line = SKINS[skin]
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    if spec.get("aura"):
        _aura(ctx, r, spec["aura"])
    if "cape" in spec["back"]:
        _cape(ctx, r, spec["cape"])
    if "arms" in spec["back"]:
        _arms(ctx, r, t, skin)
    _blob(ctx, r, seed)
    g = cairo.RadialGradient(-0.3 * r, -0.35 * r, r * 0.1, 0, 0, r * 1.05)
    g.add_color_stop_rgb(0, *light)
    g.add_color_stop_rgb(0.6, *mid)
    g.add_color_stop_rgb(1, *dark)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*line)
    ctx.set_line_width(max(1.2, r * 0.05))
    ctx.stroke()
    if r > 14:
        ctx.set_source_rgba(*line, 0.25)
        for sx, sy, sr in ((0.45, 0.45, 0.06), (-0.5, 0.4, 0.05), (0.15, 0.7, 0.04)):
            ctx.arc(sx * r, sy * r, sr * r, 0, TAU)
            ctx.fill()
    draw_eyes(ctx, r, spec["eyes"], look, blink, skin)
    if spec["cheeks"]:
        _cheeks(ctx, r)
    draw_mouth(ctx, r, spec["mouth"])
    for f in spec["face"]:
        FACE[f](ctx, r, t)
    h = spec["hat"]
    if h == "cat":
        h_cat(ctx, r, t, skin)
    elif h:
        HATS[h](ctx, r, t)
    ctx.restore()


def make_cast(rng, n=8):
    """Distribution d'une vidéo : la patatine, n-2 personnages au hasard, un boss final."""
    idx = rng.choice(len(CHARACTERS), size=n - 2, replace=False)
    cast = [PATATINE] + [CHARACTERS[i] for i in idx] + [BOSSES[int(rng.integers(len(BOSSES)))]]
    specs = [c[1] for c in cast]

    def draw(ctx, x, y, r, tier, angle=0.0, look=(0, 0), t=0.0, seed=0.0, blink=False):
        draw_character(ctx, x, y, r, specs[min(tier, len(specs) - 1)], angle, look, t, seed, blink)

    names = [c[0] for c in cast]
    return names, draw, f"{names[-1]} !", names[-1].lower()


def short(name):
    """« La patate cowboy » -> « Cowboy » (pour les étiquettes)."""
    for p in ("La patate ", "Le papy patate", "La "):
        if name.startswith(p):
            rest = name[len(p):] or "Papy"
            return rest[:1].upper() + rest[1:]
    return name


def pick(rng, k):
    idx = rng.choice(len(CHARACTERS), size=k, replace=False)
    return [CHARACTERS[i] for i in idx]


# ------------------------------------------------------------------ 1. course de patates

RACE_COLS = [(1.0, 0.3, 0.3), (0.3, 0.6, 1.0), (0.35, 0.9, 0.4), (1.0, 0.8, 0.2)]


class PotatoRace(Scene):
    caption = "Choisis ta patate en commentaire !"
    tags = ["#patate", "#course", "#satisfying", "#asmr", "#pourtoi"]
    outro = 3.0
    lengths = ALL
    G, PR = 1200.0, 22.0

    def __init__(self, rng):
        super().__init__(rng)
        self.T = self.target(float(rng.choice([35, 45, 52]))) - 2
        self.max_duration = self.T + 14
        self.n = int(np.clip(round(self.T / 4.5), 5, 12))
        self.radii = np.linspace(105, 485, self.n)
        spin = rng.uniform(0.5, 0.9)
        self.w = [(spin + 0.06 * i) * (-1 if i % 2 else 1) for i in range(self.n)]
        self.rot = list(rng.uniform(0, TAU, self.n))
        self.gap = 0.42
        self.hue0 = rng.random()
        self.k = int(rng.choice([3, 4]))
        self.racers = pick(rng, self.k)
        ang = np.linspace(0, TAU, self.k, endpoint=False) + rng.uniform(0, TAU)
        self.p = np.stack([np.cos(ang), np.sin(ang)], 1) * 35
        a = rng.uniform(0, TAU, self.k)
        self.v = np.stack([np.cos(a), np.sin(a)], 1) * 700
        self.layer = np.zeros(self.k, int)
        self.out = [None] * self.k  # rang d'arrivée
        self.order = []
        # durée « prévue » de chaque patate : l'ordre reste une surprise (la physique décide)
        self.goal = np.sort(rng.uniform(0.55, 0.98, self.k)) * self.T
        rng.shuffle(self.goal)
        self.parts = []
        self.title = "Quelle patate sort en premier ?"

    def _assist(self, i, t):
        lag = self.n * min(t, self.goal[i]) / self.goal[i] - self.layer[i] + 1.2 * max(0.0, t - self.goal[i])
        return float(np.clip((lag - 0.3) * 0.25, 0, 0.75))

    def _step(self, dt, t):
        for i in range(self.n):
            self.rot[i] += self.w[i] * dt
        for i in range(self.k):
            if self.out[i] is not None:
                self.p[i] += self.v[i] * dt
                continue
            self.v[i, 1] += self.G * dt
            self.p[i] += self.v[i] * dt
            L = self.layer[i]
            R = self.radii[L] - 5
            d = float(np.hypot(*self.p[i]))
            if d + self.PR < R:
                continue
            local = (math.atan2(self.p[i, 1], self.p[i, 0]) - self.rot[L]) % TAU
            if local < self.gap:
                self.layer[i] += 1
                self._pass(i, L, t)
                continue
            n = self.p[i] / d
            dot = self.v[i] @ n
            if dot > 0:
                self.v[i] -= 2 * dot * n
            self.p[i] = n * (R - self.PR)
            if self.rng.random() < self._assist(i, t):
                ga = self.rot[L] + self.gap / 2  # angle du milieu de la sortie
                target = np.array([math.cos(ga), math.sin(ga)]) * R
                dv = target - self.p[i]
                self.v[i] = dv / (np.linalg.norm(dv) + 1e-6) * 950
            else:
                j = self.rng.normal(0, 0.12)
                c, s = math.cos(j), math.sin(j)
                self.v[i] = np.array([self.v[i, 0] * c - self.v[i, 1] * s, self.v[i, 0] * s + self.v[i, 1] * c])
            sp = np.linalg.norm(self.v[i])
            self.v[i] *= min(max(sp, 650), 1150) / sp
            self.audio.add(t, marimba(note_freq(int(self.rng.integers(5, 12))), 0.4), gain=0.18)
        # chocs entre patates du même anneau
        for i in range(self.k):
            for j in range(i + 1, self.k):
                if self.out[i] is None and self.out[j] is None and self.layer[i] == self.layer[j]:
                    d = self.p[j] - self.p[i]
                    dist = float(np.hypot(*d))
                    if 0 < dist < 2 * self.PR:
                        n = d / dist
                        over = (2 * self.PR - dist) / 2
                        self.p[i] -= n * over
                        self.p[j] += n * over
                        rel = (self.v[j] - self.v[i]) @ n
                        if rel < 0:
                            self.v[i] += rel * n
                            self.v[j] -= rel * n

    def _pass(self, i, L, t):
        col = RACE_COLS[i]
        for a in self.rng.uniform(0, TAU, 25):
            sp = self.rng.uniform(100, 400)
            self.parts.append([self.p[i, 0], self.p[i, 1], math.cos(a) * sp, math.sin(a) * sp, 0.8, col])
        self.audio.add(t, bell(note_freq(L + 5 + 2 * i), dur=1.0, decay=0.35), gain=0.4)
        if self.layer[i] >= self.n:
            rank = len(self.order) + 1
            self.order.append(i)
            self.out[i] = rank
            d = self.p[i] / (np.linalg.norm(self.p[i]) + 1e-6)
            self.v[i] = d * 900
            self.audio.add(t, shatter(self.rng, 0.4), gain=0.3)
            if rank == 1:
                for k, st in enumerate((0, 4, 7, 12)):
                    self.audio.add(t + k * 0.08, bell(note_freq(st, 392.0), dur=1.5, decay=0.5), gain=0.45)
                self.audio.add(t + 0.5, speak(f"{self.racers[i][0].lower()} gagne !", rng=self.rng), gain=0.9)
            if rank == self.k:
                self.done = True

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 4)
        for _ in range(4):
            self._step(dt, t)
        if t > self.T + 8 and not self.done:
            self.done = True
        for p in self.parts:
            p[0] += p[2] / FPS
            p[1] += p[3] / FPS
            p[4] -= 1 / FPS
        self.parts = [p for p in self.parts if p[4] > 0]

        ctx.set_source_rgb(0.03, 0.03, 0.07)
        ctx.paint()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(self.n):
            col = hsv(self.hue0 + i / self.n * 0.8)
            ctx.set_source_rgb(*col)
            ctx.set_line_width(7)
            ctx.new_sub_path()
            ctx.arc(CX, CY, self.radii[i], self.rot[i] + self.gap, self.rot[i] + TAU)
            ctx.stroke()
        for x, y, _, _, life, col in self.parts:
            ctx.set_source_rgba(*col, life)
            ctx.arc(CX + x, CY + y, 4 * life + 1, 0, TAU)
            ctx.fill()
        for i in range(self.k):
            x, y = self.p[i]
            if self.out[i] is not None and (abs(x) > W or abs(y) > H):
                continue
            ctx.set_source_rgba(*RACE_COLS[i], 0.5)
            ctx.arc(CX + x, CY + y, self.PR * 1.35, 0, TAU)
            ctx.fill()
            sp = np.linalg.norm(self.v[i]) + 1e-6
            draw_character(ctx, CX + x, CY + y, self.PR, self.racers[i][1], 0.0,
                           (self.v[i, 0] / sp, self.v[i, 1] / sp), t, i * 1.3, (t + i) % 3.3 < 0.1)

        hook(ctx, self.title, None, t)
        # tableau des coureurs
        gap = W / self.k
        for i in range(self.k):
            x = gap * (i + 0.5)
            y = 1610
            ctx.set_source_rgba(*RACE_COLS[i], 0.22)
            ctx.arc(x, y, 48, 0, TAU)
            ctx.fill()
            draw_character(ctx, x, y + 4, 34, self.racers[i][1], 0, (0, 0), t, i * 1.3)
            text(ctx, short(self.racers[i][0]), x, y + 95, 30, RACE_COLS[i])
            rank = self.out[i]
            label = f"{rank}{'er' if rank == 1 else 'e'}" if rank else f"{self.layer[i]}/{self.n}"
            text(ctx, label, x, y + 145, 44 if rank else 34, (1, 0.85, 0.2) if rank == 1 else (1, 1, 1))
        if self.order:
            text(ctx, f"{short(self.racers[self.order[0]][0]).upper()} GAGNE !", W / 2, 420, 64, RACE_COLS[self.order[0]])


# ------------------------------------------------------------------ 2. la patate géante se divise

class PotatoSplit(SplitBalls):
    caption = "La patate géante se divise à chaque rebond..."
    tags = ["#patate", "#satisfying", "#physics", "#asmr", "#pourtoi"]

    def __init__(self, rng):
        super().__init__(rng)
        self.cap = int(rng.choice([32, 64] if self.target < 28 else [64, 100, 128]))
        self.r0 = 110.0
        self.rmin = math.sqrt(0.4 * self.R ** 2 / self.cap)
        boss = BOSSES[int(rng.integers(len(BOSSES)))]
        self.cast = [("LA PATATE GÉANTE", boss[1])] + pick(rng, 12)
        self.title = f"1 patate géante → {self.cap} ?"

    def _draw_balls(self, ctx, r, t):
        order = np.argsort(-r, kind="stable")
        for i in order:
            x, y = self.p[i]
            g = int(self.gen[i])
            spec = self.cast[min(g, len(self.cast) - 1)][1]
            sp = np.linalg.norm(self.v[i]) + 1e-6
            draw_character(ctx, CX + x, CY + y, r[i], spec, 0.25 * math.sin(t * 2 + i),
                           (self.v[i, 0] / sp, self.v[i, 1] / sp), t, (i * 0.37) % 6, (t + i * 0.7) % 3.1 < 0.1)


# ------------------------------------------------------------------ 3. la patate doit s'échapper

class PotatoEscape(ShapeEscape):
    caption = "La patate va-t-elle s'échapper ?"
    tags = ["#patate", "#satisfying", "#oddlysatisfying", "#asmr", "#pourtoi"]
    BR = 18.0

    def __init__(self, rng):
        super().__init__(rng)
        self.chars = pick(rng, len(self.cols))
        if self.duel:
            a, b = (short(c[0]) for c in self.chars)
            self.names = [a.upper(), b.upper()]
            self.title = f"{a} ou {b} ?"
            self.caption = f"{a} ou {b} : qui casse le plus de formes ? Dis-le en commentaire !"
        else:
            self.title = "La patate va s'échapper ?"
            self.caption = f"{self.chars[0][0]} est enfermée... elle va sortir ?"

    def _draw_balls(self, ctx, t):
        for j, col in enumerate(self.cols):
            for k, (x, y) in enumerate(self.trail[j]):
                a = (k + 1) / len(self.trail[j])
                ctx.set_source_rgba(*col, 0.2 * a)
                ctx.arc(CX + x, CY + y, self.BR * a, 0, TAU)
                ctx.fill()
            sp = np.linalg.norm(self.v[j]) + 1e-6
            draw_character(ctx, CX + self.p[j, 0], CY + self.p[j, 1], self.BR * 1.15, self.chars[j][1],
                           0.2 * math.sin(t * 3 + j), (self.v[j, 0] / sp, self.v[j, 1] / sp), t, j * 2.0,
                           (t + j) % 3.4 < 0.1)


# ------------------------------------------------------------------ 4. duel : deux équipes qui fusionnent

class _Arena:
    """Une fiole ronde où les patates d'une équipe fusionnent (version compacte de PotatoMerge)."""

    def __init__(self, rng, cx, R, spec):
        self.rng, self.cx, self.R, self.spec = rng, cx, R, spec
        self.p = np.zeros((0, 2))
        self.v = np.zeros((0, 2))
        self.tier = np.zeros(0, int)
        self.seed = np.zeros(0)
        self.next_spawn = 0.2
        self.score = 0
        self.best = 0
        self.rings = []

    def rad(self, tier):
        return 13 * 1.34 ** np.asarray(tier)

    def spawn(self, t, k):
        if t < self.next_spawn:
            return
        area = float((math.pi * self.rad(self.tier) ** 2).sum()) if len(self.tier) else 0.0
        if area < 0.5 * math.pi * self.R ** 2:
            self.p = np.vstack([self.p, [[self.rng.uniform(-40, 40), -self.R + 30]]])
            self.v = np.vstack([self.v, [[self.rng.normal(0, 40), 300.0]]])
            self.tier = np.append(self.tier, 0)
            self.seed = np.append(self.seed, self.rng.uniform(0, 6))
        self.next_spawn = t + float(self.rng.uniform(0.14, 0.24)) / k

    def step(self, dt, t, k, goal):
        merged = []
        if not len(self.p):
            return merged
        strength = (420 + 15 * t * k) * k
        for tier in np.unique(self.tier):
            idx = np.flatnonzero(self.tier == tier)
            if len(idx) < 2:
                continue
            P_ = self.p[idx]
            D = P_[None, :, :] - P_[:, None, :]
            dist = np.hypot(D[..., 0], D[..., 1]) + np.eye(len(idx)) * 1e9
            near = dist.argmin(1)
            dv = D[np.arange(len(idx)), near]
            self.v[idx] += dv / dist[np.arange(len(idx)), near][:, None] * strength * dt
        self.p += self.v * dt
        r = self.rad(self.tier)
        collide_balls(self.p, self.v, r, e=0.85)
        d = np.maximum(np.hypot(*self.p.T), 1e-6)
        m = d > self.R - r
        if m.any():
            n = self.p[m] / d[m, None]
            self.p[m] = n * (self.R - r[m])[:, None]
            dot = np.einsum("ij,ij->i", self.v[m], n)
            self.v[m] -= (2 * np.maximum(dot, 0))[:, None] * n
        sp = np.maximum(np.hypot(*self.v.T), 1e-6)
        self.v *= (np.clip(sp, 80, 380) / sp)[:, None]
        if len(self.p) < 2:
            return merged
        I, J = _ball_pairs(self.p, float(r.max()))
        same = self.tier[I] == self.tier[J]
        I, J = I[same], J[same]
        dd = np.hypot(*(self.p[J] - self.p[I]).T)
        ok = dd < r[I] + r[J] + 2
        used, kill = set(), []
        for i, j in zip(I[ok], J[ok]):
            if i in used or j in used or self.tier[i] >= goal:
                continue
            used.update((i, j))
            self.p[i] = (self.p[i] + self.p[j]) / 2
            self.v[i] = (self.v[i] + self.v[j]) / 2
            self.tier[i] += 1
            kill.append(j)
            self.score += 2 ** int(self.tier[i])
            self.best = max(self.best, int(self.tier[i]))
            self.rings.append((*self.p[i], float(self.rad(self.tier[i])), t))
            merged.append(int(self.tier[i]))
        if kill:
            keep = np.ones(len(self.p), bool)
            keep[kill] = False
            self.p, self.v, self.tier, self.seed = self.p[keep], self.v[keep], self.tier[keep], self.seed[keep]
        return merged


class PotatoDuel(Scene):
    tags = ["#patate", "#duel", "#merge", "#satisfying", "#pourtoi"]
    outro = 3.5
    lengths = ("moyen", "normal", "long")
    GOAL = 6
    TEAM = [(1.0, 0.32, 0.32), (0.3, 0.6, 1.0)]

    def __init__(self, rng):
        super().__init__(rng)
        tgt = self.target(46.0)
        self.k = float(np.clip(14.0 / (tgt - 2), 0.25, 1.5))
        self.max_duration = tgt + 25
        self.chars = pick(rng, 2)
        a, b = (short(c[0]) for c in self.chars)
        self.names = [a, b]
        self.title = f"{a} contre {b}"
        self.caption = f"{a} contre {b} : qui fait la patate géante en premier ? Ton pronostic en commentaire !"
        self.arenas = [_Arena(rng, W * 0.25, 240.0, self.chars[0][1]), _Arena(rng, W * 0.75, 240.0, self.chars[1][1])]
        self.winner = None

    def draw(self, ctx, t, frame):
        dt = 1 / (FPS * 2)
        for i, ar in enumerate(self.arenas):
            if not self.done:
                ar.spawn(t, self.k)
            for _ in range(2):
                for tier in ar.step(dt, t, self.k, self.GOAL):
                    self.audio.add(t, pop(note_freq(12 - tier, 196.0 * (1 + 0.25 * i))), gain=0.35, pan=-0.6 if i == 0 else 0.6)
                    if tier >= self.GOAL and self.winner is None:
                        self.winner = i
                        self.done = True
                        for k, st in enumerate((0, 4, 7, 12)):
                            self.audio.add(t + k * 0.08, bell(note_freq(st, 261.6), dur=2.0, decay=0.6), gain=0.5)
                        self.audio.add(t + 0.5, speak(f"victoire de {self.chars[i][0].lower()} !", rng=self.rng), gain=0.9)

        ctx.set_source_rgb(0.03, 0.03, 0.08)
        ctx.paint()
        for i, ar in enumerate(self.arenas):
            col = self.TEAM[i]
            ctx.set_source_rgba(*col, 0.12)
            ctx.arc(ar.cx, CY, ar.R + 4, 0, TAU)
            ctx.fill()
            ctx.set_source_rgb(*col)
            ctx.set_line_width(7)
            ctx.arc(ar.cx, CY, ar.R + 4, 0, TAU)
            ctx.stroke()
            alive = []
            for x, y, rr, t0 in ar.rings:
                age = t - t0
                if age < 0.4:
                    alive.append((x, y, rr, t0))
                    ctx.set_source_rgba(1, 1, 1, 0.7 * (1 - age / 0.4))
                    ctx.set_line_width(3)
                    ctx.arc(ar.cx + x, CY + y, rr * (1 + age), 0, TAU)
                    ctx.stroke()
            ar.rings = alive
            r = ar.rad(ar.tier)
            for j in np.argsort(-ar.tier, kind="stable"):
                sp = np.linalg.norm(ar.v[j]) + 1e-6
                draw_character(ctx, ar.cx + ar.p[j, 0], CY + ar.p[j, 1], float(r[j]), ar.spec,
                               0.2 * math.sin(t * 2 + j), (ar.v[j, 0] / sp, ar.v[j, 1] / sp), t, ar.seed[j])
            # carte de l'équipe
            draw_character(ctx, ar.cx, 1390, 46, ar.spec, 0, (0, 0), t, 1.0)
            text(ctx, self.names[i], ar.cx, 1500, 44, col)
            text(ctx, f"{ar.score}", ar.cx, 1580, 64, (1, 1, 1))
            # jauge vers la patate géante
            ctx.set_source_rgba(1, 1, 1, 0.15)
            ctx.rectangle(ar.cx - 180, 1620, 360, 22)
            ctx.fill()
            ctx.set_source_rgb(*col)
            ctx.rectangle(ar.cx - 180, 1620, 360 * min(1, ar.best / self.GOAL), 22)
            ctx.fill()
        text(ctx, "VS", W / 2, 1020, 72, (1, 1, 1))
        hook(ctx, self.title, "Qui fait la patate géante en premier ?", t)
        if self.winner is not None:
            text(ctx, f"{self.names[self.winner].upper()} GAGNE !", W / 2, 1760, 80, self.TEAM[self.winner])
