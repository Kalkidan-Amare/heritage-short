"""GPU stages on Kaggle: Wan 2.2 clips for "video" shots, and ACE-Step music candidates.

    python pipeline/kaggle_jobs.py wan     # keyframes must exist (make film once first)
    python pipeline/kaggle_jobs.py music

Each job uploads its inputs as a private dataset, pushes a script kernel from kaggle/ with the GPU on, waits for it,
and downloads the outputs. Files are named with the same keys shots.wan_key and music.ace_key compute, so the next
`make film` picks them up. Items already downloaded are not sent again."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import keyframes
import music
import shots
from common import OUT, ROOT, load_storyboard, log

KERNELS = ROOT / "kaggle"
POLL_S = 60
TIMEOUT_S = 9 * 3600  # Kaggle stops a GPU session after 9 hours


def kaggle(*args, check=True):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle")
    r = subprocess.run([exe, *map(str, args)], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"kaggle {' '.join(map(str, args))} failed: {(r.stderr or r.stdout).strip()[-1000:]}")
    return r


def username():
    if os.environ.get("KAGGLE_USERNAME"):
        return os.environ["KAGGLE_USERNAME"]
    cfg = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    if cfg.exists():
        return json.loads(cfg.read_text())["username"]
    sys.exit("Set KAGGLE_USERNAME in .env (the access-token login does not store the username).")


def push_dataset(slug, folder, title):
    """Create the dataset the first time, add a new version after that."""
    user = username()
    (folder / "dataset-metadata.json").write_text(json.dumps(
        {"title": title, "id": f"{user}/{slug}", "licenses": [{"name": "CC0-1.0"}]}))
    st = kaggle("datasets", "status", f"{user}/{slug}", check=False)
    said = (st.stdout + st.stderr).lower()
    exists = st.returncode == 0 and "404" not in said and "not found" not in said
    if exists:
        kaggle("datasets", "version", "-p", folder, "-m", time.strftime("%Y-%m-%d %H:%M"), "-r", "zip")
    else:
        kaggle("datasets", "create", "-p", folder, "-r", "zip")
    # A new version takes a moment to be ready before a kernel can mount it.
    for _ in range(30):
        if "ready" in kaggle("datasets", "status", f"{user}/{slug}", check=False).stdout.lower():
            return f"{user}/{slug}"
        time.sleep(10)
    raise RuntimeError(f"dataset {user}/{slug} not ready after 5 minutes")


def run_kernel(name, dataset, work):
    """Push kaggle/<name>_kernel.py as a GPU script kernel, wait for it, download its output folder."""
    user = username()
    slug = f"heritage-{name}"
    kdir = work / "kernel"
    kdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(KERNELS / f"{name}_kernel.py", kdir / f"{name}_kernel.py")
    (kdir / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{slug}", "title": slug, "code_file": f"{name}_kernel.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": [dataset], "competition_sources": [],
        "kernel_sources": []}))
    kaggle("kernels", "push", "-p", kdir)
    t = time.time()
    while True:
        time.sleep(POLL_S)
        status = kaggle("kernels", "status", f"{user}/{slug}", check=False).stdout.lower()
        print(f"  {slug}: {status.strip()} ({(time.time() - t) / 60:.0f} min)")
        if "complete" in status:
            break
        if "error" in status or "cancel" in status:
            out = work / "output"
            kaggle("kernels", "output", f"{user}/{slug}", "-p", out, check=False)
            log(f"kaggle-{name}", slug, "kaggle-t4", {"dataset": dataset}, time.time() - t, status="error",
                error=status.strip()[-300:])
            raise RuntimeError(f"{slug} failed; its log is in {out}")
        if time.time() - t > TIMEOUT_S:
            raise RuntimeError(f"{slug} still running after {TIMEOUT_S / 3600:.0f} h")
    out = work / "output"
    shutil.rmtree(out, ignore_errors=True)
    kaggle("kernels", "output", f"{user}/{slug}", "-p", out)
    return out, time.time() - t


def collect(out, dest, model, wall_s):
    """Move finished files into place and log one row per item from the kernel's own timings."""
    dest.mkdir(parents=True, exist_ok=True)
    timings = json.loads((out / "timings.json").read_text()) if (out / "timings.json").exists() else {}
    moved = []
    for item, t in timings.items():
        src = out / t["file"]
        if t.get("status") != "ok" or not src.exists():
            log(dest.name, item, model, t.get("params", {}), t.get("latency_s", 0), status="error",
                error=t.get("error", "missing output"))
            continue
        shutil.move(src, dest / t["file"])
        log(dest.name, item, model, t.get("params", {}), t["latency_s"], seed=t.get("seed"),
            gpu=t.get("gpu"), gpu_minutes=round(t["latency_s"] / 60, 2), kernel_wall_s=round(wall_s))
        moved.append(t["file"])
    return moved


def wan(board):
    frames = keyframes.run(board)
    todo = [s for s in board["shots"] if s["motion"] == "video" and not shots.wan_clip(s, frames[s["id"]])]
    if not todo:
        print("  every video shot already has a Wan clip for its current inputs")
        return []
    work = OUT / "kaggle" / "wan"
    data = work / "data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)
    jobs = []
    for s in todo:
        k = shots.wan_key(s, frames[s["id"]])
        image = f"{s['id']}.png"
        shutil.copy(frames[s["id"]], data / image)
        jobs.append({"id": s["id"], "key": k, "image": image, "prompt": s["motion_prompt"], "seed": s["seed"],
                     "settings": shots.WAN, "file": f"{s['id']}-{k}.mp4"})
    (data / "jobs.json").write_text(json.dumps(jobs, indent=1))
    print(f"  sending {len(jobs)} shots to Wan on Kaggle: {', '.join(j['id'] for j in jobs)}")
    out, wall = run_kernel("wan", push_dataset("heritage-wan-inputs", data, "heritage wan inputs"), work)
    return collect(out, OUT / "wan", board["models"]["video"], wall)


def music_job(board):
    if music.candidates(board):
        print("  candidates for the current music block already exist")
        return []
    m = board["music"]
    k = music.ace_key(board)
    work = OUT / "kaggle" / "ace"
    data = work / "data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)
    job = {"key": k, "caption": m["caption"], "bpm": m.get("bpm"), "keyscale": m.get("key"),
           "duration": m["duration"], "instrumental": m.get("instrumental", True), "candidates": m["candidates"],
           "seed": m["seed"]}
    (data / "job.json").write_text(json.dumps(job, indent=1))
    print(f"  sending {m['candidates']} music candidates to ACE-Step on Kaggle")
    out, wall = run_kernel("ace", push_dataset("heritage-ace-inputs", data, "heritage ace inputs"), work)
    return collect(out, OUT / "ace", board["models"]["music"], wall)


if __name__ == "__main__":
    job = sys.argv[1] if len(sys.argv) > 1 else ""
    if job not in ("wan", "music"):
        sys.exit(__doc__)
    b = load_storyboard()
    got = wan(b) if job == "wan" else music_job(b)
    print(f"  downloaded {len(got)} files")
