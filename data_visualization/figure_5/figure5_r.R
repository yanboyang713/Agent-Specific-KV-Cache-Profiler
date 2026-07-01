library(ggplot2)
library(dplyr)

set.seed(61)

agents <- c("Planner", "Executor", "Expresser", "Reviewer")
concurrency_levels <- c(1, 2, 4, 8, 16, 32)

expected_curves <- list(
  Planner   = c(0.84, 0.81, 0.76, 0.68, 0.57, 0.44),
  Executor  = c(0.47, 0.41, 0.33, 0.23, 0.15, 0.09),
  Expresser = c(0.70, 0.66, 0.59, 0.49, 0.37, 0.25),
  Reviewer  = c(0.80, 0.76, 0.70, 0.61, 0.50, 0.38)
)

n_runs <- 8
df <- data.frame()

for (agent in agents) {
  for (i in seq_along(concurrency_levels)) {
    conc <- concurrency_levels[i]
    base <- expected_curves[[agent]][i]
    sd <- 0.025 + 0.006 * log2(conc)
    values <- rnorm(n_runs, mean = base, sd = sd)
    values <- pmin(pmax(values, 0), 1)
    df <- rbind(
      df,
      data.frame(
        agent = factor(agent, levels = agents),
        concurrency = conc,
        run = seq_len(n_runs),
        cache_hit_ratio = values
      )
    )
  }
}

summary_df <- df %>%
  group_by(agent, concurrency) %>%
  summarise(
    mean_hit_ratio = mean(cache_hit_ratio),
    std_hit_ratio = sd(cache_hit_ratio),
    n = n(),
    sem = std_hit_ratio / sqrt(n),
    .groups = "drop"
  )

executor_y_at_8 <- summary_df$mean_hit_ratio[
  summary_df$agent == "Executor" & summary_df$concurrency == 8
] * 100

palette <- c(
  Planner = "#0072B2",
  Executor = "#D55E00",
  Expresser = "#009E73",
  Reviewer = "#CC79A7"
)

p <- ggplot(summary_df, aes(x = concurrency, y = mean_hit_ratio * 100, color = agent, fill = agent)) +
  geom_ribbon(
    aes(ymin = (mean_hit_ratio - sem) * 100, ymax = (mean_hit_ratio + sem) * 100),
    alpha = 0.12,
    color = NA
  ) +
  geom_line(linewidth = 0.5) +
  geom_point(size = 1.7) +
  annotate(
    "segment",
    x = 2.35, xend = 8,
    y = 20, yend = executor_y_at_8,
    arrow = arrow(length = grid::unit(0.12, "cm")),
    linewidth = 0.3
  ) +
  annotate(
    "text",
    x = 1.15,
    y = 20,
    label = "Executor degrades first\nunder project-specific\ncache pressure",
    hjust = 0,
    size = 2.6
  ) +
  scale_x_continuous(
    trans = "log2",
    breaks = concurrency_levels,
    labels = concurrency_levels
  ) +
  scale_y_continuous(limits = c(0, 95), breaks = seq(0, 95, by = 15)) +
  scale_color_manual(values = palette) +
  scale_fill_manual(values = palette) +
  guides(fill = "none") +
  labs(
    title = "Figure 5. Cache hit ratio under increasing concurrency",
    x = "Concurrent workflows",
    y = "Cache hit ratio (%)",
    color = "Agent"
  ) +
  theme_classic(base_size = 10) +
  theme(
    plot.title = element_text(size = 11, hjust = 0.5),
    axis.line = element_line(linewidth = 0.35),
    axis.ticks = element_line(linewidth = 0.35),
    panel.grid.major.y = element_line(color = "grey85", linewidth = 0.25, linetype = "dashed"),
    panel.grid.major.x = element_line(color = "grey88", linewidth = 0.20, linetype = "dotted"),
    legend.position = "bottom",
    legend.direction = "horizontal",
    legend.title = element_blank(),
    legend.text = element_text(size = 8),
    legend.key.width = grid::unit(0.7, "cm")
  )

ggsave("figure5_cache_hit_ratio_under_increasing_concurrency_R.png", p, width = 4.2, height = 2.8, dpi = 300)
ggsave("figure5_cache_hit_ratio_under_increasing_concurrency_R.svg", p, width = 4.2, height = 2.8)
write.csv(df, "figure5_fake_data_R.csv", row.names = FALSE)
