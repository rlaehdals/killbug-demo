#!/usr/bin/env python3
# =============================================================================
# [PreToolUse Gate] Plan Gate Hook
# 첫 Edit/Write 전에 task-planner 에이전트로 실행 계획 수립을 강제한다.
# .private/.task-plan-established 파일이 존재하면 통과.
# .claude/ 및 .private/ 내부, *Test.java는 항상 허용.
# fail-open: 에러 시 차단하지 않음 (품질 영역)
# =============================================================================
import json
import sys
import os


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        return

    tool_name = input_data.get("tool_name", "")

    # Edit/Write만 검사
    if tool_name not in ("Edit", "Write"):
        return

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # .claude/ 및 .private/ 내부 파일은 항상 허용
    if "/.claude/" in file_path or "\\.claude\\" in file_path or "/.private/" in file_path:
        return

    # 테스트 파일은 허용 (test-generator 에이전트가 플랜 없이 생성할 수 있음)
    if file_path.endswith("Test.java"):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    plan_file = os.path.join(project_dir, ".private", ".task-plan-established")

    # 플랜이 수립되었으면 통과
    if os.path.exists(plan_file):
        return

    # 플랜 미수립 → 차단
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "[Task Planner] 코드 수정 전 실행 계획을 먼저 수립하세요.\n\n"
                    "task-planner 에이전트를 실행하여 작업 계획을 생성하세요.\n"
                    "계획 승인 후 `.private/.task-plan-established` 파일을 생성하면 "
                    "수정이 허용됩니다."
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
