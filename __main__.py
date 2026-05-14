"""Simplatab — EUCAIM headless entrypoint.

Runs the Simplatab automated ML pipeline in batch (non-interactive) mode:

* reads ``Train.csv``, ``Test.csv`` and (optionally) a YAML parameter file
  from ``--input`` (treated as read-only),
* writes every artefact (metrics, plots, SHAP, models, bias reports) under
  ``--output``,
* emits a ``results.json`` index file at the root of the output directory
  describing the run status,
* logs to stdout/stderr (level controlled via ``--log-level``),
* traps SIGTERM/SIGINT for graceful shutdown.

The Flask UI is preserved as a separate entrypoint (``app.py``) and is not
invoked from this module.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import signal
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


_DEFAULT_PARAMS: Dict[str, Any] = {
    "BiasAssessment": False,
    "Feature": "",
    "number_of_k_folds": 5,
    "apply_grid_search": {
        "enabled": False,
        "type": {"Randomized": True, "Exhaustive": False},
    },
    "Correlation Limit": 0.9,
    "Metric For Threshold Optimization": "F-score",
    "Machine Learning Models": {
        "Logistic Regression": True,
        "Support Vector Machines": False,
        "Random Forest": True,
        "Stochastic Gradient Descent": False,
        "Multi-Layer Neural Network": False,
        "Decision Trees": False,
        "XGBoost": True,
    },
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="simplatab",
        description=(
            "Simplatab — automated ML pipeline for tabular data "
            "(EUCAIM batch mode)."
        ),
    )
    p.add_argument(
        "--input", "-i", required=True,
        help=("Read-only input directory containing Train.csv, Test.csv and "
              "optionally machine_learning_parameters.yaml."),
    )
    p.add_argument(
        "--output", "-o", required=True,
        help="Writable output directory for all generated artefacts.",
    )
    p.add_argument(
        "--params-file",
        help=("Optional path to a YAML parameter file (defaults to "
              "<input>/machine_learning_parameters.yaml if present)."),
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Log verbosity (default INFO).",
    )

    # Behavioural overrides — every flag has a sane default that mirrors the
    # YAML file; CLI flags win over the YAML values when both are present.
    p.add_argument(
        "--k-folds", type=int, default=None,
        help="Number of stratified k-folds for cross-validation (>=2).",
    )
    p.add_argument(
        "--correlation-limit", type=float, default=None,
        help="Pairwise feature correlation limit for filtering (0-1).",
    )
    p.add_argument(
        "--threshold-metric", default=None,
        choices=("F-score", "Sensitivity", "Specificity",
                 "Accuracy", "Balanced Accuracy", "AUC"),
        help="Metric used for binary threshold optimisation.",
    )

    # Boolean flags use mutually-exclusive groups (Python 3.9 lacks
    # argparse.BooleanOptionalAction in some builds and has awkward semantics
    # in others).
    bias = p.add_mutually_exclusive_group()
    bias.add_argument(
        "--bias-assessment", dest="bias_assessment", action="store_true",
        help="Enable DBDM bias assessment on Train.csv and Test.csv.",
    )
    bias.add_argument(
        "--no-bias-assessment", dest="bias_assessment", action="store_false",
        help="Disable bias assessment.",
    )
    p.set_defaults(bias_assessment=None)

    p.add_argument(
        "--bias-feature", default=None,
        help="Sensitive feature column used for bias assessment.",
    )

    grid = p.add_mutually_exclusive_group()
    grid.add_argument(
        "--grid-search", dest="grid_search", action="store_true",
        help="Enable hyper-parameter grid search.",
    )
    grid.add_argument(
        "--no-grid-search", dest="grid_search", action="store_false",
        help="Disable hyper-parameter grid search (faster).",
    )
    p.set_defaults(grid_search=None)
    p.add_argument(
        "--grid-search-type", default=None,
        choices=("randomized", "exhaustive"),
        help="Type of hyper-parameter search when --grid-search is on.",
    )

    p.add_argument(
        "--models", default=None,
        help=("Comma-separated list of models to train (overrides YAML). "
              "Allowed values: logistic_regression, svm, random_forest, "
              "sgd, mlp, decision_trees, xgboost."),
    )

    return p


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )


def _install_signal_handlers() -> None:
    def _shutdown(signum, _frame):  # pragma: no cover - signal handler
        try:
            name = signal.Signals(signum).name
        except ValueError:
            name = str(signum)
        logging.warning("Received %s — shutting down gracefully.", name)
        sys.exit(128 + signum)

    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, _shutdown)


_MODEL_KEY_ALIASES = {
    "logistic_regression": "Logistic Regression",
    "svm": "Support Vector Machines",
    "support_vector_machines": "Support Vector Machines",
    "random_forest": "Random Forest",
    "sgd": "Stochastic Gradient Descent",
    "stochastic_gradient_descent": "Stochastic Gradient Descent",
    "mlp": "Multi-Layer Neural Network",
    "multi_layer_neural_network": "Multi-Layer Neural Network",
    "neural_network": "Multi-Layer Neural Network",
    "decision_trees": "Decision Trees",
    "decision_tree": "Decision Trees",
    "xgboost": "XGBoost",
}


def _load_params(args: argparse.Namespace, log: logging.Logger) -> Dict[str, Any]:
    """Build the run parameter dict from defaults + YAML + CLI overrides."""

    import copy
    import yaml

    params: Dict[str, Any] = copy.deepcopy(_DEFAULT_PARAMS)

    yaml_path = args.params_file or os.path.join(
        args.input, "machine_learning_parameters.yaml"
    )
    if os.path.isfile(yaml_path):
        try:
            with open(yaml_path, "r") as f:
                yaml_params = yaml.safe_load(f) or {}
            params.update(yaml_params)
            log.info("Loaded YAML parameters from %s", yaml_path)
        except Exception as exc:
            log.warning("Could not parse YAML params (%s); using defaults.", exc)

    # CLI overrides win.
    if args.k_folds is not None:
        if args.k_folds < 2:
            raise ValueError("--k-folds must be >= 2")
        params["number_of_k_folds"] = args.k_folds
    if args.correlation_limit is not None:
        if not 0 <= args.correlation_limit <= 1:
            raise ValueError("--correlation-limit must be between 0 and 1")
        params["Correlation Limit"] = args.correlation_limit
    if args.threshold_metric is not None:
        params["Metric For Threshold Optimization"] = args.threshold_metric
    if args.bias_assessment is not None:
        params["BiasAssessment"] = args.bias_assessment
    if args.bias_feature is not None:
        params["Feature"] = args.bias_feature
    if args.grid_search is not None:
        params.setdefault("apply_grid_search", {})["enabled"] = args.grid_search
    if args.grid_search_type is not None:
        params.setdefault("apply_grid_search", {}).setdefault("type", {})
        params["apply_grid_search"]["type"]["Randomized"] = (
            args.grid_search_type == "randomized"
        )
        params["apply_grid_search"]["type"]["Exhaustive"] = (
            args.grid_search_type == "exhaustive"
        )
    if args.models is not None:
        wanted = {m.strip().lower() for m in args.models.split(",") if m.strip()}
        unknown = wanted - set(_MODEL_KEY_ALIASES)
        if unknown:
            raise ValueError(f"Unknown model(s): {sorted(unknown)}")
        canonical = {_MODEL_KEY_ALIASES[m] for m in wanted}
        params["Machine Learning Models"] = {
            name: (name in canonical)
            for name in _DEFAULT_PARAMS["Machine Learning Models"].keys()
        }

    return params


def _write_results_json(
    output_dir: str,
    *,
    status: str,
    started_at: str,
    finished_at: str,
    error: Optional[str],
    args: argparse.Namespace,
    params: Optional[Dict[str, Any]],
    materials_dir: str,
) -> None:
    """Write a machine-readable run index to <output>/results.json."""

    artefacts = []
    if os.path.isdir(materials_dir):
        for root, _, files in os.walk(materials_dir):
            for f in files:
                p = os.path.join(root, f)
                rel = os.path.relpath(p, output_dir).replace("\\", "/")
                artefacts.append(rel)
    artefacts.sort()

    payload = {
        "tool": "simplatab",
        "schema_version": 1,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "input_dir": os.path.abspath(args.input),
        "output_dir": os.path.abspath(args.output),
        "error": error,
        "params": params,
        "artefacts": artefacts,
    }
    out_path = os.path.join(output_dir, "results.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)


def _run_pipeline(
    input_dir: str,
    output_dir: str,
    materials_dir: str,
    params: Dict[str, Any],
    log: logging.Logger,
) -> None:
    """Execute the Simplatab pipeline. Mirrors app.py:run_pipeline."""

    import yaml as _yaml

    # Persist the effective params next to inputs (via a writable scratch
    # location) so that read_yaml() can pick them up.
    scratch_input = tempfile.mkdtemp(prefix="simplatab_input_", dir="/tmp")
    try:
        for fname in ("Train.csv", "Test.csv"):
            src = os.path.join(input_dir, fname)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"Required file missing in --input: {fname}")
            shutil.copy2(src, os.path.join(scratch_input, fname))

        with open(os.path.join(scratch_input, "machine_learning_parameters.yaml"), "w") as f:
            _yaml.safe_dump(params, f)

        # Configure the central output base for every Helpers.* module.
        from Helpers import io_paths
        io_paths.set_output_base(materials_dir)

        from Helpers.pipelines_main import train_k_fold, external_test, read_yaml
        from Helpers.data_checks import DataChecker
        from Helpers import DBDM

        read_yaml(scratch_input)

        if params.get("BiasAssessment") and params.get("Feature"):
            log.info("Running bias assessment on Train.csv ...")
            try:
                DBDM.bias_config(
                    file_path=os.path.join(scratch_input, "Train.csv"),
                    subgroup_analysis=0,
                    facet=params["Feature"],
                    outcome="Target",
                    subgroup_col="",
                    label_value=1,
                )
            except Exception as exc:
                log.error("Bias detection failed for Train.csv: %s", exc)
            log.info("Running bias assessment on Test.csv ...")
            try:
                DBDM.bias_config(
                    file_path=os.path.join(scratch_input, "Test.csv"),
                    subgroup_analysis=0,
                    facet=params["Feature"],
                    outcome="Target",
                    subgroup_col="",
                    label_value=1,
                )
            except Exception as exc:
                log.error("Bias detection failed for Test.csv: %s", exc)

        log.info("Loading data from %s ...", scratch_input)
        data_checker = DataChecker(scratch_input)
        train, test = data_checker.process_data()
        log.info("Train shape=%s  Test shape=%s", train.shape, test.shape)

        X_train = train.drop("Target", axis=1)
        y_train = train["Target"]
        X_test = test.drop("Target", axis=1)
        y_test = test["Target"]

        log.info("K-fold cross-validation training ...")
        params_dict, scores_storage, thresholds, _ = train_k_fold(X_train, y_train)

        log.info("External test set evaluation ...")
        external_test(X_train, y_train, X_test, y_test, params_dict, thresholds)
        log.info("Pipeline completed successfully.")
    finally:
        shutil.rmtree(scratch_input, ignore_errors=True)


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)
    _install_signal_handlers()
    log = logging.getLogger("simplatab")

    started_at = datetime.now(timezone.utc).isoformat()

    if not os.path.isdir(args.input):
        log.error("Input directory not found: %s", args.input)
        return 2
    try:
        os.makedirs(args.output, exist_ok=True)
    except Exception as exc:
        log.error("Cannot create output directory %s: %s", args.output, exc)
        return 2
    if not os.access(args.output, os.W_OK):
        log.error("Output directory is not writable: %s", args.output)
        return 2

    materials_dir = os.path.join(os.path.abspath(args.output), "Materials")
    os.makedirs(materials_dir, exist_ok=True)

    # Make the materials base discoverable by every Helpers.* module BEFORE
    # we import them.
    os.environ["SIMPLATAB_OUTPUT_DIR"] = materials_dir

    params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status = "success"
    rc = 0
    try:
        params = _load_params(args, log)
        log.info("Effective params: %s", json.dumps(params, default=str))
        _run_pipeline(args.input, args.output, materials_dir, params, log)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        error = str(exc)
        status = "error"
        rc = 2
    except ValueError as exc:
        log.error("%s", exc)
        error = str(exc)
        status = "error"
        rc = 2
    except Exception as exc:
        log.error("Pipeline failed: %s", exc)
        log.debug("%s", traceback.format_exc())
        error = f"{type(exc).__name__}: {exc}"
        status = "error"
        rc = 1
    finally:
        finished_at = datetime.now(timezone.utc).isoformat()
        try:
            _write_results_json(
                args.output,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                error=error,
                args=args,
                params=params,
                materials_dir=materials_dir,
            )
        except Exception as exc:  # pragma: no cover - defensive
            log.error("Failed to write results.json: %s", exc)

    return rc


if __name__ == "__main__":
    sys.exit(main())
