"""Stage: moving shots. A shot marked "video" uses its Wan 2.2 clip when the Kaggle job (pipeline/wan_kaggle.py)
has produced one for the current keyframe and motion prompt; otherwise, and for "kenburns" shots, it renders a slow
pan and zoom over the keyframe. Every shot comes out as a square BASE x BASE clip at FPS, exactly its timeline length."""
import time

from common import BASE, FPS, OUT, cached, key, log, run_ffmpeg

STAGE = "shots"
ZOOM = 0.15  # total zoom over a Ken Burns shot


def wan_key(shot, keyframe):
    """Identifies the Wan clip for a shot; wan_kaggle.py names its outputs with the same key."""
    return key("wan2.2-ti2v-5b", shot["motion_prompt"], shot["seed"], keyframe)


def wan_clip(shot, keyframe):
    p = OUT / "wan" / f"{shot['id']}-{wan_key(shot, keyframe)}.mp4"
    return p if p.exists() else None


def kenburns_filter(kb, frames):
    z = f"1+{ZOOM}*on/{frames}" if kb.get("zoom", "in") == "in" else f"{1 + ZOOM}-{ZOOM}*on/{frames}"
    cx, cy = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    pan = kb.get("pan", "none")
    x = {"left": f"(iw-iw/zoom)*(1-on/{frames})", "right": f"(iw-iw/zoom)*on/{frames}"}.get(pan, cx)
    y = {"up": f"(ih-ih/zoom)*(1-on/{frames})", "down": f"(ih-ih/zoom)*on/{frames}"}.get(pan, cy)
    # Upscale first so zoompan's integer crop steps don't jitter.
    return (f"scale={BASE * 4}:{BASE * 4},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={BASE}x{BASE}:fps={FPS},"
            f"format=yuv420p")


def render(shot, keyframe, seconds):
    frames = round(seconds * FPS)
    clip = wan_clip(shot, keyframe) if shot["motion"] == "video" else None
    kb = shot.get("kenburns", {})
    source = clip.name if clip else "kenburns"
    k = key(source, kb, frames, keyframe, BASE, FPS)
    path = cached(STAGE, shot["id"], k, "mp4")
    params = {"source": source, "frames": frames, "kenburns": kb}
    if path.exists():
        log(STAGE, shot["id"], "ffmpeg", params, 0, cache_hit=True)
        return path
    t = time.time()
    if clip:
        # Trim the weak first 0.25 s, centre-crop to square, and hold the last frame if the clip is short.
        run_ffmpeg(["-ss", "0.25", "-i", clip, "-vf",
                    f"crop='min(iw,ih)':'min(iw,ih)',scale={BASE}:{BASE},fps={FPS},tpad=stop_mode=clone:stop=-1,"
                    f"format=yuv420p", "-frames:v", frames, "-an", "-c:v", "libx264", "-crf", "18", path])
    else:
        run_ffmpeg(["-loop", "1", "-i", keyframe, "-vf", kenburns_filter(kb, frames), "-frames:v", frames,
                    "-an", "-c:v", "libx264", "-crf", "18", path])
    log(STAGE, shot["id"], "ffmpeg", params, time.time() - t)
    print(f"  shot {shot['id']} ({source}): {path.name}")
    return path


def run(board, keyframes, durations):
    if any(s["motion"] == "video" and not wan_clip(s, keyframes[s["id"]]) for s in board["shots"]):
        print("  note: some video shots have no Wan clip for their current inputs yet; using Ken Burns for those")
    return {s["id"]: render(s, keyframes[s["id"]], durations[s["id"]]) for s in board["shots"]}
