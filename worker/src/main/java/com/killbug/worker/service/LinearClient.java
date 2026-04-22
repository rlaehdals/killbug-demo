package com.killbug.worker.service;

import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.worker.config.WorkerProperties;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class LinearClient {

    private final WorkerProperties properties;
    private RestClient restClient;

    @PostConstruct
    void init() {
        restClient = RestClient.builder()
                .baseUrl(properties.getLinear().getApiUrl())
                .defaultHeader("Authorization", properties.getLinear().getApiKey())
                .defaultHeader("Content-Type", "application/json")
                .build();
    }

    public void postComment(String issueId, String body) {
        String query =
                """
                mutation($input: CommentCreateInput!) {
                    commentCreate(input: $input) { success }
                }
                """;

        restClient
                .post()
                .body(Map.of("query", query, "variables", Map.of("input", Map.of("issueId", issueId, "body", body))))
                .retrieve()
                .body(JsonNode.class);

        log.debug("[linear] 코멘트 작성: issueId={}", issueId);
    }
}
