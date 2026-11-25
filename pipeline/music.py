"""Stage: music. Uses the ACE-Step candidate chosen in the storyboard (generated on Kaggle by
pipeline/kaggle_jobs.py music); until one is chosen, a quiet synthesized placeholder bed stands in, as in a radio cut."""
import time

from common import OUT, cached, key, log, run_ffmpeg

STAGE = "music"


def ace_key(board):
    """Identifies an ACE-Step batch; kaggle_jobs.py names candidates <key>-<index>.wav with the same key."""
    m = board["music"]
    return key("ace-step-1.5", m["caption"], m.get("bpm"), m.get("key"), m["duration"], m.get("instrumental", True),
               m["candidates"], m["seed"])


def candidates(board):
    return sorted((OUT / "ace").glob(f"{ace_key(board)}-*.wav"))


def placeholder(seconds):
    """A soft A-minor pad: three sines with slow tremolo, low-passed. Deterministic, no model involved."""
    k = key("placeholder-pad", seconds)
    path = cached(STAGE, "placeholder", k, "wav")
    if path.exists():
        log(STAGE, "placeholder", "ffmpeg", {"seconds": seconds}, 0, cache_hit=True)
        return path
    t = time.time()
    expr = ("0.2*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*0.11*t))+0.15*sin(2*PI*261.63*t)*(0.6+0.4*sin(2*PI*0.07*t))"
            "+0.15*sin(2*PI*329.63*t)*(0.6+0.4*sin(2*PI*0.13*t))")
    run_ffmpeg(["-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={seconds}", "-af",
                "lowpass=f=900,afade=t=in:d=2", "-ac", "2", path])
    log(STAGE, "placeholder", "ffmpeg", {"seconds": seconds}, time.time() - t)
    return path


def run(board, seconds):
    chosen = board["music"].get("chosen")
    found = candidates(board)
    if chosen is not None:
        if chosen < len(found):
            log(STAGE, f"candidate-{chosen}", "ace-step-1.5", {"file": found[chosen].name}, 0, cache_hit=True)
            return found[chosen]
        print(f"  note: music candidate {chosen} not found for the current caption; using the placeholder bed")
    return placeholder(seconds)
