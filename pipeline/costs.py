"""Per-stage latency, GPU minutes and list-price equivalent, read from runs.jsonl. `make cost` prints it as Markdown.
Every provider ran on a free tier, so cost_usd in the log is 0; the list price says what the same calls would cost."""
import json
from collections import defaultdict

from common import RUNS

# List prices checked 2026-11-26. Sources are in COSTS.md.
IMAGE_TILE_USD = 26.05 * 0.011 / 1000  # FLUX.2 klein 4B on Workers AI: 26.05 neurons per 512x512 output tile
TTS_AUDIO_USD_PER_S = {"gemini-3.8-flash-tts": 25 * 9.00 / 1e6,  # 25 audio tokens per second
                       "gemini-3.8-flash-lite-tts": 25 * 6.00 / 1e6}
TTS_S_PER_CHAR = 0.24  # measured on this film's Amharic takes, for rows logged before audio_s was recorded
T4_USD_PER_H = 0.35  # GCP on-demand T4 GPU, UNVERIFIED, used only for the Kaggle GPU minutes


def price(r):
    m, p = r["model"], r.get("params") or {}
    if "klein" in m:
        return 4 * IMAGE_TILE_USD  # 1024x1024 output is four 512x512 tiles
    if m in TTS_AUDIO_USD_PER_S:
        seconds = p.get("audio_s") or TTS_S_PER_CHAR * (p.get("chars") or len(p.get("text", "")))
        return seconds * TTS_AUDIO_USD_PER_S[m]
    if r.get("gpu_minutes"):
        return r["gpu_minutes"] / 60 * T4_USD_PER_H
    return 0.0


def table():
    rows = [json.loads(line) for line in RUNS.read_text().splitlines() if line.strip()]
    groups = defaultdict(lambda: {"calls": 0, "errors": 0, "hits": 0, "latency": 0.0, "gpu": 0.0, "usd": 0.0})
    for r in rows:
        g = groups[(r["stage"], r["model"])]
        if r.get("cache_hit"):
            g["hits"] += 1
            continue
        g["calls"] += 1
        g["errors"] += r.get("status") != "ok"
        g["latency"] += r.get("latency_s") or 0
        g["gpu"] += r.get("gpu_minutes") or 0
        g["usd"] += price(r) if r.get("status") == "ok" else 0
    out = ["| Stage | Model | Calls (errors) | Cache hits | Total latency | GPU minutes | List-price equivalent |",
           "|---|---|---|---|---|---|---|"]
    for (stage, model), g in sorted(groups.items()):
        out.append(f"| {stage} | {model} | {g['calls']} ({g['errors']}) | {g['hits']} | {g['latency']:.0f} s | "
                   f"{g['gpu']:.1f} | ${g['usd']:.4f} |")
    total = sum(g["usd"] for g in groups.values())
    out.append(f"| **all** | | {sum(g['calls'] for g in groups.values())} | {sum(g['hits'] for g in groups.values())} "
               f"| {sum(g['latency'] for g in groups.values()) / 60:.0f} min | "
               f"{sum(g['gpu'] for g in groups.values()):.1f} | **${total:.3f}** |")
    return "\n".join(out)


if __name__ == "__main__":
    print(table())
