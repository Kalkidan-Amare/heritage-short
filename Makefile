# One command per step. `make film` runs the whole pipeline from storyboard.json; every stage is cached.
PY := .venv/bin/python

.PHONY: setup smoke script radio film wan music test

.venv/done: requirements.txt
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	touch $@

setup: .venv/done

smoke: setup        ## call each provider once, log latency to runs.jsonl
	$(PY) pipeline/smoke.py

script: setup       ## draft storyboard.draft.json from story.md with Gemini
	$(PY) pipeline/script.py

radio: setup        ## narration over placeholder music on black
	$(PY) pipeline/run.py radio

film: setup         ## keyframes, shots, music, narration, both exports
	$(PY) pipeline/run.py film

wan: setup          ## Wan 2.2 clips for "video" shots on Kaggle (needs keyframes first)
	$(PY) pipeline/kaggle_jobs.py wan

music: setup        ## ACE-Step candidates on Kaggle
	$(PY) pipeline/kaggle_jobs.py music

test: setup         ## schema and cache tests, offline, no keys needed
	$(PY) -m pytest -q tests
