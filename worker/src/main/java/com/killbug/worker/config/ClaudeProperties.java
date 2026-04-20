package com.killbug.worker.config;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class ClaudeProperties {
    private int maxTurns;
    private double confidenceThreshold;
    private int timeoutSeconds;
    private String fixPromptTemplate;
}
