"""Centralized input/output path resolver for Simplatab.

The legacy code wrote artefacts into ``./Materials`` (a path relative to the
process CWD). For the EUCAIM packaging the tool must:

* read inputs from a read-only directory (``--input`` / ``/input``),
* write all artefacts under a writable output directory
  (``--output`` / ``/output``),
* never write into ``/`` or into the input directory.

This module provides a single source of truth for the *output base directory*
(equivalent to the old ``Materials`` dir) plus helpers that create the
expected sub-folders on demand. The base directory is configured by

* :func:`set_output_base` — explicit programmatic override (used by the
  ``__main__`` CLI entrypoint and the Flask UI), or
* the ``SIMPLATAB_OUTPUT_DIR`` environment variable (set by ``__main__``
  before importing helpers), or
* the legacy default ``./Materials`` (kept so that existing notebooks /
  unit-tests still work outside the container).

All callers that previously wrote to ``./Materials`` MUST go through
:func:`materials_dir` (or a more specific helper such as
:func:`bias_assessment_dir`) so that the redirect honours the configured
output location.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

# Module-level state -- guarded by a lock so the Flask UI worker(s) and the
# background pipeline thread cannot race when overriding the output base.
_LOCK = threading.RLock()
_OUTPUT_BASE: Optional[str] = None

_ENV_VAR = "SIMPLATAB_OUTPUT_DIR"
_LEGACY_DEFAULT = "./Materials"


def set_output_base(path: str) -> str:
    """Set the absolute output base directory and ensure it exists.

    Returns the resolved absolute path.
    """
    if not path:
        raise ValueError("Output base path must be a non-empty string.")
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    with _LOCK:
        global _OUTPUT_BASE
        _OUTPUT_BASE = abs_path
    return abs_path


def get_output_base() -> str:
    """Return the configured output base directory.

    Resolution order:
      1. value set via :func:`set_output_base`,
      2. ``SIMPLATAB_OUTPUT_DIR`` environment variable,
      3. legacy default ``./Materials`` relative to the process CWD.
    """
    with _LOCK:
        if _OUTPUT_BASE:
            return _OUTPUT_BASE
    env_path = os.environ.get(_ENV_VAR)
    if env_path:
        return os.path.abspath(env_path)
    # Last-resort fallback so that legacy notebooks/tests continue to work
    # when neither set_output_base() nor the env var were used.
    return os.path.abspath(_LEGACY_DEFAULT)


def materials_dir() -> str:
    """Return the output base directory (creating it if missing)."""
    base = get_output_base()
    os.makedirs(base, exist_ok=True)
    return base


def materials_subdir(*parts: str) -> str:
    """Return ``materials_dir() / parts...`` and ensure the dir exists."""
    path = os.path.join(materials_dir(), *parts)
    os.makedirs(path, exist_ok=True)
    return path


def materials_path(*parts: str) -> str:
    """Return ``materials_dir() / parts...`` WITHOUT creating intermediate dirs.

    Useful for file paths whose parent already exists (e.g., the parent has
    been created via :func:`materials_subdir`).
    """
    return os.path.join(materials_dir(), *parts)


# Convenience helpers for well-known sub-folders so callers do not have to
# remember magic strings.

def bias_assessment_dir(file_name: str = "") -> str:
    return materials_subdir("BiasAssessment", file_name) if file_name else materials_subdir("BiasAssessment")


def confusion_matrices_dir() -> str:
    return materials_subdir("ConfusionMatrices")


def roc_curves_dir() -> str:
    return materials_subdir("ROC_Curves")


def shap_features_dir(model_name: str = "") -> str:
    return materials_subdir("Shap_Features", model_name) if model_name else materials_subdir("Shap_Features")


def models_dir() -> str:
    return materials_subdir("Models")


def error_log_path() -> str:
    return materials_path("error_log.log")
