"""Kaggle GPU kernel: ACE-Step 1.5 music candidates for job.json (pushed by pipeline/kaggle_jobs.py music).
Writes <key>-<i>.wav and timings.json to /kaggle/working. Candidate i uses seed + i, so each one can be re-made."""
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WORK = Path("/kaggle/working")
REPO = Path("/kaggle/tmp/ACE-Step-1.5")


def sh(cmd):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


def setup():
    """ACE-Step 1.5 needs Python >=3.11,<3.13 and Kaggle runs 3.13 (FAILURES.md F8), so build the repo's own
    locked env with `uv sync` as its README does, then re-run this file inside it."""
    REPO.parent.mkdir(parents=True, exist_ok=True)
    sh(f"git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git {REPO}")
    sh("pip install -q uv")
    sh(f"cd {REPO} && uv sync --python 3.12")
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    sh(f"cd {REPO} && ACE_INNER={commit} uv run --no-sync python {Path(globals().get('__file__') or '/kaggle/src/script.py').resolve()}")


def main():
    job = json.loads(Path(glob.glob("/kaggle/input/**/job.json", recursive=True)[0]).read_text())
    commit = os.environ["ACE_INNER"]
    sys.path.insert(0, str(REPO))
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                         text=True).stdout.strip().splitlines()[0]
    dit = AceStepHandler()
    dit.initialize_service(project_root=str(REPO), config_path="acestep-v15-turbo", device="cuda")
    # Tempo and key go in the caption: only caption, instrumental, duration, seed and thinking are documented fields.
    caption = ", ".join(str(x) for x in [job["caption"], job["bpm"] and f"{job['bpm']} BPM", job["keyscale"]] if x)
    timings = {}
    for i in range(job["candidates"]):
        seed = job["seed"] + i
        name = f"{job['key']}-{i}"
        params = {"caption": caption, "duration": job["duration"], "instrumental": job["instrumental"],
                  "dit": "acestep-v15-turbo", "thinking": False, "repo_commit": commit}
        t = time.time()
        try:
            res = generate_music(dit, None, GenerationParams(caption=caption, instrumental=job["instrumental"],
                                                             duration=job["duration"], seed=seed, thinking=False),
                                 GenerationConfig(batch_size=1, audio_format="flac", use_random_seed=False),
                                 save_dir="/kaggle/tmp/raw")
            src = res.audios[0]["path"]
            sh(f"ffmpeg -hide_banner -loglevel error -y -i '{src}' -ar 48000 '{WORK / (name + '.wav')}'")
            timings[name] = {"file": f"{name}.wav", "status": "ok", "latency_s": round(time.time() - t, 1),
                             "seed": seed, "gpu": gpu, "params": params}
        except Exception as e:  # recorded per candidate so one failure is visible in runs.jsonl, not lost
            timings[name] = {"file": f"{name}.wav", "status": "error", "latency_s": round(time.time() - t, 1),
                             "seed": seed, "params": params, "error": f"{type(e).__name__}: {e}"[-1500:]}
        print(name, timings[name]["status"], timings[name]["latency_s"], "s", flush=True)
        (WORK / "timings.json").write_text(json.dumps(timings, indent=1))


if os.environ.get("ACE_INNER"):
    main()
else:
    setup()
