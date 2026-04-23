#!/usr/bin/env python3
"""
plan-gate.py 복잡도 판단 업그레이드 + session-start.py 정리 파일 추가

- Edit 첫 파일: 허용 + 경고 (단순 수정)
- Edit 두 번째 파일부터: 차단 (멀티 파일 = 플랜 필요)
- Write (신규 파일): 차단 (기능 작업 = 플랜 필요)
- session-start.py: .plan-gate-first-file 삭제 추가
"""
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
    print("=== plan-gate 복잡도 판단 업그레이드 ===\n")

    # ── 1. plan-gate.py 교체 ──
    print("[1/2] plan-gate.py 업데이트")
    plan_gate = os.path.join(HOOKS, "plan-gate.py")

    new_content = '''#!/usr/bin/env python3
# =============================================================================
# [PreToolUse Gate] Plan Gate Hook
# 복잡도 기반 플랜 수립 판단:
#   - Plan 수립 완료 → 항상 통과
#   - Write (신규 파일 생성) → 플랜 강제
#   - Edit 첫 파일 → 허용 + 경고 (단순 수정 허용)
#   - Edit 두 번째 파일부터 → 플랜 강제 (멀티 파일 변경)
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

    # ── 복잡도 판단 ──

    # Write (신규 파일 생성) → 항상 플랜 강제
    if tool_name == "Write":
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        "[Task Planner] 신규 파일 생성은 실행 계획이 필요합니다.\\n\\n"
                        "task-planner 에이전트를 실행하여 작업 계획을 생성하세요.\\n"
                        "계획 승인 후 `.private/.task-plan-established` 파일을 생성하면 "
                        "수정이 허용됩니다."
                    ),
                }
            )
        )
        return

    # Edit → 첫 파일은 허용, 두 번째 파일부터 차단
    first_file_marker = os.path.join(project_dir, ".private", ".plan-gate-first-file")
    filename = os.path.basename(file_path)

    if not os.path.exists(first_file_marker):
        # 첫 Edit → 허용 + 경고
        os.makedirs(os.path.dirname(first_file_marker), exist_ok=True)
        with open(first_file_marker, "w") as f:
            f.write(filename)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": (
                        f"[Plan Gate] 단일 파일 수정 허용: {filename}\\n"
                        "추가 파일 수정 시 플랜 수립이 필요합니다."
                    )
                }
            )
        )
        return

    # 이미 한 파일을 수정한 상태 → 같은 파일이면 허용
    with open(first_file_marker) as f:
        first_file = f.read().strip()

    if first_file == filename:
        return

    # 다른 파일 → 플랜 강제
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"[Task Planner] 멀티 파일 변경은 실행 계획이 필요합니다.\\n"
                    f"(첫 수정: {first_file}, 추가 수정 시도: {filename})\\n\\n"
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

    # ── 2. session-start.py에 정리 파일 추가 ──
    print("\n[2/2] session-start.py 정리 파일 추가")
    patch(
        os.path.join(HOOKS, "session-start.py"),
        '    plan_file = os.path.join(project_dir, ".private", ".task-plan-established")\n'
        "    if os.path.exists(plan_file):\n"
        "        os.remove(plan_file)",
        '    plan_file = os.path.join(project_dir, ".private", ".task-plan-established")\n'
        "    if os.path.exists(plan_file):\n"
        "        os.remove(plan_file)\n"
        "\n"
        '    first_file_marker = os.path.join(project_dir, ".private", ".plan-gate-first-file")\n'
        "    if os.path.exists(first_file_marker):\n"
        "        os.remove(first_file_marker)",
    )

    print("\n=== 완료. 체크섬 갱신 필요: python3 .claude/scripts/update-checksums.py ===")


if __name__ == "__main__":
    main()
