#!/usr/bin/env python3
"""plan-gate.py를 원래 방식(모든 Edit/Write에 플랜 강제)으로 되돌린다."""
import os

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS = os.path.join(PROJECT, ".claude", "hooks")


def patch(filepath, old, new):
    with open(filepath) as f:
        content = f.read()
    if old not in content:
        print(f"  [SKIP] not found in {os.path.basename(filepath)}")
        return False
    content = content.replace(old, new)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  [OK] {os.path.basename(filepath)}")
    return True


def main():
    print("=== plan-gate 원래 방식으로 되돌리기 ===\n")

    # ── 1. plan-gate.py 교체 ──
    print("[1/2] plan-gate.py 되돌리기")
    plan_gate = os.path.join(HOOKS, "plan-gate.py")

    new_content = '''#!/usr/bin/env python3
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
    if "/.claude/" in file_path or "\\\\.claude\\\\" in file_path or "/.private/" in file_path:
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
                    "[Task Planner] 코드 수정 전 실행 계획을 먼저 수립하세요.\\n\\n"
                    "task-planner 에이전트를 실행하여 작업 계획을 생성하세요.\\n"
                    "계획 승인 후 `.private/.task-plan-established` 파일을 생성하면 "
                    "수정이 허용됩니다."
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
'''

    with open(plan_gate, "w") as f:
        f.write(new_content)
    print("  [OK] plan-gate.py 교체 완료")

    # ── 2. session-start.py에서 .plan-gate-first-file 정리 제거 ──
    print("\n[2/2] session-start.py에서 .plan-gate-first-file 정리 제거")
    patch(
        os.path.join(HOOKS, "session-start.py"),
        '\n    first_file_marker = os.path.join(project_dir, ".private", ".plan-gate-first-file")\n'
        "    if os.path.exists(first_file_marker):\n"
        "        os.remove(first_file_marker)",
        "",
    )

    print("\n=== 완료. 체크섬 갱신 필요 ===")


if __name__ == "__main__":
    main()
