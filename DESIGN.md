# Design

## Audience and intent
Written before any generation.
- Who watches, and where: young Ethiopians, at home and in the diaspora, on a phone (TikTok, Instagram, Telegram).
  Many grew up with the ceremony but never learned the steps or the names of the three rounds.
- What they should feel or understand at the end: that buna is about time given to each other, not about coffee.
  They should be able to name abol, tona and bereka, and want to sit through a whole ceremony next time.

## Story
- Whose story, and their relation to me: the coffee ceremony my family holds at home. It is told by a grandmother
  who is a made-up character, not a real person, so no one's face or voice is copied (see ETHICS.md).
- Language of narration: Amharic, with English subtitles.
- Notes: `story.md`. Draft storyboard by Gemini from those notes, then edited by hand (see git history of
  `storyboard.json`: Amharic wording in s01-s03, models block, end card).

## User test 1: radio cut
Narration over placeholder music on black (`make radio`, `~/Videos/three-cups-radio-cut-v2.mp4`).
- Not run as a separate test. The radio cut was ready at 10:50 on 26 Nov, but I did not get three people to listen
  to it on its own before the video was ready. I am not inventing results for it.
- What stood in for it: the machine-listener check in `EXPERIMENTS.md` E9 (the same narration, sent to three
  speech models). It flagged the round names before any person heard them, and test 2 confirmed it.

## User test 2: near-final cut
Film v3, 9:16 (`make film`, commit 6bd5d01), shown on 26 Nov evening. Roles and channel: not given yet.
Notes as given are kept word for word outside the repo; quotes below are exact.

| Person | What they said (quote) | What I changed |
|---|---|---|
| P1, role not given, written answers | Story: "traditional coffee time in ethiopia". Rounds: "Abol, tona, bereka". "the words 'roast' and 'smoke' sounded wrong". "I didn't loose interes". "The mortar and pestle picture doesn't look ethiopian". "The popcorn is too close to the fire where the jabena is on, in real life it would catch fire" | s04 prompt now describes a mukecha by shape (one log, goblet, narrow waist) and an iron rod zenezena. s05 puts the popcorn basket far from the brazier. Voice: not changed (see below) |
| P2, role not given, voice note | Story: "coffee in Ethiopia". Rounds: "abole, tona, bereka". The video "was saying bereka instead of bereka" (the transcript lost the difference; the voice says በረቃ, not በረካ). "the opening was a bit wide for jabana that I used to know". "I actually didn't lose interest" | s05 jebena: long narrow neck with a tiny opening plugged with grass, short spout at the base of the neck |
| P3, role not given (P2 called them "a desperate", likely diaspora), reported by P2 | "the sound was a bit uh lagged". "it would have been good if we could see a star the grass around the ceremony" (grass strewn on the floor). "he didn't lose uh uh an interest". "the woman actually look like uh Ethiopian but the the men are a bit they seem a bit Asian I don't know Indian". "The actual the color tone is great" | s04, s05, s08 now show fresh grass on the floor. s08 neighbours are described as Habesha, a man in a gabi and a woman with braids |

What it told me:
- All 3 named the story and all three rounds, and nobody lost interest. The audience goal in this file is met.
- 2 of 3 heard a wrong word. P1: "roast" (s02, s10) and "smoke" (s03). P2: bereka (s09). E9 had flagged s03 and s09
  (character error 20-37%) and s10 (48%). People and machine listeners agree on the same lines.
- 3 of 3 commented on a picture. Every picture problem was a missing or vague object description, the same lesson
  as E2: naming a cultural object is not enough, its shape has to be written down.

Storyboard changes made because of it: commit 24f5b9f
(https://github.com/Kalkidan-Amare/heritage-short/commit/24f5b9f). Only s04, s05 and s08 regenerated: 3 keyframe
calls and 3 shot renders, every other stage cached (run log: `keyframe s04/s05/s08`, `shot s04/s05/s08`, then the two
exports). Before and after: `outputs/experiments/user-test-2/before-top-after-bottom.jpg`.
The first s08 wording was blocked by Cloudflare's output filter (`FAILURES.md` F12).

Not changed today, and why:
- Re-voicing "roast", "smoke" and "bereka". The free TTS quota was spent (F5), and a new take of the same text may
  say the word the same way. Next step: re-voice s03, s09, s10 with the word spelled out, then re-run E9 on them.
- "The sound was a bit lagged" (P3). Too vague to act on without asking what P3 meant: voice speed, or the
  picture changing after the voice.

## Shot reasons
Each shot's reason lives in `storyboard.json` (`reason`, required by the schema).
