package com.killbug.webhook.service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
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
public class LinearClient {

    private final KillbugProperties properties;
    private RestClient restClient;

    @PostConstruct
    void init() {
        restClient = RestClient.builder()
                .baseUrl(properties.getLinear().getApiUrl())
                .defaultHeader("Authorization", properties.getLinear().getApiKey())
                .defaultHeader("Content-Type", "application/json")
                .build();
    }

    public JsonNode createIssue(String teamKey, String title, String description, int priority, String assigneeId) {
        String teamId = properties.getLinear().getTeamIds().get(teamKey);
        if (teamId == null || "REPLACE_ME".equals(teamId)) {
            throw new IllegalStateException(
                    "Linear team ID 미설정: %s — application.yml killbug.linear.team-ids 확인 필요".formatted(teamKey));
        }

        Map<String, Object> input = new HashMap<>(Map.of(
                "teamId", teamId,
                "title", title,
                "description", description,
                "priority", priority
        ));

        if (assigneeId != null) {
            input.put("assigneeId", assigneeId);
        }

        List<String> labelIds = new ArrayList<>();
        properties.getLinear().getLabelIds().forEach((key, val) -> {
            if (val != null && !"REPLACE_ME".equals(val)) labelIds.add(val);
        });
        if (!labelIds.isEmpty()) {
            input.put("labelIds", labelIds);
        }

        String query = """
                mutation CreateIssue($input: IssueCreateInput!) {
                    issueCreate(input: $input) {
                        success
                        issue { id identifier url title }
                    }
                }
                """;

        JsonNode result = graphql(query, Map.of("input", input));
        JsonNode issue = result.path("data").path("issueCreate").path("issue");

        if (issue.isMissingNode()) {
            throw new RuntimeException("Linear 이슈 생성 실패: " + result);
        }

        return issue;
    }

    public JsonNode findExistingTicket(String slackThreadTs) {
        String query = """
                query($term: String!) {
                    issueSearch(query: $term, filter: {
                        state: { type: { nin: ["completed", "canceled"] } }
                    }) {
                        nodes { id identifier url }
                    }
                }
                """;

        JsonNode result = graphql(query, Map.of("term", slackThreadTs));
        JsonNode nodes = result.path("data").path("issueSearch").path("nodes");

        if (nodes.isArray() && !nodes.isEmpty()) {
            return nodes.get(0);
        }
        return null;
    }

    private JsonNode graphql(String query, Map<String, Object> variables) {
        return restClient.post()
                .body(Map.of("query", query, "variables", variables))
                .retrieve()
                .body(JsonNode.class);
    }
}
