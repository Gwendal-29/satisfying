"""Routine quotidienne : génère de nouvelles vidéos puis les envoie sur TikTok.

    python daily.py                          # 1 vidéo (type et durée au hasard)
    python daily.py 3                        # 3 vidéos
    python daily.py --type PotatoMerge       # un type précis, envoyé tout de suite
    python daily.py --type PsyTrance --length long

Seules les vidéos créées par CET appel sont envoyées (jamais les anciennes vidéos de test).
Un verrou empêche deux envois de tourner en même temps (commande manuelle + 18h).
"""
import argparse
import contextlib
import json
import os
import time

from generate import DATA, HISTORY, LENGTHS, generate, pick_length
import tiktok

KEEP_DAYS = float(os.environ.get("KEEP_DAYS", "7"))
LOCK = os.path.join(DATA, "daily.lock")


@contextlib.contextmanager
def run_lock():
    """Verrou exclusif : si une génération tourne déjà, on attend qu'elle finisse."""
    try:
        import fcntl
    except ImportError:  # Windows : pas de verrou (usage manuel uniquement)
        yield
        return
    os.makedirs(DATA, exist_ok=True)
    with open(LOCK, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Une autre génération est en cours, j'attends qu'elle se termine...", flush=True)
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def cleanup():
    """Supprime les vidéos de plus de KEEP_DAYS jours (place disque du VPS)."""
    try:
        with open(HISTORY, encoding="utf-8") as f:
            hist = json.load(f)
    except (OSError, ValueError):
        return
    limit = time.time() - KEEP_DAYS * 86400
    for entry in hist:
        path = entry["file"]
        if os.path.exists(path) and os.path.getmtime(path) < limit:
            os.remove(path)
            if os.path.exists(path[:-4] + ".txt"):
                os.remove(path[:-4] + ".txt")


def run(count=1, kind=None, length=None):
    with run_lock():
        # même avec un type imposé, la durée suit la règle (au moins 1 vidéo longue par semaine)
        files = {generate(kind, length=length or pick_length())["file"] for _ in range(count)}
        if os.path.exists(tiktok.TOKENS):
            tiktok.pending(only=files)
        else:
            print("TikTok pas encore connecté (python tiktok.py auth) : vidéos gardées dans output/")
        cleanup()
    return sorted(files)


def send(path):
    """Envoie une vidéo déjà générée (bouton « Envoyer » du centre de contrôle)."""
    with run_lock():
        return tiktok.pending(only={path})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("count", nargs="?", type=int, default=1)
    ap.add_argument("--type", help="type de vidéo (voir python generate.py --list)")
    ap.add_argument("--length", choices=list(LENGTHS), help="court, moyen, normal ou long")
    args = ap.parse_args()
    run(args.count, args.type, args.length)
