# Simplatab — EUCAIM Processing Tool

Automated ML pipeline for tabular biomedical data: bias assessment,
k-fold cross-validation, threshold optimisation, and SHAP explainability.

| | |
|---|---|
| Image | `harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0` |
| License | [EUPL-1.2](LICENSE.md) |
| Maintainer | Dimitrios Zaridis \<dimzaridis@gmail.com\> |

---

## Input volume

Mount a directory as read-only `/input` containing these three files:

```
/input/
├── Train.csv                          ← training set
├── Test.csv                           ← hold-out test set
└── machine_learning_parameters.yaml   ← pipeline configuration
```

### Train.csv / Test.csv

| Rule | Detail |
|---|---|
| Format | Comma-separated, UTF-8 |
| `Target` column | Required in both files — exact name, case-sensitive |
| `Target` values | Integers: `0`/`1` for binary; `0`/`1`/`2`/… for multiclass |
| Feature columns | Must be the same set in both files |
| Missing values | Allowed in features (imputed); `Target` must be complete |

### machine_learning_parameters.yaml

This file replaces the interactive UI in headless mode. A fully-commented
template with explanations for every field is at
`examples/machine_learning_parameters.yaml`.

| Key | Type | Default | What it controls |
|---|---|---|---|
| `BiasAssessment` | bool | `false` | Run bias detection (DBDM) |
| `Feature` | string | `""` | Sensitive column for bias analysis |
| `number_of_k_folds` | int | `5` | Stratified CV folds (≥ 2) |
| `apply_grid_search.enabled` | bool | `false` | Hyper-parameter search on/off |
| `apply_grid_search.type.Randomized` | bool | `true` | Randomized search (faster) |
| `apply_grid_search.type.Exhaustive` | bool | `false` | Exhaustive grid (slow) |
| `Correlation Limit` | float | `0.9` | Drop features above this correlation |
| `Metric For Threshold Optimization` | string | `"F-score"` | Binary threshold metric |
| `Machine Learning Models.*` | bool | varies | `true` to train that model |

---

## How to run

### Headless / batch mode (EUCAIM)

**bash / Linux / macOS:**
```bash
docker run --rm \
  -v "/path/to/your/input:/input:ro" \
  -v "/path/to/your/output:/output" \
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0 \
  --input /input --output /output
```

**PowerShell (Windows):**
```powershell
docker run --rm `
  -v "C:\path\to\your\input:/input:ro" `
  -v "C:\path\to\your\output:/output" `
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0 `
  --input /input --output /output
```

Results are written to `/output/Materials/` and a run index to `/output/results.json`.

### Interactive UI (local use)

```bash
docker run --rm -p 5000:5000 \
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0
# open http://localhost:5000/automl/
```

### Introspection

```bash
docker run --rm harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0 --help
```

---

## Further documentation

| Document | Contents |
|---|---|
| [`docs/REFERENCE.md`](docs/REFERENCE.md) | Full CLI flags, output schema, resource requirements, local dev, Harbor publishing |
| [`docs/BUILD_AND_TEST.md`](docs/BUILD_AND_TEST.md) | Step-by-step build, compliance checks, and publish workflow |
| [`examples/machine_learning_parameters.yaml`](examples/machine_learning_parameters.yaml) | Fully-commented YAML template |
| [`examples/README.md`](examples/README.md) | Example datasets and expected output layout |
| [`docs/Simplatab_EUCAIM_Tool_Documentation.docx`](docs/Simplatab_EUCAIM_Tool_Documentation.docx) | EUCAIM tool documentation (4-section format) |
| [`metadata/descriptor.yml`](metadata/descriptor.yml) | CWL CommandLineTool descriptor |
