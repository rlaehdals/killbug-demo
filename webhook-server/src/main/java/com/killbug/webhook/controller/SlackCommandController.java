package com.killbug.webhook.controller;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import com.killbug.webhook.service.KillbugService;
import com.killbug.webhook.service.SlackEventService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@RestController
@RequiredArgsConstructor
public class SlackCommandController {

    private final SlackEventService slackEventService;
    private final KillbugService killbugService;

    @PostMapping(value = "/slack/commands", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public Map<String, String> handleCommand(
            @RequestBody String rawBody,
            @RequestHeader(value = "X-Slack-Request-Timestamp", required = false) String timestamp,
            @RequestHeader(value = "X-Slack-Signature", required = false) String signature
    ) {
        if (!slackEventService.verifySignature(rawBody, timestamp, signature)) {
            return Map.of("text", "서명 검증 실패");
        }

        Map<String, String> params = parseFormUrlEncoded(rawBody);
        String command = params.getOrDefault("command", "");
        String text = params.getOrDefault("text", "").trim();
        String channelId = params.getOrDefault("channel_id", "");
        String userId = params.getOrDefault("user_id", "");
        String responseUrl = params.getOrDefault("response_url", "");

        if (!"/killbug".equals(command) || text.isBlank()) {
            return Map.of("text", "사용법: `/killbug MAIN a1b2c3d4` 또는 `/killbug MAIN a1b2c3d4 메모`");
        }

        String[] parts = text.split("\\s+", 3);
        if (parts.length < 2) {
            return Map.of("text", "사용법: `/killbug MAIN a1b2c3d4`\n알림 메시지의 ID를 포함해주세요.");
        }

        String teamKey = parts[0].toUpperCase();
        String alertId = parts[1].toLowerCase();
        String memo = parts.length > 2 ? parts[2] : "";

        log.info("[slash] /killbug {} {} (channel={}, user={})", teamKey, alertId, channelId, userId);
        killbugService.processFromCommand(channelId, teamKey, alertId, memo, responseUrl, userId);

        return Map.of(
                "response_type", "ephemeral",
                "text", "🔄 알림 `%s`를 처리 중입니다...".formatted(alertId)
        );
    }

    private Map<String, String> parseFormUrlEncoded(String body) {
        return Arrays.stream(body.split("&"))
                .map(pair -> pair.split("=", 2))
                .collect(Collectors.toMap(
                        p -> URLDecoder.decode(p[0], StandardCharsets.UTF_8),
                        p -> p.length > 1 ? URLDecoder.decode(p[1], StandardCharsets.UTF_8) : "",
                        (a, b) -> b
                ));
    }
}
