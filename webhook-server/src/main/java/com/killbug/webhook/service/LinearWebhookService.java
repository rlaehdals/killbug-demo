package com.killbug.webhook.service;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.killbug.webhook.config.KillbugProperties;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.client.RestClient;

@Slf4j
@Service
@RequiredArgsConstructor
public class LinearWebhookService {

    private static final Pattern META_PATTERN_CHANNEL =
            Pattern.compile("slack_channel:\\s*(\\S+)");
    private static final Pattern META_PATTERN_THREAD =
            Pattern.compile("slack_thread_ts:\\s*(\\S+)");

    private final SlackClient slackClient;
    private final KillbugProperties properties;


    public void handle(JsonNode payload) {
        String action = payload.path("action").asText();
        String type = payload.path("type").asText();

        if (!"create".equals(action) || !"Comment".equals(type)) {
            return;
        }

        JsonNode data = payload.path("data");
        JsonNode issue = data.path("issue");
        String description = issue.path("description").asText("");

        if (!description.contains("made_by: @KillBug")) {
            return;
        }

        String channel = extractMeta(META_PATTERN_CHANNEL, description);
        String threadTs = extractMeta(META_PATTERN_THREAD, description);

        if (channel == null || threadTs == null) {
            log.warn("[linear] Slack 메타데이터 누락: {}", issue.path("identifier").asText());
            return;
        }

        String issueId = issue.path("identifier").asText();
        String commentBody = data.path("body").asText("");

        slackClient.postMessage(channel, threadTs,
                "\uD83E\uDD16 *%s* 작업 결과:\n\n%s".formatted(issueId, commentBody));

        log.info("[linear] → Slack 회신: {} → {}/{}", issueId, channel, threadTs);

        if ("Issue".equals(payload.path("type").asText())) {
            forwardToWorker(payload);
        }
    }

    private void forwardToWorker(JsonNode payload) {
        String workerUrl = properties.getWorker().getUrl();
        try {
            RestClient.create().post()
                    .uri(workerUrl + "/linear/webhook")
                    .header("Content-Type", "application/json")
                    .body(payload)
                    .retrieve()
                    .toBodilessEntity();
            log.info("[forward] Issue → worker: {}", payload.path("data").path("identifier").asText());
        } catch (Exception e) {
            log.error("[forward] worker 전달 실패 ({}): {}", workerUrl, e.getMessage());
        }
    }

    private String extractMeta(Pattern pattern, String description) {
        Matcher matcher = pattern.matcher(description);
        return matcher.find() ? matcher.group(1) : null;
    }
}
