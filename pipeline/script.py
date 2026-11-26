"""Stage: script. Drafts a storyboard from story.md (my notes from talking to the storyteller) with Gemini, then
validates it against the schema. It writes storyboard.draft.json and never overwrites storyboard.json: I edit the
draft by hand and copy it over, so every change after that is mine and shows in git.

    python pipeline/script.py [story.md]
"""
import json
import sys
import time
from pathlib import Path

import jsonschema

from common import ROOT, Retryable, load_storyboard, log, retry

MODEL = "gemini-3.8-flash"  # id per https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash (checked 2026-11-26)
# The first draft invented retired model ids (gemini-1.5-pro, svd-xt), so the models block is ours, not Gemini's.
MODELS = {
    "text": MODEL,
    "image": "@cf/black-forest-labs/flux-2-klein-4b",  # takes reference images, so the character can stay the same
    "tts": "gemini-3.8-flash-tts",
    "tts_voice": "Gacrux",
    "tts_style": "an elderly grandmother, warm, slow and tender, speaking to her grandchild",
    "video": "wan2.2-ti2v-5b",
    "music": "ace-step-1.5",
}

INSTRUCTIONS = """You draft a storyboard for a 60 to 90 second heritage short film.
Return only JSON that matches the schema below. Rules:
- 8 to 12 shots. Durations add up to 60-85 seconds. Every shot has a one-line reason it exists.
- Narration is in {language}, spoken by the storyteller in the first person, short sentences, about 2 words per second
  of shot duration. subtitle_en is a faithful English translation of that line.
- image_prompt describes one still: subject, setting, light, framing. No text or letters in the image.
- Shots with the main character set shows_character true. Keep the character's look out of image_prompt; it is added.
- motion "video" only for 3 to 5 shots where movement matters; motion_prompt says only what moves and how the camera moves.
- Use only facts from the notes. Do not invent names, dates or events.
Schema:
{schema}
Notes from the storyteller:
{notes}"""


def draft(notes, language, model):
    import os
    from google import genai
    from google.genai import errors

    schema = (ROOT / "schema" / "storyboard.schema.json").read_text()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = INSTRUCTIONS.format(language=language, schema=schema, notes=notes)

    def call():
        try:
            r = client.models.generate_content(model=model, contents=prompt,
                                               config={"response_mime_type": "application/json"})
        except errors.APIError as e:
            if e.code in (429, 500, 502, 503, 504):
                raise Retryable(f"{e.code} {e.message}") from e
            raise
        return r.text

    # Free-tier Gemini 3.8 answers 503 "high demand" for minutes at a time (FAILURES.md), so wait longer than the default.
    return retry(call, attempts=6, base_delay=15)


def main(notes_path="story.md"):
    notes = (ROOT / notes_path).read_text()
    language = next((ln.split(":", 1)[1].strip() for ln in notes.splitlines() if ln.lower().startswith("language:")),
                    "English")
    t = time.time()
    try:
        text = draft(notes, language, MODEL)
    except Exception as e:
        log("script", "storyboard", MODEL, {"notes_chars": len(notes), "language": language}, time.time() - t,
            status="error", error=str(e)[:300])
        raise
    out = ROOT / "storyboard.draft.json"
    try:
        board = json.loads(text)
        board["models"] = MODELS
        text = json.dumps(board, ensure_ascii=False, indent=2) + "\n"
    except (json.JSONDecodeError, TypeError):
        pass  # saved as is; validation below reports it
    out.write_text(text)
    try:
        board = load_storyboard(out)
        status, err = "ok", None
        print(f"  draft ok: {len(board['shots'])} shots, {sum(s['duration'] for s in board['shots'])} s -> {out.name}")
    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
        status, err = "invalid", str(e).splitlines()[0][:300]
        print(f"  draft saved but invalid: {err}")
    log("script", "storyboard", MODEL, {"notes_chars": len(notes), "language": language}, time.time() - t,
        status=status, **({"error": err} if err else {}))


if __name__ == "__main__":
    main(*sys.argv[1:])
