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
