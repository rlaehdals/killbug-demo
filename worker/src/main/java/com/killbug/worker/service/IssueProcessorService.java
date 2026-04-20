package com.killbug.worker.service;

import java.io.File;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.worker.config.RepoRoute;
import com.killbug.worker.config.WorkerProperties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class IssueProcessorService {

    private static final Pattern SLACK_CHANNEL_PATTERN = Pattern.compile("slack_channel:\\s*(\\S+)");
    private static final Pattern SLACK_THREAD_PATTERN = Pattern.compile("slack_thread_ts:\\s*(\\S+)");

    private final WorkerProperties properties;
    private final LinearClient linearClient;
    private final SlackClient slackClient;
    private final GitService gitService;
    private final ClaudeCodeRunner claudeCode;
    private final GithubService githubService;

    @Async("workerExecutor")
    public void process(JsonNode issue, Runnable cleanup) {
        String identifier = issue.path("identifier").asText();
        String issueId = issue.path("id").asText();

        try {
            doProcess(issue);
        } catch (Exception e) {
            log.error("[worker] {} 처리 실패", identifier, e);
            linearClient.postComment(issueId,
                    "❌ Worker 에러가 발생했습니다:\n```\n%s\n```".formatted(e.getMessage()));
        } finally {
            cleanup.run();
            log.info("[worker] {} 처리 완료", identifier);
        }
    }

    private void doProcess(JsonNode issue) {
        String identifier = issue.path("identifier").asText();
        String issueId = issue.path("id").asText();
        String title = issue.path("title").asText();
        String description = issue.path("description").asText("");
        int priority = issue.path("priority").asInt(3);

        String teamKey = identifier.split("-")[0];
        RepoRoute route = properties.getRouting().get(teamKey);
        if (route == null) {
            linearClient.postComment(issueId,
                    "⚠️ 팀 키 `%s`에 대한 레포 라우팅이 설정되지 않았습니다.".formatted(teamKey));
            return;
        }

        Path basePath = Path.of(properties.getReposBaseDir()).toAbsolutePath();
        File repoDir = basePath.resolve(route.getLocalPath()).toFile();
        File worktreeDir = basePath.resolve(".worktree-" + identifier).toFile();
        String branchName = "fix/" + identifier;

        if (!repoDir.exists()) {
            linearClient.postComment(issueId,
                    "⚠️ 레포 디렉토리가 없습니다: `%s`\n`git clone`으로 먼저 클론해주세요.".formatted(repoDir));
            return;
        }

        gitService.createWorktree(repoDir, branchName, worktreeDir, route.getBaseBranch());

        try {
            String prompt = claudeCode.buildPrompt(title, identifier, priority, description);
            log.info("[worker] {} Claude Code 실행 중...", identifier);

            ClaudeCodeRunner.Result result = claudeCode.run(worktreeDir, prompt);
            double confidence = result.confidence();
            double threshold = properties.getClaude().getConfidenceThreshold();

            log.info("[worker] {} confidence: {}", identifier, confidence);

            if (confidence >= threshold) {
                handleHighConfidence(worktreeDir, issue, route, branchName, result);
            } else {
                handleLowConfidence(issue, result, threshold);
            }
        } finally {
            gitService.removeWorktree(repoDir, worktreeDir);
        }
    }

    private void handleHighConfidence(File worktreeDir, JsonNode issue,
                                       RepoRoute route, String branchName,
                                       ClaudeCodeRunner.Result result) {
        String issueId = issue.path("id").asText();
        String identifier = issue.path("identifier").asText();
        String title = issue.path("title").asText();
        String description = issue.path("description").asText("");

        gitService.exec(worktreeDir, "add", "-A");

        if (!gitService.hasChanges(worktreeDir)) {
            log.warn("[worker] {} confidence {} 이지만 코드 변경 없음", identifier, result.confidence());
            linearClient.postComment(issueId,
                    "ℹ️ 분석 완료했으나 코드 변경이 필요하지 않습니다.\n\nConfidence: %s\n\n%s"
                            .formatted(result.confidence(), result.truncated(2000)));
            notifySlack(description, "📋 *%s* 분석 완료 (변경 없음)\nConfidence: %s\n\n%s"
                    .formatted(identifier, result.confidence(), result.truncated(500)));
            return;
        }

        String commitMsg = "fix: %s (%s)".formatted(title, identifier);
        gitService.exec(worktreeDir, "commit", "-m", commitMsg);
        gitService.exec(worktreeDir, "push", "-u", "origin", branchName);

        String issueUrl = issue.path("url").asText("");
        String prTitle = "fix: %s (%s)".formatted(title, identifier);
        String prBody = """
                ## Linear Issue

                [%s](%s)

                ## Summary

                **Confidence:** %s | **Priority:** P%d

                %s

                ---
                🤖 Auto-generated by KillBug Worker""".formatted(
                identifier, issueUrl, result.confidence(),
                issue.path("priority").asInt(3), title);

        String prUrl = githubService.createDraftPr(
                worktreeDir, prTitle, prBody, route.getBaseBranch(), branchName);

        linearClient.postComment(issueId,
                "✅ Draft PR이 생성되었습니다!\n\n🔗 %s\n📊 Confidence: %s\n\n### 분석 요약\n%s"
                        .formatted(prUrl, result.confidence(), result.truncated(2000)));

        notifySlack(description, "✅ *%s* Draft PR이 생성되었습니다!\n🔗 %s\n📊 Confidence: %s"
                .formatted(identifier, prUrl, result.confidence()));

        log.info("[worker] {} PR 생성 완료: {}", identifier, prUrl);
    }

    private void handleLowConfidence(JsonNode issue, ClaudeCodeRunner.Result result, double threshold) {
        String issueId = issue.path("id").asText();
        String identifier = issue.path("identifier").asText();
        String description = issue.path("description").asText("");

        linearClient.postComment(issueId,
                "📋 분석 완료 (Confidence: %s — 임계값 %s 미만)\n\nPR을 생성하지 않고 분석 결과만 보고합니다.\n\n%s"
                        .formatted(result.confidence(), threshold, result.truncated(3000)));

        notifySlack(description, "📋 *%s* 분석 완료 (Confidence: %s — 임계값 %s 미만)\nPR 미생성, Linear 티켓에서 분석 결과를 확인하세요."
                .formatted(identifier, result.confidence(), threshold));

        log.info("[worker] {} 분석만 보고 (confidence {} < {})", identifier, result.confidence(), threshold);
    }

    private void notifySlack(String description, String message) {
        String channel = extractMeta(description, SLACK_CHANNEL_PATTERN);
        String threadTs = extractMeta(description, SLACK_THREAD_PATTERN);

        if (channel == null || threadTs == null) {
            log.warn("[worker] Slack 메타데이터 없음 — 알림 생략");
            return;
        }

        try {
            slackClient.postMessage(channel, threadTs, message);
        } catch (Exception e) {
            log.warn("[worker] Slack 알림 실패: {}", e.getMessage());
        }
    }

    private String extractMeta(String description, Pattern pattern) {
        Matcher m = pattern.matcher(description);
        return m.find() ? m.group(1) : null;
    }
}
