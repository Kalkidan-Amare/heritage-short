import copy
import json

import jsonschema
import pytest

from common import ROOT, load_storyboard

FIXTURE = ROOT / "tests" / "fixtures" / "storyboard.sample.json"


def write(tmp_path, board):
    p = tmp_path / "board.json"
    p.write_text(json.dumps(board))
    return p


def test_sample_validates():
    board = load_storyboard(FIXTURE)
    assert [s["id"] for s in board["shots"]] == ["s01", "s02", "s03"]


@pytest.mark.parametrize("mutate", [
    lambda b: b.pop("audience"),
    lambda b: b["shots"][0].pop("reason"),
    lambda b: b["shots"][0].update(id="shot1"),
    lambda b: b["shots"][0].update(duration=1),
    lambda b: b["shots"][0].update(motion="zoom"),
    lambda b: b.update(unknown_field=True),
    lambda b: b["language"].update(code="Amharic"),
], ids=["no-audience", "shot-without-reason", "bad-id", "too-short", "bad-motion", "unknown-field", "bad-lang-code"])
def test_invalid_boards_are_rejected(tmp_path, mutate):
    board = json.loads(FIXTURE.read_text())
    mutate(board)
    with pytest.raises(jsonschema.ValidationError):
        load_storyboard(write(tmp_path, board))


def test_duplicate_shot_ids_are_rejected(tmp_path):
    board = json.loads(FIXTURE.read_text())
    board["shots"].append(copy.deepcopy(board["shots"][0]))
    with pytest.raises(jsonschema.ValidationError, match="duplicate shot ids"):
        load_storyboard(write(tmp_path, board))
