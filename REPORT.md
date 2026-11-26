# Three Cups (ሶስት ሲኒ): report

Repository: https://github.com/Kalkidan-Amare/heritage-short. Every claim below points at a file there.

## What I set out to make, and for whom
- A 78.5 s film about the Ethiopian coffee ceremony, told in Amharic by a grandmother to her grandchild, with
  English subtitles. Two formats: 9:16 for phones, 16:9.
- Audience: young Ethiopians at home and abroad who grew up around buna but never learned the steps or the names
  of the three rounds. They watch on a phone, on TikTok, Instagram and Telegram.
- Goal: at the end they can name abol, tona and bereka, and they feel that buna is about time given to each
  other, not about coffee. Written before any generation (`DESIGN.md`, Audience and intent).
- The grandmother is a made-up character with a stock voice, so no real face or voice is copied (`ETHICS.md`).

## What I learned from my audience
- Test 1, the radio cut, did not happen as its own test. The cut was ready by mid-morning, but I did not get three
  listeners before the video was done. I report that rather than make it up. The machine-listener check (E9)
  stood in for it, and it flagged the same words people flagged later (`DESIGN.md`, User test 1).

- Test 2: three people from the audience watched the 9:16 near-final cut. Their words are quoted in `DESIGN.md`.
- The story worked. All three said it was about coffee time in Ethiopia, all three named abol, tona and bereka,
  and none lost interest. That was the goal I wrote before generating anything.
- The voice did not fully work. One heard "roast" and "smoke" wrong, one heard "bereka" said wrong (the voice
  says በረቃ). E9 had already flagged the smoke line and the bereka line at 20-37% character error, so people and
  machine listeners agree.
- The pictures were the main complaint. The mortar did not look Ethiopian, the popcorn sat next to the fire, the
  jebena mouth was too wide, the men looked South Asian, and one wanted grass on the floor.
- What I changed: I rewrote the prompts for s04, s05 and s08 to describe each object by shape (goblet mukecha,
  narrow-neck jebena with a grass stopper, popcorn far from the brazier) and the neighbours by clothes, not
  faces. Only those three shots regenerated (commit 24f5b9f). The first s08 wording was blocked by the output
  filter (`FAILURES.md` F12).
- Lesson, the same as E2 but from people this time: a model does not know what an Ethiopian object looks like
  from its name. Every fix was a shape written down.

## The hardest problem: fitting 90 s on 10 voice calls a day
- The first radio cut ran 92.6 s. The voice style "slow and tender" made every Amharic line run past its shot.
  s06 took 11.0 s against an 8 s shot (`FAILURES.md` F4).
- The obvious fix was a faster voice style. That re-voices all 10 lines, and the free TTS tier allows 10 calls a
  day. I had already used them. The next call failed with a 429 (`FAILURES.md` F5).
- What I did: I cut only the five longest lines to their core meaning, from 178 to 125 syllables. I kept every
  named object and all three round names (`EXPERIMENTS.md` E5).
- To re-voice only those five lines I added a per-shot `tts_model` to the storyboard schema. They went to the
  lite TTS model, which has its own quota. The other five kept their cached takes. Film: 74.5 s plus a 4 s card.
- What it cost: the line saying no one leaves before the third cup. I put that question to user test 2.
- Measured side effect: the lite model speaks faster, 4.3 syllables per second against 3.8 (`EXPERIMENTS.md` E4).

## A suggested practice that beat my instinct: a JSON contract between stages
- My instinct was a script per stage passing files along. The brief suggested one validated `storyboard.json`.
- It paid off on the quota day above. Because every stage reads the same contract and caches on its inputs, one
  new field (`tts_model`) re-voiced 5 lines and left everything else cached. A second run with no change took
  1.9 s and made 0 model calls (`EXPERIMENTS.md` E6).
- It paid off again for 9:16. A per-shot `focus_x` field moved the crop on 3 shots and touched only the 9:16
  export, so 16:9 stayed cached (`EXPERIMENTS.md` E8).
- Logging every call to `runs.jsonl` is what made these numbers possible at all (`COSTS.md` is built from it).

## A suggested practice that did not: a reference sheet before keyframes
- The brief suggests conditioning every character shot on a reference sheet.
- I tested it on four shots, same prompt and seed, with and without the reference (`EXPERIMENTS.md` E3).
- With the reference, FLUX.2 klein copied the portrait. Every shot became the same front view: no roasting pan in
  s03, popcorn instead of a cup in s07, no neighbours in s08.
- Without it, each shot did its action, and she still read as the same woman because the text description is
  detailed (netela, tibeb border, white kemis, silver hair).
- So I set `character.use_reference: false`. This holds for klein 4B with one portrait. A full turnaround sheet or a
  LoRA might change the result.

## Ceiling work
- Open-weight models on a free GPU. ACE-Step 1.5 and Wan 2.2 TI2V-5B run as Kaggle kernels on a T4. The
  pipeline uploads the inputs, runs the kernel, downloads the results and names them by the same input hash as
  the local stages, so a rerun skips them (`pipeline/kaggle_jobs.py`).
- Music worked. ACE-Step does not install on Kaggle's Python 3.13, so the kernel builds the repo's own locked
  Python 3.12 env with uv (`FAILURES.md` F8). Three seeds of the same caption came out with very different
  shapes. I measured loudness per cue segment and picked the one that rises and falls with the story
  (`EXPERIMENTS.md` E10). About 8 s of GPU per 84 s of music.
- Motion did not. Wan crashed on numpy and missing imports (F9), then I found by reading the code that it needs
  flash-attn and bf16, which a T4 lacks. I patched in SDPA with the padding mask and fp16 (F10). The third run
  loaded, then ran out of GPU memory at 1280x704 (F11). With 4 hours left I kept Ken Burns moves on the
  keyframes and took Wan off the end card. Lesson: check the memory need against the GPU before the first run,
  not after the third.
- Is the Amharic voice clear? I sent each take to three Gemini speech models and measured character errors
  against the script. 7 of 10 lines were missed by every listener, and the errors fell on the round names:
  "tona" and "bereka" came back misspelled (`EXPERIMENTS.md` E9). A model listener is not a person, so this only
  flags lines. It is why the subtitles spell the three names in Latin letters.

## Other things I measured
- Cultural objects: naming them failed. "Sini" and "jebena" gave mugs with handles and a teapot. Describing the
  shape fixed the cups (`EXPERIMENTS.md` E2).
- Music ducking: a 1.5 s release kept the score 8 dB down in every short gap, so it sounded flat. 600 ms recovers
  to within 1.4 dB and keeps the voice 27 dB on top (`EXPERIMENTS.md` E7).
- Cost: $0 spent, all free tiers. At list price the film is under $0.10. The limits were daily quotas and
  wall-clock time, not money. One TTS call took 475 s because of 503 retries (`COSTS.md`).

## What I would build next
- Motion on a bigger GPU. The Wan stage, kernel and cache are done; it needs a 24 GB card or CPU offload of the
  text encoder (`FAILURES.md` F11). Then measure GPU minutes per second of video against Ken Burns.
- A character LoRA on the portrait, then re-run E3 to see if consistency improves without freezing the pose.
- Re-voice s03, s09 and s10, the lines two testers and E9 all flagged, once the TTS quota resets. Spell the hard
  words out in the prompt, then re-run E9 on just those lines to check they improved.
