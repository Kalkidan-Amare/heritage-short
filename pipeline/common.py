"""Shared plumbing for every stage: storyboard loading and validation, the content-addressed cache,
the runs.jsonl call log, retries and the ffmpeg binary."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import jsonschema
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Tests point these at a temporary folder so they never touch the real outputs or call log.
OUT = Path(os.environ.get("PIPELINE_OUT", ROOT / "outputs"))
RUNS = Path(os.environ.get("PIPELINE_RUNS", ROOT / "runs.jsonl"))
load_dotenv(ROOT / ".env")


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_storyboard(path=None):
    path = Path(path or os.environ.get("STORYBOARD", "storyboard.json"))
    if not path.is_absolute():
        path = ROOT / path
    board = json.loads(path.read_text())
    schema = json.loads((ROOT / "schema" / "storyboard.schema.json").read_text())
    jsonschema.validate(board, schema)
    ids = [s["id"] for s in board["shots"]]
    if len(ids) != len(set(ids)):
        raise jsonschema.ValidationError(f"duplicate shot ids: {ids}")
    return board


def key(*parts):
    """Cache key: a hash of everything that changes a stage's output for one item."""
    def file_hash(o):
        if isinstance(o, Path):
            return "file:" + hashlib.sha256(o.read_bytes()).hexdigest()
        raise TypeError(f"cannot hash {type(o).__name__}")

    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=file_hash)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def cached(stage, name, k, ext):
    """Path for an output, keyed by its inputs. If the file exists, the stage skips the call."""
    d = OUT / stage
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}-{k}.{ext}"


def log(stage, item, model, params, latency_s, status="ok", cost_usd=0.0, seed=None, cache_hit=False, **extra):
    """One line per model call (and per cache hit, marked cache_hit) in runs.jsonl."""
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stage": stage, "item": item, "model": model,
           "seed": seed, "params": params, "latency_s": round(latency_s, 3), "cost_usd": cost_usd,
           "status": status, "cache_hit": cache_hit, **extra}
    with RUNS.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


class Retryable(Exception):
    """A failure worth retrying: rate limit, timeout or server error."""


def retry(fn, attempts=3, base_delay=4.0):
    for i in range(attempts):
        try:
            return fn()
        except Retryable as e:
            if i == attempts - 1:
                raise
            delay = base_delay * 2 ** i
            print(f"  retry {i + 1}/{attempts - 1} in {delay:.0f}s: {e}")
            time.sleep(delay)


def run_ffmpeg(args):
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed: {r.stderr.strip()[-2000:]}")
    return r


def media_duration(path):
    """Duration in seconds, read from ffmpeg's stream info (no ffprobe needed)."""
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    t = [ln for ln in r.stderr.splitlines() if "time=" in ln]
    if not t:
        raise RuntimeError(f"cannot read duration of {path}")
    hms = t[-1].split("time=")[1].split()[0]
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def prompt_for(board, shot):
    parts = [shot["image_prompt"]]
    if shot.get("shows_character"):
        parts.append(board["character"]["description"])
    parts.append(board["style_block"])
    return ". ".join(p.strip().rstrip(".") for p in parts) + "."


FPS = 24
BASE = 1280  # square working frame; the 16:9 and 9:16 cuts are 1280x720 and 720x1280 crops of it
PAD = 0.5  # seconds of breathing room after each narration line


def timeline(board, narration):
    """Final on-screen seconds per shot: the storyboard duration, stretched if its narration runs longer."""
    out = {}
    for shot in board["shots"]:
        d = shot["duration"]
        wav = narration.get(shot["id"])
        if wav:
            spoken = media_duration(wav) + PAD
            if spoken > d:
                print(f"  note: {shot['id']} narration {spoken:.1f}s > storyboard {d}s, holding the shot longer")
                d = spoken
        out[shot["id"]] = round(d * FPS) / FPS
    return out
