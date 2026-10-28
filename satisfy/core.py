"""Socle commun : dessin (cairo), encodage vidéo (ffmpeg) et synthèse audio (numpy)."""
import colorsys
import math
import os
import subprocess
import tempfile
import wave

import cairo
import imageio_ffmpeg
import numpy as np

W, H, FPS = 1080, 1920, 60
SR = 44100
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT = os.environ.get("FONT", "Segoe UI Black" if os.name == "nt" else "DejaVu Sans")

# Gamme pentatonique majeure : n'importe quelle suite de notes sonne juste.
PENTA = [0, 2, 4, 7, 9]


def note_freq(step, base=261.63):
    """Fréquence du `step`-ième degré de la pentatonique à partir de `base` (do4)."""
    octave, degree = divmod(step, len(PENTA))
    return base * 2 ** (octave + PENTA[degree] / 12)


def hsv(h, s=0.85, v=1.0):
    return colorsys.hsv_to_rgb(h % 1.0, s, v)


# ---------------------------------------------------------------- dessin

def background(ctx, top=(0.04, 0.04, 0.08), bottom=(0.0, 0.0, 0.02)):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bottom)
    ctx.set_source(g)
    ctx.paint()


def circle(ctx, x, y, r, rgb, alpha=1.0):
    ctx.set_source_rgba(*rgb, alpha)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def ring(ctx, x, y, r, rgb, width, alpha=1.0, a0=0.0, a1=2 * math.pi):
    ctx.set_source_rgba(*rgb, alpha)
    ctx.set_line_width(width)
    ctx.new_sub_path()
    ctx.arc(x, y, r, a0, a1)
    ctx.stroke()


def glow(ctx, x, y, r, rgb, strength=0.6, spread=3.0):
    g = cairo.RadialGradient(x, y, r * 0.5, x, y, r * spread)
    g.add_color_stop_rgba(0, *rgb, strength)
    g.add_color_stop_rgba(1, *rgb, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r * spread, 0, 2 * math.pi)
    ctx.fill()


def text(ctx, s, x, y, size, rgb=(1, 1, 1), alpha=1.0, outline=True):
    """Texte centré horizontalement sur x, ligne de base en y."""
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ext = ctx.text_extents(s)
    if ext.width > W - 100:  # les polices Linux sont plus larges : on réduit pour tenir dans l'écran
        size *= (W - 100) / ext.width
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
    ctx.move_to(x - ext.width / 2 - ext.x_bearing, y)
    ctx.text_path(s)
    if outline:
        ctx.set_source_rgba(0, 0, 0, 0.85 * alpha)
        ctx.set_line_width(size * 0.12)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*rgb, alpha)
    ctx.fill()


def hook(ctx, title, subtitle=None, t=0.0):
    """Accroche en haut de l'écran (zone non masquée par l'interface TikTok)."""
    pulse = 1 + 0.03 * math.sin(t * 6)
    text(ctx, title, W / 2, 300, 78 * pulse)
    if subtitle:
        text(ctx, subtitle, W / 2, 390, 48, (1, 0.85, 0.3))


# ---------------------------------------------------------------- audio

def _env(n, attack=0.002, decay=0.4):
    t = np.arange(n) / SR
    a = np.minimum(t / attack, 1.0)
    return a * np.exp(-t / decay)


def bell(freq, dur=1.2, decay=0.35):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * freq * t)
           + 0.5 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t / (decay * 0.5))
           + 0.25 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t / (decay * 0.3)))
    return sig * _env(n, decay=decay) * 0.5


def marimba(freq, dur=0.8):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t / 0.03)
    return sig * _env(n, attack=0.001, decay=0.18) * 0.6


def pop(freq=600, dur=0.12):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = freq * (1 + 1.5 * np.exp(-t / 0.01))
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * _env(n, attack=0.0005, decay=0.03) * 0.7


def tick(rng, dur=0.04, bright=0.5):
    n = int(SR * dur)
    noise = rng.standard_normal(n)
    k = max(1, int(8 * (1 - bright)) + 1)
    noise = np.convolve(noise, np.ones(k) / k, mode="same")
    return noise * _env(n, attack=0.0003, decay=0.006) * 0.5


def beep(freq, dur=0.05):
    n = int(SR * dur)
    t = np.arange(n) / SR
    tri = 2 * np.abs(2 * (t * freq % 1) - 1) - 1
    return tri * np.minimum(1, (n - np.arange(n)) / (SR * 0.01)) * np.minimum(1, np.arange(n) / 50) * 0.25


