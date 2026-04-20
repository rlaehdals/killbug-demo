package com.killbug.worker.service;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

import org.springframework.stereotype.Service;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class GitService {

    public String exec(File cwd, String... args) {
        try {
            String[] cmd = new String[args.length + 1];
            cmd[0] = "git";
            System.arraycopy(args, 0, cmd, 1, args.length);

            Process process = new ProcessBuilder(cmd)
                    .directory(cwd)
                    .redirectErrorStream(true)
                    .start();

            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
            int exitCode = process.waitFor();

            if (exitCode != 0) {
                throw new RuntimeException("git %s failed (exit %d): %s".formatted(
                        Arrays.toString(args), exitCode, output));
            }

            return output;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("git 실행 실패: " + Arrays.toString(args), e);
        }
    }

    public boolean hasChanges(File cwd) {
        return !exec(cwd, "status", "--porcelain").isEmpty();
    }

    public void createWorktree(File repoDir, String branchName, File worktreeDir, String baseBranch) {
        exec(repoDir, "fetch", "origin", baseBranch);
        exec(repoDir, "worktree", "add", "-b", branchName,
                worktreeDir.getAbsolutePath(), "origin/" + baseBranch);
    }

    public void removeWorktree(File repoDir, File worktreeDir) {
        try {
            exec(repoDir, "worktree", "remove", "--force", worktreeDir.getAbsolutePath());
        } catch (Exception e) {
            log.warn("[git] worktree 정리 실패: {}", worktreeDir, e);
        }
    }
}
