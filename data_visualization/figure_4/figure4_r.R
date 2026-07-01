library(ggplot2)
library(dplyr)

set.seed(41)

agents <- c("Planner", "Executor", "Expresser", "Reviewer")
turns <- seq_len(6)
n_runs <- 8

expected_means <- list(
  Planner = c(0.52, 0.72, 0.80, 0.84, 0.86, 0.87),
  Executor = c(0.30, 0.38, 0.44, 0.47, 0.49, 0.50),
  Expresser = c(0.42, 0.56, 0.63, 0.67, 0.69, 0.70),
  Reviewer = c(0.48, 0.69, 0.77, 0.81, 0.83, 0.84)
)
expected_std <- c(Planner = 0.030, Executor = 0.045, Expresser = 0.035, Reviewer = 0.030)

df <- do.call(
  rbind,
  lapply(agents, function(agent) {
    do.call(
      rbind,
      lapply(turns, function(turn) {
        values <- rnorm(n_runs, mean = expected_means[[agent]][turn], sd = expected_std[[agent]])
        values <- pmin(pmax(values, 0), 1)
        data.frame(
          agent = factor(agent, levels = agents),
          turn = turn,
          run = seq_len(n_runs),
          cache_hit_ratio = values
        )
      })
    )
  })
)

summary_df <- df %>%
  group_by(agent, turn) %>%
  summarise(
    mean_hit_ratio = mean(cache_hit_ratio),
    std_hit_ratio = sd(cache_hit_ratio),
    n = n(),
    sem = std_hit_ratio / sqrt(n),
    .groups = "drop"
  )

palette <- c(
  Planner = "#0072B2",
  Executor = "#D55E00",
  Expresser = "#009E73",
  Reviewer = "#CC79A7"
)

p <- ggplot(summary_df, aes(x = turn, y = mean_hit_ratio * 100, color = agent, fill = agent)) +
  geom_ribbon(
    aes(ymin = (mean_hit_ratio - sem) * 100, ymax = (mean_hit_ratio + sem) * 100),
    alpha = 0.12,
    color = NA
  ) +
  geom_line(linewidth = 0.5) +
  geom_point(size = 1.7) +
  annotate(
    "segment",
    x = 2.35, xend = 2,
    y = 90, yend = summary_df$mean_hit_ratio[summary_df$agent == "Planner" & summary_df$turn == 2] * 100,
    arrow = arrow(length = grid::unit(0.12, "cm")),
    linewidth = 0.3
  ) +
  annotate(
    "text",
    x = 2.45,
    y = 90,
    label = "Reuse improves\nafter Turn 1",
    hjust = 0,
    size = 2.7
  ) +
  scale_x_continuous(breaks = turns) +
  scale_y_continuous(limits = c(0, 100), breaks = seq(0, 100, by = 20), expand = c(0, 0)) +
  scale_color_manual(values = palette) +
  scale_fill_manual(values = palette) +
  guides(fill = "none") +
  labs(
    title = "Figure 4. Cache hit ratio across workflow turns",
    x = "Workflow turn",
    y = "Cache hit ratio (%)",
    color = "Agent",
    fill = "Agent"
  ) +
  theme_classic(base_size = 10) +
  theme(
    plot.title = element_text(size = 11, hjust = 0.5),
    axis.line = element_line(linewidth = 0.35),
    axis.ticks = element_line(linewidth = 0.35),
    panel.grid.major.y = element_line(color = "grey85", linewidth = 0.25, linetype = "dashed"),
    legend.position = "bottom",
    legend.direction = "horizontal",
    legend.title = element_blank(),
    legend.text = element_text(size = 8),
    legend.key.width = grid::unit(0.7, "cm")
  )

ggsave("figure4_cache_hit_ratio_by_turn_R.png", p, width = 4.2, height = 3.0, dpi = 300)
ggsave("figure4_cache_hit_ratio_by_turn_R.svg", p, width = 4.2, height = 3.0)
write.csv(df, "figure4_fake_data_R.csv", row.names = FALSE)
