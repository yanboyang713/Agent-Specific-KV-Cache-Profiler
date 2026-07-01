# Figure 4: Cache Hit Ratio Across Workflow Turns

This directory contains Python and R implementations of Figure 4:

- `figure4_python.py`
- `figure4_r.R`
- `environment.yml`

Both scripts generate synthetic turn-level cache-hit-ratio data for repeated PEER-style KVFlow cycles:

```text
Planner -> Executor -> Expresser -> Reviewer -> Planner
```

## Figure Meaning

**Figure 4. Cache hit ratio across workflow turns**

**Purpose:** Analyze cache behavior over repeated PEER cycles.

**Expected observation:** Reuse improves after the first turn, especially for Planner and Reviewer.

## Why a Multi-Line Chart?

For Figure 4, the best choice is a multi-line chart. The x-axis is workflow turn, the y-axis is cache-hit ratio, and each line is one agent. It directly shows whether reuse improves after Turn 1 and whether Planner/Reviewer improve faster than Executor.

This chart shows both turn-by-turn trend and agent-specific difference. Planner/Reviewer rising faster after Turn 1 directly supports the expected observation.

How to read it:

- The x-axis is workflow turn.
- The y-axis is cache hit ratio in percent.
- Each line is one agent.
- The shaded band around each line is the standard error of the mean across synthetic runs.
- A steeper upward slope after Turn 1 means cache reuse improves more quickly for that agent.

## Conda Environment

Use the same Conda environment as Figures 1, 2, and 3:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_4
conda env update -n kv-cache-figure1 -f environment.yml
conda activate kv-cache-figure1
```

## Run the Python Figure

Run from this directory so the generated files are saved next to the script:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_4
python figure4_python.py
```

Expected outputs:

```text
figure4_cache_hit_ratio_by_turn.png
figure4_cache_hit_ratio_by_turn.svg
figure4_fake_data.csv
```

## Run the R Figure

Run from this directory:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_4
Rscript figure4_r.R
```

Expected outputs:

```text
figure4_cache_hit_ratio_by_turn_R.png
figure4_cache_hit_ratio_by_turn_R.svg
figure4_fake_data_R.csv
```

## Run Without Activating the Environment

If you prefer not to activate the environment, use `conda run`:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_4
conda run -n kv-cache-figure1 python figure4_python.py
conda run -n kv-cache-figure1 Rscript figure4_r.R
```

## Notes

- The scripts use fixed random seeds, so repeated runs should produce the same synthetic data and figures.
- The Python and R scripts write outputs to the current working directory, not necessarily to the script directory. Run them from `figure_4/` unless you intentionally want outputs elsewhere.
