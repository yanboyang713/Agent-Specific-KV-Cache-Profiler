# Data Visualization

## Figure 1. Cache Hit Ratio by Agent

![Figure 1. Cache hit ratio by agent](figure_1/figure1_cache_hit_ratio_by_agent_R.png)

**Purpose:** Identify whether Planner, Executor, Expresser, and Reviewer exhibit different cache reuse behavior.

**Expected observation:** Planner and Reviewer have higher cache-hit ratios; Executor has lower cache-hit ratio due to dynamic tool outputs.

A violin plot shows the distribution of cache hit ratios across repeated runs.

## Figure 2. New Prefill Tokens by Agent

![Figure 2. New prefill tokens by agent](figure_2/figure2_new_prefill_tokens_by_agent_R.png)

**Purpose:** Measure recomputation burden per agent.

**Expected observation:** Executor contributes the largest number of newly computed prefill tokens.

**Prefill:** LLM processing input prompt tokens before generating output tokens.

**New prefill tokens:** Prompt tokens that cannot reuse existing KV cache and must be recomputed.

**Recomputation burden:** Total newly computed prefill tokens. Higher burden usually means higher prefill latency and TTFT.

**Why Executor highest?** Executor often receives dynamic tool outputs, logs, JSON results, traces, or retrieved content. These change across runs, so prefix reuse is weaker and more tokens must be recomputed.

A violin plot shows the distribution of new prefill tokens across repeated runs.
