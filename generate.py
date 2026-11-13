"""Génère une (ou plusieurs) vidéo satisfaisante dans le dossier output/.

    python generate.py                 # une vidéo d'un type au hasard
    python generate.py --type Galton   # un type précis
    python generate.py --count 3       # plusieurs vidéos
    python generate.py --list          # liste des types
    python generate.py --length long   # durée imposée : court, moyen, normal, long (>= 61 s)
"""
import argparse
import json
import os
import random
import time

import numpy as np

from satisfy.core import render_scene
from satisfy.scenes import SCENES

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", ROOT)
OUT = os.path.join(DATA, "output")
HISTORY = os.path.join(DATA, "history.json")
# Types tirés au hasard (variable SCENES, séparés par des virgules). Vide = tous les types.
POOL = [s.strip().lower() for s in os.environ.get("SCENES", "").split(",") if s.strip()]


def _history():
    try:
        with open(HISTORY, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


# Catégories de durée (secondes). « long » sert aussi de garantie : au moins une vidéo de
# plus d'une minute par semaine (TikTok favorise les vidéos de plus de 60 s).
LENGTHS = {"court": (18, 28), "moyen": (30, 42), "normal": (45, 58), "long": (62, 72)}
WEIGHTS = {"court": 0.35, "moyen": 0.30, "normal": 0.25, "long": 0.10}
LONG_MIN = 61.0


def pick_length(hist=None):
    """Durée du jour : longue si aucune vidéo >= 61 s dans les 6 dernières, sinon au hasard."""
    hist = _history() if hist is None else hist
    recent = hist[-6:]
    if not any(h.get("duration", 0) >= LONG_MIN for h in recent):
        return "long"
    return random.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]


def pick_scene(name=None, length=None):
    if name:
        for cls in SCENES:
            if cls.__name__.lower() == name.lower():
                return cls
        raise SystemExit(f"Type inconnu : {name}. Types : {', '.join(c.__name__ for c in SCENES)}")
    allowed = [c for c in SCENES if not POOL or c.__name__.lower() in POOL] or SCENES
    if length:
        allowed = [c for c in allowed if length in c.lengths] or allowed
    # Rotation équilibrée : on tire parmi les types les moins utilisés jusqu'ici, donc chaque
    # type passe une fois avant qu'un autre revienne (ordre aléatoire à chaque tour).
    hist = _history()
    counts = {c.__name__: 0 for c in allowed}
    for h in hist:
        if h.get("type") in counts:
            counts[h["type"]] += 1
    low = min(counts.values())
    pool = [c for c in allowed if counts[c.__name__] == low]
    last = hist[-1].get("type") if hist else None
    pool = [c for c in pool if c.__name__ != last] or pool
    return random.choice(pool)


def generate(name=None, seed=None, length=None):
    os.makedirs(OUT, exist_ok=True)
    if length is None and name is None:
        length = pick_length()
    cls = pick_scene(name, length)
    if length and length not in cls.lengths:
        length = cls.lengths[-1] if length == "long" else cls.lengths[0]
    seed = seed if seed is not None else random.randrange(1 << 30)
    rng = np.random.default_rng(seed)
    cls.LENGTH = float(rng.uniform(*LENGTHS[length])) if length else None
    scene = cls(rng)
    if length == "long" and not scene.loop:
        scene.min_duration = LONG_MIN + 0.5
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUT, f"{stamp}_{cls.__name__}.mp4")
    t0 = time.time()
    duration = render_scene(scene, path)
    caption = f"{scene.caption} {' '.join(scene.tags)}"
    with open(path[:-4] + ".txt", "w", encoding="utf-8") as f:
        f.write(caption + "\n")
    entry = {"file": path, "type": cls.__name__, "seed": seed, "duration": round(duration, 1), "length": length,
             "caption": caption, "created": stamp, "uploaded": False}
    hist = _history()
    hist.append(entry)
    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    print(f"[ok] {cls.__name__} [{length or 'libre'}] ({duration:.1f} s, rendu en {time.time() - t0:.0f} s) -> {path}")
    return entry


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--type")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--length", choices=list(LENGTHS), help="court, moyen, normal ou long")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for c in SCENES:
            print(f"{c.__name__:15} {'/'.join(c.lengths):26} {c.caption}")
    else:
        for _ in range(args.count):
            generate(args.type, args.seed, args.length)
