# Figure 5: Cache Hit Ratio Under Increasing Concurrency

This directory contains Python and R implementations of Figure 5:

- `figure5_python.py`
- `figure5_r.R`
- `environment.yml`

Both scripts generate synthetic cache-hit-ratio data under increasing workflow concurrency for the baseline KVFlow agents:

```text
Planner -> Executor -> Expresser -> Reviewer
```

## Figure Meaning

**Figure 5. Cache hit ratio under increasing concurrency**

**Purpose:** Study cache pressure effects.

**Expected observation:** Cache-hit ratio decreases as concurrency increases; Executor degrades first.

Different users may use the same workflow template, but different projects create different dynamic contexts, retrieved documents, tool outputs, logs, and execution traces. That is why cache reuse drops as concurrency increases, and Executor is expected to degrade first.

## Why a Multi-Line Chart?

A multi-line chart directly shows how cache-hit ratio changes as more workflows run concurrently. The x-axis is concurrent workflows, the y-axis is cache-hit ratio, and each line is one agent.

This chart shows both cache pressure and agent-specific sensitivity. A steeper downward slope means that agent loses reusable prompt prefixes more quickly as concurrency increases.

How to read it:

- The x-axis is concurrent workflows.
- The y-axis is cache hit ratio in percent.
- Each line is one agent.
- The shaded band around each line is the standard error of the mean across synthetic runs.
- Executor is expected to drop fastest because its prompt context often contains project-specific dynamic data.

## Conda Environment

Use the same Conda environment as Figures 1 through 4:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_5
conda env update -n kv-cache-figure1 -f environment.yml
conda activate kv-cache-figure1
```

## Run the Python Figure

Run from this directory so the generated files are saved next to the script:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_5
python figure5_python.py
```

Expected outputs:

```text
figure5_cache_hit_ratio_under_increasing_concurrency.png
figure5_cache_hit_ratio_under_increasing_concurrency.svg
figure5_fake_data.csv
```

## Run the R Figure

Run from this directory:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_5
Rscript figure5_r.R
```

Expected outputs:

```text
figure5_cache_hit_ratio_under_increasing_concurrency_R.png
figure5_cache_hit_ratio_under_increasing_concurrency_R.svg
figure5_fake_data_R.csv
```

## Run Without Activating the Environment

If you prefer not to activate the environment, use `conda run`:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_5
conda run -n kv-cache-figure1 python figure5_python.py
conda run -n kv-cache-figure1 Rscript figure5_r.R
```

## Notes

- The scripts use fixed random seeds, so repeated runs should produce the same synthetic data and figures.
- The Python and R scripts write outputs to the current working directory, not necessarily to the script directory. Run them from `figure_5/` unless you intentionally want outputs elsewhere.
