import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

np.random.seed(7)

agents = ["Planner", "Executor", "Expresser", "Reviewer"]
expected_means = {
    "Planner": 0.84,
    "Executor": 0.43,
    "Expresser": 0.68,
    "Reviewer": 0.78,
}
expected_std = {
    "Planner": 0.035,
    "Executor": 0.060,
    "Expresser": 0.045,
    "Reviewer": 0.040,
}

rows = []
n_runs = 10
for agent in agents:
    vals = np.random.normal(expected_means[agent], expected_std[agent], n_runs)
    vals = np.clip(vals, 0, 1)
    for i, v in enumerate(vals, start=1):
        rows.append({"agent": agent, "run": i, "cache_hit_ratio": v})

df = pd.DataFrame(rows)
summary = (
    df.groupby("agent", sort=False)
    .agg(
        mean_hit_ratio=("cache_hit_ratio", "mean"),
        n=("cache_hit_ratio", "count"),
    )
    .reset_index()
)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig, ax = plt.subplots(figsize=(3.6, 2.6), dpi=300)

x = np.arange(len(agents))
means = summary["mean_hit_ratio"].to_numpy()
violin_data = [
    df.loc[df["agent"] == agent, "cache_hit_ratio"].to_numpy() * 100
    for agent in agents
]

violins = ax.violinplot(
    violin_data,
    positions=x,
    widths=0.72,
    showmeans=False,
    showmedians=False,
    showextrema=False,
)
for body in violins["bodies"]:
    body.set_facecolor("0.85")
    body.set_edgecolor("black")
    body.set_linewidth(0.8)
    body.set_alpha(0.9)

ax.scatter(
    x,
    means * 100,
    marker="D",
    s=20,
    facecolors="black",
    edgecolors="black",
    linewidths=0.5,
    zorder=5,
    label="Mean",
)

rng = np.random.default_rng(11)
for i, agent in enumerate(agents):
    y = df.loc[df["agent"] == agent, "cache_hit_ratio"].to_numpy() * 100
    jitter = rng.uniform(-0.12, 0.12, size=len(y))
    ax.scatter(
        np.full_like(y, i, dtype=float) + jitter,
        y,
        s=12,
        facecolors="white",
        edgecolors="black",
        linewidths=0.5,
        zorder=4,
    )

ax.set_ylabel("Cache hit ratio (%)")
ax.set_xticks(x)
ax.set_xticklabels(agents, rotation=20, ha="right")
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 20))
ax.set_title("Figure 1. Cache hit ratio distribution by agent", pad=6)
ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5, zorder=1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(frameon=False, loc="lower right", handletextpad=0.3)

ax.annotate(
    "Dynamic tool outputs\nreduce reuse",
    xy=(1, means[1] * 100),
    xytext=(1.32, 28),
    arrowprops=dict(arrowstyle="->", linewidth=0.8),
    fontsize=8,
    ha="left",
    va="center",
)

fig.tight_layout(pad=0.5)
fig.savefig("figure1_cache_hit_ratio_by_agent.png", bbox_inches="tight")
fig.savefig("figure1_cache_hit_ratio_by_agent.svg", bbox_inches="tight")
df.to_csv("figure1_fake_data.csv", index=False)
