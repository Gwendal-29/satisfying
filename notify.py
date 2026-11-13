"""Notifications Discord (webhook) : la légende de chaque vidéo, prête à copier-coller dans TikTok.

Mets l'URL du webhook dans DISCORD_WEBHOOK_URL (.env). Sans URL, rien n'est envoyé.

    python notify.py test    # envoie un message de test
"""
import os
import sys

import requests

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()


def _post(content):
    if not WEBHOOK:
        return False
    try:
        r = requests.post(WEBHOOK, json={"content": content[:2000], "username": "Vidéos satisfaisantes"},
                          timeout=15)
        if r.status_code >= 300:
            print(f"[!] Discord a refusé le message : {r.status_code} {r.text[:200]}")
            return False
        return True
    except requests.RequestException as e:  # une notification ratée ne doit jamais bloquer l'envoi
        print(f"[!] Discord injoignable : {e}")
        return False


def video_ready(kind, duration, caption, where="dans tes brouillons TikTok"):
    """Deux messages : l'info, puis la légende seule (appui long → Copier le texte)."""
    _post(f"🎬 **Nouvelle vidéo {where}** : {kind} ({duration:.0f} s)\n"
          "Copie la légende ci-dessous, ouvre le brouillon et colle-la avant de publier 👇")
    _post(caption)


def error(message):
    _post(f"⚠️ **Problème avec la vidéo du jour**\n```{message[-1800:]}```")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        if not WEBHOOK:
            raise SystemExit("DISCORD_WEBHOOK_URL n'est pas défini dans .env")
        ok = _post("✅ Le webhook fonctionne : tu recevras ici la légende de chaque vidéo.")
        print("Message envoyé." if ok else "Échec de l'envoi.")
    else:
        print(__doc__)
