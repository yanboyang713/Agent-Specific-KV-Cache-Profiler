# Figure 3: Transition-Level Cache Reuse Matrix

This directory contains Python and R implementations of Figure 3:

- `figure3_python.py`
- `figure3_r.R`
- `environment.yml`

Both scripts generate a synthetic transition-level cache reuse matrix for the baseline KVFlow loop:

```text
Planner -> Executor -> Expresser -> Reviewer -> Planner
```

## Figure Meaning

**Figure 3. Transition-level cache reuse matrix**

**Purpose:** Study whether workflow position affects cache reuse.

**Expected observation:** Executor->Expresser and Reviewer->Planner show stronger reuse than Planner->Executor.

**Why Executor->Expresser is stronger:** Expresser usually consumes Executor's concrete output, such as tool results, logs, retrieved evidence, or execution traces, so the next prompt may share a large suffix/prefix region.

**Why Reviewer->Planner is stronger:** Reviewer's feedback often becomes the next Planner's planning context, so the next cycle can reuse previous review/state tokens.

**Why Planner->Executor is weaker:** Planner gives high-level instructions, but Executor expands them into dynamic tool calls and observations, which are less stable and reduce exact KV reuse.

## Why a Matrix?

A transition matrix compares cache reuse by workflow edge:

```text
previous_agent -> current_agent
```

Rows represent the previous agent, columns represent the current agent, and each cell reports the cache reuse ratio for that transition. This view is useful because cache reuse is not only an agent-level property; it can depend on where the agent appears in the workflow and which agent ran immediately before it.

How to read it:

- Darker cells indicate higher cache reuse.
- `N/A` cells are transitions that are not part of the baseline KVFlow loop.
- Highlighted cells mark stronger reuse transitions.
- Planner->Executor is expected to be weaker because Executor prompts often introduce dynamic observations.

## Conda Environment

Use the same Conda environment as Figures 1 and 2:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_3
conda env update -n kv-cache-figure1 -f environment.yml
conda activate kv-cache-figure1
```

## Run the Python Figure

Run from this directory so the generated files are saved next to the script:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_3
python figure3_python.py
```

Expected outputs:

```text
figure3_transition_cache_reuse_matrix.png
figure3_transition_cache_reuse_matrix.svg
figure3_fake_matrix.csv
```

## Run the R Figure

Run from this directory:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_3
Rscript figure3_r.R
```

Expected outputs:

```text
figure3_transition_cache_reuse_matrix_R.png
figure3_transition_cache_reuse_matrix_R.svg
figure3_fake_matrix_R.csv
```

## Run Without Activating the Environment

If you prefer not to activate the environment, use `conda run`:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_3
conda run -n kv-cache-figure1 python figure3_python.py
conda run -n kv-cache-figure1 Rscript figure3_r.R
```

## Notes

- The scripts use fixed synthetic transition values, so repeated runs should produce the same matrix.
- The Python and R scripts write outputs to the current working directory, not necessarily to the script directory. Run them from `figure_3/` unless you intentionally want outputs elsewhere.
