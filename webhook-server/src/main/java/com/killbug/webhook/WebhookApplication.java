package com.killbug.webhook;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableAsync;

import com.killbug.webhook.config.KillbugProperties;

@SpringBootApplication
@EnableAsync
@EnableConfigurationProperties(KillbugProperties.class)
public class WebhookApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebhookApplication.class, args);
    }
}
