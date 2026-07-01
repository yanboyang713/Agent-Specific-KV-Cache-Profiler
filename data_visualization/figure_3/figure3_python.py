import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

agents = ["Planner", "Executor", "Expresser", "Reviewer"]

reuse_matrix = np.array([
    [np.nan, 0.46,   np.nan, np.nan],
    [np.nan, np.nan, 0.74,   np.nan],
    [np.nan, np.nan, np.nan, 0.61],
    [0.82,   np.nan, np.nan, np.nan],
])

df_matrix = pd.DataFrame(reuse_matrix, index=agents, columns=agents)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig, ax = plt.subplots(figsize=(3.8, 3.1), dpi=300)

masked = np.ma.masked_invalid(reuse_matrix)
im = ax.imshow(masked * 100, vmin=0, vmax=100, aspect="equal", zorder=1)

ax.set_facecolor("white")
for i in range(len(agents)):
    for j in range(len(agents)):
        if np.isnan(reuse_matrix[i, j]):
            rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor="0.93",
                                 edgecolor="white", linewidth=1.0, zorder=0)
            ax.add_patch(rect)

for i in range(len(agents)):
    for j in range(len(agents)):
        value = reuse_matrix[i, j]
        if np.isnan(value):
            ax.text(j, i, "N/A", ha="center", va="center", fontsize=8, color="0.45")
        else:
            ax.text(j, i, f"{value*100:.0f}%", ha="center", va="center",
                    fontsize=9, color="white" if value >= 0.65 else "black",
                    fontweight="bold" if value >= 0.70 else "normal")

ax.set_xticks(np.arange(len(agents)))
ax.set_yticks(np.arange(len(agents)))
ax.set_xticklabels(agents, rotation=25, ha="right")
ax.set_yticklabels(agents)

ax.set_xlabel("Current agent")
ax.set_ylabel("Previous agent")
ax.set_title("Figure 3. Transition-level cache reuse matrix", pad=8)

ax.set_xticks(np.arange(-0.5, len(agents), 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(agents), 1), minor=True)
ax.grid(which="minor", color="white", linestyle="-", linewidth=1.0)
ax.tick_params(which="minor", bottom=False, left=False)

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Cache reuse ratio (%)")
cbar.set_ticks([0, 25, 50, 75, 100])

for prev_agent, cur_agent in [("Executor", "Expresser"), ("Reviewer", "Planner")]:
    i = agents.index(prev_agent)
    j = agents.index(cur_agent)
    rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                         edgecolor="black", linewidth=1.5, zorder=4)
    ax.add_patch(rect)

fig.tight_layout(pad=0.6)
fig.savefig("figure3_transition_cache_reuse_matrix.png", bbox_inches="tight")
fig.savefig("figure3_transition_cache_reuse_matrix.svg", bbox_inches="tight")
df_matrix.to_csv("figure3_fake_matrix.csv")
