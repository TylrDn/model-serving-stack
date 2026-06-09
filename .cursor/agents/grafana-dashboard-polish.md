# Subagent: grafana-dashboard-polish

**Invoke:** `/grafana-dashboard-polish`
**Repo:** model-serving-stack
**Task Ref:** TASKS.md §2.3
**Estimated Time:** 20 min

---

## Objective

Polish `monitoring/grafana/gpu_serving_dashboard.json` to include at least 6 production-grade panels using correct DCGM metric names, and confirm the dashboard is auto-provisioned via the Docker Compose setup (not the duplicate root-level file).

---

## Context

- The canonical dashboard is at `monitoring/grafana/gpu_serving_dashboard.json`.
- The root-level `monitoring/grafana_dashboard.json` is a duplicate that should be removed by `/cleanup-duplicates` (run that first if it still exists).
- Grafana provisioning config should mount `monitoring/grafana/` as a dashboard provisioner volume.
- NVIDIA DCGM exporter exposes GPU metrics under these correct metric names:
  - `DCGM_FI_DEV_GPU_UTIL` — GPU utilization %
  - `DCGM_FI_DEV_MEM_COPY_UTIL` — memory bandwidth utilization %
  - `DCGM_FI_DEV_FB_USED` — GPU frame buffer used (MB)
  - `DCGM_FI_DEV_FB_FREE` — GPU frame buffer free (MB)
  - `vllm:e2e_request_latency_seconds_bucket` — for TTFT histograms
  - `vllm:num_requests_running` — active connections
  - `vllm:request_success_total` — for error rate calculation

---

## Step-by-Step Instructions

### Step 1 — Read the current dashboard JSON

```bash
cat monitoring/grafana/gpu_serving_dashboard.json | python -m json.tool | grep '"title"' | head -20
```

Note: which panels already exist, what their metric queries are.

---

### Step 2 — Verify / fix DCGM metric names

For every existing panel, find metric queries containing `DCGM_FI_` and verify they use the exact names listed above. Common wrong spellings to fix:
- `dcgm_fi_dev_gpu_util` → `DCGM_FI_DEV_GPU_UTIL` (uppercase)
- `DCGM_FI_DEV_MEM_USED` → `DCGM_FI_DEV_FB_USED`
- `dcgm_gpu_utilization` → `DCGM_FI_DEV_GPU_UTIL`

```bash
grep -i "dcgm" monitoring/grafana/gpu_serving_dashboard.json
```

---

### Step 3 — Ensure 6 required panels exist

The dashboard must have ALL of these panels (add any missing ones):

**Panel 1: GPU Utilization (%)**
```json
{
  "title": "GPU Utilization",
  "type": "timeseries",
  "targets": [{"expr": "DCGM_FI_DEV_GPU_UTIL{instance=~\"$instance\"}", "legendFormat": "GPU {{gpu}}"}]
}
```

**Panel 2: GPU Memory Used (MB)**
```json
{
  "title": "GPU Memory Used",
  "type": "timeseries",
  "targets": [{"expr": "DCGM_FI_DEV_FB_USED{instance=~\"$instance\"}", "legendFormat": "GPU {{gpu}}"}]
}
```

**Panel 3: TTFT P95 (ms) per backend**
```json
{
  "title": "Time to First Token P95",
  "type": "timeseries",
  "targets": [{
    "expr": "histogram_quantile(0.95, sum(rate(vllm:e2e_request_latency_seconds_bucket[5m])) by (le, model_name)) * 1000",
    "legendFormat": "{{model_name}} P95 TTFT"
  }]
}
```

**Panel 4: Tokens/sec per model**
```json
{
  "title": "Throughput (tokens/sec)",
  "type": "timeseries",
  "targets": [{
    "expr": "sum(rate(vllm:generation_tokens_total[1m])) by (model_name)",
    "legendFormat": "{{model_name}}"
  }]
}
```

**Panel 5: Error Rate (%)**
```json
{
  "title": "Request Error Rate",
  "type": "timeseries",
  "targets": [{
    "expr": "100 * (1 - sum(rate(vllm:request_success_total[5m])) / sum(rate(api_requests_total[5m])))",
    "legendFormat": "Error Rate %"
  }]
}
```

**Panel 6: Active Connections**
```json
{
  "title": "Active Requests",
  "type": "stat",
  "targets": [{"expr": "sum(vllm:num_requests_running)", "legendFormat": "Active"}]
}
```

---

### Step 4 — Add `$instance` template variable (if missing)

Ensure the dashboard JSON has a `templating` section with an `$instance` variable:

```json
"templating": {
  "list": [{
    "name": "instance",
    "type": "query",
    "query": "label_values(DCGM_FI_DEV_GPU_UTIL, instance)",
    "refresh": 2
  }]
}
```

---

### Step 5 — Validate dashboard JSON

```bash
python -c "
import json, sys
with open('monitoring/grafana/gpu_serving_dashboard.json') as f:
    d = json.load(f)
panels = d.get('panels', [])
print(f'Total panels: {len(panels)}')
for p in panels:
    print(f'  - {p[\"title\"]}')
assert len(panels) >= 6, 'Need at least 6 panels'
print('Dashboard JSON is valid')
"
```

---

### Step 6 — Verify Grafana provisioning config

Check `monitoring/grafana/provisioning/dashboards/` (or similar) for a provisioner YAML that references `gpu_serving_dashboard.json`. If missing, create:

```yaml
# monitoring/grafana/provisioning/dashboards/gpu-serving.yaml
apiVersion: 1
providers:
  - name: gpu-serving
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

Ensure the Grafana service in `docker-compose.yml` mounts:
```yaml
volumes:
  - ./monitoring/grafana/gpu_serving_dashboard.json:/var/lib/grafana/dashboards/gpu_serving_dashboard.json:ro
  - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
```

---

## Acceptance Criteria

- [ ] Dashboard JSON validates as valid JSON (`python -m json.tool` exits 0)
- [ ] At least 6 panels: GPU utilization, memory used, TTFT P95, throughput (tokens/sec), error rate, active connections
- [ ] All DCGM metric names are uppercase and correct (`DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED`, `DCGM_FI_DEV_MEM_COPY_UTIL`)
- [ ] `$instance` template variable defined
- [ ] Dashboard provisioned automatically via `monitoring/grafana/provisioning/` on `docker compose up`
- [ ] Root-level `monitoring/grafana_dashboard.json` does NOT exist (removed by `/cleanup-duplicates`)

---

## Do NOT

- Do NOT modify `monitoring/grafana_dashboard.json` — it should be deleted, not updated
- Do NOT hardcode host:port values in panel queries — use template variables
- Do NOT change Prometheus scrape configs — that is out of scope
- Do NOT add auth panels — Grafana auth is managed externally
