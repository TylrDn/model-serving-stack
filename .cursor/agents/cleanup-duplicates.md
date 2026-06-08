---
name: cleanup-duplicates
description: Invoke when removing duplicate files or directories from the repo. Use when the user asks to clean up triton/model_repo/, remove the root grafana_dashboard.json, consolidate duplicate paths, or audit for stale files.
model: inherit
readonly: false
is_background: false
---

# Clean Up Duplicate Files and Directories

## Objective

Remove two known duplicate file trees that create confusion and maintenance overhead:
1. `triton/model_repo/` — duplicate of `triton/model_repository/` (canonical)
2. `monitoring/grafana_dashboard.json` (root) — duplicate of `monitoring/grafana/gpu_serving_dashboard.json` (canonical)

This is a pure cleanup task — no new functionality. Follow the safe removal workflow: audit references → verify canonical has latest content → update references → remove duplicates → test.

---

## Safe Removal Workflow

### Step 1: Audit References to Duplicate Paths

Run these searches before touching any files:

```bash
# Find all references to the duplicate triton path
grep -r "model_repo/" \
  --include="*.py" \
  --include="*.yaml" \
  --include="*.yml" \
  --include="*.json" \
  --include="*.sh" \
  --include="*.md" \
  -l .

# Find all references to root grafana_dashboard.json
grep -r "grafana_dashboard.json" \
  --include="*.py" \
  --include="*.yaml" \
  --include="*.yml" \
  --include="*.json" \
  --include="*.sh" \
  --include="*.md" \
  -l .
```

Document every file that references the duplicate paths.

---

### Step 2: Verify Canonical Content is Superset

```bash
# Compare directory structures
diff -rq triton/model_repository/ triton/model_repo/ 2>/dev/null || echo "Differences found"

# Compare Grafana dashboards
diff monitoring/grafana/gpu_serving_dashboard.json monitoring/grafana_dashboard.json 2>/dev/null || echo "Differences found"
```

**If the duplicate has newer content than the canonical:**
1. Merge any unique content from the duplicate INTO the canonical path
2. Document what was merged in a comment or changelog entry
3. Only then remove the duplicate

**If canonical and duplicate are identical:** proceed directly to removal.

---

### Step 3: Update All References

For each file found in Step 1, update references:

**`triton/model_repo/` → `triton/model_repository/`:**

Files to check and update:
- `triton/client.py` — may reference `MODEL_REPO` path
- `kubernetes/triton-deployment.yaml` — may mount `model_repo` as volume
- `deploy/docker-compose.yml` — volume mounts
- `docker-compose.yml` (root) — volume mounts
- `docs/architecture.md` — documentation references
- Any shell scripts in `triton/`
- `.github/workflows/ci.yml` — if it references the path
- `configs/serving.yaml` — if it sets a model repo path

Update pattern: `s|triton/model_repo/|triton/model_repository/|g`

**`monitoring/grafana_dashboard.json` → `monitoring/grafana/gpu_serving_dashboard.json`:**

Files to check and update:
- `monitoring/prometheus/prometheus.yml` — scrape configs
- `deploy/docker-compose.yml` — Grafana provisioning volume mounts
- `docker-compose.yml` (root) — Grafana service config
- `kubernetes/` manifests — ConfigMap references
- `docs/architecture.md`
- `README.md`

---

### Step 4: Remove Duplicate Files

Only after ALL references are updated:

```bash
# Remove duplicate Triton model_repo directory
rm -rf triton/model_repo/

# Remove duplicate root Grafana dashboard
rm monitoring/grafana_dashboard.json
```

---

### Step 5: Verify No Broken References

```bash
# Confirm no remaining references to removed paths
grep -r "model_repo/" \
  --include="*.py" --include="*.yaml" --include="*.yml" \
  --include="*.json" --include="*.sh" --include="*.md" . \
  | grep -v "model_repository" \
  | grep -v ".git"

grep -r '"grafana_dashboard.json"' \
  --include="*.py" --include="*.yaml" --include="*.yml" . \
  | grep -v "gpu_serving_dashboard"
```

Both commands should return empty output.

---

### Step 6: Update Documentation

**Files to update:**

`docs/architecture.md` — update any path references:
```markdown
<!-- Old: triton/model_repo/ -->
<!-- New: triton/model_repository/ -->
Triton model repository: `triton/model_repository/`
```

`README.md` (if it exists) — update quick-start instructions referring to model_repo.

Add a `CHANGELOG.md` entry or note in the relevant PR description:
```
### Cleanup
- Removed duplicate `triton/model_repo/` directory (canonical: `triton/model_repository/`)
- Removed duplicate `monitoring/grafana_dashboard.json` (canonical: `monitoring/grafana/gpu_serving_dashboard.json`)
```

---

## Files to Modify (After Reference Audit)

### Modify: `triton/client.py`

Search for `model_repo` and update to `model_repository`:
```python
# Before:
MODEL_REPO_PATH = "triton/model_repo"
# After:
MODEL_REPO_PATH = "triton/model_repository"
```

### Modify: `docker-compose.yml` (root) and `deploy/docker-compose.yml`

Update Triton server volume mounts:
```yaml
# Before:
volumes:
  - ./triton/model_repo:/models
# After:
volumes:
  - ./triton/model_repository:/models
```

Update Grafana provisioning:
```yaml
# Before:
volumes:
  - ./monitoring/grafana_dashboard.json:/etc/grafana/provisioning/dashboards/dashboard.json
# After:
volumes:
  - ./monitoring/grafana/gpu_serving_dashboard.json:/etc/grafana/provisioning/dashboards/gpu_serving_dashboard.json
```

### Modify: `kubernetes/triton-deployment.yaml`

Update ConfigMap or hostPath volume for model repository:
```yaml
# Before:
hostPath:
  path: /mnt/models/model_repo
# After:
hostPath:
  path: /mnt/models/model_repository
```

---

## Tests to Run After Cleanup

```bash
# 1. All unit tests still pass
pytest tests/ -m "not gpu" -v

# 2. No references to duplicate paths remain
! grep -r "triton/model_repo[^i]" --include="*.py" --include="*.yaml" .
! grep -r '"grafana_dashboard.json"' --include="*.yaml" --include="*.yml" . | grep -v "gpu_serving"

# 3. Docker compose validates
docker-compose config --quiet

# 4. Kubernetes manifests validate
kubectl apply --dry-run=client -f kubernetes/ 2>&1 | grep -v "configured"
```

---

## Acceptance Criteria

- [ ] `triton/model_repo/` directory does not exist
- [ ] `monitoring/grafana_dashboard.json` file does not exist at repo root
- [ ] `grep -r "model_repo/" . | grep -v "model_repository" | grep -v ".git"` returns empty
- [ ] `docker-compose config` exits 0 after cleanup
- [ ] `pytest tests/ -m "not gpu"` passes after cleanup
- [ ] `triton/client.py` references `triton/model_repository` (not `model_repo`)
- [ ] Grafana dashboard JSON is provisioned from `monitoring/grafana/gpu_serving_dashboard.json`
- [ ] `docs/architecture.md` updated to reflect canonical paths
- [ ] No new functionality added — this is purely cleanup
