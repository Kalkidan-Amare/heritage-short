# Ethics

## Consent record
Every real person shown, named or voiced. Recorded before anything of them is generated.

| Person (role) | Appears as | Consent given for | How recorded | Date |
|---|---|---|---|---|
| None | - | - | - | - |

No real person is shown, named or voiced. The grandmother is a made-up character, drawn by FLUX.2 from a text
description, and her voice is the stock Gemini voice `Gacrux`. No voice was cloned and no photo of a relative was
used as a reference. If a real relative is added later, their consent goes in this table first.

## Licences
| Item | Model or source | Licence | Link |
|---|---|---|---|
| Storyboard draft | Gemini 3.8 Flash | Gemini API terms (outputs are mine to use) | https://ai.google.dev/gemini-api/terms |
| Narration | Gemini 3.8 Flash TTS, voice Gacrux | Gemini API terms | https://ai.google.dev/gemini-api/terms |
| Keyframes | FLUX.2 klein 4B on Cloudflare Workers AI | Apache 2.0 (model card, checked 2026-11-26) | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B |
| Moving shots | Wan 2.2 TI2V-5B on Kaggle | Apache 2.0 (model card, checked 2026-11-26) | https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B |
| Score | ACE-Step 1.5 on Kaggle | MIT (model card, checked 2026-11-26); outputs may be used commercially | https://huggingface.co/ACE-Step/Ace-Step1.5 |
| Fonts | Noto Sans Ethiopic, DejaVu Sans | SIL OFL / free licence | system packages |

## Labelling plan
- End card in both exports: the `end_card.text` in `storyboard.json`.
- The public post says the film was made with AI and names the models. The platform's AI-content switch is on.
- Provenance: files are not re-encoded to strip metadata; any SynthID watermark in the Gemini audio stays in.

## Style and private data
- Style is described by qualities (painterly, warm umber, charcoal glow), never by a living artist's name.
- Nothing private is sent to the free endpoints: the story notes are general cultural facts, no family names,
  photos or addresses. Free-tier Gemini may use inputs to improve its models, so this matters.
