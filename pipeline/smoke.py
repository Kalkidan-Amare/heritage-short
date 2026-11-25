"""Smoke test: call each provider once and log latency to runs.jsonl, so a missing key or a changed API shows up
before the real run. A provider without its key is logged as skipped. Outputs go to outputs/smoke/."""
import json
import os
import time

import keyframes
import narration
from common import OUT, log

TTS_MODEL = "gemini-3.8-flash-tts"
IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
# One English and one Amharic line: the brief asks how well TTS handles the narration language.
LINES = {"en": "This is a short test of the narration voice.", "am": "ይህ የድምፅ ሙከራ ነው።"}


def check(name, model, needs, fn, params):
    missing = [k for k in needs if not os.environ.get(k)]
    if missing:
        log("smoke", name, model, params, 0, status="skipped", error=f"missing {', '.join(missing)}")
        print(f"  {name}: skipped (missing {', '.join(missing)})")
        return
    t = time.time()
    try:
        note = fn()
        log("smoke", name, model, params, time.time() - t, note=note)
        print(f"  {name}: ok in {time.time() - t:.1f}s ({note})")
    except Exception as e:
        log("smoke", name, model, params, time.time() - t, status="error", error=f"{type(e).__name__}: {e}"[:500])
        print(f"  {name}: FAILED: {type(e).__name__}: {e}")


def main():
    d = OUT / "smoke"
    d.mkdir(parents=True, exist_ok=True)

    for code, text in LINES.items():
        def tts(code=code, text=text):
            path = d / f"tts-{code}.wav"
            narration.write_wav(path, narration.tts_gemini(text, TTS_MODEL, "Kore", "calm, warm storyteller"))
            return f"{path.name}, {path.stat().st_size} bytes"
        check(f"tts-{code}", TTS_MODEL, ["GEMINI_API_KEY"], tts, {"text": text, "voice": "Kore"})

    def image():
        path = d / "image.png"
        keyframes.save_png(path, keyframes.flux_cloudflare(IMAGE_MODEL, "a clay coffee pot on a wooden table", 1, 4))
        return path.name
    check("image", IMAGE_MODEL, ["CF_ACCOUNT_ID", "CF_API_TOKEN"], image, {"steps": 4, "seed": 1})

    def kaggle_auth():
        import kaggle_jobs
        r = kaggle_jobs.kaggle("kernels", "list", "--mine", "--page-size", "1")
        return r.stdout.strip().splitlines()[0][:80] if r.stdout.strip() else "authenticated"
    check("kaggle", "kaggle-cli", [], kaggle_auth, {})

    print(json.dumps({"log": "runs.jsonl", "outputs": str(d)}))


if __name__ == "__main__":
    main()
