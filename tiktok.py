"""Envoi des vidéos sur TikTok (Content Posting API).

    python tiktok.py auth            # une seule fois : connexion au compte TikTok
    python tiktok.py auth --manual   # idem sur un serveur sans navigateur (VPS / Docker)
    python tiktok.py upload FICHIER  # envoie une vidéo
    python tiktok.py pending         # envoie toutes les vidéos générées pas encore envoyées

Deux modes (variable TIKTOK_MODE) :
  draft  : la vidéo arrive dans la boîte de réception de l'app TikTok, tu la publies d'un clic.
  direct : publication directe avec la légende. Tant que TikTok n'a pas audité ton app,
           les vidéos sont forcément privées (SELF_ONLY).
"""
import hashlib
import http.server
import json
import os
import secrets
import sys
import time
import urllib.parse
import webbrowser

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", ROOT)
CONFIG = os.path.join(DATA, "config.json")
TOKENS = os.path.join(DATA, "tokens.json")
HISTORY = os.path.join(DATA, "history.json")
API = "https://open.tiktokapis.com/v2"
PORT = 3455
REDIRECT = f"http://localhost:{PORT}/callback/"
MB = 1024 * 1024
MODE = os.environ.get("TIKTOK_MODE", "draft").lower()
PRIVACY = os.environ.get("TIKTOK_PRIVACY", "PUBLIC_TO_EVERYONE")


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _config():
    cfg = _load(CONFIG) or {}
    cfg = {"client_key": os.environ.get("TIKTOK_CLIENT_KEY") or cfg.get("client_key", ""),
           "client_secret": os.environ.get("TIKTOK_CLIENT_SECRET") or cfg.get("client_secret", "")}
    if not cfg["client_key"] or "XXX" in cfg["client_key"]:
        raise SystemExit("Renseigne TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET (fichier .env ou config.json, voir README.md).")
    return cfg


def _token_request(cfg, **params):
    r = requests.post(f"{API}/oauth/token/", data={
        "client_key": cfg["client_key"], "client_secret": cfg["client_secret"], **params})
    data = r.json()
    if "access_token" not in data:
        raise SystemExit(f"Erreur TikTok OAuth : {data}")
    data["expires_at"] = time.time() + data["expires_in"] - 60
    _save(TOKENS, data)
    return data


def _wait_callback():
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>C'est bon, tu peux fermer cette page.</h2>".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()
    return result


def auth(manual=False):
    cfg = _config()
    verifier = secrets.token_urlsafe(64)[:96]
    state = secrets.token_urlsafe(16)
    scopes = "user.info.basic,video.upload" + (",video.publish" if MODE == "direct" else "")
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
        "client_key": cfg["client_key"], "response_type": "code", "scope": scopes,
        "redirect_uri": REDIRECT, "state": state,
        # TikTok attend le SHA256 en hexadécimal (et non en base64url comme la RFC 7636).
        "code_challenge": hashlib.sha256(verifier.encode()).hexdigest(), "code_challenge_method": "S256"})
    if manual:
        print("1. Ouvre ce lien sur ton PC ou ton téléphone et accepte :\n\n" + url + "\n")
        print("2. Le navigateur affiche ensuite une page d'erreur « localhost » : c'est normal.")
        back = input("3. Copie l'adresse complète de cette page et colle-la ici : ").strip()
        result = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(back).query).items()}
    else:
        print("Ouverture du navigateur pour te connecter à TikTok...\n" + url)
        webbrowser.open(url)
        result = _wait_callback()
    if result.get("state") != state or "code" not in result:
        raise SystemExit(f"Connexion refusée ou invalide : {result}")
    _token_request(cfg, code=result["code"], grant_type="authorization_code",
                   redirect_uri=REDIRECT, code_verifier=verifier)
    print(f"[ok] Compte TikTok connecté. Jeton enregistré dans {TOKENS}")


def access_token():
    tok = _load(TOKENS)
    if not tok:
        raise SystemExit("Pas encore connecté : lance d'abord  python tiktok.py auth")
    if time.time() > tok["expires_at"]:
        tok = _token_request(_config(), grant_type="refresh_token", refresh_token=tok["refresh_token"])
    return tok["access_token"]


def _api(token, path, body):
    r = requests.post(f"{API}{path}", json=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    data = r.json()
    if data.get("error", {}).get("code") != "ok":
        raise SystemExit(f"Erreur TikTok {path} : {data}")
    return data.get("data", {})


def _chunks(size):
    """Découpage imposé par TikTok : morceaux de 5 à 64 Mo, le reste fusionné dans le dernier."""
    if size <= 64 * MB:
        return size, 1
    chunk = 32 * MB
    return chunk, size // chunk


def _post_info(token, caption):
    options = _api(token, "/post/publish/creator_info/query/", {}).get("privacy_level_options", [])
    privacy = PRIVACY if PRIVACY in options else ("SELF_ONLY" if "SELF_ONLY" in options else options[0])
    if privacy != PRIVACY:
        print(f"[!] {PRIVACY} non autorisé pour ce compte/app, publication en {privacy}")
    return {"title": caption[:2200], "privacy_level": privacy, "disable_comment": False,
            "disable_duet": False, "disable_stitch": False, "video_cover_timestamp_ms": 1000}


def upload(path, caption=""):
    token = access_token()
    size = os.path.getsize(path)
    chunk, count = _chunks(size)
    source = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}
    if MODE == "direct":
        data = _api(token, "/post/publish/video/init/", {"post_info": _post_info(token, caption), "source_info": source})
    else:
        data = _api(token, "/post/publish/inbox/video/init/", {"source_info": source})
    publish_id, upload_url = data["publish_id"], data["upload_url"]

    with open(path, "rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1
            f.seek(start)
            body = f.read(end - start + 1)
            put = requests.put(upload_url, data=body, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(body)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            if put.status_code not in (200, 201, 206):
                raise SystemExit(f"Erreur envoi morceau {i + 1}/{count} : {put.status_code} {put.text}")

    status = None
    for _ in range(60):
        st = _api(token, "/post/publish/status/fetch/", {"publish_id": publish_id})
        status = st.get("status")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            break
        time.sleep(5)
    if status == "FAILED":
        raise SystemExit(f"TikTok a refusé la vidéo : {st}")
    where = "publiée" if MODE == "direct" else "envoyée dans tes brouillons TikTok"
    print(f"[ok] {os.path.basename(path)} {where} (statut : {status})")
    return publish_id


def pending(limit=None):
    hist = _load(HISTORY, [])
    sent = 0
    for entry in hist:
        if limit is not None and sent >= limit:
            break
        if not entry.get("uploaded") and os.path.exists(entry["file"]):
            if sent:
                time.sleep(15)  # TikTok limite le nombre d'envois par minute
            entry["publish_id"] = upload(entry["file"], entry.get("caption", ""))
            entry["uploaded"] = True
            entry["uploaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save(HISTORY, hist)
            sent += 1
    return sent


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "auth":
        auth(manual="--manual" in sys.argv)
    elif cmd == "upload" and len(sys.argv) > 2:
        upload(sys.argv[2])
    elif cmd == "pending":
        pending()
    else:
        print(__doc__)
