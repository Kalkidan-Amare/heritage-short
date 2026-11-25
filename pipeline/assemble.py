"""Stage: assembly. Lays narration on the timeline, ducks the score under it, normalises loudness, burns in
English subtitles, appends the AI end card and exports 16:9 and 9:16. The radio cut is the same mix on black."""
import time
import textwrap

from PIL import Image, ImageDraw, ImageFont

from common import BASE, FPS, OUT, cached, key, log, run_ffmpeg

STAGE = "assemble"
CUTS = {"16x9": (1280, 720), "9x16": (720, 1280)}
DUCK = "sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500"
MUSIC_GAIN_DB = -6  # music bed level before ducking, relative to its own -24 LUFS pre-normalisation


def srt_time(s):
    ms = round(s * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def subtitles(board, starts, narr_len):
    """SRT cues: at most two lines of about 40 characters; long lines are split across the narration time by words."""
    cues = []
    for shot in board["shots"]:
        text = shot["subtitle_en"].strip()
        if not text:
            continue
        lines = textwrap.wrap(text, 40)
        chunks = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        span = narr_len.get(shot["id"]) or shot["duration"] - 0.5
        words = [len(" ".join(c).split()) for c in chunks]
        t = starts[shot["id"]]
        for c, w in zip(chunks, words):
            d = span * w / sum(words)
            cues.append((t, t + d, "\n".join(c)))
            t += d
    return "\n".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cues, 1))


def end_card(text, size, path):
    w, h = size
    img = Image.new("RGB", size, "black")
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=max(28, w // 22))
    lines = textwrap.wrap(text, 26 if w < h else 40)
    y = h / 2 - len(lines) * font.size * 0.7
    for ln in lines:
        d.text((w / 2, y), ln, font=font, fill="white", anchor="ma")
        y += font.size * 1.4
    img.save(path)


def loudnorm_two_pass(src, dst, extra_out):
    """Measure, then normalise to -14 LUFS integrated, -1 dBTP, as YouTube and most social platforms expect."""
    import json
    import subprocess
    from common import ffmpeg
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(src), "-af",
                        "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    run_ffmpeg(["-i", src, "-af",
                f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
                f"linear=true,aresample=48000", *extra_out, dst])
    return m


def mix(board, narration, music, durations, total):
    """Narration placed at each shot start, music ducked under it, then two-pass loudness normalisation."""
    starts, t = {}, 0.0
    for s in board["shots"]:
        starts[s["id"]] = t
        t += durations[s["id"]]
    ids = [s["id"] for s in board["shots"] if s["id"] in narration]
    k = key("mix", [(i, starts[i], narration[i]) for i in ids], music, total, DUCK, MUSIC_GAIN_DB)
    path = cached(STAGE, "mix", k, "wav")
    if path.exists():
        log(STAGE, "mix", "ffmpeg", {"total": total}, 0, cache_hit=True)
        return path, starts
    tm = time.time()
    args, chains = [], []
    for n, i in enumerate(ids):
        args += ["-i", narration[i]]
        ms = round(starts[i] * 1000)
        chains.append(f"[{n}:a]aresample=48000,adelay={ms}|{ms},apad[n{n}]")
    voice = "".join(f"[n{n}]" for n in range(len(ids)))
    m = len(ids)
    args += ["-stream_loop", "-1", "-i", music]
    graph = ";".join(chains) + (
        f";{voice}amix=inputs={len(ids)}:normalize=0,atrim=0:{total},pan=stereo|c0=c0|c1=c0,asplit=2[v][sc]"
        f";[{m}:a]aresample=48000,atrim=0:{total},loudnorm=I=-24:TP=-2,volume={MUSIC_GAIN_DB}dB,"
        f"afade=t=out:st={total - 3}:d=3,aformat=channel_layouts=stereo[mu]"
        f";[mu][sc]{DUCK}[ducked];[v][ducked]amix=inputs=2:normalize=0[out]")
    raw = path.with_suffix(".raw.wav")
    run_ffmpeg([*args, "-filter_complex", graph, "-map", "[out]", "-t", total, raw])
    measured = loudnorm_two_pass(raw, path, ["-ac", "2"])
    raw.unlink()
    log(STAGE, "mix", "ffmpeg", {"total": total, "duck": DUCK, "input_lufs": measured["input_i"]}, time.time() - tm)
    return path, starts


def export(board, shots, audio, srt, total, radio=False):
    outs = {}
    film_len = total - board["end_card"]["duration"]
    for name, (w, h) in CUTS.items():
        if radio and name == "9x16":
            continue
        label = "radio-cut" if radio else name
        inputs = [shots[s["id"]] for s in board["shots"]] if not radio else []
        margin = 60 if h > w else 30  # keep vertical subtitles above the platform buttons
        style = f"FontName=DejaVu Sans,FontSize={8 if h > w else 14},Outline=2,MarginV={margin}"
        k = key("export", label, inputs, audio, srt, board["end_card"], board["title"], style, (w, h))
        path = cached("film", label, k, "mp4")
        if path.exists():
            log(STAGE, label, "ffmpeg", {}, 0, cache_hit=True)
            outs[label] = path
            continue
        t = time.time()
        srt_path = path.with_suffix(".srt")
        srt_path.write_text(srt)
        card = path.with_suffix(".card.png")
        end_card(board["end_card"]["text"], (w, h), card)
        sub = f"subtitles={srt_path.as_posix()}:force_style='{style}'"
        if radio:
            args = ["-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={FPS}:d={film_len}"]
            vchain = f"[0:v]{sub},format=yuv420p[film]"
            n = 1
        else:
            args = []
            for p in inputs:
                args += ["-i", p]
            n = len(inputs)
            crop = f"crop={w}:{h}:{(BASE - w) // 2}:{(BASE - h) // 2}" if w != h else ""
            vchain = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0,{crop},{sub},format=yuv420p[film]"
        args += ["-loop", "1", "-t", board["end_card"]["duration"], "-r", FPS, "-i", card, "-i", audio]
        graph = (f"{vchain};[{n}:v]format=yuv420p,fade=t=in:d=0.5[card];[film][card]concat=n=2:v=1:a=0[v]")
        run_ffmpeg([*args, "-filter_complex", graph, "-map", "[v]", "-map", f"{n + 1}:a", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "20", "-r", FPS, "-c:a", "aac", "-b:a", "192k", "-t", total,
                    "-movflags", "+faststart", path])
        card.unlink()
        log(STAGE, label, "ffmpeg", {"size": f"{w}x{h}", "seconds": total}, time.time() - t)
        print(f"  export {label}: {path.relative_to(OUT.parent)}")
        outs[label] = path
    return outs


def run(board, narration, music, durations, shots=None, radio=False):
    from common import media_duration
    film_len = sum(durations.values())
    total = round((film_len + board["end_card"]["duration"]) * FPS) / FPS
    audio, starts = mix(board, narration, music, durations, total)
    narr_len = {i: media_duration(p) for i, p in narration.items()}
    srt = subtitles(board, starts, narr_len)
    return export(board, shots, audio, srt, total, radio=radio)
