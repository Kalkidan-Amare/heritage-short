"""Caching: an unchanged re-run calls nothing, and a change to one shot regenerates only what depends on it."""
import json
from pathlib import Path

import pytest

import common
import run
from common import ROOT, key

FIXTURE = ROOT / "tests" / "fixtures" / "storyboard.sample.json"


def rows_since(n):
    lines = common.RUNS.read_text().splitlines() if common.RUNS.exists() else []
    return [json.loads(ln) for ln in lines[n:]]


def log_len():
    return len(common.RUNS.read_text().splitlines()) if common.RUNS.exists() else 0


def film(monkeypatch, tmp_path, board):
    p = tmp_path / "board.json"
    p.write_text(json.dumps(board))
    monkeypatch.setenv("STORYBOARD", str(p))
    n = log_len()
    run.main("film")
    return {(r["stage"], r["item"]) for r in rows_since(n) if not r["cache_hit"]}


def test_key_tracks_values_and_file_contents(tmp_path):
    f = tmp_path / "ref.png"
    f.write_bytes(b"a")
    k1 = key("m", "prompt", 1, f)
    assert k1 == key("m", "prompt", 1, f)
    assert k1 != key("m", "prompt", 2, f)
    f.write_bytes(b"b")
    assert k1 != key("m", "prompt", 1, f)


@pytest.fixture(scope="module")
def warm(tmp_path_factory):
    """One full offline run so the cache is warm for every test below."""
    mp = pytest.MonkeyPatch()
    board = json.loads(FIXTURE.read_text())
    film(mp, tmp_path_factory.mktemp("warm"), board)
    yield board
    mp.undo()


def test_unchanged_rerun_regenerates_nothing(warm, monkeypatch, tmp_path):
    assert film(monkeypatch, tmp_path, warm) == set()


def test_new_image_prompt_regenerates_only_that_shot(warm, monkeypatch, tmp_path):
    board = json.loads(json.dumps(warm))
    board["shots"][2]["image_prompt"] = "close-up of a radio dial, its needle trembling"
    changed = film(monkeypatch, tmp_path, board)
    # The audio does not depend on pictures, so the mix stays cached.
    assert changed == {("keyframes", "s03"), ("shots", "s03"), ("assemble", "16x9"), ("assemble", "9x16")}


def test_new_narration_line_regenerates_only_that_voice(warm, monkeypatch, tmp_path):
    board = json.loads(json.dumps(warm))
    board["shots"][0]["narration"] = "Every morning, long before the sun, the shop door opened."
    changed = film(monkeypatch, tmp_path, board)
    assert ("narration", "s01") in changed
    assert ("narration", "s02") not in changed
    assert not any(stage == "keyframes" for stage, _ in changed)


def test_every_call_is_logged_with_the_required_fields(warm):
    rows = rows_since(0)
    assert rows
    for r in rows:
        assert {"ts", "stage", "item", "model", "seed", "params", "latency_s", "cost_usd", "status", "cache_hit"} <= r.keys()
    assert all(r["seed"] is not None for r in rows if r["stage"] == "keyframes")
