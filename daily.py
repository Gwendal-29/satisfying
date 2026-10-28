"""Routine quotidienne : génère de nouvelles vidéos puis les envoie sur TikTok.

    python daily.py            # 1 vidéo
    python daily.py 3          # 3 vidéos
"""
import json
import os
import sys
import time

from generate import HISTORY, generate
import tiktok

KEEP_DAYS = float(os.environ.get("KEEP_DAYS", "7"))


def cleanup():
    """Supprime les vidéos déjà envoyées depuis plus de KEEP_DAYS jours (place disque du VPS)."""
    try:
        with open(HISTORY, encoding="utf-8") as f:
            hist = json.load(f)
    except (OSError, ValueError):
        return
    limit = time.time() - KEEP_DAYS * 86400
    for entry in hist:
        path = entry["file"]
        if entry.get("uploaded") and os.path.exists(path) and os.path.getmtime(path) < limit:
            os.remove(path)
            if os.path.exists(path[:-4] + ".txt"):
                os.remove(path[:-4] + ".txt")


def run(count=1):
    for _ in range(count):
        generate()
    if os.path.exists(tiktok.TOKENS):
        tiktok.pending(limit=count)
    else:
        print("TikTok pas encore connecté (python tiktok.py auth) : vidéos gardées dans output/")
    cleanup()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
