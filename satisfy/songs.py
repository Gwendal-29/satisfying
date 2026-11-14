"""Mélodies très connues (toutes dans le domaine public) et petit « studio » qui les arrange :
mélodie + basse + batterie, rendues en une seule piste audio.

Utilisé par SongBounce (la bille rebondit sur chaque note) et SongRing (la musique n'avance
qu'à chaque rebond, puis joue en entier quand il y a assez de billes).
"""
import numpy as np

from .core import SR
from .marble import SONGS as _BASE

# (note MIDI, durée en temps)
SONGS = dict(_BASE)
SONGS.update({
    "Korobeïniki (Tetris)": [
        (76, 1), (71, .5), (72, .5), (74, 1), (72, .5), (71, .5), (69, 1), (69, .5), (72, .5), (76, 1), (74, .5),
        (72, .5), (71, 1.5), (72, .5), (74, 1), (76, 1), (72, 1), (69, 1), (69, 2),
        (74, 1.5), (77, .5), (81, 1), (79, .5), (77, .5), (76, 1.5), (72, .5), (76, 1), (74, .5), (72, .5),
        (71, 1), (71, .5), (72, .5), (74, 1), (76, 1), (72, 1), (69, 1), (69, 2)],
    "La Marche turque": [
        (71, .25), (69, .25), (68, .25), (69, .25), (72, 1), (74, .25), (72, .25), (71, .25), (72, .25), (76, 1),
        (77, .25), (76, .25), (75, .25), (76, .25), (83, .25), (81, .25), (80, .25), (81, .25), (83, .25),
        (81, .25), (80, .25), (81, .25), (84, 2)],
    "The Entertainer": [
        (74, .25), (75, .25), (76, .25), (84, .5), (76, .25), (84, .5), (76, .25), (84, 1.5), (84, .25), (86, .25),
        (87, .25), (88, .25), (84, .25), (86, .25), (88, .5), (83, .25), (86, .5), (84, 2)],
    "Greensleeves": [
        (69, 1), (72, 2), (74, 1), (76, 1.5), (77, .5), (76, 1), (74, 2), (71, 1), (67, 1.5), (69, .5), (71, 1),
        (72, 2), (69, 1), (69, 1.5), (68, .5), (69, 1), (71, 2), (68, 1), (64, 2)],
    "Le Lac des cygnes": [
        (78, 3), (71, .5), (73, .5), (74, .5), (76, .5), (78, 1.5), (74, .5), (78, 1.5), (74, .5), (78, 1.5),
        (71, .5), (74, .5), (71, .5), (67, .5), (74, .5), (71, 3)],
    "French cancan": [
        (60, 1), (62, .5), (65, .5), (64, .5), (62, .5), (67, 1), (67, 1), (67, .5), (69, .5), (64, .5), (65, .5),
        (62, 1), (62, 1), (62, .5), (65, .5), (64, .5), (62, .5), (60, .5), (72, .5), (71, .5), (69, .5),
        (67, .5), (65, .5), (64, .5), (62, .5), (60, 2)],
    "Canon de Pachelbel": [
        (78, 1), (76, 1), (74, 1), (73, 1), (71, 1), (69, 1), (71, 1), (73, 1),
        (74, 1), (73, 1), (71, 1), (69, 1), (67, 1), (66, 1), (67, 1), (64, 1), (66, 2)],
    "Berceuse de Brahms": [
        (64, .5), (64, .5), (67, 2), (64, .5), (64, .5), (67, 2), (64, .5), (67, .5), (72, 1), (71, 1.5), (69, .5),
        (69, 1), (67, 1), (62, .5), (64, .5), (65, 1), (62, 1), (62, .5), (64, .5), (65, 2), (62, .5), (65, .5),
        (71, .5), (69, .5), (67, 1), (71, 1), (72, 2)],
    "La Cucaracha": [
        (60, .25), (60, .25), (60, .25), (65, .75), (69, .5), (60, .25), (60, .25), (60, .25), (65, .75),
        (69, 1), (65, .5), (65, .25), (64, .25), (64, .25), (62, .25), (62, .25), (60, 1.5)],
    "Guillaume Tell": [
        (64, .25), (64, .25), (64, .5), (64, .25), (64, .25), (64, .5), (64, .25), (64, .25), (69, .5), (71, .5),
        (73, .5), (64, .25), (64, .25), (64, .5), (64, .25), (64, .25), (64, .5), (64, .25), (64, .25),
        (73, .5), (71, .5), (69, 1)],
})


def freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def song_beats(name, cut=None):
    return sum(b for _, b in SONGS[name][:cut])


def _env(n, attack, decay, release=0.0):
    t = np.arange(n) / SR
    e = np.minimum(t / attack, 1.0) * np.exp(-t / decay)
    if release:
        r = int(release * SR)
        e[-r:] *= np.linspace(1, 0, r)
    return e


def lead(f, dur):
    """Synthé « pluck » brillant : deux dents de scie légèrement désaccordées, filtre qui se referme."""
    n = int(SR * (dur + 0.25))
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 9):
        bright = np.exp(-t * k * 3.5)  # les harmoniques aiguës s'éteignent vite : son qui « claque » puis s'adoucit
        sig += (np.sin(2 * np.pi * f * k * t) + np.sin(2 * np.pi * f * 1.004 * k * t + k)) / k * bright
    hold = np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.06))
    return sig * _env(n, 0.004, 0.9) * hold * 0.22


def bass(f, dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08)
    return sig * _env(n, 0.003, 0.35, release=0.02) * 0.5


def kick(dur=0.3):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) * 0.9


def hat(rng, dur=0.05):
    n = int(SR * dur)
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, mode="same")  # passe-haut grossier
    return noise * np.exp(-np.arange(n) / SR / 0.012) * 0.25


def clap(rng, dur=0.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.convolve(rng.standard_normal(n), np.ones(3) / 3, mode="same")
    return noise * (np.exp(-t / 0.05) + 0.6 * np.exp(-((t - 0.012) % 0.012) / 0.003) * (t < 0.036)) * 0.3


def render_track(names, beat, rng, gap_beats=2, cut=None, drums=True):
    """Enchaîne les mélodies en une piste. Renvoie (piste mono, notes, sections).

    notes : [(instant, midi, n° de mélodie, dernière note ?)] ; sections : [(début, fin, nom)].
    """
    notes, sections, t = [], [], 0.0
    for s, name in enumerate(names):
        start = t
        seq = SONGS[name][:cut]
        for k, (midi, d) in enumerate(seq):
            notes.append((t, midi, s, k == len(seq) - 1))
            t += d * beat
        sections.append((start, t, name))
        t += gap_beats * beat
    total = t
    out = np.zeros(int(SR * (total + 1.0)))

    def put(at, sig, g=1.0):
        i = int(at * SR)
        seg = sig[: len(out) - i]
        out[i:i + len(seg)] += seg * g

    times = [n[0] for n in notes]
    for i, (at, midi, s, last) in enumerate(notes):
        nxt = times[i + 1] if i + 1 < len(times) and not last else at + 2 * beat
        m = midi
        while m < 67:
            m += 12  # mélodie dans un registre clair
        put(at, lead(freq(m), max(0.08, nxt - at - 0.02)))
    # basse et batterie, temps par temps, sur chaque mélodie
    for start, end, name in sections:
        seq = SONGS[name][:cut]
        on = np.cumsum([0] + [d for _, d in seq])[:-1] * beat + start
        nb = int(round((end - start) / beat))
        for b in range(nb):
            at = start + b * beat
            # basse : la note la plus grave de la mesure, deux octaves plus bas, en croches
            bar0 = start + (b // 4) * 4 * beat
            in_bar = [seq[k][0] for k in range(len(seq)) if bar0 - 1e-6 <= on[k] < bar0 + 4 * beat - 1e-6]
            root = (min(in_bar) if in_bar else seq[0][0]) % 12 + 36
            put(at, bass(freq(root), beat * 0.48))
            put(at + beat / 2, bass(freq(root + 12), beat * 0.45), 0.7)
            if drums:
                put(at, kick())
                put(at + beat / 2, hat(rng))
                if b % 2 == 1:
                    put(at, clap(rng), 0.8)
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 0.8, notes, sections
