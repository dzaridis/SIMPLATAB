# Simplatab — Full Reference

This document covers everything beyond the quick-start in `README.md`:
run modes, input/output contracts, CLI flags, resource requirements,
local development, EUCAIM compliance checklist, and Harbor publishing.

---

## Two run modes

The same image supports two complementary modes:

| Mode | Trigger | Purpose |
|---|---|---|
| **Headless / EUCAIM batch** | `--input` and/or `--output` present (or `SIMPLATAB_MODE=batch`) | Non-interactive run; reads `/input` (read-only), writes `/output`. |
| **Interactive UI**          | no flags (default) | Local development. Flask UI on `:5000`. |

---

## Inputs (headless mode)

```
/input/
├── Train.csv                              ← required
├── Test.csv                               ← required
└── machine_learning_parameters.yaml       ← required in headless mode
```

The YAML file replaces every choice the user would otherwise make in the
interactive UI. A fully-commented template is in `examples/machine_learning_parameters.yaml`.

CLI flags override YAML values when both are present.

### CSV requirements

| Rule | Detail |
|---|---|
| Format | Comma-separated, UTF-8 |
| `Target` column | Mandatory in both files; exact name, case-sensitive |
| `Target` values | Integers: `0`/`1` for binary; `0`/`1`/`2`/… for multiclass |
| Feature columns | Same set in `Train.csv` and `Test.csv` |
| Missing values | Allowed in features (imputed); NOT in `Target` |
| Index column | Not required; auto-generated if absent |

### machine_learning_parameters.yaml — quick reference

| Key | Type | Default | Notes |
|---|---|---|---|
| `BiasAssessment` | bool | `false` | Run DBDM bias detection |
| `Feature` | string | `""` | Sensitive column for bias analysis |
| `number_of_k_folds` | int | `5` | Stratified CV folds (≥ 2) |
| `apply_grid_search.enabled` | bool | `false` | Enable hyper-parameter search |
| `apply_grid_search.type.Randomized` | bool | `true` | Randomized (faster) |
| `apply_grid_search.type.Exhaustive` | bool | `false` | Exhaustive grid search (slow) |
| `Correlation Limit` | float | `0.9` | Drop features above this pairwise correlation |
| `Metric For Threshold Optimization` | string | `"F-score"` | Binary threshold metric |
| `Machine Learning Models.*` | bool | varies | `true` to enable that model |

For full field-by-field explanations see the annotated template at
`examples/machine_learning_parameters.yaml`.

---

## Outputs

```
/output/
├── results.json                           ← machine-readable run index
└── Materials/
    ├── test_results.xlsx                  ← per-model external metrics
    ├── <k>_fold_results.xlsx              ← per-model k-fold CV metrics
    ├── error_log.log
    ├── ConfusionMatrices/                 ← one PNG per model & dataset
    ├── ROC_Curves/                        ← ROC + PR curves (binary)
    ├── BiasAssessment/                    ← only when --bias-assessment
    ├── Shap_Features/<model>/             ← bar / summary / beeswarm / heatmap
    └── Models/<model>_pipeline.pkl        ← pickled sklearn Pipeline
```

`results.json` schema (v1):

```json
{
  "tool": "simplatab",
  "schema_version": 1,
  "status": "success | error | terminated",
  "started_at": "<ISO-8601 UTC>",
  "finished_at": "<ISO-8601 UTC>",
  "input_dir": "/input",
  "output_dir": "/output",
  "error": null,
  "params": { "...": "effective parameter dict" },
  "artefacts": ["Materials/test_results.xlsx", "..."]
}
```

---

## CLI flags

| Flag | Default | Purpose |
|---|---|---|
| `--input`, `-i` | _required_ | Read-only input directory |
| `--output`, `-o` | _required_ | Writable output directory |
| `--params-file` | `<input>/machine_learning_parameters.yaml` | Alternative YAML path |
| `--log-level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--k-folds` | 5 (or YAML) | Stratified CV folds (≥ 2) |
| `--correlation-limit` | 0.9 (or YAML) | Pairwise feature correlation threshold |
| `--threshold-metric` | `F-score` | Binary threshold optimisation metric |
| `--bias-assessment` / `--no-bias-assessment` | off | Run DBDM on Train/Test |
| `--bias-feature` | _empty_ | Sensitive feature column for bias |
| `--grid-search` / `--no-grid-search` | off | Enable hyper-parameter search |
| `--grid-search-type` | `randomized` | `randomized` or `exhaustive` |
| `--models` | all enabled in YAML | Comma-list: `logistic_regression`, `svm`, `random_forest`, `sgd`, `mlp`, `decision_trees`, `xgboost` |

