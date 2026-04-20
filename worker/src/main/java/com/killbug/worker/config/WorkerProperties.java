package com.killbug.worker.config;

import java.util.HashMap;
import java.util.Map;

import org.springframework.boot.context.properties.ConfigurationProperties;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@ConfigurationProperties(prefix = "worker")
public class WorkerProperties {

    private String reposBaseDir;
    private Map<String, RepoRoute> routing = new HashMap<>();
    private ClaudeProperties claude = new ClaudeProperties();
    private PrProperties pr = new PrProperties();
    private LinearProperties linear = new LinearProperties();
    private SlackProperties slack = new SlackProperties();
    private GithubProperties github = new GithubProperties();
    private AsyncProperties async = new AsyncProperties();
}
