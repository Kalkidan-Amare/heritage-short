# Architecture

`storyboard.json` is the contract. Each stage reads it, writes only its own folder under `outputs/`, and hands file paths to the next stage. `pipeline/run.py` runs them in order.

```
storyboard.json -> validate (schema/) -> narration -> timeline -> music
                                             |                     |
                                  keyframes -> shots ----------> assemble -> outputs/film/{16x9,9x16}.mp4
Kaggle (async):  kaggle_jobs.py wan   -> outputs/wan/<shot>-<key>.mp4  (read by shots)
                 kaggle_jobs.py music -> outputs/ace/<key>-<i>.wav     (read by music)
```

## Stages

| Stage | File | Input | Output | Model |
|---|---|---|---|---|
| Validate | `common.load_storyboard` | `storyboard.json` | dict, or a schema error | none |
| Narration | `narration.py` | shot `narration`, voice, style | `narration/<shot>-<key>.wav`, silence trimmed | Gemini TTS |
| Timeline | `common.timeline` | durations, narration lengths | seconds per shot (stretched to voice + 0.5 s) | none |
| Keyframes | `keyframes.py` | character sheet prompt, shot prompts, seeds | `keyframes/<shot>-<key>.png`, 1024 square | FLUX on Cloudflare |
| Shots | `shots.py` | keyframe, motion, timeline | `shots/<shot>-<key>.mp4`, 1280 square, 24 fps | Wan 2.2 clip if present, else Ken Burns |
| Music | `music.py` | `music` block | chosen ACE-Step candidate, else a synth pad | ACE-Step 1.5 |
| Assemble | `assemble.py` | shots, narration, music | mix, SRT, end card, two exports | FFmpeg |

`radio` mode skips keyframes and shots and puts the same mix and subtitles on black.

## Contracts

- The schema (`schema/storyboard.schema.json`) is checked before every run. Unknown fields fail. Every shot needs a `reason`, a `seed` and an English subtitle. A `video` shot needs a `motion_prompt`. Shot ids are unique.
- Keyframes are square, so one image serves both crops. 16:9 is the middle 1280x720 of the 1280 frame. 9:16 is a 720x1280 slice whose position is the shot's `focus_x` (0 left, 0.5 centre, 1 right), so an off-centre subject stays in frame (E8).
- The character description is appended to every prompt of a shot with `shows_character`. The reference sheet is sent as an input image only when `character.use_reference` is true; it is false since E3.
- A shot may set `tts_model` to voice its line with a different TTS model than `models.tts` (used when the main model ran out of daily quota, F5).
- Kaggle outputs are matched by key, not by name. `shots.wan_key` and `music.ace_key` compute the same key the Kaggle job used. A stale clip is ignored.

## Caching

- Every output file is named `<item>-<key>`. The key is a hash of everything that changes that output: model id, prompt, seed, steps, voice, and the bytes of any input file (`common.key`).
- If the file exists, the stage skips the call and logs a `cache_hit` row. Nothing is ever overwritten.
- Keys chain through files. A new image prompt changes one keyframe, so only that shot and the two exports rebuild. The audio mix stays cached. A new narration line re-takes one voice file, then the mix and exports.
- `tests/test_cache.py` checks both cases and that an unchanged re-run calls nothing.

## Kaggle jobs

- `pipeline/kaggle_jobs.py` uploads the inputs as a private dataset, pushes `kaggle/<job>_kernel.py` as a T4 script kernel, polls every minute and downloads the output folder.
- The kernel writes `timings.json` (per item: file, status, latency, seed, GPU, error). Each item becomes one `runs.jsonl` row with `gpu_minutes`. A failed item is logged and not moved, so the next run sends it again.
- Wan settings (`shots.WAN`: model, size, frames, steps) are part of the clip key. Changing them re-makes every clip.

## Failure handling

- Rate limits, timeouts and 5xx raise `Retryable`. `common.retry` backs off exponentially (3 tries from 4 s by default; Gemini calls 6 tries from 15 s, because the free tier returns 503 for minutes at a time). Other errors stop the run with the provider's message.
- A Kaggle kernel that fails logs an error row and saves its log to `outputs/kaggle/<job>/output/`.
- A failed call writes nothing to the cache, so the next run retries only that item.
- Missing Wan clip: the shot falls back to Ken Burns and the run prints a note. Missing music candidate: the placeholder bed.
- Narration longer than its shot: the shot is held longer instead of cutting the voice.
- `PIPELINE_OFFLINE=1` swaps every model for a placeholder (colour cards, silence), so the whole pipeline and the tests run with no keys.

## Logging

One JSON line per model call and per cache hit in `runs.jsonl`: time, stage, item, model, seed, params, latency, cost, status, `cache_hit`. TTS rows also carry `audio_s`, which is what TTS is billed on. `make cost` (`pipeline/costs.py`) turns it into the table in COSTS.md.

## Audio

Narration at 48 kHz, music pre-normalised to -24 LUFS and 6 dB down, sidechain-ducked under the voice (ratio 6, release 600 ms, from E7), faded out at the end. The mix is then normalised in two passes to -14 LUFS integrated, -1 dBTP.

## Secrets

Keys live in `.env` (git-ignored) and are read with python-dotenv: `GEMINI_API_KEY`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`. Kaggle uses its own credentials file. No key is ever logged.
