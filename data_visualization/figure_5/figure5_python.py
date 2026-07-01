import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

np.random.seed(61)

agents = ["Planner", "Executor", "Expresser", "Reviewer"]
concurrency_levels = np.array([1, 2, 4, 8, 16, 32])

expected_curves = {
    "Planner":   np.array([0.84, 0.81, 0.76, 0.68, 0.57, 0.44]),
    "Executor":  np.array([0.47, 0.41, 0.33, 0.23, 0.15, 0.09]),
    "Expresser": np.array([0.70, 0.66, 0.59, 0.49, 0.37, 0.25]),
    "Reviewer": np.array([0.80, 0.76, 0.70, 0.61, 0.50, 0.38]),
}

rows = []
n_runs = 8
for agent in agents:
    for idx, conc in enumerate(concurrency_levels):
        base = expected_curves[agent][idx]
        sd = 0.025 + 0.006 * np.log2(conc)
        vals = np.random.normal(base, sd, n_runs)
        vals = np.clip(vals, 0, 1)
        for run, v in enumerate(vals, start=1):
            rows.append({
                "agent": agent,
                "concurrency": int(conc),
                "run": run,
                "cache_hit_ratio": float(v),
            })

df = pd.DataFrame(rows)

summary = (
    df.groupby(["agent", "concurrency"], sort=False)
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
    "legend.fontsize": 8.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig, ax = plt.subplots(figsize=(4.2, 2.8), dpi=300)

styles = {
    "Planner": {"color": "#0072B2", "marker": "o"},
    "Executor": {"color": "#D55E00", "marker": "s"},
    "Expresser": {"color": "#009E73", "marker": "^"},
    "Reviewer": {"color": "#CC79A7", "marker": "D"},
}

for agent in agents:
    sub = summary[summary["agent"] == agent]
    x = sub["concurrency"].to_numpy()
    y = sub["mean_hit_ratio"].to_numpy() * 100
    sem = sub["sem"].to_numpy() * 100
    style = styles[agent]

    ax.plot(
        x,
        y,
        label=agent,
        color=style["color"],
        marker=style["marker"],
        linewidth=1.4,
        markersize=4.0,
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

ax.set_xscale("log", base=2)
ax.set_xlabel("Concurrent workflows")
ax.set_ylabel("Cache hit ratio (%)")
ax.set_xticks(concurrency_levels)
ax.set_xticklabels([str(x) for x in concurrency_levels])
ax.set_ylim(0, 95)
ax.set_yticks(np.arange(0, 96, 15))
ax.set_title("Figure 5. Cache hit ratio under increasing concurrency", pad=6)

ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5, zorder=1)
ax.grid(axis="x", linestyle=":", linewidth=0.4, alpha=0.35, zorder=1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(frameon=False, ncol=2, loc="upper right", handletextpad=0.4)

ax.annotate(
    "Executor degrades first\nunder project-specific\ncache pressure",
    xy=(8, summary[(summary["agent"] == "Executor") & (summary["concurrency"] == 8)]["mean_hit_ratio"].iloc[0] * 100),
    xytext=(1.15, 20),
    arrowprops=dict(arrowstyle="->", linewidth=0.8),
    fontsize=8,
    ha="left",
    va="center",
)

fig.tight_layout(pad=0.5)
fig.savefig("figure5_cache_hit_ratio_under_increasing_concurrency.png", bbox_inches="tight")
fig.savefig("figure5_cache_hit_ratio_under_increasing_concurrency.svg", bbox_inches="tight")
df.to_csv("figure5_fake_data.csv", index=False)
