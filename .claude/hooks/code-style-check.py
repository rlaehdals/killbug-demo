#!/usr/bin/env python3
# =============================================================================
# [코드 스타일] PostToolUse Hook
# Java 파일 수정 시:
#   1. 컨벤션 위반 즉시 피드백
#   2. 세션 내 편집 파일 수 추적 → 임계값 초과 시 code-reviewer 에이전트 트리거
# 포매팅(Spotless)은 output-verify.py에서 debounce 후 실행.
# =============================================================================
import json
import sys
import re
import os

# N개 이상 Java 파일 수정 시 code-reviewer 에이전트 트리거
REVIEW_TRIGGER_THRESHOLD = 5


def check_conventions(content):
    """포매터가 잡지 못하는 컨벤션 위반 검사."""
    issues = []

    if re.search(r"System\.(out|err)\.(println|print|printf)", content):
        issues.append("System.out/err detected. Use @Slf4j logger instead.")

    if re.search(r"new\s+Date\(\)", content):
        issues.append(
            "new Date() detected. Use java.time API (LocalDateTime, Instant)."
        )

    if re.search(r"@Autowired", content):
        issues.append(
            "@Autowired detected. Use constructor injection (@RequiredArgsConstructor)."
        )

    if re.search(r"\bvar\s+\w+\s*=", content):
        issues.append("var detected. Use explicit type declaration.")

    if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", content):
        issues.append(
            "Empty catch block detected. Log the exception or handle it."
        )

    return issues


def track_edits_and_trigger(file_path, project_dir):
    """세션 내 수정된 Java 파일 수를 추적하고, 임계값 초과 시 리뷰 트리거."""
    counter_file = os.path.join(project_dir, ".private", ".edit-count")
    edited_files_file = os.path.join(project_dir, ".private", ".edited-files")

    # 현재까지 수정된 파일 목록 로드
    edited_files = set()
    if os.path.exists(edited_files_file):
        with open(edited_files_file) as f:
            edited_files = set(line.strip() for line in f if line.strip())

    # 새 파일 추가
    filename = os.path.basename(file_path)
    edited_files.add(filename)

    # 저장
    os.makedirs(os.path.dirname(edited_files_file), exist_ok=True)
    with open(edited_files_file, "w") as f:
        f.write("\n".join(sorted(edited_files)))

    count = len(edited_files)

    # 임계값 도달 시 트리거 (한 번만)
    already_triggered = False
    if os.path.exists(counter_file):
        with open(counter_file) as f:
            already_triggered = f.read().strip() == "triggered"

    if count >= REVIEW_TRIGGER_THRESHOLD and not already_triggered:
        with open(counter_file, "w") as f:
            f.write("triggered")
        return count

    return None


def main():
    hook_input = json.loads(sys.stdin.read())
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    file_path = tool_input.get("file_path", "")

    if not file_path.endswith(".java"):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # ── 1. 컨벤션 위반 검사 ──
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
    else:
        return

    issues = check_conventions(content)

    # ── 2. 편집 추적 + code-reviewer 트리거 ──
    trigger_count = track_edits_and_trigger(file_path, project_dir)

    # ── 3. 피드백 출력 ──
    feedback_parts = []

    if issues:
        filename = file_path.split("/")[-1]
        lines = [f"  - {issue}" for issue in issues]
        feedback_parts.append(
            f"[Convention] Issues in {filename}:\n"
            + "\n".join(lines)
            + "\nPlease fix these before proceeding."
        )

    if trigger_count:
        feedback_parts.append(
            f"[Review Trigger] Java 파일 {trigger_count}개가 수정되었습니다. "
            f"code-reviewer 에이전트로 코드 리뷰를 실행하세요."
        )

    if feedback_parts:
        print(json.dumps({"hookSpecificOutput": "\n".join(feedback_parts)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # PostToolUse 훅은 fail-open
        pass
