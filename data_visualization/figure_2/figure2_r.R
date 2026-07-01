library(ggplot2)
library(dplyr)

set.seed(17)

agents <- c("Planner", "Executor", "Expresser", "Reviewer")
expected_means <- c(Planner = 520, Executor = 1650, Expresser = 780, Reviewer = 910)
expected_std <- c(Planner = 85, Executor = 260, Expresser = 140, Reviewer = 160)
n_runs <- 12

df <- do.call(
  rbind,
  lapply(agents, function(agent) {
    values <- rnorm(n_runs, mean = expected_means[[agent]], sd = expected_std[[agent]])
    values <- round(pmax(values, 0))
    data.frame(agent = factor(agent, levels = agents), run = seq_len(n_runs), new_prefill_tokens = values)
  })
)

summary_df <- df %>%
  group_by(agent) %>%
  summarise(
    mean_new_prefill_tokens = mean(new_prefill_tokens),
    n = n(),
    .groups = "drop"
  )

executor_mean <- summary_df$mean_new_prefill_tokens[summary_df$agent == "Executor"]

p <- ggplot(df, aes(x = agent, y = new_prefill_tokens)) +
  geom_violin(width = 0.72, trim = FALSE, fill = "grey85", color = "black", linewidth = 0.35) +
  stat_summary(fun = mean, geom = "point", shape = 23, size = 2,
               stroke = 0.3, fill = "black", color = "black") +
  geom_point(position = position_jitter(width = 0.08, height = 0, seed = 19),
             shape = 21, size = 1.4, stroke = 0.3, fill = "white", color = "black") +
  annotate("segment", x = 2.45, xend = 2.05, y = 1750, yend = executor_mean,
           arrow = arrow(length = grid::unit(0.12, "cm")), linewidth = 0.3) +
  annotate("text", x = 2.5, y = 1730,
           label = "Dynamic tool outputs\nincrease\nrecomputation", hjust = 0, size = 2.7) +
  scale_y_continuous(breaks = seq(0, 2300, by = 500), expand = c(0, 0)) +
  coord_cartesian(ylim = c(0, 2300)) +
  labs(title = "Figure 2. New prefill tokens by agent", x = NULL, y = "New prefill tokens") +
  theme_classic(base_size = 10) +
  theme(
    plot.title = element_text(size = 11, hjust = 0.5),
    axis.text.x = element_text(angle = 20, hjust = 1),
    axis.line = element_line(linewidth = 0.35),
    axis.ticks = element_line(linewidth = 0.35),
    panel.grid.major.y = element_line(color = "grey85", linewidth = 0.25, linetype = "dashed")
  )

ggsave("figure2_new_prefill_tokens_by_agent_R.png", p, width = 3.6, height = 2.6, dpi = 300)
ggsave("figure2_new_prefill_tokens_by_agent_R.svg", p, width = 3.6, height = 2.6)
write.csv(df, "figure2_fake_data_R.csv", row.names = FALSE)
