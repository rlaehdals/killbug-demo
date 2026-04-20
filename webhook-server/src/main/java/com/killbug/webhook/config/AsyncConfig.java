package com.killbug.webhook.config;

import java.util.concurrent.Executor;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import lombok.RequiredArgsConstructor;

@Configuration
@RequiredArgsConstructor
public class AsyncConfig {

    private final KillbugProperties properties;

    @Bean("webhookExecutor")
    public Executor webhookExecutor() {
        AsyncProperties async = properties.getAsync();
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(async.getCorePoolSize());
        executor.setMaxPoolSize(async.getMaxPoolSize());
        executor.setQueueCapacity(async.getQueueCapacity());
        executor.setThreadNamePrefix(async.getThreadNamePrefix());
        executor.initialize();
        return executor;
    }
}
