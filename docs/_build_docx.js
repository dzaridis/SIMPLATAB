// Build Simplatab_EUCAIM_Tool_Documentation.docx
// Mirrors the RACLAHE / ProstAI EUCAIM tool documentation structure:
//   I.   Purpose
//   II.  Conceptual validation (Name, Contributor, Area, Description, ...)
//   III. Technical specifications
//   IV.  Integration validation
//
// Run:  node _build_docx.js
// Output: ../docs/Simplatab_EUCAIM_Tool_Documentation.docx (relative to this file)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak,
} = require("docx");

const NAVY = "1F3864";
const BLUE = "2E74B5";
const GREY = "595959";

const cellBorder = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const cellBorders = {
  top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder,
};

// ---------------- helpers ----------------

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 300 },
    alignment: opts.align || AlignmentType.LEFT,
    children: [new TextRun({
      text,
      bold: !!opts.bold,
      italics: !!opts.italic,
      color: opts.color,
      size: opts.size,
    })],
  });
}

function h(text, level, color) {
  const sizeMap = { 1: 36, 2: 30, 3: 26, 4: 24 };
  const headingMap = {
    1: HeadingLevel.HEADING_1,
    2: HeadingLevel.HEADING_2,
    3: HeadingLevel.HEADING_3,
    4: HeadingLevel.HEADING_4,
  };
  return new Paragraph({
    heading: headingMap[level],
    spacing: { before: 240, after: 120 },
    children: [new TextRun({
      text, bold: true, color: color || (level === 1 ? NAVY : BLUE),
      size: sizeMap[level],
    })],
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text })],
  });
}

function numbered(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text })],
  });
}

function cell(text, opts = {}) {
  const widthDxa = opts.width || 4680;
  return new TableCell({
    borders: cellBorders,
    width: { size: widthDxa, type: WidthType.DXA },
    shading: opts.shade
      ? { fill: opts.shade, type: ShadingType.CLEAR }
      : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({
        text,
        bold: !!opts.bold,
        color: opts.color,
        size: 22,
      })],
    })],
  });
}

function twoColTable(rows) {
  // rows: [[label, value], ...]
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [3120, 6240],
    rows: rows.map(([label, value]) =>
      new TableRow({
        children: [
          cell(label, { bold: true, shade: "DEEAF6", width: 3120 }),
          cell(value, { width: 6240 }),
        ],
      })
    ),
  });
}

function threeColTable(headers, dataRows) {
  const widths = [2080, 3640, 3640];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) =>
          cell(h, { bold: true, shade: NAVY, color: "FFFFFF", width: widths[i] })
        ),
      }),
      ...dataRows.map((row) =>
        new TableRow({
          children: row.map((c, i) => cell(c, { width: widths[i] })),
        })
      ),
    ],
  });
}

// ---------------- content ----------------

