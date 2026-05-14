# Simplatab — Example Datasets

This folder contains two ready-to-run sample datasets for EUCAIM headless
batch mode. Each sub-folder includes `Train.csv`, `Test.csv` **and** a
pre-filled `machine_learning_parameters.yaml`.

| Folder | Dataset | Task | Rows (Train / Test) | Features | Notes |
|---|---|---|---|---|---|
| `binary/`     | Breast Cancer (Wisconsin) | Binary classification    | 455 / 114 | 30 numeric  | `Target` is `0` (malignant) / `1` (benign). |
| `multiclass/` | Iris                      | 3-class classification   | 120 / 30  |  4 numeric  | `Target` ∈ {0, 1, 2}. |

## Input directory contract

Every input directory passed to the container must contain these three files:

```
<your_input_dir>/
├── Train.csv                          ← training set with "Target" column
├── Test.csv                           ← hold-out test set with "Target" column
└── machine_learning_parameters.yaml   ← pipeline configuration
```

The **fully-commented template** is at `examples/machine_learning_parameters.yaml`.
Copy it, fill it in, and place it alongside your CSVs.

### CSV requirements

* Comma-separated, UTF-8.
* A column named exactly `Target` (case-sensitive) with integer labels.
* Same feature columns in both files.
* Missing values in feature columns are handled internally; `Target` must be complete.

---

## Quick start — binary example

**bash / Linux / macOS:**
```bash
docker run --rm \
  -v "$(pwd)/examples/binary:/input:ro" \
  -v "$(pwd)/out_binary:/output" \
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0 \
  --input /input --output /output
```

**PowerShell (Windows):**
```powershell
docker run --rm `
  -v "${PWD}/examples/binary:/input:ro" `
  -v "${PWD}/out_binary:/output" `
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0 `
  --input /input --output /output
```

> The YAML in `examples/binary/` already configures 5-fold CV, no grid
> search, and three models (Logistic Regression, Random Forest, XGBoost).
> Override individual settings with CLI flags — they take priority over
> the YAML. Example: add `--k-folds 3 --models logistic_regression` to
> the command above.

---

## Quick start — multiclass example

```bash
docker run --rm \
  -v "$(pwd)/examples/multiclass:/input:ro" \
  -v "$(pwd)/out_multi:/output" \
  harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0 \
  --input /input --output /output
```

---

## Expected output layout

```
<output_dir>/
├── results.json                       ← machine-readable run index
└── Materials/
    ├── <k>_fold_results.xlsx          ← internal CV metrics (mean ± std)
    ├── test_results.xlsx              ← hold-out test metrics
    ├── ConfusionMatrices/
    │   └── <model>_<type>_confusion_matrix.png
    ├── ROC_Curves/
    │   ├── ROC_CURVES.png
    │   └── PR_CURVES.png
    ├── Shap_Features/
    │   └── <model>/
    │       ├── summary_plot_<model>.png
    │       ├── beeswarm_plot_<model>.png
    │       ├── bar_plot_<model>.png
    │       └── heatmap_plot_<model>.png
    └── Models/
        └── <model>_pipeline.pkl
```

## Regenerating the CSVs

```python
from sklearn.datasets import load_breast_cancer, load_iris
from sklearn.model_selection import train_test_split
import pandas as pd

# Binary
df = load_breast_cancer(as_frame=True).frame
df['Target'] = df['target']; df = df.drop(columns=['target'])
train, test = train_test_split(df, test_size=0.2, random_state=42, stratify=df['Target'])
train.to_csv('examples/binary/Train.csv', index=False)
test.to_csv('examples/binary/Test.csv', index=False)

# Multiclass
df = load_iris(as_frame=True).frame
df['Target'] = df['target']; df = df.drop(columns=['target'])
train, test = train_test_split(df, test_size=0.2, random_state=42, stratify=df['Target'])
train.to_csv('examples/multiclass/Train.csv', index=False)
test.to_csv('examples/multiclass/Test.csv', index=False)
```
