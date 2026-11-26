"""E10: which ACE-Step candidate follows the storyboard's music cues?

The cues ask for an arc: a quiet drone at 0 s, a livelier pulse from 27 s, the flute from 49 s, a tender resolution
from 62 s. For each candidate this measures, with ffmpeg only: short-term loudness (EBU R128, 3 s window) per cue
segment, loudness range, crest factor (peak over RMS, higher means more percussive) per segment, silent gaps, and
how the track ends.

    .venv/bin/python experiments/e10_music.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from common import OUT, ffmpeg, load_storyboard, log  # noqa: E402
import music  # noqa: E402
import subprocess  # noqa: E402


def ff(path, af, start=0, length=None):
    cut = ["-ss", str(start)] + (["-t", str(length)] if length else [])
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-v", "verbose", *cut, "-i", str(path), "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    return r.stderr


def short_term(path):
    """(t, short-term LUFS) every 0.1 s."""
    out = ff(path, "ebur128=framelog=verbose")
    return [(float(t), float(s)) for t, s in re.findall(r"t:\s*([\d.]+)\s+TARGET.*?S:\s*(-?[\d.]+)", out)]


def summary(path):
    out = ff(path, "ebur128")
    i = float(re.findall(r"I:\s*(-?[\d.]+) LUFS", out)[-1])
    lra = float(re.findall(r"LRA:\s*([\d.]+) LU", out)[-1])
    return i, lra


def crest(path, start, length):
    out = ff(path, "astats", start, length)
    return float(re.findall(r"Crest factor:\s*([\d.]+)", out)[-1])


def silences(path):
    out = ff(path, "silencedetect=noise=-50dB:d=1")
    return len(re.findall(r"silence_start", out))


def main():
    board = load_storyboard()
    cues = [c["at"] for c in board["music"]["cues"]] + [board["music"]["duration"]]
    segs = list(zip(cues, cues[1:]))
    for idx, path in enumerate(music.candidates(board)):
        st = short_term(path)
        seg_lufs = []
        for a, b in segs:
            vals = [s for t, s in st if a + 3 <= t <= b and s > -70]  # skip the first 3 s, the window is filling
            seg_lufs.append(round(sum(vals) / len(vals), 1) if vals else None)
        seg_crest = [round(crest(path, a, b - a), 1) for a, b in segs]
        i, lra = summary(path)
        end = [s for t, s in st if t >= st[-1][0] - 2]
        res = {"file": path.name, "integrated_lufs": i, "lra_lu": lra, "segment_lufs": seg_lufs,
               "segment_crest": seg_crest, "silent_gaps": silences(path),
               "last_2s_lufs": round(sum(end) / len(end), 1) if end else None}
        log("experiment-e10", f"candidate-{idx}", "ffmpeg", {"cues": cues}, 0, **res)
        print(idx, res)


if __name__ == "__main__":
    main()
