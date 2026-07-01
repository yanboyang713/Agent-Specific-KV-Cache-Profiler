# Figure 1. Cache hit ratio by agent
# Purpose: Identify whether Planner, Executor, Expresser, and Reviewer exhibit different cache reuse behavior.

library(ggplot2)
library(dplyr)

set.seed(7)

agents <- c("Planner", "Executor", "Expresser", "Reviewer")
expected_means <- c(Planner = 0.84, Executor = 0.43, Expresser = 0.68, Reviewer = 0.78)
expected_std <- c(Planner = 0.035, Executor = 0.060, Expresser = 0.045, Reviewer = 0.040)

n_runs <- 10

df <- do.call(
  rbind,
  lapply(agents, function(agent) {
    values <- rnorm(n_runs, mean = expected_means[[agent]], sd = expected_std[[agent]])
    values <- pmin(pmax(values, 0), 1)
    data.frame(
      agent = factor(agent, levels = agents),
      run = seq_len(n_runs),
      cache_hit_ratio = values
    )
  })
)

summary_df <- df %>%
  group_by(agent) %>%
  summarise(
    mean_hit_ratio = mean(cache_hit_ratio),
    n = n(),
    .groups = "drop"
  )

p <- ggplot(df, aes(x = agent, y = cache_hit_ratio * 100)) +
  geom_violin(
    width = 0.72,
    trim = FALSE,
    fill = "grey85",
    color = "black",
    linewidth = 0.35
  ) +
  stat_summary(
    fun = mean,
    geom = "point",
    shape = 23,
    size = 2,
    stroke = 0.3,
    fill = "black",
    color = "black"
  ) +
  geom_point(
    position = position_jitter(width = 0.08, height = 0, seed = 11),
    shape = 21,
    size = 1.4,
    stroke = 0.3,
    fill = "white",
    color = "black"
  ) +
  annotate(
    "segment",
    x = 2.45, xend = 2.05,
    y = 32, yend = summary_df$mean_hit_ratio[summary_df$agent == "Executor"] * 100,
    arrow = arrow(length = grid::unit(0.12, "cm")),
    linewidth = 0.3
  ) +
  annotate(
    "text",
    x = 2.5,
    y = 28,
    label = "Dynamic tool outputs\nreduce reuse",
    hjust = 0,
    size = 2.7
  ) +
  scale_y_continuous(
    limits = c(0, 100),
    breaks = seq(0, 100, by = 20),
    expand = c(0, 0)
  ) +
  labs(
    title = "Figure 1. Cache hit ratio distribution by agent",
    x = NULL,
    y = "Cache hit ratio (%)"
  ) +
  theme_classic(base_size = 10) +
  theme(
    plot.title = element_text(size = 11, hjust = 0.5),
    axis.text.x = element_text(angle = 20, hjust = 1),
    axis.line = element_line(linewidth = 0.35),
    axis.ticks = element_line(linewidth = 0.35),
    panel.grid.major.y = element_line(color = "grey85", linewidth = 0.25, linetype = "dashed")
  )

ggsave("figure1_cache_hit_ratio_by_agent_R.png", p, width = 3.6, height = 2.6, dpi = 300)
ggsave("figure1_cache_hit_ratio_by_agent_R.svg", p, width = 3.6, height = 2.6)
write.csv(df, "figure1_fake_data_R.csv", row.names = FALSE)
