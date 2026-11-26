# Costs

Every provider ran on a free tier, so the real spend is $0. The table is `make cost`, built from `runs.jsonl`;
the list-price column says what the same calls would cost on paid tiers.

## Free-tier limits hit or checked
| Provider | Limit | How I found it | Source |
|---|---|---|---|
| Gemini TTS (`gemini-3.8-flash-tts`) | 10 requests per day | hit it: 429 `generate_content_free_tier_requests, limit: 10` (F5) | error text, [rate limits](https://aistudio.google.com/docs/rate-limits) |
| Gemini TTS lite | separate daily quota per model | 6 calls worked after the full model ran out | `runs.jsonl` |
| Cloudflare Workers AI | 10,000 neurons per day, shared by all models | about 104 neurons per 1024x1024 klein image, so ~95 images a day | [pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) |
| Kaggle GPU | 30 GPU hours per week, 9 h per session | internet in kernels needs a phone-verified account (F6) | Kaggle settings |

## Per stage (2026-11-26, `make cost`)
| Stage | Model | Calls (errors) | Cache hits | Total latency | GPU minutes | List-price equivalent |
|---|---|---|---|---|---|---|
| assemble | ffmpeg | 15 (0) | 13 | 443 s | 0.0 | $0.0000 |
| experiment-e3 | @cf/black-forest-labs/flux-2-klein-4b | 4 (0) | 0 | 61 s | 0.0 | $0.0046 |
| experiment-e7 | ffmpeg | 6 (0) | 0 | 0 s | 0.0 | $0.0000 |
| keyframes | @cf/black-forest-labs/flux-2-klein-4b | 23 (0) | 65 | 213 s | 0.0 | $0.0264 |
| keyframes | offline-placeholder | 4 (0) | 12 | 1 s | 0.0 | $0.0000 |
| music | ffmpeg | 4 (0) | 11 | 6 s | 0.0 | $0.0000 |
| narration | gemini-3.8-flash-lite-tts | 5 (0) | 35 | 20 s | 0.0 | $0.0060 |
| narration | gemini-3.8-flash-tts | 10 (0) | 41 | 540 s | 0.0 | $0.0226 |
| narration | offline-silence | 4 (0) | 8 | 0 s | 0.0 | $0.0000 |
| probe-tts | gemini-3.8-flash-lite-tts | 1 (0) | 0 | 5 s | 0.0 | $0.0012 |
| script | gemini-3.8-flash | 1 (0) | 0 | 219 s | 0.0 | $0.0000 |
| shots | ffmpeg | 13 (0) | 39 | 198 s | 0.0 | $0.0000 |
| smoke | @cf/black-forest-labs/flux-1-schnell | 2 (1) | 0 | 3 s | 0.0 | $0.0000 |
| smoke | @cf/black-forest-labs/flux-2-klein-4b | 2 (0) | 0 | 13 s | 0.0 | $0.0023 |
| smoke | gemini-3.8-flash-tts | 2 (0) | 0 | 8 s | 0.0 | $0.0032 |
| smoke | kaggle-cli | 1 (0) | 0 | 2 s | 0.0 | $0.0000 |
| **all** | | 97 | 224 | 29 min | 0.0 | **$0.066** |

## How the list price is worked out
- FLUX.2 klein 4B: 26.05 neurons per 512x512 output tile, $0.011 per 1,000 neurons; a 1024x1024 image is 4 tiles,
  so $0.00115 per image ([Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)).
- Gemini TTS: $9 (full) and $6 (lite) per million audio tokens until 31 Dec 2026, 25 tokens per second of audio, so
  about $0.014 per minute of narration on the full model
  ([Google TTS pricing](https://cloud.google.com/text-to-speech/pricing)). Rows logged before `audio_s` was
  recorded use 0.24 s per character, measured on this film's takes.
- Gemini 3.8 Flash text (one script call) and ffmpeg are not priced: one call, and local CPU.
- Kaggle T4 minutes would use an on-demand T4 rate of $0.35 per hour (UNVERIFIED); no successful GPU run yet.

## What it means
- The whole film so far costs well under a dollar at list price. Money is not the limit; **free-tier daily
  quotas and wall-clock time are**. One TTS call took 475 s because of 503 retries; the script call took 219 s.
- Caching saved more calls than were made: 224 cache hits against 97 calls.

## Frontier comparison
No org access to a paid frontier video or voice model, so none was run.
