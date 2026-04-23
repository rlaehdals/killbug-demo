package com.killbug.webhook.service;

import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.webhook.config.KillbugProperties;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class SlackClient {

    private final KillbugProperties properties;
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

    public String findBugThread(String channel, String alertId) {
        JsonNode result = restClient
                .get()
                .uri(uri -> uri.path("/conversations.history")
                        .queryParam("channel", channel)
                        .queryParam("limit", 50)
                        .build())
                .retrieve()
                .body(JsonNode.class);

        if (result == null || !result.path("ok").asBoolean(false)) {
            log.warn("[slack] conversations.history 실패: {}", result);
            return null;
        }

        for (JsonNode msg : result.path("messages")) {
            if (msg.path("text").asText("").contains(alertId)) {
                log.info(
                        "[slack] alertId={} 스레드 발견: ts={}",
                        alertId,
                        msg.path("ts").asText());
                return msg.path("ts").asText();
            }
        }
        log.warn(
                "[slack] alertId={} 미발견 (검색 {}건)",
                alertId,
                result.path("messages").size());
        return null;
    }

    public void addReaction(String channel, String timestamp, String emoji) {
        restClient
                .post()
                .uri("/reactions.add")
                .body(Map.of("channel", channel, "timestamp", timestamp, "name", emoji))
                .retrieve()
                .toBodilessEntity();
    }

    public void respondToUrl(String responseUrl, String text) {
        RestClient.create()
                .post()
                .uri(responseUrl)
                .header("Content-Type", "application/json")
                .body(Map.of("text", text, "response_type", "ephemeral"))
                .retrieve()
                .toBodilessEntity();
    }

    public String getThreadMessages(String channel, String threadTs) {
        JsonNode result = restClient
                .get()
                .uri(uri -> uri.path("/conversations.replies")
                        .queryParam("channel", channel)
                        .queryParam("ts", threadTs)
                        .queryParam("limit", 100)
                        .build())
                .retrieve()
                .body(JsonNode.class);

        if (result == null || !result.has("messages")) return "";

        StringBuilder sb = new StringBuilder();
        for (JsonNode msg : result.path("messages")) {
            String user = msg.has("user") ? msg.path("user").asText() : "bot";
            sb.append("[")
                    .append(user)
                    .append("] ")
                    .append(msg.path("text").asText(""))
                    .append("\n");
        }
        return sb.toString();
    }
}
