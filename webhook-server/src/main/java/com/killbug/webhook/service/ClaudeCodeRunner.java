package com.killbug.webhook.service;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.killbug.webhook.config.KillbugProperties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class ClaudeCodeRunner {

    private final KillbugProperties properties;
    private final ObjectMapper objectMapper;

    public JsonNode chat(String prompt) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "claude",
                    "--print",
                    "--output-format", "json",
                    "--max-turns", String.valueOf(properties.getClaudeCode().getMaxTurns()),
                    prompt
            );
            pb.environment().put("CLAUDE_CODE_HEADLESS", "1");
            pb.redirectInput(ProcessBuilder.Redirect.from(new java.io.File("/dev/null")));

            Process process = pb.start();

            Thread stderrReader = Thread.ofVirtual().start(() -> {
                try {
                    String err = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
                    if (!err.isBlank()) {
                        log.warn("[claude] stderr: {}", err.trim());
                    }
                } catch (Exception ignored) {}
            });

            boolean finished = process.waitFor(
                    properties.getClaudeCode().getTimeoutSeconds(), TimeUnit.SECONDS);

            String output;
            if (!finished) {
                process.destroyForcibly();
                output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                log.warn("[claude] 타임아웃 ({}초)", properties.getClaudeCode().getTimeoutSeconds());
            } else {
                output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            }
            stderrReader.join(5000);

            JsonNode cliResponse = objectMapper.readTree(output.trim());
            String content = cliResponse.path("result").asText("");

            return extractJson(content);
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Claude Code 실행 실패", e);
        }
    }

    private JsonNode extractJson(String content) {
        var blockMatcher = Pattern.compile("```json\\s*([\\s\\S]*?)```").matcher(content);
        if (blockMatcher.find()) {
            JsonNode result = tryParseJson(blockMatcher.group(1).trim());
            if (result != null) return result;
        }

        int first = content.indexOf('{');
        int last = content.lastIndexOf('}');
        if (first >= 0 && last > first) {
            JsonNode result = tryParseJson(content.substring(first, last + 1));
            if (result != null) return result;
        }

        log.warn("[claude] JSON 파싱 실패, regex fallback");
        return extractByRegex(content);
    }

    private JsonNode tryParseJson(String json) {
        try {
            return objectMapper.readTree(json);
        } catch (Exception e) {
            log.debug("[claude] JSON 파싱 실패: {}", e.getMessage());
            return null;
        }
    }

    private JsonNode extractByRegex(String content) {
        ObjectNode node = objectMapper.createObjectNode();
        node.put("title", extractField(content, "title", "버그 리포트"));
        node.put("description", extractField(content, "description", ""));
        node.put("resolution", extractField(content, "resolution", ""));
        node.put("priority", extractPriority(content));
        return node;
    }

    private String extractField(String content, String fieldName, String defaultValue) {
        Matcher m = Pattern.compile("\"" + fieldName + "\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
                .matcher(content);
        if (m.find()) {
            return m.group(1).replace("\\n", "\n").replace("\\\"", "\"");
        }
        return defaultValue;
    }

    private int extractPriority(String content) {
        Matcher m = Pattern.compile("\"priority\"\\s*:\\s*(\\d)").matcher(content);
        if (m.find()) {
            return Integer.parseInt(m.group(1));
        }
        return 3;
    }
}
