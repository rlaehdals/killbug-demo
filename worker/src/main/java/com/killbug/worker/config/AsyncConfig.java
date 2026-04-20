package com.killbug.worker.config;

import java.util.concurrent.Executor;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import lombok.RequiredArgsConstructor;

@Configuration
@RequiredArgsConstructor
public class AsyncConfig {

    private final WorkerProperties properties;

    @Bean("workerExecutor")
    public Executor workerExecutor() {
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
