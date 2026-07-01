import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

np.random.seed(41)

agents = ["Planner", "Executor", "Expresser", "Reviewer"]
turns = np.arange(1, 7)
n_runs = 8

expected_means = {
    "Planner": [0.52, 0.72, 0.80, 0.84, 0.86, 0.87],
    "Executor": [0.30, 0.38, 0.44, 0.47, 0.49, 0.50],
    "Expresser": [0.42, 0.56, 0.63, 0.67, 0.69, 0.70],
    "Reviewer": [0.48, 0.69, 0.77, 0.81, 0.83, 0.84],
}
expected_std = {
    "Planner": 0.030,
    "Executor": 0.045,
    "Expresser": 0.035,
    "Reviewer": 0.030,
}

rows = []
for agent in agents:
    for turn, mean in zip(turns, expected_means[agent]):
        vals = np.random.normal(mean, expected_std[agent], n_runs)
        vals = np.clip(vals, 0, 1)
        for run, value in enumerate(vals, start=1):
            rows.append({
                "agent": agent,
                "turn": int(turn),
                "run": run,
                "cache_hit_ratio": value,
            })

df = pd.DataFrame(rows)
summary = (
    df.groupby(["agent", "turn"], sort=False)
    .agg(
        mean_hit_ratio=("cache_hit_ratio", "mean"),
        std_hit_ratio=("cache_hit_ratio", "std"),
        n=("cache_hit_ratio", "count"),
    )
    .reset_index()
)
summary["sem"] = summary["std_hit_ratio"] / np.sqrt(summary["n"])

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 8,
    "legend.title_fontsize": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=300)

styles = {
    "Planner": {"color": "#0072B2", "marker": "o"},
    "Executor": {"color": "#D55E00", "marker": "s"},
    "Expresser": {"color": "#009E73", "marker": "^"},
    "Reviewer": {"color": "#CC79A7", "marker": "D"},
}

for agent in agents:
    agent_summary = summary[summary["agent"] == agent]
    x = agent_summary["turn"].to_numpy()
    y = agent_summary["mean_hit_ratio"].to_numpy() * 100
    sem = agent_summary["sem"].to_numpy() * 100
    style = styles[agent]
    ax.plot(
        x,
        y,
        label=agent,
        color=style["color"],
        marker=style["marker"],
        linewidth=1.4,
        markersize=4,
        zorder=3,
    )
    ax.fill_between(
        x,
        y - sem,
        y + sem,
        color=style["color"],
        alpha=0.12,
        linewidth=0,
        zorder=2,
    )

ax.set_xlabel("Workflow turn")
ax.set_ylabel("Cache hit ratio (%)")
ax.set_xticks(turns)
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 20))
ax.set_title("Figure 4. Cache hit ratio across workflow turns", pad=6)
ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5, zorder=1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(title="Agent", frameon=False, loc="lower right")

ax.annotate(
    "Reuse improves\nafter Turn 1",
    xy=(2, summary[(summary["agent"] == "Planner") & (summary["turn"] == 2)]["mean_hit_ratio"].iloc[0] * 100),
    xytext=(2.35, 90),
    arrowprops=dict(arrowstyle="->", linewidth=0.8),
    fontsize=8,
    ha="left",
    va="center",
)

fig.tight_layout(pad=0.5)
fig.savefig("figure4_cache_hit_ratio_by_turn.png", bbox_inches="tight")
fig.savefig("figure4_cache_hit_ratio_by_turn.svg", bbox_inches="tight")
df.to_csv("figure4_fake_data.csv", index=False)
