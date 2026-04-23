#!/usr/bin/env python3
# =============================================================================
# [감사 로그] PostToolUse Hook (비동기)
# 모든 도구 호출을 JSONL 형식으로 기록한다.
# 하네스 엔지니어링의 "감시(Monitoring)" 레이어.
# =============================================================================
import json, sys, os
from datetime import datetime

def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        return

    tool_name = hook_input.get("tool_name", "unknown")
    tool_input = hook_input.get("tool_input", {})

    # 도구 입력 요약 (300자 제한)
    input_summary = json.dumps(tool_input, ensure_ascii=False)
    if len(input_summary) > 300:
        input_summary = input_summary[:300] + "...(truncated)"

    # 응답 상태 추출
    tool_response = hook_input.get("tool_response", {})
    if isinstance(tool_response, dict):
        status = tool_response.get("success", tool_response.get("exit_code", "unknown"))
    else:
        status = "unknown"

    # 세션 ID (환경변수 또는 PID 기반)
    session_id = os.environ.get("CLAUDE_SESSION_ID", str(os.getppid()))

    # 감사 로그 엔트리
    entry = {
        "ts": datetime.now().isoformat(),
        "session": session_id,
        "tool": tool_name,
        "input": input_summary,
        "status": str(status)
    }

    # 감사 디렉토리 생성
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    audit_dir = os.path.join(project_dir, ".private", "audit")
    os.makedirs(audit_dir, exist_ok=True)

    # 일별 JSONL 파일에 추가
    log_file = os.path.join(audit_dir, f"{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
