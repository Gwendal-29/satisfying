"""Génère une (ou plusieurs) vidéo satisfaisante dans le dossier output/.

    python generate.py                 # une vidéo d'un type au hasard
    python generate.py --type Galton   # un type précis
    python generate.py --count 3       # plusieurs vidéos
    python generate.py --list          # liste des types
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


def pick_scene(name=None):
    if name:
        for cls in SCENES:
            if cls.__name__.lower() == name.lower():
                return cls
        raise SystemExit(f"Type inconnu : {name}. Types : {', '.join(c.__name__ for c in SCENES)}")
    allowed = [c for c in SCENES if not POOL or c.__name__.lower() in POOL] or SCENES
    # Évite de reposter le même type que les dernières vidéos.
    skip = min(3, len(allowed) // 2)
    recent = [h["type"] for h in _history()[-skip:]] if skip else []
    pool = [c for c in allowed if c.__name__ not in recent] or allowed
    return random.choice(pool)


def generate(name=None, seed=None):
    os.makedirs(OUT, exist_ok=True)
    cls = pick_scene(name)
    seed = seed if seed is not None else random.randrange(1 << 30)
    scene = cls(np.random.default_rng(seed))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUT, f"{stamp}_{cls.__name__}.mp4")
    t0 = time.time()
    duration = render_scene(scene, path)
    caption = f"{scene.caption} {' '.join(scene.tags)}"
    with open(path[:-4] + ".txt", "w", encoding="utf-8") as f:
        f.write(caption + "\n")
    entry = {"file": path, "type": cls.__name__, "seed": seed, "duration": round(duration, 1),
             "caption": caption, "created": stamp, "uploaded": False}
    hist = _history()
    hist.append(entry)
    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    print(f"[ok] {cls.__name__} ({duration:.1f} s, rendu en {time.time() - t0:.0f} s) -> {path}")
    return entry


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--type")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for c in SCENES:
            print(f"{c.__name__:14} {c.caption}")
    else:
        for _ in range(args.count):
            generate(args.type, args.seed)
