"""Réglages modifiables depuis le centre de contrôle (fichier DATA_DIR/settings.json).

Au premier lancement, les valeurs viennent du .env (POST_TIMES, VIDEOS_PER_RUN, SCENES).
Ensuite le site web écrit dans settings.json et tout le reste le relit à chaque utilisation :
pas besoin de redémarrer quoi que ce soit après un changement.
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", ROOT)
PATH = os.path.join(DATA, "settings.json")

LENGTH_NAMES = ("court", "moyen", "normal", "long")


def defaults():
    times = [t.strip() for t in os.environ.get("POST_TIMES", "18:00").split(",") if t.strip()]
    types = [s.strip() for s in os.environ.get("SCENES", "").split(",") if s.strip()]
    return {
        "paused": False,
        "times": times,                       # heures de publication, chaque jour
        "per_run": int(os.environ.get("VIDEOS_PER_RUN", "1")),
        "types": types,                       # vide = tous les types
        "weights": {"court": 35, "moyen": 30, "normal": 25, "long": 10},
        "weekly_long": True,                  # au moins une vidéo de plus de 61 s par semaine
    }


def _valid_time(t):
    try:
        datetime.time.fromisoformat(t)
        return True
    except (TypeError, ValueError):
        return False


def clean(s):
    """Normalise des réglages (venant du site) : jamais de valeur qui ferait planter le planificateur."""
    d = defaults()
    out = dict(d)
    out["paused"] = bool(s.get("paused", d["paused"]))
    times = sorted({t.strip()[:5] for t in s.get("times", d["times"]) if isinstance(t, str) and _valid_time(t.strip()[:5])})
    out["times"] = times
    try:
        out["per_run"] = max(1, min(5, int(s.get("per_run", d["per_run"]))))
    except (TypeError, ValueError):
        pass
    out["types"] = [t for t in s.get("types", d["types"]) if isinstance(t, str)]
    w = s.get("weights", d["weights"])
    out["weights"] = {k: max(0, min(100, int(w.get(k, d["weights"][k]) or 0))) for k in LENGTH_NAMES}
    if not any(out["weights"].values()):
        out["weights"] = d["weights"]
    out["weekly_long"] = bool(s.get("weekly_long", d["weekly_long"]))
    return out


def load():
    try:
        with open(PATH, encoding="utf-8") as f:
            return clean(json.load(f))
    except (OSError, ValueError):
        return defaults()


def save(s):
    s = clean(s)
    os.makedirs(DATA, exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PATH)
    return s


def next_run(now=None, s=None):
    """Prochain créneau de publication (None si en pause ou aucun horaire)."""
    s = s or load()
    now = now or datetime.datetime.now()
    if s["paused"] or not s["times"]:
        return None
    for day in range(2):
        for t in s["times"]:
            when = datetime.datetime.combine(now.date() + datetime.timedelta(days=day), datetime.time.fromisoformat(t))
            if when > now:
                return when
    return None
