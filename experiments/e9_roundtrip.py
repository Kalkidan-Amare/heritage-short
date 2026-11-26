"""E9 and E10: how intelligible is Gemini TTS in Amharic, and in three other Ethiopian languages?

Round trip: each narration take is transcribed by Gemini 3.8 Flash (audio in, text out) and compared with the line
that was sent to TTS. Character error rate (CER) after normalising punctuation, spaces and the Ge'ez letters that
sound the same (ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ), so spelling variants do not count as errors.

    .venv/bin/python experiments/e9_roundtrip.py amharic     # E9: the 10 film takes, no TTS calls
    .venv/bin/python experiments/e9_roundtrip.py languages   # E10: s07 in ti, om, so (1 TTS call each)

Limitation: the listener is a model from the same family as the speaker, so this measures machine
intelligibility, not how natural it sounds to a person. User tests cover that."""
import json
import os
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from common import OUT, Retryable, cached, key, load_storyboard, log, media_duration, retry  # noqa: E402
import narration  # noqa: E402

LISTENER = os.environ.get("E9_LISTENER", "gemini-3.8-flash")  # any audio-capable Gemini model
TTS_LITE = "gemini-3.8-flash-lite-tts"
DIR = OUT / "experiments" / "e9"
# Same sound, different letter: map the rarer series onto the common one, order by order (7 vowels each).
SAME = {"ሐ": "ሀ", "ኀ": "ሀ", "ሠ": "ሰ", "ዐ": "አ", "ፀ": "ጸ"}


def fold(ch):
    for src, dst in SAME.items():
        off = ord(ch) - ord(src)
        if 0 <= off < 8:
            return chr(ord(dst) + off)
    return ch


def norm(text):
    text = unicodedata.normalize("NFC", text).lower()
    return "".join(fold(c) for c in text if c.isalnum())


def cer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i]
        for j, hc in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / max(len(r), 1)


def gemini(contents, model=LISTENER):
    from google import genai
    from google.genai import errors

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def call():
        try:
            return client.models.generate_content(model=model, contents=contents).text.strip()
        except errors.APIError as e:
            if e.code in (429, 500, 502, 503, 504):
                raise Retryable(f"{e.code} {e.message}") from e
            raise

    return retry(call, attempts=6, base_delay=15)


def transcribe(wav, language):
    from google.genai import types

    prompt = (f"Transcribe this {language} speech exactly as spoken, in the language's usual script. "
              "Output only the transcript, no translation, no notes.")
    return gemini([types.Part.from_bytes(data=Path(wav).read_bytes(), mime_type="audio/wav"), prompt])


def score(label, wav, ref, language, tts_model):
    t = time.time()
    hyp = transcribe(wav, language)
    c = cer(ref, hyp)
    log("experiment-e9", label, LISTENER, {"tts_model": tts_model, "language": language}, time.time() - t,
        cer=round(c, 3), ref=ref, hyp=hyp, audio_s=round(media_duration(wav), 2))
    print(f"{label:10} {tts_model:28} CER {c:5.1%}  {hyp}")
    return c


def amharic():
    board = load_storyboard()
    m = board["models"]
    rows = []
    for shot in board["shots"]:
        text = shot["narration"].strip()
        model = shot.get("tts_model", m["tts"])
        k = key(model, m["tts_voice"], m.get("tts_style", ""), board["language"]["code"], text)
        wav = cached("narration", shot["id"], k, "wav")
        rows.append((shot["id"], model, score(shot["id"], wav, text, "Amharic", model)))
    for model in sorted({r[1] for r in rows}):
        cs = [r[2] for r in rows if r[1] == model]
        print(f"{model}: mean CER {sum(cs) / len(cs):.1%} over {len(cs)} lines")


def languages():
    board = load_storyboard()
    m = board["models"]
    src = next(s for s in board["shots"] if s["id"] == "s07")["narration"]
    DIR.mkdir(parents=True, exist_ok=True)
    for code, name in [("ti", "Tigrinya"), ("om", "Afaan Oromo"), ("so", "Somali")]:
        line_file = DIR / f"s07-{code}.txt"
        if not line_file.exists():
            t = time.time()
            line = gemini(f"Translate this Amharic sentence into {name}. Output only the translation.\n\n{src}")
            log("experiment-e9", f"translate-{code}", LISTENER, {"language": name}, time.time() - t, text=line)
            line_file.write_text(line)
        line = line_file.read_text().strip()
        wav = DIR / f"s07-{code}.wav"
        if not wav.exists():
            t = time.time()
            narration.write_wav(wav, narration.tts_gemini(line, TTS_LITE, m["tts_voice"], m.get("tts_style", "")))
            log("experiment-e9", f"tts-{code}", TTS_LITE, {"language": name, "chars": len(line)}, time.time() - t,
                audio_s=round(media_duration(wav), 2))
        score(f"s07-{code}", wav, line, name, TTS_LITE)


if __name__ == "__main__":
    {"amharic": amharic, "languages": languages}[sys.argv[1]]()
