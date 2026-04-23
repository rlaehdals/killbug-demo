#!/usr/bin/env python3
# =============================================================================
# [출력 검증] PostToolUse Hook
# Java 파일 수정 후 Spotless 포매팅 + incremental compile을 실행한다.
#
# Edit이 연속될 때는 debounce로 스킵하고,
# 편집이 멈춘 뒤(30초 후) 다음 Edit에서 한 번에 실행한다.
#   1. Spotless (palantir-java-format) — import 순서, 들여쓰기, 줄바꿈 자동 수정
#   2. compileJava — 존재하지 않는 클래스, 타입 불일치 등 의미적 오류 감지
# =============================================================================
import json
import sys
import os
import subprocess
import time

# 마지막 체크 후 최소 대기 시간 (초)
DEBOUNCE_SECONDS = 30


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Java 파일만 대상
    if not file_path.endswith(".java"):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # gradlew 없으면 스킵
    gradlew = os.path.join(project_dir, "gradlew")
    if not os.path.exists(gradlew):
        return

    # Debounce: 마지막 체크 이후 충분한 시간이 지났는지 확인
    marker_file = os.path.join(project_dir, ".private", ".last-compile-check")
    now = time.time()

    if os.path.exists(marker_file):
        last_check = os.path.getmtime(marker_file)
        if now - last_check < DEBOUNCE_SECONDS:
            return  # 아직 이르다 — 스킵

    # 마커 갱신
    os.makedirs(os.path.dirname(marker_file), exist_ok=True)
    with open(marker_file, "w") as f:
        f.write(str(now))

    # 어느 모듈의 파일인지 판별
    module = detect_module(file_path)
    if not module:
        return

    feedback_parts = []

    # ── 1. Spotless 자동 포매팅 ──
    try:
        spotless = subprocess.run(
            [gradlew, f":{module}:spotlessApply", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir,
        )
        if spotless.returncode == 0:
            feedback_parts.append(
                "[Auto-fixed] Spotless applied: import order, indentation, "
                "unused imports, trailing whitespace."
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # ── 2. Incremental compile ──
    try:
        result = subprocess.run(
            [gradlew, f":{module}:compileJava", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_dir,
        )
    except subprocess.TimeoutExpired:
        feedback_parts.append(
            "[Output Verify] 컴파일 체크 타임아웃 (60초). "
            "수동으로 ./gradlew compileJava를 실행하세요."
        )
        if feedback_parts:
            print(json.dumps({"hookSpecificOutput": "\n".join(feedback_parts)}))
        return
    except FileNotFoundError:
        return

    if result.returncode != 0:
        errors = extract_compile_errors(result.stdout + result.stderr)
        if errors:
            feedback_parts.append(
                f"[Output Verify] {module} 컴파일 실패. "
                f"아래 오류를 수정하세요:\n\n{errors}"
            )

    if feedback_parts:
        print(json.dumps({"hookSpecificOutput": "\n".join(feedback_parts)}))


def detect_module(file_path):
    """파일 경로에서 모듈명 추출."""
    if "webhook-server" in file_path:
        return "webhook-server"
    elif "worker" in file_path:
        return "worker"
    return None


def extract_compile_errors(output):
    """컴파일 출력에서 에러만 추출 (최대 10개)."""
    errors = []
    for line in output.split("\n"):
        line = line.strip()
        if "error:" in line.lower() or "cannot find symbol" in line.lower():
            errors.append(line)
        if len(errors) >= 10:
            break

    if not errors:
        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
        errors = lines[-5:]

    return "\n".join(errors) if errors else None


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # PostToolUse 훅은 fail-open
        pass
