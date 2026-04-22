package com.killbug.worker.service;

import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import com.killbug.worker.config.WorkerProperties;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class SlackClient {

    private final WorkerProperties properties;
    private RestClient restClient;

    @PostConstruct
    void init() {
        restClient = RestClient.builder()
                .baseUrl(properties.getSlack().getApiUrl())
                .defaultHeader(
                        "Authorization", "Bearer " + properties.getSlack().getBotToken())
                .defaultHeader("Content-Type", "application/json; charset=utf-8")
                .build();
    }

    public void postMessage(String channel, String threadTs, String text) {
        restClient
                .post()
                .uri("/chat.postMessage")
                .body(Map.of("channel", channel, "thread_ts", threadTs, "text", text))
                .retrieve()
                .toBodilessEntity();
        log.debug("[slack] postMessage: channel={}, threadTs={}", channel, threadTs);
    }
}
