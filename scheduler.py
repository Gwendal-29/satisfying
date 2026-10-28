"""Processus principal du conteneur : lance daily.run() aux heures de POST_TIMES, chaque jour.

Variables : POST_TIMES="18:00" (plusieurs possibles : "12:30,19:00"), TZ="Europe/Paris",
VIDEOS_PER_RUN=1, RUN_ON_START=0 (1 = publie aussi une vidéo au démarrage, pratique pour tester).
"""
import datetime
import os
import time
import traceback

import daily

TIMES = sorted(datetime.time.fromisoformat(t.strip()) for t in os.environ.get("POST_TIMES", "18:00").split(","))
COUNT = int(os.environ.get("VIDEOS_PER_RUN", "1"))


def next_run(now):
    for day in range(2):
        for t in TIMES:
            when = datetime.datetime.combine(now.date() + datetime.timedelta(days=day), t)
            if when > now:
                return when


def job():
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] génération + envoi de {COUNT} vidéo(s)", flush=True)
    try:
        daily.run(COUNT)
    except BaseException as e:  # SystemExit des erreurs TikTok compris : le planificateur continue
        if isinstance(e, KeyboardInterrupt):
            raise
        traceback.print_exc()


if __name__ == "__main__":
    if os.environ.get("RUN_ON_START") == "1":
        job()
    while True:
        when = next_run(datetime.datetime.now())
        print(f"Prochaine vidéo : {when:%Y-%m-%d %H:%M}", flush=True)
        while datetime.datetime.now() < when:
            time.sleep(min(60, max(1, (when - datetime.datetime.now()).total_seconds())))
        job()