Exit codes: `0` success · `1` runtime error · `2` invalid args / missing files · `128 + signum` on SIGTERM/SIGINT.

---

## Resource requirements

| Resource | Minimum | Recommended |
|---|---|---|
| CPU cores | 2 | 4–8 |
| RAM | 4 GB | 8–16 GB |
| Disk (output) | 1 GB | 2 GB |
| Network | none | none |
| GPU | not used | not used |

---

## Interactive UI

```bash
docker run --rm -p 7111:5000 \
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0
# open http://localhost:7111/automl/
```

The UI generates `machine_learning_parameters.yaml` from your selections —
useful for creating a valid config file to reuse in batch mode.

---

## Local development without Docker

```bash
git clone https://github.com/dzaridis/simplatab-machine-learning-automator.git
cd simplatab-machine-learning-automator
python -m venv .venv && source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\Activate.ps1                        # Windows PowerShell
pip install -r requirements.txt

# Run UI:
python app.py

# Run headless:
python __main__.py --input examples/binary --output out_binary
```

Run the smoke tests:

```bash
pytest tests/test_smoke.py -v
# Full end-to-end pipeline (slow, opt-in):
RUN_FULL_PIPELINE=1 pytest tests/test_smoke.py -v
```

---

## Publishing the image to Harbor (manual)

CI does **not** push the image automatically. Tag bumps and GitHub Releases
are automated via `.github/workflows/release.yml` (source code only).

**PowerShell:**
```powershell
$REGISTRY = "harbor.eucaim.cancerimage.eu"
$PROJECT  = "processing-tools"
$IMAGE    = "simplatab"
$VERSION  = "1.1.0"

docker login $REGISTRY
docker build `
  -t "${REGISTRY}/${PROJECT}/${IMAGE}:${VERSION}" `
  -t "${REGISTRY}/${PROJECT}/${IMAGE}:v${VERSION}" `
  -t "${REGISTRY}/${PROJECT}/${IMAGE}:latest" .
docker push --all-tags "${REGISTRY}/${PROJECT}/${IMAGE}"
```

**bash:**
```bash
REGISTRY=harbor.eucaim.cancerimage.eu
PROJECT=processing-tools
IMAGE=simplatab
VERSION=1.1.0

docker login "$REGISTRY"
docker build \
  -t "$REGISTRY/$PROJECT/$IMAGE:$VERSION" \
  -t "$REGISTRY/$PROJECT/$IMAGE:v$VERSION" \
  -t "$REGISTRY/$PROJECT/$IMAGE:latest" .
docker push --all-tags "$REGISTRY/$PROJECT/$IMAGE"
```

Notes:
* Always tag with both an explicit version AND `latest`.
* Harbor has no rename-repository — pushing under a new name creates a new
  repo. Delete the old one from the Harbor UI if needed.

---

## EUCAIM packaging compliance checklist

- [x] Multi-stage Dockerfile (`python:3.9-slim` builder → runtime).
- [x] Non-root runtime user `eucaim` (UID 2323 / GID 2323).
- [x] Read-only `/input`, writable `/output`, scratch under `/tmp`.
- [x] CLI-configurable; no behaviour-changing env vars at runtime.
- [x] Structured stdout/stderr logging with `--log-level`.
- [x] `SIGTERM` / `SIGINT` graceful shutdown (exit `128 + signum`).
- [x] OCI image labels (`source`, `revision`, `version`, `licenses`, `vendor`, …).
- [x] `HEALTHCHECK` (importable stack + `/tmp` writable).
- [x] No outbound network access at runtime.
- [x] CWL descriptor at `metadata/descriptor.yml`.
- [x] `results.json` index written to `/output` on every run.

---

## Citing

If you use Simplatab in academic work, please cite:

> Zaridis D., et al. *Simplatab: a simplified, automated machine-learning
> pipeline for tabular biomedical data with bias assessment and
> SHAP-based explainability* — EUCAIM Tools.

---

## License

This project is licensed under the European Union Public Licence v. 1.2 (EUPL-1.2) — see [LICENSE.md](../LICENSE.md) for the full text.
Canonical: https://joinup.ec.europa.eu/collection/eupl/
