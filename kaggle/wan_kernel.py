"""Kaggle GPU kernel: Wan 2.2 TI2V-5B image-to-video for each job in jobs.json (pushed by pipeline/kaggle_jobs.py).
Writes <shot>-<key>.mp4 and timings.json to /kaggle/working. One failed shot does not stop the others."""
import glob
import json
import subprocess
import time
from pathlib import Path

from PIL import Image

WORK = Path("/kaggle/working")
REPO = Path("/kaggle/tmp/Wan2.2")
CKPT = Path("/kaggle/tmp/Wan2.2-TI2V-5B")
VENV = Path("/kaggle/tmp/wan-venv")
BUDGET_S = 8 * 3600  # start no new shot after 8 h; Kaggle stops the session at 9 h


def sh(cmd, **kw):
    print("+", cmd, flush=True)
    return subprocess.run(cmd, shell=True, check=True, **kw)


def setup():
    REPO.parent.mkdir(parents=True, exist_ok=True)
    sh(f"git clone --depth 1 https://github.com/Wan-Video/Wan2.2.git {REPO}")
    # Wan pins numpy<2, which breaks transformers on Kaggle's Python 3.13 (FAILURES.md F9), so it gets its own
    # Python 3.12 env. flash_attn does not build for a T4; the attention code falls back to PyTorch SDPA.
    sh("pip install -q uv")
    sh(f"uv venv -p 3.12 {VENV}")
    sh(f"grep -v flash_attn {REPO}/requirements.txt > /kaggle/tmp/req.txt && "
       f"uv pip install -p {VENV}/bin/python --torch-backend cu126 -r /kaggle/tmp/req.txt")
    from huggingface_hub import snapshot_download
    snapshot_download("Wan-AI/Wan2.2-TI2V-5B", local_dir=str(CKPT))
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def gpu_name():
    r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
    return r.stdout.strip().replace("\n", ", ")


def landscape(src, dst, w, h):
    """The square keyframe, centre-cropped to the model's frame so Wan does not squash it."""
    img = Image.open(src).convert("RGB")
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    img.crop((left, top, left + w, top + h)).save(dst)


def main():
    jobs_file = glob.glob("/kaggle/input/**/jobs.json", recursive=True)[0]
    data = Path(jobs_file).parent
    jobs = json.loads(Path(jobs_file).read_text())
    t0 = time.time()
    commit = setup()
    gpu = gpu_name()
    timings = {}
    for j in jobs:
        s = j["settings"]
        params = {"prompt": j["prompt"], **s, "repo_commit": commit}
        if time.time() - t0 > BUDGET_S:
            timings[j["id"]] = {"file": j["file"], "status": "skipped", "error": "time budget", "params": params}
            continue
        w, h = map(int, s["size"].split("*"))
        img = Path("/kaggle/tmp") / f"{j['id']}-in.png"
        landscape(data / j["image"], img, w, h)
        t = time.time()
        cmd = [str(VENV / "bin" / "python"), "generate.py", "--task", "ti2v-5B", "--size", s["size"], "--ckpt_dir", str(CKPT),
               "--offload_model", "True", "--convert_model_dtype", "--t5_cpu", "--image", str(img),
               "--prompt", j["prompt"], "--frame_num", str(s["frames"]), "--sample_steps", str(s["steps"]),
               "--base_seed", str(j["seed"]), "--save_file", str(WORK / j["file"])]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        ok = r.returncode == 0 and (WORK / j["file"]).exists()
        timings[j["id"]] = {"file": j["file"], "status": "ok" if ok else "error", "latency_s": round(time.time() - t, 1),
                            "seed": j["seed"], "gpu": gpu, "params": params,
                            **({} if ok else {"error": (r.stderr or r.stdout)[-1500:]})}
        print(j["id"], timings[j["id"]]["status"], timings[j["id"]]["latency_s"], "s", flush=True)
        (WORK / "timings.json").write_text(json.dumps(timings, indent=1))
    (WORK / "timings.json").write_text(json.dumps(timings, indent=1))


main()
