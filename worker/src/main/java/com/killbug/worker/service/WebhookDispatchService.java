package com.killbug.worker.service;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class WebhookDispatchService {

    private final IssueProcessorService issueProcessor;
    private final Set<String> processing = ConcurrentHashMap.newKeySet();

    public Map<String, Object> healthStatus() {
        return Map.of("ok", true, "processing", processing.toArray());
    }

    public void dispatch(JsonNode payload) {
        String action = payload.path("action").asText();
        String type = payload.path("type").asText();
        JsonNode data = payload.path("data");

        if (!"Issue".equals(type)) return;
        if (!"create".equals(action) && !"update".equals(action)) return;
        if (!data.path("description").asText("").contains("made_by: @KillBug")) return;
        if ("update".equals(action) && !payload.path("updatedFrom").has("assigneeId")) return;

        String issueId = data.path("id").asText();
        String identifier = data.path("identifier").asText();

        if (!processing.add(issueId)) {
            log.info("[worker] {} 이미 처리 중 — 스킵", identifier);
            return;
        }

        log.info("[worker] {} 작업 시작", identifier);
        issueProcessor.process(data, () -> processing.remove(issueId));
    }
}
