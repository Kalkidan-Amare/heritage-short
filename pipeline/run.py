"""One command for the whole pipeline: validate the storyboard, then run each stage in order.
Every stage is cached by its inputs, so a re-run only regenerates what changed.

    python pipeline/run.py radio   # narration over placeholder music on black (the first prototype)
    python pipeline/run.py film    # keyframes, shots, music, narration, both exports
"""
import sys
import time

import assemble
import keyframes
import music
import narration
import shots
from common import load_storyboard, timeline


def main(mode="film"):
    t = time.time()
    board = load_storyboard()
    print(f"storyboard ok: {board['title']} ({len(board['shots'])} shots, {board['language']['name']})")
    narr = narration.run(board)
    durations = timeline(board, narr)
    total = sum(durations.values()) + board["end_card"]["duration"]
    bed = music.run(board, total)
    if mode == "radio":
        outs = assemble.run(board, narr, bed, durations, radio=True)
    else:
        frames = keyframes.run(board)
        clips = shots.run(board, frames, durations)
        outs = assemble.run(board, narr, bed, durations, shots=clips)
    print(f"done in {time.time() - t:.1f}s, film {sum(durations.values()):.1f}s + end card:")
    for name, p in outs.items():
        print(f"  {name}: {p}")


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["film"]))
