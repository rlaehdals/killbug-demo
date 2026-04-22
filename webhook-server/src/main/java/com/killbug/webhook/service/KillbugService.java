package com.killbug.webhook.service;

import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.webhook.config.Feature;
import com.killbug.webhook.config.KillbugProperties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class KillbugService {

    private final KillbugProperties properties;
    private final SlackClient slackClient;
    private final LinearClient linearClient;
    private final ClaudeCodeRunner claudeCodeRunner;

    @Async("webhookExecutor")
    public void process(
            String channel, String threadTs, String teamKey, String alertId, String memo, String slackUserId) {
        try {
            doProcess(channel, threadTs, teamKey, memo, slackUserId);
        } catch (Exception e) {
            log.error("[killbug] 처리 실패: channel={}, alertId={}", channel, alertId, e);
            slackClient.postMessage(channel, threadTs, "❌ 티켓 생성 중 에러가 발생했습니다: " + e.getMessage());
        }
    }

    @Async("webhookExecutor")
    public void processFromCommand(
            String channel, String teamKey, String alertId, String memo, String responseUrl, String slackUserId) {
        try {
            Feature feature = properties.findByTeamKey(teamKey);
            if (feature == null) {
                String validKeys = String.join(", ", properties.validTeamKeys());
                slackClient.respondToUrl(
                        responseUrl, "❌ `%s`는 유효하지 않은 팀 키입니다.\n사용 가능한 팀: %s".formatted(teamKey, validKeys));
                return;
            }

            String threadTs = slackClient.findBugThread(channel, alertId);
            if (threadTs == null) {
                slackClient.respondToUrl(responseUrl, "❌ 알림 ID `%s`에 해당하는 에러 스레드를 찾을 수 없습니다.".formatted(alertId));
                return;
            }

            doProcess(channel, threadTs, teamKey, memo, slackUserId);
        } catch (Exception e) {
            log.error("[killbug] 커맨드 처리 실패: channel={}, alertId={}", channel, alertId, e);
            slackClient.respondToUrl(responseUrl, "❌ 처리 중 에러가 발생했습니다: " + e.getMessage());
        }
    }

    private void doProcess(String channel, String threadTs, String teamKey, String memo, String slackUserId) {
        Feature feature = properties.findByTeamKey(teamKey);
        if (feature == null) {
            String validKeys = String.join(", ", properties.validTeamKeys());
            slackClient.postMessage(
                    channel,
                    threadTs,
                    "❌ `%s`는 유효하지 않은 팀 키입니다.\n사용 가능한 팀: %s\n사용법: `/killbug PAY`".formatted(teamKey, validKeys));
            return;
        }

        JsonNode existing = linearClient.findExistingTicket(threadTs);
        if (existing != null) {
            slackClient.postMessage(
                    channel,
                    threadTs,
                    "⚠️ 이 스레드에 이미 티켓이 있습니다: <%s|%s>"
                            .formatted(
                                    existing.path("url").asText(),
                                    existing.path("identifier").asText()));
            return;
        }

        slackClient.postMessage(channel, threadTs, "🔄 스레드를 분석하고 Linear 티켓을 생성 중입니다...");

        String threadText = slackClient.getThreadMessages(channel, threadTs);
        JsonNode analysis = analyzeThread(threadText, feature, memo);

        String title = analysis.path("title").asText("버그 리포트");
        String description = analysis.path("description").asText("");
        String resolution = analysis.path("resolution").asText("");
        int priority = analysis.path("priority").asInt(3);

        String fullDescription = buildDescription(description, resolution, channel, threadTs, feature.getRepository());
        String linearUserId = properties.getLinear().getUserMappings().get(slackUserId);

        JsonNode ticket =
                linearClient.createIssue(feature.getLinearTeamKey(), title, fullDescription, priority, linearUserId);

        slackClient.postMessage(
                channel,
                threadTs,
                """
                ✅ Linear 티켓이 생성되었습니다!
                📋 <%s|%s: %s>
                우선순위: P%d
                🤖 자동 분석이 시작됩니다. 완료되면 이 스레드에 결과를 알려드립니다."""
                        .formatted(
                                ticket.path("url").asText(),
                                ticket.path("identifier").asText(),
                                ticket.path("title").asText(),
                                priority));

        slackClient.addReaction(channel, threadTs, "white_check_mark");
        log.info(
                "[killbug] 티켓 생성 완료: {} (thread: {})", ticket.path("identifier").asText(), threadTs);
    }

    private JsonNode analyzeThread(String threadText, Feature feature, String memo) {
        String prompt = properties
                .getClaudeCode()
                .getAnalyzePromptTemplate()
                .replace("{threadText}", threadText)
                .replace("{memo}", memo.isBlank() ? "" : "## 추가 메모\n" + memo)
                .replace("{featureName}", feature.getName())
                .replace("{repository}", feature.getRepository());

        return claudeCodeRunner.chat(prompt);
    }

    private String buildDescription(
            String description, String resolution, String channel, String threadTs, String repository) {
        return """
                %s

                ---
                ### 수정 방향
                %s

                ---
                <details>
                <summary>메타데이터 (자동 생성)</summary>

                - slack_channel: %s
                - slack_thread_ts: %s
                - repository: %s
                - made_by: @KillBug
                </details>"""
                .formatted(description, resolution, channel, threadTs, repository);
    }
}
