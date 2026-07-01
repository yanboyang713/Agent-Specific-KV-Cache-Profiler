library(ggplot2)
library(dplyr)

agents <- c("Planner", "Executor", "Expresser", "Reviewer")

df <- expand.grid(
  previous_agent = factor(agents, levels = agents),
  current_agent = factor(agents, levels = agents)
)

df$reuse_ratio <- NA_real_
df$reuse_ratio[df$previous_agent == "Planner" & df$current_agent == "Executor"] <- 0.46
df$reuse_ratio[df$previous_agent == "Executor" & df$current_agent == "Expresser"] <- 0.74
df$reuse_ratio[df$previous_agent == "Expresser" & df$current_agent == "Reviewer"] <- 0.61
df$reuse_ratio[df$previous_agent == "Reviewer" & df$current_agent == "Planner"] <- 0.82

df$label <- ifelse(is.na(df$reuse_ratio), "N/A", paste0(round(df$reuse_ratio * 100), "%"))
df$label_color <- ifelse(!is.na(df$reuse_ratio) & df$reuse_ratio >= 0.65, "white", "black")
df$label_face <- ifelse(!is.na(df$reuse_ratio) & df$reuse_ratio >= 0.70, "bold", "plain")
df$highlight <- df$previous_agent == "Executor" & df$current_agent == "Expresser" |
                df$previous_agent == "Reviewer" & df$current_agent == "Planner"

p <- ggplot(df, aes(x = current_agent, y = previous_agent)) +
  geom_tile(aes(fill = reuse_ratio), color = "white", linewidth = 0.5) +
  geom_text(aes(label = label, color = label_color, fontface = label_face), size = 3.0) +
  geom_tile(data = df %>% filter(highlight), fill = NA, color = "black", linewidth = 0.7) +
  scale_fill_gradient(
    low = "grey90",
    high = "grey20",
    limits = c(0, 1),
    na.value = "grey93",
    name = "Cache reuse\nratio",
    labels = function(x) paste0(x * 100, "%")
  ) +
  scale_color_identity() +
  labs(
    title = "Figure 3. Transition-level cache reuse matrix",
    x = "Current agent",
    y = "Previous agent"
  ) +
  theme_classic(base_size = 10) +
  theme(
    plot.title = element_text(size = 11, hjust = 0.5),
    axis.text.x = element_text(angle = 25, hjust = 1),
    axis.line = element_blank(),
    axis.ticks = element_blank(),
    legend.title = element_text(size = 9),
    legend.text = element_text(size = 8)
  ) +
  coord_fixed()

ggsave("figure3_transition_cache_reuse_matrix_R.png", p, width = 3.8, height = 3.1, dpi = 300)
ggsave("figure3_transition_cache_reuse_matrix_R.svg", p, width = 3.8, height = 3.1)
write.csv(df, "figure3_fake_matrix_R.csv", row.names = FALSE)
