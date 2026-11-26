# Failures

What broke, what I tried, what fixed it.

## F1: no FFmpeg on the machine (2026-11-25)
- Broke: no system `ffmpeg`, and no sudo to install it.
- Tried: the static binary that ships with the `imageio-ffmpeg` pip package.
- Fixed: `common.ffmpeg()` uses the system binary if present, else that one. It has `subtitles`, `zoompan`, `sidechaincompress` and `loudnorm`, which the pipeline needs.

## F2: changed subtitle style did not rebuild the export (2026-11-25)
- Broke: after a subtitle style change, the export came from the cache with the old style.
- Fixed: the export cache key now includes the subtitle style string (`assemble.export`).

## F3: offline test could not see a prompt change (2026-11-25)
- Broke: the cache test changed one image prompt, but the offline placeholder image did not depend on the prompt, so the same bytes came out and nothing downstream rebuilt.
- Fixed: the placeholder card now prints its prompt (`keyframes.placeholder`). The real model output always depends on the prompt, so this only affected offline runs.

## F4: first radio cut ran 92.6 s, over the 90 s cap (2026-11-26)
- Broke: every Amharic line ran past its shot. Gacrux with a "slow and tender" style speaks slowly; s05 took 10.5 s
  and s06 11.0 s against 7 s and 8 s shots. `timeline()` holds a shot until its line ends, so the film grew.
- Tried: a faster `tts_style` would re-voice all 10 lines (10 calls on a 10-per-day quota). Shortening only the
  longest lines re-voices 5.
- Fixed: cut s02, s05, s06, s08, s09 to their core meaning (s06 now "The first cup is abol, strong and awakening")
  and the end card to 4 s. Film 74.5 s + 4 s card = 78.5 s. See E5 in EXPERIMENTS.md.

## F5: Gemini TTS daily quota hit mid-run (2026-11-26)
- Broke: `make radio` stopped with 429 "generate_content_free_tier_requests, limit: 10, model:
  gemini-3.8-flash-tts". The day's 10 calls had gone on the first take of all lines plus retakes.
- Tried: listed the TTS models the key can call (5), probed `gemini-3.8-flash-lite-tts` with one line: OK in 4.7 s.
- Fixed: a per-shot `tts_model` override in the schema, so only the 5 new lines use lite and the other 5 keep their
  cached full-model takes. The voice is the same Gacrux; by ear the lite take is slightly different but close.

## F6: Kaggle kernels had no internet (2026-11-26)
- Broke: both GPU kernels (Wan 2.2 and ACE-Step) failed on their first line: `git clone ... Could not resolve host:
  github.com`. `enable_internet: true` is set in the kernel metadata, but Kaggle grants internet only to
  phone-verified accounts.
- Tried: read both kernel logs (`outputs/kaggle/*/output/*.log`) to confirm it was DNS, not code.
- Fixed: the user phone-verified the account. Until then video shots fell back to Ken Burns (`shots.py`) and music
  to the placeholder bed, so `make film` still finished.

## F7: one stray word left alone on screen (2026-11-26)
- Broke: the s01 subtitle split into "...the frankincense is burning. Come" and then "closer." for 0.5 s, because
  cues were cut every two wrapped lines regardless of sentences.
- Fixed: `assemble.subtitles` now breaks at sentence ends first and only wraps within a sentence.

## F8: ACE-Step would not install on Kaggle's Python (2026-11-26)
- Broke: `pip install -e ACE-Step-1.5` exited 1. Its `pyproject.toml` says `requires-python = ">=3.11,<3.13"` and
  the Kaggle image runs Python 3.13 (`outputs/kaggle/ace/output/heritage-ace.log`).
- Fixed: the kernel now does what the ACE-Step README does: `uv sync --python 3.12` builds the repo's locked env,
  then the kernel re-runs itself inside it (`kaggle/ace_kernel.py` `setup`).

## F9: Wan 2.2 crashed on import on Kaggle (2026-11-26)
- Broke: all 4 shots failed in 7 to 27 s with `module 'numpy.dtypes' has no attribute 'StringDType'`. Wan's
  `requirements.txt` pins `numpy<2`; pip put numpy 1.26.4 into Kaggle's Python 3.13, and the preinstalled
  transformers needs numpy 2 there (`outputs/kaggle/wan/output-run1/`). 233 s of setup, 0 GPU work done.
- Fixed: Wan runs in its own Python 3.12 env made with `uv`, torch from the CUDA 12.6 index
  (`kaggle/wan_kernel.py` `setup`). Same idea as F8.
- Second run (17:26): numpy was fixed, then `No module named 'einops'`. Wan's requirements do not list every import:
  `import wan` also loads its speech and animate modules, which need decord, peft and librosa. The kernel now
  installs those and runs `generate.py --help` in a loop, installing whatever it still reports missing.

## F10: Wan's code assumes flash-attn and bf16, a T4 has neither (2026-11-26)
- Found before the third run, by reading the code instead of waiting 20 minutes for Kaggle to show it.
  `wan/modules/model.py` calls `flash_attention()` directly, and that function asserts flash-attn 2 is installed.
  The kernel comment that said "falls back to SDPA" was wrong: only `attention()` falls back, and it is not used.
- The model runs in bf16. A T4 has no bf16 tensor cores, so SDPA would take the slow math path and its memory
  grows with the square of the tokens. At 121 frames that is about 27k tokens per call (31 latent frames x 22 x 40).
- Changes: the kernel appends an SDPA `flash_attention` that keeps the key padding mask (the stock fallback drops
  it), runs the DiT in fp16, and cuts the clip to 49 frames and 20 steps (`shots.WAN`). One shot (s06) is sent
  first as a timing test (`WAN_SHOTS=s06 make wan`), with a 2.5 h cap per shot.

## F11: Wan 2.2 TI2V-5B ran out of GPU memory on a T4 (2026-11-26)
- Broke: run 3 (one shot, s06, 49 frames, 20 steps, fp16, SDPA patch from F10) got through setup and weights, then
  died after 456 s with `torch.OutOfMemoryError` in `norm_q` (14.49 of 14.56 GiB in use;
  `outputs/kaggle/wan/output/timings.json`). 1280x704 is the only size the 5B model card lists for TI2V.
- Not fixed: the next steps would be offloading the T5 encoder and VAE to CPU, or a smaller size the model was not
  trained on. Each try costs about 30 minutes of queue and setup, and the deadline was 4 hours away.
- Decision: the film keeps Ken Burns motion from the keyframes. The end card no longer credits Wan
  (`storyboard.json` `end_card`). The Wan stage, kernel and cache stay in the repo for a bigger GPU.

## F12: Cloudflare's output filter blocked the new s08 keyframe (2026-11-26)
- Broke: after user test 2, the s08 prompt asked for "two Ethiopian neighbours ... with dark brown skin and Ethiopian
  highland features". FLUX.2 klein on Cloudflare returned 400, code 3030: "Your output has been flagged". The
  filter judges the image, not the text, and gives no reason.
- Fixed: described the people by clothes and place instead of face (Habesha neighbours from Addis Ababa, a man in a
  white gabi, a woman with braided hair). Same seed, passed on the next call, and the men no longer look South Asian.
- Lesson: describe what people wear and where they are from, not their facial features.
