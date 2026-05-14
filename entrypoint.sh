#!/bin/sh
# Simplatab — dual-mode container entrypoint.
#
# Default behaviour: launch the Flask UI on :5000 (legacy / interactive use).
# When EUCAIM-style flags or env vars are present, switch to the headless
# batch entrypoint (`python /app/__main__.py`).
#
# Trigger conditions for batch mode:
#   * any of --input/-i/--output/-o/--help/-h appear in the argv, OR
#   * SIMPLATAB_MODE=batch (or EUCAIM_MODE=batch) is exported.
set -e

mode="${SIMPLATAB_MODE:-${EUCAIM_MODE:-}}"

for arg in "$@"; do
    case "$arg" in
        --input|-i|--output|-o|--help|-h|--params-file|--log-level|--k-folds|--correlation-limit|--threshold-metric|--bias-assessment|--no-bias-assessment|--bias-feature|--grid-search|--no-grid-search|--grid-search-type|--models)
            mode="batch"
            ;;
    esac
done

if [ "$mode" = "batch" ]; then
    exec python /app/__main__.py "$@"
fi

# Default: Flask UI for local development.
exec python /app/app.py
