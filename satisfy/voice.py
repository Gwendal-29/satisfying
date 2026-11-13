"""Voix synthétique, de la meilleure à la plus simple :
Piper (voix neuronale locale et gratuite), espeak-ng, voix Windows, babillage de dessin animé.

`deep` (en demi-tons, négatif = plus grave) baisse la hauteur ET ralentit, comme un disque
qu'on freine : la voix devient de plus en plus grave et monstrueuse.
"""
import io
import os
import shutil
import subprocess
import tempfile
import wave

import numpy as np

from .core import SR


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES = os.environ.get("PIPER_DIR", os.path.join(ROOT, "voices"))
PIPER_VOICE = os.environ.get("PIPER_VOICE", "fr_FR-siwis-medium")
_piper_cache = {}


def _piper(text):
    """Piper : voix neuronale qui tourne en local (modèle .onnx dans voices/)."""
    model = os.path.join(VOICES, PIPER_VOICE + ".onnx")
    if not os.path.exists(model):
        return None
    try:
        from piper import PiperVoice
        voice = _piper_cache.get(model) or _piper_cache.setdefault(model, PiperVoice.load(model))
        chunks = list(voice.synthesize(text))
        if not chunks:
            return None
        data = np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32)
        return data, chunks[0].sample_rate
    except Exception as e:  # la voix ne doit jamais faire échouer une vidéo
        print(f"[!] Piper indisponible ({e}), voix de secours utilisée")
        return None


def _espeak(text, lang="fr"):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "-v", lang, "-s", "150", "-p", "55", "-a", "180", "--stdout", text],
                             capture_output=True, timeout=20, check=True).stdout
        with wave.open(io.BytesIO(out)) as w:
            rate = w.getframerate()
            data = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        return data, rate
    except (OSError, subprocess.SubprocessError, wave.Error, EOFError):
        return None


def _windows(text):
    """Voix Windows (SAPI), de préférence française (Microsoft Hortense)."""
    if os.name != "nt":
        return None
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v = $s.GetInstalledVoices() | ? { $_.VoiceInfo.Culture.Name -like 'fr*' } | select -First 1;"
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) };"
        f"$s.SetOutputToWaveFile('{path}');"
        "$s.Speak([Console]::In.ReadToEnd()); $s.Dispose()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", script], input=text.encode("utf-8"),
                       capture_output=True, timeout=30, check=True)
        with wave.open(path) as w:
            rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(w.getnframes())
        if width != 2 or not raw:
            return None
        data = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
        return data.reshape(-1, ch).mean(1), rate
    except (OSError, subprocess.SubprocessError, wave.Error, EOFError):
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _babble(text, rng):
    """Babillage façon personnage de jeu : syllabes voyelles avec formants."""
    vowels = [(730, 1090, 2440), (570, 840, 2410), (300, 870, 2240), (270, 2290, 3010), (530, 1840, 2480)]
    n_syl = max(2, min(10, len(text.split()) * 2))
    f0 = 210.0
    out = []
    for i in range(n_syl):
        dur = rng.uniform(0.09, 0.16)
        n = int(SR * dur)
        t = np.arange(n) / SR
        pitch = f0 * (1 + 0.12 * np.sin(i * 1.7)) * (1 - 0.15 * t / dur)
        phase = 2 * np.pi * np.cumsum(pitch) / SR
        F = vowels[int(rng.integers(len(vowels)))]
        sig = np.zeros(n)
        for k in range(1, 30):
            fk = k * pitch.mean()
            if fk > 5000:
                break
            amp = sum(np.exp(-((fk - f) / 110) ** 2) * g for f, g in zip(F, (1.0, 0.6, 0.25)))
            sig += (amp + 0.02) / k ** 0.3 * np.sin(k * phase)
        env = np.minimum(1, t / 0.015) * np.minimum(1, (dur - t) / 0.03)
        out.append(sig * env)
        out.append(np.zeros(int(SR * rng.uniform(0.01, 0.04))))
    sig = np.concatenate(out)
    return (sig / (np.abs(sig).max() + 1e-9) * 0.8).astype(np.float32), SR


def speak(text, deep=0.0, rng=None):
    """Renvoie le signal (float, SR Hz) de `text` prononcé `deep` demi-tons plus grave."""
    rng = rng or np.random.default_rng(0)
    got = _piper(text) or _espeak(text) or _windows(text) or _babble(text, rng)
    data, rate = got
    factor = 2 ** (deep / 12)  # < 1 : plus grave et plus lent
    n_out = int(len(data) * SR / rate / factor)
    x = np.linspace(0, len(data) - 1, n_out)
    sig = np.interp(x, np.arange(len(data)), data)
    return sig / (np.abs(sig).max() + 1e-9) * 0.9
