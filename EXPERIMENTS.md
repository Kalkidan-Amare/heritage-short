# Experiments

One entry per experiment: hypothesis, change, result, evidence (runs.jsonl rows, file names), decision.

<!-- Template
## E1: <short name> (YYYY-MM-DD)
- Hypothesis:
- Change:
- Result:
- Evidence:
- Decision:
-->

## E1: which FLUX model on Cloudflare (2026-11-26)
- Hypothesis: schnell is fastest and good enough; FLUX.2 klein 4B is worth it only if it keeps the character.
- Change: the same prompt and seed sent to schnell, klein 4B, and klein 4B with a reference image.
- Result: schnell 2.5 s, klein 7.6 s, klein with reference 5.0 s. Schnell rejects a `seed` field (400), so its
  images can't be reproduced. Klein takes a seed and reference images.
- Evidence: `runs.jsonl` rows `smoke` image, image-schnell, image-klein, image-klein-ref; `outputs/smoke/`.
- Decision: klein 4B. Reproducible seeds matter more than 5 s per image.

## E2: prompt wording for cultural objects (2026-11-26)
- Hypothesis: naming the object (sini, jebena) is enough for the model to draw it right.
- Change: v1 used the names. v2 describes the shape instead ("tiny round white cup like a small bowl, the size of
  an egg cup, with no handle"), and the character as Habesha with a netela and tibeb border.
- Result: v1 drew mugs with handles, a teapot, a lantern and a fruit basket in place of cups, and a grandmother who
  did not read as Ethiopian. v2 fixed the cups, the shawl and the skin tone. The jebena is still teapot-like.
- Evidence: `outputs/experiments/e2/keyframes-v1.png`, `keyframes-v2.png`; keyframes rows in `runs.jsonl`.
- Decision: describe shapes, never rely on the Amharic name. Jebena needs another pass.

## E3: reference image vs text description for the character (2026-11-26)
- Hypothesis (the brief's advice): conditioning every character shot on a reference sheet keeps her consistent.
- Change: s03, s07, s08, s09 made with the reference attached and without it (same prompt and seed).
- Result: with the reference, the face is locked but every shot is the same front portrait: no pan in s03,
  popcorn instead of a cup in s07, no neighbours in s08. Without it, each shot does its action and she still looks
  like the same woman, because the description is detailed (netela, tibeb border, white kemis, silver hair).
- Evidence: `outputs/experiments/e3/with-vs-without-ref.png`; `experiment-e3` rows in `runs.jsonl`.
- Decision: `character.use_reference: false`. This is the case where the suggested practice lost to my instinct,
  at least for klein 4B with a single portrait as the reference.

## E4: lite vs full Gemini TTS for Amharic (2026-11-26)
- Hypothesis: `gemini-3.8-flash-lite-tts` sounds close enough to the full model to mix lines from both in one film.
- Change: the 5 re-written lines on lite, the other 5 kept from the full model, same voice (Gacrux) and style.
- Result: lite median latency 4.0 s (5 calls, no retries) vs full 5.7 s median and one call at 475 s after 503
  retries. Lite speaks faster: 4.3 Amharic syllables per second on average vs 3.8 for the full model (10 takes).
  By ear the timbre is slightly different but close; the user accepted it.
- Evidence: `runs.jsonl` narration rows by model; `probe-tts` row; durations from `common.media_duration`.
- Decision: keep the mix for this cut. If a full re-voice is needed, do all 10 lines on one model.

## E5: shorter lines vs a faster voice to fit 90 s (2026-11-26)
- Hypothesis: cutting words from the five longest lines saves more time than it costs in meaning.
- Change: s02, s05, s06, s08, s09 re-written (178 to 125 syllables, -30%). Kept every named object and all three
  round names (abol, tona, bereka); dropped "no one leaves before it" and the tray in s06.
- Result: those five lines went from 47.8 s to 29.3 s of speech. Film 87.6 s to 74.5 s, plus a 4 s card: 78.5 s.
- Evidence: `outputs/film/radio-cut-3b6fc104463c` (92.6 s) vs `radio-cut-eafa3c0ddf7c` (78.5 s); assemble rows.
- Decision: keep. The lost line about bereka is the one thing worth asking about in user test 2.

## E6: does the cache really skip unchanged work (2026-11-26)
- Hypothesis: a re-run with nothing changed calls no model and takes seconds; a code change to subtitles rebuilds
  only the exports.
- Change: `make film` right after the subtitle fix (F7), then again with no change.
- Result: first run 164 s, 35 rows, only the 16:9 and 9:16 exports uncached (the SRT text changed). Second run
  1.9 s, 0 uncached rows.
- Evidence: `runs.jsonl` rows at 16:07-16:10 with `cache_hit`.
- Decision: the cache keys are right; nothing to change.

## E7: how deep and how fast the music ducks (2026-11-26)
- Hypothesis: ratio 6 with a 1.5 s release ducks well under speech and recovers between lines.
- Change: rendered the voice and the ducked music bed separately for 6 settings; RMS in 0.4 s windows, speech
  windows = voice above -40 dBFS (152 speech, 44 gap windows).

  | Setting | Music under speech | Music in gaps | Voice over music |
  |---|---|---|---|
  | no ducking | -32.4 dB | -32.0 dB | 14.1 dB |
  | ratio 3, release 1500 | -45.4 | -38.5 | 26.8 |
  | ratio 6, release 1500 (old) | -48.6 | -40.0 | 29.9 |
  | ratio 12, release 1500 | -50.3 | -40.4 | 31.4 |
  | ratio 6, release 600 | -45.3 | -33.4 | 27.3 |
  | ratio 6, release 300 | -42.8 | -32.1 | 24.3 |
- Result: the hypothesis was half wrong. Ducking works, but with a 1.5 s release the music never comes back in the
  short gaps (8 dB below its natural level), so the score sounded flat. 600 ms recovers to within 1.4 dB and still
  keeps the voice 27 dB on top. 300 ms lets the music creep up under speech.
- Evidence: `experiment-e7` rows in `runs.jsonl`.
- Decision: `release=600` in `assemble.DUCK`. Re-check with the real ACE-Step track, which is less steady.

## E8: centre crop vs a per-shot focus point for 9:16 (2026-11-26)
- Hypothesis: square keyframes with a centred subject survive a centre crop to 9:16 (56% of the width).
- Change: a contact sheet of every shot in the 9:16 export, then an optional `focus_x` per shot (0 left to 1 right)
  that moves the vertical slice; set on s01 (0.2), s08 (0.7), s09 (0.85).
- Result: the centre crop failed on 3 of 10 shots. In s09, "Here is your cup", the grandchild was cut to an edge of
  a face, so the key moment lost the person receiving the cup. In s01 the open door (the invitation) was out of
  frame. With focus points both are back; s09 now trades the grandmother's face for the child and the cup.
- Evidence: contact sheets of `9x16-4a019839064e.mp4` (before) and `9x16-2da98b4a0c9c.mp4` (after); FLUX does not
  centre two-person shots, so "centred subject" in ARCHITECTURE.md was an assumption, now removed.
- Decision: keep `focus_x`. It touches only the 9:16 export key, so 16:9 stays cached.

## E9: can a machine listener follow the Amharic voice (2026-11-26)
- Hypothesis: Gemini TTS Amharic is clear enough that a speech model transcribes most lines within 15% character
  error rate (CER), so the voice is not the weak point.
- Change: each of the 10 film takes went to 3 Gemini listeners (3.5-flash-lite, 3.1-flash-lite, 3.6-flash),
  CER after merging Ge'ez letters that sound the same (`experiments/e9_roundtrip.py amharic`). A line counts as
  unclear only when every listener misses it. 3.6-flash failed from s04 on (503 overload, then its 20-a-day free quota, 429), so
  s04-s09 have 2 listeners and s10 has 1.

  | Shot | TTS | Best CER | Worst CER | Unclear? |
  |---|---|---|---|---|
  | s01 | full | 16% | 28% | yes |
  | s02 | lite | 8% | 12% | no |
  | s03 | full | 20% | 37% | yes |
  | s04 | full | 19% | 33% | yes |
  | s05 | lite | 0% | 10% | no |
  | s06 | lite | 4% | 13% | no |
  | s07 | full | 21% | 28% | yes |
  | s08 | lite | 27% | 27% | yes |
  | s09 | lite | 20% | 35% | yes |
  | s10 | full | 48% (1 listener) | 48% | yes |
- Result: the hypothesis was wrong. 7 of 10 lines are unclear to every listener. The errors gather on the
  words that matter most, the round names: "ቶና" came back as "ቶናኖ" and "ቶ ነው" (s08), "በረካ" as "በረቃ" and
  "በርቃ" (s09). An earlier probe heard s01's feminine "ቀረብ በይ" as masculine "በል". Listeners also disagree a lot
  on the same take (s03: 20% to 37%), so one listener is not a measure.
- The 3 clear lines are all short lite-TTS lines from E5, but so are s08 and s09, so length or model alone does
  not explain it.
- Limitation: the listener is a model from the same family, not a person. This flags lines to check; the user
  tests judge how it sounds.
- Evidence: `experiment-e9` rows in `runs.jsonl` from 19:20 on; `outputs/experiments/e9-amharic.log`.
- Decision: keep the burned-in English subtitles, which spell abol, tona and bereka in Latin letters
  (`storyboard.json` s06, s08, s09 `subtitle_en`), so a viewer who mishears a name still reads it. The round
  names are the first thing to ask the testers about.

## E10: which ACE-Step candidate follows the music cues (2026-11-26)
- Hypothesis: with one caption and three seeds, the candidates differ mostly in melody, not in shape, so any of
  them fits the cue arc (quiet drone, livelier from 27 s, flute from 49 s, tender from 62 s).
- Change: 3 candidates (seeds 40192834-36, ACE-Step 1.5 turbo, 84 s, T4). Measured with ffmpeg only
  (`experiments/e10_music.py`): short-term loudness per cue segment, crest factor, silent gaps of 1 s or more.

  | Cand. | 0-27 s | 27-49 s | 49-62 s | 62-84 s | Silent gaps (mid-film) |
  |---|---|---|---|---|---|
  | 0 | -25.6 LUFS | -22.3 | -23.2 | -23.2 | 27.6-30.5 s |
  | 1 | -22.6 | -19.2 | -18.5 | -20.9 | none |
  | 2 | -20.0 | -27.9 | -18.8 | -24.8 | none |
- Result: the hypothesis was wrong. The shapes differ a lot. Candidate 2 drops 8 dB at 27 s, the opposite of the
  cue. Candidate 0 goes silent for 2.9 s right where the pulse should start. Candidate 1 rises at 27 s and 49 s and
  softens from 62 s, the closest to the arc. Generation took 13.0 s, 7.7 s, 7.7 s.
- Evidence: `experiment-e10` and `ace` rows in `runs.jsonl`; `outputs/ace/9072530580d1-{0,1,2}.wav`.
- Decision: `music.chosen: 1`. Loudness cannot tell a krar from a guitar, so the choice still needs a listen.
  Lesson: generate several seeds and measure before listening; a seed changes the structure, not just the notes.
