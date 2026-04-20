package com.killbug.webhook.service;

import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.webhook.config.KillbugProperties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class SlackEventService {

    private static final Pattern KILLBUG_PATTERN =
            Pattern.compile("^/?killbug\\s+(\\w+)\\s+([a-f0-9]{8})(?:\\s+(.*))?$", Pattern.CASE_INSENSITIVE);

    private final KillbugProperties properties;
    private final KillbugService killbugService;

    public void handleEvent(JsonNode body, String rawBody, String timestamp, String signature) {
        if (!verifySignature(rawBody, timestamp, signature)) {
            log.warn("[slack] 서명 검증 실패");
            return;
        }

        JsonNode event = body.path("event");
        if (event.isMissingNode() || !"message".equals(event.path("type").asText())) {
            return;
        }

        if (event.has("bot_id") || event.has("subtype")) {
            return;
        }

        Matcher matcher = KILLBUG_PATTERN.matcher(event.path("text").asText(""));
        if (!matcher.matches()) {
            return;
        }

        String teamKey = matcher.group(1);
        String alertId = matcher.group(2);
        String memo = matcher.group(3) != null ? matcher.group(3) : "";
        String channel = event.path("channel").asText();
        String slackUserId = event.path("user").asText();
        String threadTs = event.has("thread_ts")
                ? event.path("thread_ts").asText()
                : event.path("ts").asText();

        killbugService.process(channel, threadTs, teamKey, alertId, memo, slackUserId);
    }

    public boolean verifySignature(String rawBody, String timestamp, String signature) {
        String secret = properties.getSlack().getSigningSecret();
        if (secret == null || secret.isBlank()) {
            log.warn("[slack] SLACK_SIGNING_SECRET 미설정 — 검증 스킵");
            return true;
        }
        if (timestamp == null || signature == null) return false;

        long now = System.currentTimeMillis() / 1000;
        if (Math.abs(now - Long.parseLong(timestamp)) > 300) return false;

        try {
            String sigBase = "v0:" + timestamp + ":" + rawBody;
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] hash = mac.doFinal(sigBase.getBytes(StandardCharsets.UTF_8));
            String mySig = "v0=" + bytesToHex(hash);
            return mySig.equals(signature);
        } catch (Exception e) {
            log.error("[slack] 서명 검증 에러", e);
            return false;
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
