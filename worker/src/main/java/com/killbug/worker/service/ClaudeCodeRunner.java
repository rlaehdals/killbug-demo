package com.killbug.worker.service;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.stereotype.Service;

import com.killbug.worker.config.WorkerProperties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class ClaudeCodeRunner {

    private static final Pattern CONFIDENCE_PATTERN = Pattern.compile("\\[CONFIDENCE:\\s*([\\d.]+)]");

    private final WorkerProperties properties;

    public Result run(File cwd, String prompt) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "claude",
                    "--print",
                    "--dangerously-skip-permissions",
                    "--max-turns",
                    String.valueOf(properties.getClaude().getMaxTurns()),
                    prompt);
            pb.directory(cwd);
            pb.environment().put("CLAUDE_CODE_HEADLESS", "1");
            pb.redirectInput(ProcessBuilder.Redirect.from(new File("/dev/null")));

            Process process = pb.start();

            Thread stderrReader = Thread.ofVirtual().start(() -> {
                try {
                    String err = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
                    if (!err.isBlank()) {
                        log.warn("[claude] stderr: {}", err.trim());
                    }
                } catch (Exception ignored) {
                }
            });

            boolean finished = process.waitFor(properties.getClaude().getTimeoutSeconds(), TimeUnit.SECONDS);

            String output;
            if (!finished) {
                process.destroyForcibly();
                output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                log.warn("[claude] 타임아웃 ({}초)", properties.getClaude().getTimeoutSeconds());
            } else {
                output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            }
            stderrReader.join(5000);

            return new Result(output, extractConfidence(output));
        } catch (Exception e) {
            throw new RuntimeException("Claude Code 실행 실패", e);
        }
    }

    public String buildPrompt(String title, String identifier, int priority, String description) {
        String cleanDesc = description.replaceAll("(?s)<details>.*?</details>", "");

        return properties
                .getClaude()
                .getFixPromptTemplate()
                .replace("{title}", title)
                .replace("{identifier}", identifier)
                .replace("{priority}", String.valueOf(priority))
                .replace("{description}", cleanDesc);
    }

    private double extractConfidence(String output) {
        Matcher matcher = CONFIDENCE_PATTERN.matcher(output);
        return matcher.find() ? Double.parseDouble(matcher.group(1)) : 0.0;
    }

    public record Result(String output, double confidence) {
        public String truncated(int max) {
            if (output.length() <= max) return output;
            return output.substring(0, max) + "\n\n... (truncated)";
        }
    }
}
