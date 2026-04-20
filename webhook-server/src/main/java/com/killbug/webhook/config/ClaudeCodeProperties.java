package com.killbug.webhook.config;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class ClaudeCodeProperties {
    private int maxTurns;
    private int timeoutSeconds;
    private String analyzePromptTemplate;
}