def shatter(rng, dur=0.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n) * np.exp(-t / 0.08)
    sparkle = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / 0.15)
                  for f in rng.uniform(2000, 6000, 6)) / 6
    return (0.35 * noise + 0.5 * sparkle) * np.minimum(1, np.arange(n) / 30)


def whoosh(rng, dur=0.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.convolve(rng.standard_normal(n), np.ones(12) / 12, mode="same")
    return noise * np.sin(np.pi * t / dur) ** 2 * 0.8


def pad(duration, freqs, gain=0.06, loop=False):
    """Nappe douce en fond : comble les silences, garde l'oreille accrochée.

    En boucle, chaque fréquence fait un nombre entier de cycles sur la durée : pas de
    fondu ni de raccord audible quand la vidéo recommence.
    """
    n = int(SR * duration)
    t = np.arange(n) / SR
    lfo = 0.1
    if loop:
        freqs = [round(f * duration) / duration for f in freqs]
        lfo = max(1, round(lfo * duration)) / duration
    sig = sum(np.sin(2 * np.pi * f * t + i) * (1 + 0.3 * np.sin(2 * np.pi * lfo * t + i))
              for i, f in enumerate(freqs))
    fade = 1.0 if loop else np.minimum(1, np.minimum(t / 2.0, (duration - t) / 1.5))
    return sig / len(freqs) * fade * gain


class Audio:
    def __init__(self):
        self.events = []  # (temps, signal, gain, pan)

    def add(self, t, sig, gain=1.0, pan=0.0):
        self.events.append((t, sig, gain, max(-1.0, min(1.0, pan))))

    def render(self, duration, path, bed=None, loop=False):
        n = int(SR * duration)
        tail = 4 * SR
        out = np.zeros((n + tail, 2))
        if bed is not None:
            m = min(n, len(bed))
            out[:m] += bed[:m, None]
        for t, sig, gain, pan in self.events:
            i = int(t * SR)
            if i >= n:
                continue
            seg = sig[: n + tail - i] * gain
            out[i:i + len(seg), 0] += seg * math.sqrt((1 - pan) / 2)
            out[i:i + len(seg), 1] += seg * math.sqrt((1 + pan) / 2)
        if loop:
            # Les sons qui dépassent la fin reprennent au début : la boucle est inaudible.
            out[:tail] += out[n:]
        out = out[:n]
        # Limiteur doux : évite la saturation quand beaucoup d'événements se superposent.
        peak = np.percentile(np.abs(out), 99.9) or 1.0
        out = np.tanh(out / peak * 0.9) * 0.9
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((out * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- rendu

class Scene:
    """Une scène dessine une image à la fois dans `draw` et ajoute ses sons dans `self.audio`.

    Elle met `self.done = True` quand l'animation est terminée ; on ajoute alors
    `outro` secondes pour laisser respirer la fin avant que la vidéo boucle.
    """
    max_duration = 55.0
    outro = 1.5
    loop = False  # True : vidéo qui boucle parfaitement, durée exacte = max_duration
    title = ""
    caption = ""
    bed_freqs = (130.81, 196.0, 261.63)

    def __init__(self, rng):
        self.rng = rng
        self.audio = Audio()
        self.done = False

    def draw(self, ctx, t, frame):
        raise NotImplementedError


def render_scene(scene, out_path):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)
    tmp = tempfile.mkdtemp(prefix="satisfy_")
    video_tmp = os.path.join(tmp, "video.mp4")
    wav_tmp = os.path.join(tmp, "audio.wav")

    enc = subprocess.Popen(
        [FFMPEG, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", video_tmp],
        stdin=subprocess.PIPE)

    frame, done_at = 0, None
    max_frames = round(scene.max_duration * FPS)
    while frame < max_frames:
        t = frame / FPS
        ctx.save()
        scene.draw(ctx, t, frame)
        ctx.restore()
        surface.flush()
        enc.stdin.write(bytes(surface.get_data()))
        frame += 1
        if scene.done and done_at is None:
            done_at = frame
        if not scene.loop and done_at is not None and frame - done_at >= scene.outro * FPS:
            break
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("échec de l'encodage vidéo")

    duration = frame / FPS
    scene.audio.render(duration, wav_tmp, bed=pad(duration, scene.bed_freqs, loop=scene.loop), loop=scene.loop)
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", video_tmp, "-i", wav_tmp,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path],
        check=True)
    for p in (video_tmp, wav_tmp):
        os.remove(p)
    os.rmdir(tmp)
    return duration
