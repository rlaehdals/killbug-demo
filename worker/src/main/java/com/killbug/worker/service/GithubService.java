package com.killbug.worker.service;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.List;

import org.springframework.stereotype.Service;

import com.killbug.worker.config.WorkerProperties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class GithubService {

    private final WorkerProperties properties;

    public String createDraftPr(File cwd, String title, String body, String baseBranch, String headBranch) {
        try {
            ProcessBuilder pb = new ProcessBuilder(List.of(
                    "gh",
                    "pr",
                    "create",
                    "--draft",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--base",
                    baseBranch,
                    "--head",
                    headBranch));
            pb.directory(cwd);
            pb.redirectErrorStream(true);

            String ghToken = properties.getGithub().getToken();
            if (ghToken != null && !ghToken.isBlank()) {
                pb.environment().put("GH_TOKEN", ghToken);
            }

            Process process = pb.start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
            int exitCode = process.waitFor();

            if (exitCode != 0) {
                throw new RuntimeException("gh pr create failed (exit %d): %s".formatted(exitCode, output));
            }

            return output;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("gh CLI 실행 실패", e);
        }
    }
}
