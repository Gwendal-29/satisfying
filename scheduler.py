"""Processus principal du conteneur : génère et envoie les vidéos aux heures choisies.

Les horaires, le nombre de vidéos, les types et la pause se règlent dans le centre de contrôle
(panel.py) et sont relus toutes les 30 secondes : aucun redémarrage nécessaire.
Au premier lancement, les valeurs viennent du .env (POST_TIMES, VIDEOS_PER_RUN, SCENES).
RUN_ON_START=1 : publie aussi une vidéo au démarrage (pratique pour tester).
"""
import datetime
import json
import os
import time
import traceback

import daily
import notify
import settings

STATE = os.path.join(settings.DATA, "scheduler_state.json")
CATCH_UP = datetime.timedelta(hours=2)  # créneau raté (VPS éteint...) : rattrapé s'il date de moins de 2 h


def _load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return datetime.datetime.fromisoformat(json.load(f)["last"])
    except (OSError, ValueError, KeyError):
        return None


def _save_state(last):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"last": last.isoformat(timespec="seconds")}, f)


def due_slot(now, s, last):
    """Le créneau d'aujourd'hui (ou d'hier soir) qui doit être lancé maintenant, s'il y en a un."""
    slots = []
    for day in (now.date() - datetime.timedelta(days=1), now.date()):
        for t in s["times"]:
            slots.append(datetime.datetime.combine(day, datetime.time.fromisoformat(t)))
    due = [x for x in slots if x <= now and (last is None or x > last) and now - x < CATCH_UP]
    return max(due) if due else None


def job(count):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] génération + envoi de {count} vidéo(s)", flush=True)
    try:
        daily.run(count)
    except BaseException as e:  # SystemExit des erreurs TikTok compris : le planificateur continue
        if isinstance(e, KeyboardInterrupt):
            raise
        traceback.print_exc()
        notify.error(traceback.format_exc())


if __name__ == "__main__":
    os.makedirs(settings.DATA, exist_ok=True)
    last = _load_state()
    if last is None:  # premier lancement : on ne rattrape pas les créneaux déjà passés aujourd'hui
        last = datetime.datetime.now()
        _save_state(last)
    if os.environ.get("RUN_ON_START") == "1":
        job(settings.load()["per_run"])
    shown = None
    while True:
        s = settings.load()
        now = datetime.datetime.now()
        # le centre de contrôle avance ce repère quand il change les horaires : un horaire
        # ajouté dans le passé ne déclenche donc pas de vidéo surprise
        saved = _load_state()
        if saved and saved > last:
            last = saved
        slot = due_slot(now, s, last)
        if slot is not None:
            last = slot
            _save_state(last)
            if s["paused"]:
                print(f"[{now:%Y-%m-%d %H:%M}] créneau {slot:%H:%M} ignoré : publication en pause", flush=True)
            else:
                job(s["per_run"])
        nxt = settings.next_run(datetime.datetime.now(), s)
        msg = f"Prochaine vidéo : {nxt:%Y-%m-%d %H:%M}" if nxt else "Publication en pause (ou aucun horaire)"
        if msg != shown:
            print(msg, flush=True)
            shown = msg
        time.sleep(30)
