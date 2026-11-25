"""Stage: keyframes. The character reference sheet first, then one still per shot, all from Cloudflare Workers AI.
Keyframes are square with the subject centred, so one still serves both the 16:9 and the 9:16 cut."""
import base64
import io
import os
import time

import requests
from PIL import Image, ImageDraw

from common import Retryable, cached, key, load_storyboard, log, prompt_for, retry

STAGE = "keyframes"
SIZE = 1024
CF_URL = "https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"


def flux_cloudflare(model, prompt, seed, steps, reference=None):
    url = CF_URL.format(acct=os.environ["CF_ACCOUNT_ID"], model=model)
    headers = {"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}

    def call():
        if "flux-2" in model:
            # FLUX.2 takes multipart form data and can be conditioned on reference images.
            fields = {"prompt": (None, prompt), "seed": (None, str(seed)), "width": (None, str(SIZE)),
                      "height": (None, str(SIZE))}
            if steps:
                fields["steps"] = (None, str(steps))
            if reference is not None:
                fields["input_image_0"] = ("ref.png", reference.read_bytes(), "image/png")
            r = requests.post(url, headers=headers, files=fields, timeout=120)
        else:
            body = {"prompt": prompt, "seed": seed}
            if steps:
                body["steps"] = steps
            r = requests.post(url, headers=headers, json=body, timeout=120)
        if r.status_code in (429, 500, 502, 503, 504):
            raise Retryable(f"{r.status_code} {r.text[:200]}")
        if not r.ok:
            raise RuntimeError(f"Cloudflare {r.status_code}: {r.text[:500]}")
        if r.headers.get("content-type", "").startswith("image/"):
            return r.content
        return base64.b64decode(r.json()["result"]["image"])

    return retry(call)


def placeholder(label, seed):
    """Offline stand-in: a flat colour card with the item id, for tests and dry runs."""
    img = Image.new("RGB", (SIZE, SIZE), ((seed * 53) % 200 + 30, (seed * 97) % 200 + 30, (seed * 31) % 200 + 30))
    ImageDraw.Draw(img).text((40, 40), label, fill="white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def save_png(path, data):
    Image.open(io.BytesIO(data)).convert("RGB").resize((SIZE, SIZE)).save(path, "PNG")


def generate(item, prompt, seed, board, reference=None):
    m = board["models"]
    offline = os.environ.get("PIPELINE_OFFLINE") == "1"
    model = "offline-placeholder" if offline else m["image"]
    steps = m.get("image_steps")
    k = key(model, prompt, seed, steps, reference if reference else None)
    path = cached(STAGE, item, k, "png")
    params = {"prompt": prompt, "steps": steps, "reference": reference.name if reference else None}
    if path.exists():
        log(STAGE, item, model, params, 0, seed=seed, cache_hit=True)
        return path
    t = time.time()
    data = placeholder(item, seed) if offline else flux_cloudflare(model, prompt, seed, steps, reference)
    save_png(path, data)
    log(STAGE, item, model, params, time.time() - t, seed=seed)
    print(f"  keyframe {item}: {path.name}")
    return path


def run(board):
    c = board["character"]
    ref = generate("reference", f"{c['reference_prompt']}. {c['description']}. {board['style_block']}.", c["seed"], board)
    uses_ref = "flux-2" in board["models"]["image"]
    out = {"reference": ref}
    for shot in board["shots"]:
        reference = ref if uses_ref and shot.get("shows_character") else None
        out[shot["id"]] = generate(shot["id"], prompt_for(board, shot), shot["seed"], board, reference)
    return out


if __name__ == "__main__":
    run(load_storyboard())
