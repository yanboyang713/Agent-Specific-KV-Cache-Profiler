# Figure 2: New Prefill Tokens by Agent

This directory contains Python and R implementations of Figure 2:

- `figure2_python.py`
- `figure2_r.R`
- `environment.yml`

Both scripts generate synthetic new-prefill-token data for the baseline KVFlow agents:

```text
Planner -> Executor -> Expresser -> Reviewer
```

## Figure Meaning

**Figure 2. New prefill tokens by agent**

**Purpose:** Measure recomputation burden per agent.

**Expected observation:** Executor contributes the largest number of newly computed prefill tokens.

**Prefill:** LLM processing input prompt tokens before generating output tokens.

**New prefill tokens:** Prompt tokens that cannot reuse existing KV cache and must be recomputed.

**Recomputation burden:** Total newly computed prefill tokens. Higher burden usually means higher prefill latency and TTFT.

**Why Executor highest?** Executor often receives dynamic tool outputs, logs, JSON results, traces, or retrieved content. These change across runs, so prefix reuse is weaker and more tokens must be recomputed.

## Why a Violin Plot?

A violin plot shows the distribution of new prefill tokens across repeated runs. This is useful because recomputation burden is not only about the average token count; variability matters too. An agent with dynamic inputs may have both a higher mean and a wider distribution.

How to read it:

- The y-axis is new prefill tokens.
- Each violin is one agent.
- Wider parts of the violin indicate values where more runs are concentrated.
- Narrower parts indicate fewer observations.
- White points show individual benchmark runs.
- The black diamond marks the mean for that agent.

## Conda Environment

Use the same Conda environment as Figure 1:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_2
conda env update -n kv-cache-figure1 -f environment.yml
conda activate kv-cache-figure1
```

## Run the Python Figure

Run from this directory so the generated files are saved next to the script:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_2
python figure2_python.py
```

Expected outputs:

```text
figure2_new_prefill_tokens_by_agent.png
figure2_new_prefill_tokens_by_agent.svg
figure2_fake_data.csv
```

## Run the R Figure

Run from this directory:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_2
Rscript figure2_r.R
```

Expected outputs:

```text
figure2_new_prefill_tokens_by_agent_R.png
figure2_new_prefill_tokens_by_agent_R.svg
figure2_fake_data_R.csv
```

## Run Without Activating the Environment

If you prefer not to activate the environment, use `conda run`:

```bash
cd /home/yanboyang713/projects/Agent-Specific-KV-Cache-Profiler/data_visualization/figure_2
conda run -n kv-cache-figure1 python figure2_python.py
conda run -n kv-cache-figure1 Rscript figure2_r.R
```

## Notes

- The scripts use fixed random seeds, so repeated runs should produce the same synthetic data and figures.
- The Python and R scripts write outputs to the current working directory, not necessarily to the script directory. Run them from `figure_2/` unless you intentionally want outputs elsewhere.
