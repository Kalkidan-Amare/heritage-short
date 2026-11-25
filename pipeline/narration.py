"""Stage: narration. One WAV per shot from Gemini TTS, so a changed line re-takes only that shot."""
import os
import time
import wave

from common import Retryable, cached, key, load_storyboard, log, retry, run_ffmpeg

STAGE = "narration"
RATE = 24000  # Gemini TTS audio is 16-bit mono at 24 kHz


def tts_gemini(text, model, voice, style):
    """One call per line. The text is read verbatim, so the delivery direction goes in speech_metadata.style."""
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"api_version": "v1beta"})
    part = types.Part(text=text, speech_metadata=types.SpeechMetadata(style=style) if style else None)
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(voice=voice)))

    def call():
        try:
            r = client.models.generate_content(model=model, contents=[types.Content(role="user", parts=[part])],
                                               config=config)
        except errors.APIError as e:
            if e.code in (429, 500, 502, 503, 504):
                raise Retryable(f"{e.code} {e.message}") from e
            raise
        return r.candidates[0].content.parts[0].inline_data.data

    return retry(call)


def tts_offline(text):
    """Silent stand-in sized to ~2.3 words per second, for tests and dry runs without a key."""
    seconds = max(1.0, len(text.split()) / 2.3)
    return b"\0\0" * int(RATE * seconds)


def write_wav(path, audio):
    """Gemini 3.8 TTS returns a complete WAV; older models return bare 16-bit PCM, which needs a header."""
    if audio[:4] == b"RIFF":
        path.write_bytes(audio)
        return
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(audio)


def run(board):
    m = board["models"]
    offline = os.environ.get("PIPELINE_OFFLINE") == "1"
    model = "offline-silence" if offline else m["tts"]
    out = {}
    for shot in board["shots"]:
        text = shot["narration"].strip()
        if not text:
            continue
        k = key(model, m["tts_voice"], m.get("tts_style", ""), board["language"]["code"], text)
        path = cached(STAGE, shot["id"], k, "wav")
        params = {"voice": m["tts_voice"], "style": m.get("tts_style", ""), "chars": len(text)}
        if path.exists():
            log(STAGE, shot["id"], model, params, 0, cache_hit=True)
        else:
            t = time.time()
            pcm = tts_offline(text) if offline else tts_gemini(text, model, m["tts_voice"], m.get("tts_style", ""))
            tmp = path.with_suffix(".raw.wav")
            write_wav(tmp, pcm)
            # Trim leading and trailing silence so shot timing follows the voice.
            if offline:
                tmp.rename(path)
            else:
                run_ffmpeg(["-i", tmp, "-af", "silenceremove=start_periods=1:start_threshold=-45dB,"
                            "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse", path])
                tmp.unlink()
            log(STAGE, shot["id"], model, params, time.time() - t)
            print(f"  narration {shot['id']}: {path.name}")
        out[shot["id"]] = path
    return out


if __name__ == "__main__":
    run(load_storyboard())
