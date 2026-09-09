.PHONY: install test test-verbose lint gate1

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

test-verbose:
	python -m pytest -v

# Gate 1 = every mechanism assertion passes. This target is the gate.
gate1:
	python -m pytest -v tests/test_surprise_gate.py tests/test_promotion_gate.py tests/test_ttl.py tests/test_replay.py tests/test_clock_skew.py tests/test_supersession.py
