# Simplatab — Build, Test & Publish Guide

Step-by-step instructions for building the Docker image on your local
machine, verifying EUCAIM compliance, and publishing to Harbor.

---

## Prerequisites

Docker Desktop must be running. Verify:

```powershell
docker info
```

---

## Step 1 — Build the image

```powershell
cd "D:\EUCAIM Tools\simplatab-machine-learning-automator"

docker build -t simplatab:1.1.0 .
```

The multi-stage build takes **5–15 minutes** the first time (downloads
`python:3.9-slim` and installs all wheels). Subsequent builds are fast
due to layer caching.

---

## Step 2 — Verify the image

```powershell
# Confirm it exists and check the compressed size
docker images simplatab

# Verify all OCI labels are present
docker inspect simplatab:1.1.0 --format "{{json .Config.Labels}}" | python -m json.tool

# Confirm non-root execution (must show uid=2323)
docker run --rm simplatab:1.1.0 id
# Expected: uid=2323(eucaim) gid=2323(eucaim) groups=2323(eucaim)
```

---

## Step 3 — --help smoke test

```powershell
docker run --rm simplatab:1.1.0 --help
```

Must print the argument list and exit `0`.

---

## Step 4 — Headless batch run (binary example)

```powershell
New-Item -ItemType Directory -Force -Path "$PWD\_run_out_binary"

docker run --rm `
  -v "${PWD}/examples/binary:/input:ro" `
  -v "${PWD}/_run_out_binary:/output" `
  simplatab:1.1.0 `
  --input /input --output /output --log-level INFO

# Inspect the results index
Get-Content "$PWD\_run_out_binary\results.json" | python -m json.tool

# Check output artefacts were created
Get-ChildItem "$PWD\_run_out_binary\Materials" -Recurse -File | Select-Object FullName
```

**Expected:** `results.json` with `"status": "success"` and a `Materials/`
tree containing `.xlsx` metrics, `.png` plots, `.pkl` model files, and
SHAP figures.

---

## Step 5 — Headless batch run (multiclass example)

```powershell
New-Item -ItemType Directory -Force -Path "$PWD\_run_out_multi"

docker run --rm `
  -v "${PWD}/examples/multiclass:/input:ro" `
  -v "${PWD}/_run_out_multi:/output" `
  simplatab:1.1.0 `
  --input /input --output /output --log-level INFO

Get-Content "$PWD\_run_out_multi\results.json" | python -m json.tool
```

---

## Step 6 — Interactive UI smoke test

```powershell
# Start in foreground; press Ctrl+C to stop
docker run --rm -p 5000:5000 --name simplatab_ui simplatab:1.1.0
```

Open **http://localhost:5000/automl/** in your browser. Walk through the
UI to confirm it loads and the upload flow works. Stop when done:

```powershell
docker stop simplatab_ui
```

---

## Step 7 — HEALTHCHECK verification

```powershell
# Start a background container (UI mode is fine here)
docker run -d --name simplatab_hc simplatab:1.1.0

# Wait for the first healthcheck to fire (~15 s)
Start-Sleep -Seconds 20
docker inspect simplatab_hc --format "{{.State.Health.Status}}"
# Expected: healthy

docker stop simplatab_hc; docker rm simplatab_hc
```

---

## Step 8 — Read-only input enforcement

```powershell
docker run --rm `
  -v "${PWD}/examples/binary:/input:ro" `
  -v "${PWD}/_run_out_binary:/output" `
  --entrypoint /bin/sh `
  simplatab:1.1.0 `
  -c "touch /input/should_fail.txt"
# Expected: touch: /input/should_fail.txt: Read-only file system
```

---

## Step 9 — Host-side smoke tests (no Docker required)

```powershell
# Install test dependencies if not already present
pip install pytest pandas scikit-learn

pytest tests/test_smoke.py -v
```

The three lightweight tests (help, missing args, missing input dir) run
without Docker or the full ML stack. The full end-to-end pipeline test
is opt-in:

```powershell
$env:RUN_FULL_PIPELINE = "1"
pytest tests/test_smoke.py -v
```

---

## EUCAIM compliance checklist

Run through these checks before publishing. All must pass.

| # | Check | Command / verification | Expected result |
|---|---|---|---|
| 1 | Non-root UID | `docker run --rm simplatab:1.1.0 id` | `uid=2323(eucaim)` |
| 2 | OCI labels | `docker inspect ... --format {{json .Config.Labels}}` | All 8 labels present |
| 3 | `--help` exits 0 | Step 3 | Exit code 0 |
| 4 | Binary batch run | Step 4 | `"status":"success"` in `results.json` |
| 5 | Multiclass batch run | Step 5 | `"status":"success"` in `results.json` |
| 6 | UI mode works | Step 6 | Flask UI loads at `/automl/` |
| 7 | HEALTHCHECK | Step 7 | `healthy` |
| 8 | Read-only input | Step 8 | Permission denied error |
| 9 | Smoke tests pass | Step 9 | All tests green |

---

## Publishing to Harbor (manual)

Once all checks above pass, publish the image.

**PowerShell:**
```powershell
$REGISTRY = "harbor.eucaim.cancerimage.eu"
$PROJECT  = "processing-tools"
$IMAGE    = "simplatab"
$VERSION  = "1.1.0"

docker login $REGISTRY

docker tag simplatab:1.1.0 "${REGISTRY}/${PROJECT}/${IMAGE}:${VERSION}"
docker tag simplatab:1.1.0 "${REGISTRY}/${PROJECT}/${IMAGE}:v${VERSION}"
docker tag simplatab:1.1.0 "${REGISTRY}/${PROJECT}/${IMAGE}:latest"

docker push "${REGISTRY}/${PROJECT}/${IMAGE}:${VERSION}"
docker push "${REGISTRY}/${PROJECT}/${IMAGE}:v${VERSION}"
docker push "${REGISTRY}/${PROJECT}/${IMAGE}:latest"
```

**bash:**
```bash
REGISTRY=harbor.eucaim.cancerimage.eu
PROJECT=processing-tools
IMAGE=simplatab
VERSION=1.1.0

docker login "$REGISTRY"

docker tag simplatab:1.1.0 "$REGISTRY/$PROJECT/$IMAGE:$VERSION"
docker tag simplatab:1.1.0 "$REGISTRY/$PROJECT/$IMAGE:v$VERSION"
docker tag simplatab:1.1.0 "$REGISTRY/$PROJECT/$IMAGE:latest"

docker push "$REGISTRY/$PROJECT/$IMAGE:$VERSION"
docker push "$REGISTRY/$PROJECT/$IMAGE:v$VERSION"
docker push "$REGISTRY/$PROJECT/$IMAGE:latest"
```

> Always tag with an explicit version **and** `latest`. Never re-push
> `latest` without bumping the version tag first.
