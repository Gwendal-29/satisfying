"""Centre de contrôle web : planning, types de vidéos, durées, envoi immédiat, historique.

    python panel.py            # http://0.0.0.0:8090 (dans Docker : port publié sur le VPS)

Pensé pour être ouvert depuis le téléphone via Tailscale. Optionnel : PANEL_PASSWORD
(identifiant au choix + ce mot de passe, demandé par le navigateur).
"""
import base64
import contextlib
import datetime
import hmac
import io
import json
import os
import re
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import daily
import generate
import notify
import settings
import tiktok
from satisfy.scenes import SCENES

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PANEL_PORT", "8090"))
PASSWORD = os.environ.get("PANEL_PASSWORD", "")

# Nom affiché et rubrique de chaque type dans l'interface
LABELS = {
    "PotatoMerge": ("Patates qui fusionnent", "Patates"),
    "PotatoRace": ("Course de patates", "Patates"),
    "PotatoSplit": ("Patate géante qui se divise", "Patates"),
    "PotatoEscape": ("Patate qui s'échappe (solo / duel)", "Patates"),
    "PotatoDuel": ("Duel de patates (deux équipes)", "Patates"),
    "PlanetMerge": ("Planètes qui fusionnent", "Fusions"),
    "SlimeMerge": ("Slimes qui fusionnent", "Fusions"),
    "EscapeRings": ("Balle qui sort des anneaux", "Balles et évasions"),
    "EscapeBox": ("Boîte qui libère des billes", "Balles et évasions"),
    "RingCountdown": ("Anneaux arc-en-ciel à briser", "Balles et évasions"),
    "ShapeEscape": ("Formes à quitter (solo / duel)", "Balles et évasions"),
    "SplitBalls": ("Balle qui se divise", "Balles et évasions"),
    "ClockSweep": ("Aiguilles d'horloge et billes", "Balles et évasions"),
    "GearArcs": ("Engrenage et arcs", "Balles et évasions"),
    "Katana": ("Katana qui coupe les balles", "Balles et évasions"),
    "GrowingBall": ("Balle qui grandit", "Balles et évasions"),
    "Multiply": ("Balles qui se multiplient", "Balles et évasions"),
    "InfiniteCube": ("Cube infini (boucle)", "3D et illusions"),
    "InfiniteSpiral": ("Spirale hypnotique (boucle)", "3D et illusions"),
    "PinArt": ("Plaque 3D qui se déforme (boucle)", "3D et illusions"),
    "ParticleMorph": ("Particules 3D qui se transforment", "3D et illusions"),
    "SongBounce": ("Bille qui rebondit sur chaque note", "Musique"),
    "SongRing": ("Musique hachée qui finit en entier", "Musique"),
    "MarbleMelody": ("Bille musicale (top mélodies)", "Musique"),
    "PsyTrance": ("Psytrance hypnotique", "Musique"),
    "Polyrhythm": ("Polyrythmie", "Musique"),
    "Sorting": ("Le son d'un tri", "Autres"),
    "PendulumWave": ("Vague de pendules", "Autres"),
    "Galton": ("Planche de Galton", "Autres"),
}
GROUPS = ["Patates", "Fusions", "Balles et évasions", "3D et illusions", "Musique", "Autres"]


# ------------------------------------------------------------------ tâche en arrière-plan

