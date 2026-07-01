# Data Visualization

## Figure 1. Cache Hit Ratio by Agent

![Figure 1. Cache hit ratio by agent](figure_1/figure1_cache_hit_ratio_by_agent_R.png)

**Purpose:** Identify whether Planner, Executor, Expresser, and Reviewer exhibit different cache reuse behavior.

**Expected observation:** Planner and Reviewer have higher cache-hit ratios; Executor has lower cache-hit ratio due to dynamic tool outputs.

A violin plot shows the distribution of cache hit ratios across repeated runs.
