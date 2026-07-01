import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

np.random.seed(17)

agents = ["Planner", "Executor", "Expresser", "Reviewer"]
expected_means = {"Planner": 520, "Executor": 1650, "Expresser": 780, "Reviewer": 910}
expected_std = {"Planner": 85, "Executor": 260, "Expresser": 140, "Reviewer": 160}

rows = []
n_runs = 12
for agent in agents:
    vals = np.random.normal(expected_means[agent], expected_std[agent], n_runs)
    vals = np.clip(vals, 0, None).round().astype(int)
    for i, v in enumerate(vals, start=1):
        rows.append({"agent": agent, "run": i, "new_prefill_tokens": int(v)})

df = pd.DataFrame(rows)

summary = (
    df.groupby("agent", sort=False)
    .agg(
        mean_new_prefill_tokens=("new_prefill_tokens", "mean"),
        n=("new_prefill_tokens", "count"),
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
means = summary["mean_new_prefill_tokens"].to_numpy()
violin_data = [
    df.loc[df["agent"] == agent, "new_prefill_tokens"].to_numpy()
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
    means,
    marker="D",
    s=20,
    facecolors="black",
    edgecolors="black",
    linewidths=0.5,
    zorder=5,
    label="Mean",
)

rng = np.random.default_rng(19)
for i, agent in enumerate(agents):
    y = df.loc[df["agent"] == agent, "new_prefill_tokens"].to_numpy()
    jitter = rng.uniform(-0.12, 0.12, size=len(y))
    ax.scatter(np.full_like(y, i, dtype=float) + jitter, y, s=12, facecolors="white",
               edgecolors="black", linewidths=0.5, zorder=4)

ax.set_ylabel("New prefill tokens")
ax.set_xticks(x)
ax.set_xticklabels(agents, rotation=20, ha="right")
ax.set_ylim(0, 2300)
ax.set_yticks(np.arange(0, 2301, 500))
ax.set_title("Figure 2. New prefill tokens by agent", pad=6)
ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5, zorder=1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(frameon=False, loc="upper right", handletextpad=0.3)

ax.annotate(
    "Dynamic tool outputs\nincrease\nrecomputation",
    xy=(1, means[1]),
    xytext=(1.55, 1730),
    arrowprops=dict(arrowstyle="->", linewidth=0.8),
    fontsize=8,
    ha="left",
    va="center",
)

fig.tight_layout(pad=0.5)
fig.savefig("figure2_new_prefill_tokens_by_agent.png", bbox_inches="tight")
fig.savefig("figure2_new_prefill_tokens_by_agent.svg", bbox_inches="tight")
df.to_csv("figure2_fake_data.csv", index=False)
