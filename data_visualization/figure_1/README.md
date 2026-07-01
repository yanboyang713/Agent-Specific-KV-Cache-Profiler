# Figure 1: Cache Hit Ratio by Agent

This directory contains Python and R implementations of Figure 1:

- `figure1_python.py`
- `figure1_r.R`
- `environment.yml`

Both scripts generate synthetic cache-hit-ratio data for the baseline KVFlow agents:

```text
Planner -> Executor -> Expresser -> Reviewer
```

## Why a Violin Plot?

Figure 1 now uses a violin plot instead of a bar chart. A bar chart mainly shows one summary value, usually the mean, for each agent. A violin plot shows the distribution of cache hit ratios across repeated runs.

How to read it:

- The y-axis is cache hit ratio in percent.
- Each violin is one agent.
- Wider parts of the violin indicate values where more runs are concentrated.
- Narrower parts indicate fewer observations.
- White points show individual benchmark runs.
- The black diamond marks the mean for that agent.

This is useful for cache profiling because two agents can have similar average cache reuse but different variability. For example, an agent with a stable prompt structure should produce a tight violin, while an agent with dynamic tool outputs may produce a wider distribution. Because this example uses only 10 runs per agent, the overlaid raw points are important; they prevent the smoothed violin shape from hiding the actual sample values.

## Create the Conda Environment

Create one Conda environment with Python, R, and all required plotting packages:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_1
conda env create -f environment.yml
```

If you prefer the explicit command instead of the environment file:

```bash
conda create -n kv-cache-figure1 -c conda-forge \
  python=3.11 \
  numpy pandas matplotlib \
  r-base r-ggplot2 r-dplyr r-svglite
```

Activate it:

```bash
conda activate kv-cache-figure1
```

## Run the Python Figure

Run from this directory so the generated files are saved next to the script:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_1
python figure1_python.py
```

Expected outputs:

```text
figure1_cache_hit_ratio_by_agent.png
figure1_cache_hit_ratio_by_agent.svg
figure1_fake_data.csv
```

## Run the R Figure

Run from this directory:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_1
Rscript figure1_r.R
```

Expected outputs:

```text
figure1_cache_hit_ratio_by_agent_R.png
figure1_cache_hit_ratio_by_agent_R.svg
figure1_fake_data_R.csv
```

## Run Without Activating the Environment

If you prefer not to activate the environment, use `conda run`:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_1
conda run -n kv-cache-figure1 python figure1_python.py
conda run -n kv-cache-figure1 Rscript figure1_r.R
```

## Notes

- The scripts use fixed random seeds, so repeated runs should produce the same synthetic data and figures.
- The Python and R scripts write outputs to the current working directory, not necessarily to the script directory. Run them from `figure_1/` unless you intentionally want outputs elsewhere.
- If `Rscript` is not found, confirm the Conda environment is active or use `conda run -n kv-cache-figure1 Rscript figure1_r.R`.
