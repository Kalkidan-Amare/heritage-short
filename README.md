# Heritage Short

A pipeline that turns one `storyboard.json` into a narrated short film with English subtitles, a ducked music score and an AI end card, in 16:9 and 9:16.

## Run it

```
git clone <this repo> && cd heritage-short
cp .env.example .env      # then fill in the three keys
make film
```

`make film` validates the storyboard, then makes narration, keyframes, shots and music, mixes and exports. Results land in `outputs/film/`. Every stage is cached by its inputs, so a second run with no changes calls no model.

No keys? `PIPELINE_OFFLINE=1 make film` runs the whole thing with placeholders (colour cards, silence).

| Command | What it does |
|---|---|
| `make setup` | creates `.venv` and installs `requirements.txt` |
| `make smoke` | calls each provider once and logs the latency to `runs.jsonl` |
| `make script` | drafts `storyboard.draft.json` from my notes in `story.md`; I edit it into `storyboard.json` |
| `make radio` | narration over a placeholder bed on black: the first cut to test with people |
| `make wan` | sends the `video` shots to Wan 2.2 on a Kaggle GPU and downloads the clips |
| `make music` | makes the ACE-Step music candidates on Kaggle |
| `make film` | the full film, both formats |
| `make test` | schema and cache tests, offline |
| `make cost` | per-stage calls, latency, GPU minutes and list-price cost from `runs.jsonl` |

Order for a first full run: `make film` (keyframes), `make wan`, `make music`, pick a candidate in `storyboard.json` (`music.chosen`), `make film` again.

## Keys

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio |
| `CF_ACCOUNT_ID`, `CF_API_TOKEN` | Cloudflare dashboard, a token with Workers AI permission |
| Kaggle | phone-verified account; `kaggle auth login` (or a token in `~/.kaggle/access_token`), plus `KAGGLE_USERNAME` in `.env` |

`.env` is git-ignored. Nothing in this repo holds a key.

## Requirements

Python 3.12 and `make`. FFmpeg is optional: the pipeline uses the binary from the `imageio-ffmpeg` package when there is no system one.

## What it costs

All providers are on free tiers. Measured latency, GPU minutes and list-price equivalents per stage are in [COSTS.md](COSTS.md).

## Files

| File | What |
|---|---|
| `storyboard.json` | the contract: shots, durations, prompts, narration, music |
| `schema/` | JSON Schema, checked before every run |
| `pipeline/` | one script per stage, see [ARCHITECTURE.md](ARCHITECTURE.md) |
| `runs.jsonl` | one line per model call |
| `outputs/` | generated files, kept so the run can be inspected |
| [DESIGN.md](DESIGN.md) | audience, intent, the two user tests |
| [EXPERIMENTS.md](EXPERIMENTS.md), [FAILURES.md](FAILURES.md) | what I tried, what broke |
| [ETHICS.md](ETHICS.md) | consent, licences, labelling |
