#!/usr/bin/env python3
# =============================================================================
# [피드백 루프] PostToolUse Hook
# 하네스 3대 축 중 "개선(Feedback)" 담당.
#
# 도구 실행이 실패하면 자동으로 교훈을 .claude/.learnings에 기록한다.
# session-start.sh가 다음 세션에서 이 교훈을 읽어 Claude에 주입한다.
# → "반복되는 오류를 방치하지 않는 지속적 개선 구조"
# =============================================================================
import json, sys, os
from datetime import datetime

MAX_LEARNINGS = 20  # 최근 20개 교훈만 유지 (오래된 것 자동 삭제)

def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})

    # 실패한 도구 호출만 처리
    if not is_failure(tool_name, tool_response):
        return

    # 교훈 추출
    learning = extract_learning(tool_name, tool_input, tool_response)
    if not learning:
        return

    # .learnings 파일에 추가
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    learnings_file = os.path.join(project_dir, ".private", ".learnings")

    # 기존 교훈 읽기
    existing = []
    if os.path.exists(learnings_file):
        with open(learnings_file) as f:
            existing = [line.strip() for line in f if line.strip()]

    # 중복 방지: 같은 패턴의 교훈이 이미 있으면 스킵
    learning_key = learning.split("|")[1].strip() if "|" in learning else learning
    for entry in existing:
        if learning_key in entry:
            return

    # 새 교훈 추가 (최근 N개만 유지)
    existing.append(learning)
    if len(existing) > MAX_LEARNINGS:
        existing = existing[-MAX_LEARNINGS:]

    with open(learnings_file, "w") as f:
        f.write("\n".join(existing) + "\n")


def is_failure(tool_name, tool_response):
    """도구 실행이 실패했는지 판단"""
    if isinstance(tool_response, dict):
        # Bash: exit code != 0
        exit_code = tool_response.get("exit_code")
        if exit_code is not None and exit_code != 0:
            return True
        # 일반: success == false
        if tool_response.get("success") is False:
            return True
        # stderr에 에러 패턴
        stderr = tool_response.get("stderr", "")
        if isinstance(stderr, str) and any(kw in stderr.lower() for kw in ["error", "exception", "failed"]):
            return True
    return False


def extract_learning(tool_name, tool_input, tool_response):
    """실패 내용에서 교훈을 추출"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    stderr = ""
    if isinstance(tool_response, dict):
        stderr = tool_response.get("stderr", "") or tool_response.get("stdout", "") or ""

    if tool_name == "Bash":
        command = tool_input.get("command", "")[:100]
        error_line = extract_error_line(stderr)
        if error_line:
            return f"{ts} | Bash 실패: `{command}` | {error_line}"

    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        filename = file_path.split("/")[-1] if file_path else "unknown"
        error_line = extract_error_line(stderr)
        if error_line:
            return f"{ts} | {tool_name} 실패: {filename} | {error_line}"

    # 일반적인 실패
    error_line = extract_error_line(stderr)
    if error_line:
        return f"{ts} | {tool_name} 실패 | {error_line}"

    return None


def extract_error_line(output):
    """에러 메시지에서 핵심 한 줄 추출"""
    if not output or not isinstance(output, str):
        return None
    for line in output.strip().split("\n"):
        line = line.strip()
        if any(kw in line.lower() for kw in ["error", "exception", "failed", "cannot", "not found"]):
            return line[:200]
    # 마지막 줄 반환
    lines = output.strip().split("\n")
    if lines:
        return lines[-1][:200]
    return None


if __name__ == "__main__":
    main()
