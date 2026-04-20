package com.killbug.webhook.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.killbug.webhook.service.SlackEventService;

import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
public class SlackController {

    private final ObjectMapper objectMapper;
    private final SlackEventService slackEventService;

    @PostMapping("/slack/events")
    public Map<String, Object> handleSlackEvent(
            @RequestBody String rawBody,
            @RequestHeader(value = "X-Slack-Request-Timestamp", required = false) String timestamp,
            @RequestHeader(value = "X-Slack-Signature", required = false) String signature
    ) throws Exception {
        JsonNode body = objectMapper.readTree(rawBody);

        if ("url_verification".equals(body.path("type").asText())) {
            return Map.of("challenge", body.path("challenge").asText());
        }

        slackEventService.handleEvent(body, rawBody, timestamp, signature);

        return Map.of("ok", true);
    }
}