class Job:
    """Une seule génération à la fois depuis le site (le verrou de daily gère aussi 18 h)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state = {"running": False}

    def snapshot(self):
        with self.lock:
            s = dict(self.state)
            s["log"] = list(s.get("log", []))[-12:]
            if s.get("started"):
                s["elapsed"] = int((s.get("ended") or time.time()) - s["started"])
            return s

    def _log(self, line):
        with self.lock:
            self.state.setdefault("log", []).append(line)

    def start(self, label, fn):
        with self.lock:
            if self.state.get("running"):
                return False
            self.state = {"running": True, "label": label, "started": time.time(), "log": [], "files": []}
        threading.Thread(target=self._run, args=(fn,), daemon=True).start()
        return True

    def _run(self, fn):
        job = self

        class Tee(io.TextIOBase):
            def write(self, s):
                sys.__stdout__.write(s)
                for line in s.splitlines():
                    if line.strip():
                        job._log(line.strip())
                return len(s)

        ok, files, error = True, [], None
        try:
            with contextlib.redirect_stdout(Tee()):
                files = fn() or []
        except BaseException as e:  # SystemExit des erreurs TikTok compris
            ok = False
            error = str(e) or e.__class__.__name__
            traceback.print_exc()
            notify.error(traceback.format_exc())
        with self.lock:
            self.state.update(running=False, ok=ok, error=error, files=list(files) if isinstance(files, (list, set)) else [],
                              ended=time.time())


JOB = Job()


# ------------------------------------------------------------------ données pour l'interface

def _entry_view(e):
    name = os.path.basename(e["file"])
    exists = os.path.exists(e["file"])
    return {
        "file": e["file"], "name": name, "type": e.get("type"),
        "label": LABELS.get(e.get("type"), (e.get("type"), ""))[0],
        "duration": e.get("duration"), "length": e.get("length"),
        "created": e.get("created"), "caption": e.get("caption", ""),
        "uploaded": bool(e.get("uploaded")), "uploaded_at": e.get("uploaded_at"),
        "exists": exists, "url": f"/media/{name}" if exists else None,
    }


def state():
    s = settings.load()
    nxt = settings.next_run(datetime.datetime.now(), s)
    hist = generate._history()
    scenes = [{"name": c.__name__, "label": LABELS.get(c.__name__, (c.__name__, "Autres"))[0],
               "group": LABELS.get(c.__name__, (c.__name__, "Autres"))[1], "lengths": list(c.lengths)}
              for c in SCENES]
    return {
        "settings": s,
        "env_types": [t for t in os.environ.get("SCENES", "").split(",") if t.strip()],
        "scenes": scenes, "groups": GROUPS,
        "next_run": nxt.strftime("%Y-%m-%d %H:%M") if nxt else None,
        "now": datetime.datetime.now().strftime("%H:%M"),
        "history": [_entry_view(e) for e in reversed(hist[-40:])],
        "job": JOB.snapshot(),
        "tiktok": os.path.exists(tiktok.TOKENS),
        "mode": tiktok.MODE,
        "discord": bool(notify.WEBHOOK),
    }


def _bump_scheduler():
    """Après un changement d'horaires : seuls les créneaux à venir comptent (pas de vidéo surprise)."""
    import scheduler
    scheduler._save_state(datetime.datetime.now())


# ------------------------------------------------------------------ serveur HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "CentreDeControle/1.0"

    def log_message(self, fmt, *args):
        pass

    def _auth(self):
        if not PASSWORD:
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                _, pw = base64.b64decode(h[6:]).decode().split(":", 1)
                if hmac.compare_digest(pw, PASSWORD):
                    return True
            except (ValueError, UnicodeDecodeError):
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Centre de controle"')
        self.end_headers()
        return False

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 100_000:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        if not self._auth():
            return
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(os.path.join(ROOT, "panel.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/state":
            self._json(state())
        elif path.startswith("/media/"):
            self._media(unquote(path[len("/media/"):]))
        else:
            self._json({"error": "introuvable"}, 404)

    def do_POST(self):
        if not self._auth():
            return
        path = urlparse(self.path).path
        body = self._body()
        if path == "/api/settings":
            old = settings.load()
            new = settings.save({**old, **body})
            if new["times"] != old["times"] or new["paused"] != old["paused"]:
                _bump_scheduler()
            self._json({"ok": True, "settings": new})
        elif path == "/api/run":
            kind = body.get("type") or None
            if kind and kind not in {c.__name__ for c in SCENES}:
                return self._json({"ok": False, "error": "type inconnu"}, 400)
            length = body.get("length") if body.get("length") in settings.LENGTH_NAMES else None
            label = LABELS.get(kind, ("Type au hasard", ""))[0] if kind else "Type au hasard"
            started = JOB.start(label, lambda: daily.run(1, kind, length))
            self._json({"ok": started, "error": None if started else "une génération est déjà en cours"})
        elif path == "/api/send":
            f = body.get("file", "")
            known = {e["file"] for e in generate._history()}
            if f not in known or not os.path.exists(f):
                return self._json({"ok": False, "error": "vidéo introuvable"}, 404)
            started = JOB.start("Envoi d'une vidéo déjà prête", lambda: (daily.send(f), [f])[1])
            self._json({"ok": started, "error": None if started else "une tâche est déjà en cours"})
        else:
            self._json({"error": "introuvable"}, 404)

    def _media(self, name):
        if not re.fullmatch(r"[\w.-]+\.mp4", name):
            return self._json({"error": "nom invalide"}, 400)
        path = os.path.join(generate.OUT, name)
        if not os.path.isfile(path):
            return self._json({"error": "introuvable"}, 404)
        size = os.path.getsize(path)
        start, end = 0, size - 1
        rng = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if rng and (rng.group(1) or rng.group(2)):
            if rng.group(1):
                start = int(rng.group(1))
                end = min(int(rng.group(2)), size - 1) if rng.group(2) else size - 1
            else:
                start = max(0, size - int(rng.group(2)))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(256 * 1024, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    print(f"Centre de contrôle : http://0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
