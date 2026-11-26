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
