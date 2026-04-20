package com.killbug.webhook.config;

import java.util.ArrayList;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@ConfigurationProperties(prefix = "killbug")
public class KillbugProperties {

    private List<Feature> features = new ArrayList<>();
    private SlackProperties slack = new SlackProperties();
    private LinearProperties linear = new LinearProperties();
    private WorkerProperties worker = new WorkerProperties();
    private ClaudeCodeProperties claudeCode = new ClaudeCodeProperties();
    private AsyncProperties async = new AsyncProperties();

    public Feature findByTeamKey(String teamKey) {
        return features.stream()
                .filter(f -> f.getLinearTeamKey().equalsIgnoreCase(teamKey))
                .findFirst()
                .orElse(null);
    }

    public List<String> validTeamKeys() {
        return features.stream()
                .map(Feature::getLinearTeamKey)
                .toList();
    }
}
