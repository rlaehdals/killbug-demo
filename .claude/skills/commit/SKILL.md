---
name: commit
description: Conventional Commits 기반 커밋 생성
effort: low
argument-hint: "[push]"
allowed-tools: Bash(git *) Read
---

# Commit Skill

변경사항을 분석하고 Conventional Commits 스펙에 따라 커밋한다.

**Arguments: $ARGUMENTS**

## Steps

1. `git status`, `git diff`, `git diff --staged`를 실행하여 모든 변경사항을 파악한다.
2. `${CLAUDE_SKILL_DIR}/conventional-commits-spec.md`를 읽어 Conventional Commits 스펙을 확인한다.
3. `git log --oneline -5`로 최근 커밋 스타일을 참고한다.
4. 변경사항을 분석하고 스펙에 맞는 커밋 메시지를 작성한다.
5. 관련 파일을 개별적으로 staging한다 (`git add -A`나 `git add .` 사용 금지). 시크릿 파일(.env, credentials 등)은 절대 staging하지 않는다.
6. HEREDOC으로 커밋을 생성한다:
   ```
   git commit -m "$(cat <<'EOF'
   <type>[optional scope]: <description>
   EOF
   )"
   ```
   `EOF` 종료자는 반드시 줄 시작에 위치해야 한다 (들여쓰기 금지).
7. `git status`로 커밋 성공을 확인한다.
8. **[필수]** arguments에 "push"가 포함되면 반드시 `git push`를 실행한다 (upstream 없으면 `git push -u origin <branch>`). push 요청 시 push 없이 끝내면 실패다.

## Rules

- 커밋 메시지는 영어로 작성한다.
- description은 간결하게 (1-2문장), "what" 보다 "why"에 집중한다.
- 적절한 type을 사용한다: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
- scope는 모듈명을 사용한다: `webhook-server`, `worker`, `common` 등
- pre-commit 훅 실패 시 에러를 보고하고 중단한다. amend나 재시도 금지.
- 훅 우회(--no-verify) 금지.
- 시크릿이 포함된 파일은 커밋하지 않는다.
