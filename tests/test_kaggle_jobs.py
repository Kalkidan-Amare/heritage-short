"""The Kaggle round trip, with the Kaggle CLI faked: files the kernel returns must be the ones the next film run finds."""
import json

import common
import kaggle_jobs
import keyframes
import music
import shots
import pytest
from common import load_storyboard


@pytest.fixture(autouse=True)
def own_outputs(monkeypatch, tmp_path):
    """Fake clips must never reach the cache the film tests use."""
    for mod in (common, kaggle_jobs, music, shots):
        monkeypatch.setattr(mod, "OUT", tmp_path / "outputs")


def fake_kernel(make_files):
    def run_kernel(name, dataset, work):
        out = work / "output"
        out.mkdir(parents=True, exist_ok=True)
        timings = make_files(work / "data", out)
        (out / "timings.json").write_text(json.dumps(timings))
        return out, 1.0
    return run_kernel


def test_wan_clips_land_where_shots_look(monkeypatch):
    board = load_storyboard()
    monkeypatch.setattr(kaggle_jobs, "push_dataset", lambda slug, folder, title: "me/" + slug)

    def make(data, out):
        jobs = json.loads((data / "jobs.json").read_text())
        timings = {}
        for j in jobs:
            assert (data / j["image"]).exists()
            (out / j["file"]).write_bytes(b"mp4")
            timings[j["id"]] = {"file": j["file"], "status": "ok", "latency_s": 600, "seed": j["seed"]}
        return timings

    monkeypatch.setattr(kaggle_jobs, "run_kernel", fake_kernel(make))
    n = len(common.RUNS.read_text().splitlines()) if common.RUNS.exists() else 0
    got = kaggle_jobs.wan(board)
    frames = keyframes.run(board)
    video = [s for s in board["shots"] if s["motion"] == "video"]
    assert len(got) == len(video) == 1
    assert all(shots.wan_clip(s, frames[s["id"]]) for s in video)
    rows = [json.loads(ln) for ln in common.RUNS.read_text().splitlines()[n:] if '"stage": "wan"' in ln]
    assert rows and rows[0]["gpu_minutes"] == 10.0
    # A second call has nothing left to send.
    assert kaggle_jobs.wan(board) == []


def test_failed_candidate_is_logged_not_moved(monkeypatch):
    board = load_storyboard()
    monkeypatch.setattr(kaggle_jobs, "push_dataset", lambda slug, folder, title: "me/" + slug)

    def make(data, out):
        job = json.loads((data / "job.json").read_text())
        (out / f"{job['key']}-0.wav").write_bytes(b"wav")
        return {f"{job['key']}-0": {"file": f"{job['key']}-0.wav", "status": "ok", "latency_s": 90, "seed": 42},
                f"{job['key']}-1": {"file": f"{job['key']}-1.wav", "status": "error", "latency_s": 5,
                                    "error": "CUDA out of memory"}}

    monkeypatch.setattr(kaggle_jobs, "run_kernel", fake_kernel(make))
    got = kaggle_jobs.music_job(board)
    assert len(got) == 1
    assert [p.name for p in music.candidates(board)] == [f"{music.ace_key(board)}-0.wav"]
    last = json.loads(common.RUNS.read_text().splitlines()[-1])
    assert last["status"] == "error" and "out of memory" in last["error"]