const children = [
  // Title page
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 1200, after: 240 },
    children: [new TextRun({
      text: "EUCAIM Tool Documentation",
      bold: true, color: NAVY, size: 48,
    })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 600 },
    children: [new TextRun({
      text: "Simplatab — Simplified Machine Pipeline Automator for Tabular Data",
      bold: true, color: BLUE, size: 32,
    })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [new TextRun({
      text: "Processing-tool documentation",
      italics: true, color: GREY, size: 24,
    })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
    children: [new TextRun({ text: "Version 1.1.0", color: GREY, size: 22 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [new TextRun({
      text: "Maintainer: Dimitrios Zaridis (dimzaridis@gmail.com)",
      color: GREY, size: 22,
    })],
  }),
  new Paragraph({ children: [new PageBreak()] }),

  // ============================== I. Purpose ==============================
  h("I. Purpose", 1),
  p(
    "Simplatab is a fully automated machine-learning pipeline for tabular " +
    "biomedical data. It is packaged as an EUCAIM processing-tool so it can " +
    "be executed inside the EUCAIM federated analytics infrastructure on " +
    "data that never leaves the data-host node."
  ),
  p("The tool's purpose is to:"),
  bullet("Take a labelled training set (Train.csv) and a held-out test set (Test.csv)."),
  bullet("Automatically run data bias detection (DBDM) on both files."),
  bullet("Train and evaluate a configurable battery of classifiers under stratified k-fold cross-validation."),
  bullet("Optionally perform randomised or exhaustive hyper-parameter search."),
  bullet("Produce ROC / PR curves, confusion matrices, k-fold and external-test metrics, and SHAP explainability artefacts for every trained model."),
  bullet("Emit a machine-readable run index (results.json) so that EUCAIM workflow engines can chain Simplatab with downstream tools."),
  p(
    "Simplatab supports both binary and multiclass classification problems " +
    "and adapts the metric set, threshold-optimisation logic and SHAP plots " +
    "automatically based on the number of unique values in the Target column."
  ),

  new Paragraph({ children: [new PageBreak()] }),

  // ============== II. Conceptual validation ==============
  h("II. Conceptual validation", 1),

  h("Name", 2),
  twoColTable([
    ["Tool name", "Simplatab — Simplified Machine Pipeline Automator for Tabular Data"],
    ["Image", "harbor.eucaim.cancerimage.eu/processing-tools/simplatab:1.1.0"],
    ["Repository", "https://github.com/dzaridis/simplatab-machine-learning-automator"],
    ["Version", "1.1.0"],
    ["License", "MIT"],
  ]),

  h("Contributor", 2),
  twoColTable([
    ["Lead developer", "Dimitrios Zaridis"],
    ["Contact", "dimzaridis@gmail.com"],
    ["Affiliation", "EUCAIM tools working group"],
  ]),

  h("Area", 2),
  p(
    "Simplatab targets the analysis of tabular clinical, radiomic, omics " +
    "and other structured-feature data for cancer-imaging research within " +
    "EUCAIM. It is modality-agnostic with respect to the imaging upstream — " +
    "the inputs are CSV feature tables, regardless of whether the features " +
    "originate from radiomics, clinical records, laboratory measurements " +
    "or AI-extracted descriptors."
  ),

  h("Tool description", 2),
  p(
    "Simplatab orchestrates a complete supervised classification pipeline:"
  ),
  numbered("Data Bias Detection (DBDM): demographic disparity, class imbalance, Jensen-Shannon divergence and L2-norm metrics computed over a sensitive feature."),
  numbered("Data quality checks: target-column validation, automatic creation of an ID column when missing, NaN-row removal, and removal of categorical columns whose unique-value sets disagree between train and test."),
  numbered("Feature selection: correlation-based filtering with a configurable threshold."),
  numbered("Stratified k-fold cross-validation training of every enabled classifier."),
  numbered("Optional hyper-parameter grid search (randomised or exhaustive)."),
  numbered("Threshold optimisation against a chosen metric (binary problems only)."),
  numbered("External evaluation on Test.csv with full metric reporting."),
  numbered("ROC / PR curve generation (per-class for multiclass) and confusion-matrix plots."),
  numbered("SHAP explainability (bar, summary, beeswarm, heatmap) per model and — for multiclass — per class."),
  numbered("Serialization of every trained sklearn Pipeline object as a .pkl file."),

  h("Data", 2),
  twoColTable([
    ["Input data type", "Tabular CSV (Train.csv + Test.csv)"],
    ["Schema", "Identical columns in train/test; numeric Target column required"],
    ["Optional index", "ID or patient_id column (auto-detected)"],
    ["Categorical features", "Auto-encoded; mismatched-vocab columns dropped"],
    ["Missing values", "Rows with any NaN are dropped"],
    ["Output data type", "Excel + PNG plots + .pkl model files + results.json"],
  ]),

  h("Methodology / performance", 2),
  p(
    "Each enabled classifier is fitted within a sklearn Pipeline that " +
    "includes the feature selector, the standard scaler and the model " +
    "itself. Performance is reported as the mean ± standard deviation " +
    "across the k folds for the cross-validation step, and as a single " +
    "value computed on Test.csv for the external-test step. The reported " +
    "metrics are: Sensitivity, Specificity, AUC, F-score, Accuracy and " +
    "Balanced Accuracy. For multiclass problems all metrics are computed " +
    "with the macro average and the AUC uses the one-vs-rest strategy."
  ),

  h("Use", 2),
  p(
    "Simplatab is intended for non-clinical, research-grade feasibility " +
    "studies. The tool is not a medical device and its outputs must not " +
    "be used to take direct clinical decisions about individual patients."
  ),

  h("Input / output formats", 2),
  threeColTable(
    ["Direction", "Path inside container", "Content"],
    [
      ["Input",  "/input/Train.csv",  "Training set (CSV, numeric Target)"],
      ["Input",  "/input/Test.csv",   "External test set (CSV, numeric Target)"],
      ["Input",  "/input/machine_learning_parameters.yaml", "Optional override file"],
      ["Output", "/output/results.json", "Machine-readable run index"],
      ["Output", "/output/Materials/test_results.xlsx", "External-test metrics"],
      ["Output", "/output/Materials/<k>_fold_results.xlsx", "K-fold CV metrics"],
      ["Output", "/output/Materials/ConfusionMatrices/", "PNG confusion matrices"],
      ["Output", "/output/Materials/ROC_Curves/", "PNG ROC + PR curves"],
      ["Output", "/output/Materials/Shap_Features/<model>/", "SHAP plots per model"],
      ["Output", "/output/Materials/Models/<model>_pipeline.pkl", "Pickled Pipeline"],
      ["Output", "/output/Materials/BiasAssessment/", "DBDM reports (when enabled)"],
    ],
  ),

  h("Quantitative results", 2),
  p(
    "All quantitative results are emitted as standard XLSX files written " +
    "under /output/Materials/. Per-fold scores are aggregated in " +
    "<k>_fold_results.xlsx (mean ± std for every metric and every model). " +
    "External-test results are written to test_results.xlsx with one row " +
    "per model. Threshold values used per fold are persisted internally " +
    "and re-used (averaged for binary tasks) on the external test set."
  ),

  h("Qualitative results", 2),
  p(
    "Qualitative artefacts include: per-model confusion-matrix heatmaps " +
    "(both for the cross-validation aggregate and for the external test " +
    "set), ROC and PR curves, and SHAP plots (bar, summary, beeswarm and " +
    "heatmap variants). For multiclass problems, SHAP plots are also " +
    "produced per class so that the user can inspect feature importance " +
    "for each label individually."
  ),

  h("Additional information", 2),
  p(
    "When the --bias-assessment flag is enabled, Simplatab also produces a " +
    "BiasAssessment/ sub-folder containing per-file metric tables and " +
    "PNGs that illustrate the demographic disparity, class imbalance and " +
    "Jensen-Shannon divergence of the chosen sensitive feature. The bias " +
    "assessment is run once on Train.csv and once on Test.csv."
  ),

  new Paragraph({ children: [new PageBreak()] }),

  // ============== III. Technical specifications ==============
  h("III. Technical specifications", 1),

  h("Data", 2),
  p(
    "Simplatab consumes only structured tabular data and never accesses " +
    "raw imaging files, DICOMs, or PHI fields. The CSVs are expected to " +
    "be the output of an upstream feature-extraction step (for instance, " +
    "PyRadiomics over segmented imaging volumes, or curated EHR pulls)."
  ),

  h("Methods", 2),
  p("The technical stack is:"),
  bullet("Language: Python 3.9."),
  bullet("Numerics: numpy 1.23.5, scipy 1.10.1, pandas 2.0.3."),
  bullet("Models: scikit-learn 1.3.1, xgboost 1.7.6, lightgbm 4.1.0."),
  bullet("Explainability: shap 0.43.0."),
  bullet("Feature selection: featurewiz 0.3.2 + correlation filtering."),
  bullet("UI (development only): Flask 3.0.3 + Werkzeug 3.0.3."),
  bullet("Bias detection: in-house DBDM module (Helpers/DBDM.py) using MiniSom 2.3.2 for clustering."),

  h("Specific technical info", 2),
  twoColTable([
    ["Base image",        "python:3.9-slim (multi-stage build)"],
    ["Runtime user",      "eucaim (UID 2323 / GID 2323), non-root"],
    ["GPU",               "Not used — CPU-only stack"],
    ["Network at runtime","None (no pip install / no model download)"],
    ["Healthcheck",       "Imports core stack, checks /tmp writable"],
    ["Signal handling",   "SIGTERM and SIGINT trapped, exit 128 + signum"],
    ["Logging",           "Structured stdout, --log-level controllable"],
    ["Resource (min)",    "2 CPU cores, 4 GB RAM, 1 GB output disk"],
    ["Resource (rec.)",   "4-8 CPU cores, 8-16 GB RAM, 2 GB output disk"],
  ]),

  h("Traceability", 2),
  p(
    "Every run produces a results.json index that captures: tool name, " +
    "schema version, run status (success/error), ISO-8601 UTC timestamps " +
    "for start and finish, the absolute input/output directories, the " +
    "effective parameter dictionary (CLI-overridden YAML), the optional " +
    "error message and the full list of generated artefacts. This index " +
    "is sufficient for downstream EUCAIM workflow engines to verify that " +
    "the run completed successfully and to enumerate the produced files."
  ),

  h("Unitary tests", 2),
  p("Smoke tests under tests/test_smoke.py verify:"),
  bullet("python __main__.py --help returns 0 and prints usage."),
  bullet("Missing required arguments yield exit code 2."),
  bullet("Missing input directory yields exit code 2."),
  bullet("io_paths.set_output_base() correctly redirects every write target."),
  bullet("DataChecker can load and validate Iris-style CSVs."),
  bullet("(Opt-in) full end-to-end pipeline on the bundled multiclass example, gated by RUN_FULL_PIPELINE=1."),

  h("Access restriction", 2),
  p(
    "The image is intended to be publicly accessible in the EUCAIM images " +
    "repository (see the authorization OCI label on the Dockerfile). The " +
    "tool itself does not enforce any access control at runtime — it is " +
    "the responsibility of the EUCAIM federated infrastructure to gate " +
    "execution and to decide which datasets can be exposed to the tool."
  ),

  h("Additional info", 2),
  twoColTable([
    ["Image labels (OCI)",   "title, description, source, revision, version, licenses, vendor, authors"],
    ["Stateless",            "Yes — no persistent state between runs"],
    ["Read-only input mount","Yes — /input mounted as :ro"],
    ["Writable output mount","Yes — /output is the only writable destination"],
    ["Scratch space",        "Always under /tmp"],
    ["CWL descriptor",       "metadata/descriptor.yml (CWL CommandLineTool v1.2)"],
  ]),

  new Paragraph({ children: [new PageBreak()] }),

  // ============== IV. Integration validation ==============
  h("IV. Integration validation", 1),

  h("Communication channel", 2),
  p(
    "Simplatab does not maintain any persistent communication channel. " +
    "It is invoked as a one-shot, batch container by an external workflow " +
    "engine (CWL runner, EUCAIM federated runtime). The entrypoint reads " +
    "/input, writes /output and exits. Logs are streamed to stdout/stderr " +
    "during execution and can be captured by the orchestrator."
  ),
  p(
    "When the image is started without batch flags, it instead launches a " +
    "Flask UI on port 5000. This mode is intended for local development " +
    "only and must NOT be exposed inside the EUCAIM federated execution " +
    "context."
  ),

  h("Most common errors", 2),
  threeColTable(
    ["Symptom", "Cause", "Resolution"],
    [
      ["Exit 2 / 'Required file missing in --input: Train.csv'", "Train.csv or Test.csv missing or misnamed", "Verify the input directory contains exactly Train.csv and Test.csv (case-sensitive)."],
      ["ValueError 'target column ... should contain numeric values'", "Target column is non-numeric (e.g., Yes/No)", "Re-encode the Target column as integer labels prior to upload."],
      ["Empty dataframe after process_data", "All rows contained a NaN value, or the categorical columns disagreed across train/test", "Impute or drop NaNs upstream; align categorical vocabularies."],
      ["Output directory is not writable", "Mount option missed or wrong UID", "Mount the output volume with write permissions for UID 2323 or use chmod 0777 on the host folder."],
      ["Pipeline finishes but results.json reports status='error'", "An unexpected exception was raised during training", "Inspect the 'error' field of results.json and the stdout log for the traceback."],
    ],
  ),

  h("FAQs", 2),
  p("Q. Can I run Simplatab without GPU?"),
  bullet("Yes. The default stack is CPU-only and does not depend on CUDA."),
  p("Q. Does the tool need internet access at runtime?"),
  bullet("No. All dependencies are installed at image-build time."),
  p("Q. Can I disable a model without editing YAML?"),
  bullet("Yes — use --models with the comma-separated list of models you want to keep (e.g., --models logistic_regression,xgboost)."),
  p("Q. How do I switch between binary and multiclass mode?"),
  bullet("There is nothing to switch — the number of unique values in the Target column is detected automatically."),
  p("Q. Where are the trained models stored?"),
  bullet("Inside /output/Materials/Models/<model>_pipeline.pkl as pickled sklearn Pipeline objects."),

  h("User Manual", 2),
  p("Refer to the README.md shipped at the root of the repository for:"),
  bullet("the complete CLI flag table,"),
  bullet("two ready-to-run examples (binary, multiclass),"),
  bullet("the Harbor manual-publish commands,"),
  bullet("the local-development workflow without Docker."),

  h("Integration tests", 2),
  p("Recommended integration test sequence (executed by the maintainer before each Harbor publish):"),
  numbered("docker build -t simplatab:<version> ."),
  numbered("docker run --rm simplatab:<version> --help            (verifies CLI plumbing)"),
  numbered("docker run --rm -v $PWD/examples/binary:/input:ro -v $PWD/out_binary:/output simplatab:<version> --input /input --output /output --k-folds 3 --no-grid-search --models logistic_regression,random_forest"),
  numbered("docker run --rm -v $PWD/examples/multiclass:/input:ro -v $PWD/out_multi:/output simplatab:<version> --input /input --output /output --k-folds 3 --no-grid-search --models logistic_regression,random_forest"),
  numbered("docker run --rm -p 5000:5000 simplatab:<version>      (verifies UI mode boots)"),
  numbered("cwltool --validate metadata/descriptor.yml             (verifies CWL descriptor)"),
  numbered("pytest tests/test_smoke.py -v                          (verifies code-level smoke)"),
];

// ---------------- assemble ----------------

const doc = new Document({
  creator: "Simplatab maintainers",
  title: "Simplatab — EUCAIM Tool Documentation",
  description: "EUCAIM processing-tool documentation for Simplatab",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 36, bold: true, color: NAVY },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 30, bold: true, color: BLUE },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 26, bold: true, color: BLUE },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }] },
      { reference: "numbers", levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 }, // US Letter
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children,
  }],
});

const outPath = path.join(__dirname, "Simplatab_EUCAIM_Tool_Documentation.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log("WROTE:", outPath, "(" + buf.length + " bytes)");
});
