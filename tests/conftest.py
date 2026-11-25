"""Every test runs offline against a temporary outputs folder and call log, never the real ones."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_tmp = Path(tempfile.mkdtemp(prefix="heritage-test-"))
os.environ["PIPELINE_OUT"] = str(_tmp / "outputs")
os.environ["PIPELINE_RUNS"] = str(_tmp / "runs.jsonl")
os.environ["PIPELINE_OFFLINE"] = "1"
os.environ["STORYBOARD"] = str(ROOT / "tests" / "fixtures" / "storyboard.sample.json")
sys.path.insert(0, str(ROOT / "pipeline"))
