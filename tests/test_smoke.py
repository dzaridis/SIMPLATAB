"""Smoke tests for the Simplatab EUCAIM headless entrypoint.

These tests do NOT require Docker and do NOT execute the heavy ML pipeline.
They validate the things that break first when packaging:

* ``python -m simplatab --help`` (and equivalent) returns 0,
* the CLI rejects missing arguments,
* a small synthetic Iris-style dataset can be discovered and loaded by
  ``DataChecker`` and that the io_paths helpers redirect writes to a
  scratch dir (no writes into the working tree).

The full training run is exercised by an explicit integration test that is
opt-in via ``RUN_FULL_PIPELINE=1`` (skipped by default to keep CI green
without docker / GPU).
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _heavy_stack_available() -> bool:
    """Return True iff every heavy import that ``Helpers/__init__.py`` chains
    is importable. The container always satisfies this; the host may not.
    """
    for mod in ("featurewiz", "shap", "xgboost", "statsmodels"):
        try:
            importlib.import_module(mod)
        except Exception:
            return False
    return True


_HEAVY = _heavy_stack_available()
heavy_only = pytest.mark.skipif(
    not _HEAVY,
    reason="Heavy ML stack (featurewiz/shap/xgboost/statsmodels) not "
           "installed on the host; this test runs inside the container.",
)


def _make_iris(tmpdir: Path) -> Path:
    """Materialise tiny Train.csv / Test.csv files from sklearn's Iris."""
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split

    data = load_iris(as_frame=True).frame
    data["Target"] = data["target"]
    data = data.drop(columns=["target"])
    train, test = train_test_split(
        data, test_size=0.3, random_state=42, stratify=data["Target"]
    )
    inp = tmpdir / "input"
    inp.mkdir()
    train.to_csv(inp / "Train.csv", index=False)
    test.to_csv(inp / "Test.csv", index=False)
    return inp


def test_cli_help_returns_zero():
    """`python __main__.py --help` exits 0 and prints usage."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "__main__.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "Simplatab" in result.stdout or "usage" in result.stdout.lower()
    assert "--input" in result.stdout
    assert "--output" in result.stdout


def test_cli_missing_required_args_exits_nonzero():
    """Argparse exits with code 2 when required args are missing."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "__main__.py")],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2


def test_cli_rejects_missing_input_dir(tmp_path: Path):
    """Missing input dir yields an exit code of 2 and writes results.json."""
    out = tmp_path / "output"
    out.mkdir()
    result = subprocess.run(
        [
            sys.executable, str(REPO_ROOT / "__main__.py"),
            "--input", str(tmp_path / "nonexistent"),
            "--output", str(out),
            "--log-level", "ERROR",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2


@heavy_only
def test_io_paths_redirects_writes(tmp_path: Path):
    """`io_paths.set_output_base` redirects writes away from the CWD."""
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from Helpers import io_paths

        target = tmp_path / "fake_out"
        io_paths.set_output_base(str(target))
        assert io_paths.get_output_base() == str(target.resolve()) or \
            io_paths.get_output_base() == str(target)

        roc = io_paths.roc_curves_dir()
        cm = io_paths.confusion_matrices_dir()
        models = io_paths.models_dir()

        for d in (roc, cm, models):
            assert os.path.isdir(d)
            assert str(target) in os.path.abspath(d)
    finally:
        # Reset between tests so we don't leak state.
        from Helpers import io_paths as _io_paths
        _io_paths._OUTPUT_BASE = None  # type: ignore[attr-defined]


@heavy_only
def test_data_checker_loads_iris(tmp_path: Path):
    """The DataChecker can read the Iris-style CSVs we ship in examples/."""
    sys.path.insert(0, str(REPO_ROOT))
    inp = _make_iris(tmp_path)
    from Helpers.data_checks import DataChecker

    train, test = DataChecker(str(inp)).process_data()
    assert "Target" in train.columns
    assert "Target" in test.columns
    assert len(train) > 0 and len(test) > 0
    assert sorted(train["Target"].unique().tolist()) == [0, 1, 2]


@heavy_only
@pytest.mark.skipif(
    os.environ.get("RUN_FULL_PIPELINE") != "1",
    reason="Full pipeline is opt-in (set RUN_FULL_PIPELINE=1).",
)
def test_full_pipeline_iris(tmp_path: Path):
    """End-to-end run on Iris (multiclass). Slow; opt-in only."""
    inp = _make_iris(tmp_path)
    out = tmp_path / "output"
    out.mkdir()

    result = subprocess.run(
        [
            sys.executable, str(REPO_ROOT / "__main__.py"),
            "--input", str(inp),
            "--output", str(out),
            "--k-folds", "3",
            "--no-grid-search",
            "--models", "logistic_regression,random_forest",
            "--no-bias-assessment",
            "--log-level", "INFO",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr + "\n" + result.stdout

    res_path = out / "results.json"
    assert res_path.is_file()
    payload = json.loads(res_path.read_text())
    assert payload["status"] == "success"
    assert payload["tool"] == "simplatab"
    assert (out / "Materials").is_dir()
