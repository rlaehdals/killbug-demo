#!/usr/bin/env python3
# =============================================================================
# [Stop Gate] Stop Hook
# 세션 종료 전:
#   1. 보안 민감 파일 수정 감지 → security-auditor 에이전트 트리거 (최대 3회)
#   2. Java 소스 수정 + 테스트 미작성 → test-generator 에이전트 트리거 (1회)
#   3. build.gradle 수정 감지 → dependency-checker 에이전트 트리거 (1회)
#   4. Java 소스 3개+ 수정 → change-validator 에이전트 트리거 (1회)
#   5. Service/Repository/Entity 수정 → performance-checker 에이전트 트리거 (1회)
#   6. 빌드 검증 (compileJava)
#
# 개선: 에이전트 트리거를 묶어서 병렬 실행 안내
# =============================================================================
import json
import sys
import subprocess
import os


# 보안 민감 패턴: 파일 내용에 이 패턴이 있으면 보안 감사 대상
SECURITY_PATTERNS = [
    "ProcessBuilder",
    "Runtime.getRuntime().exec",
    "RestClient",
    "WebClient",
    "HttpClient",
    "HmacSHA",
    "MessageDigest",
    "SecretKey",
    "Mac.getInstance",
    "@Query",
]

MAX_SECURITY_AUDIT = 3


def check_security_sensitive_files(project_dir):
    """세션 중 수정된 파일 중 보안 민감 파일이 있는지 확인."""
    edited_files_path = os.path.join(project_dir, ".private", ".edited-files")
    if not os.path.exists(edited_files_path):
        return []

    with open(edited_files_path) as f:
        edited_files = [line.strip() for line in f if line.strip()]

    if not edited_files:
        return []

    # 수정된 Java 파일에서 보안 민감 패턴 검색
    sensitive_files = []
    for root, dirs, files in os.walk(project_dir):
        if ".git" in root or "build" in root:
            continue
        for fname in files:
            if fname not in edited_files or not fname.endswith(".java"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath) as f:
                    content = f.read()
                found = [p for p in SECURITY_PATTERNS if p in content]
                if found:
                    sensitive_files.append(f"{fname} ({', '.join(found)})")
            except Exception:
                continue

    return sensitive_files


def load_edited_files(project_dir):
    """세션 중 수정된 파일 목록 로드 (캐시)."""
    edited_files_path = os.path.join(project_dir, ".private", ".edited-files")
    if not os.path.exists(edited_files_path):
        return []
    with open(edited_files_path) as f:
        return [line.strip() for line in f if line.strip()]


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    os.chdir(project_dir)

    if not os.path.exists("gradlew"):
        return

    agent_triggers = []  # 병렬 실행 가능한 에이전트 트리거
    build_issues = []    # 빌드 실패 (먼저 해결 필요)

    edited = load_edited_files(project_dir)

    # ── 1. Security-auditor 트리거 (최대 3회) ──
    audit_counter_file = os.path.join(project_dir, ".private", ".security-audit-count")
    audit_count = 0
    if os.path.exists(audit_counter_file):
        try:
            with open(audit_counter_file) as f:
                audit_count = int(f.read().strip())
        except (ValueError, IOError):
            audit_count = 0

    if audit_count < MAX_SECURITY_AUDIT:
        sensitive_files = check_security_sensitive_files(project_dir)
        if sensitive_files:
            audit_count += 1
            with open(audit_counter_file, "w") as f:
                f.write(str(audit_count))

            file_list = "\n".join(f"    - {sf}" for sf in sensitive_files)
            agent_triggers.append(
                f"  **security-auditor** ({audit_count}/{MAX_SECURITY_AUDIT}회차):\n{file_list}"
            )

    # ── 2. Test-generator 트리거 (Java 소스 수정 + 테스트 미작성 시, 1회) ──
    test_trigger_file = os.path.join(project_dir, ".private", ".test-generator-triggered")
    if not os.path.exists(test_trigger_file) and edited:
        java_sources = [
            fn for fn in edited
            if fn.endswith(".java") and not fn.endswith("Test.java")
        ]
        test_files = [fn for fn in edited if fn.endswith("Test.java")]

        if java_sources and not test_files:
            with open(test_trigger_file, "w") as f:
                f.write("triggered")
            source_list = ", ".join(java_sources[:5])
            if len(java_sources) > 5:
                source_list += f" 외 {len(java_sources) - 5}개"
            agent_triggers.append(
                f"  **test-generator**: Java 소스 {len(java_sources)}개 수정, 테스트 없음 ({source_list})"
            )

    # ── 3. Dependency-checker 트리거 (build.gradle 수정 시, 1회) ──
    dep_trigger_file = os.path.join(project_dir, ".private", ".dep-checker-triggered")
    if not os.path.exists(dep_trigger_file) and edited:
        gradle_files = [fn for fn in edited if fn.endswith(".gradle")]
        if gradle_files:
            with open(dep_trigger_file, "w") as f:
                f.write("triggered")
            agent_triggers.append(
                f"  **dependency-checker**: {', '.join(gradle_files)} 수정됨"
            )

    # ── 4. Change-validator 트리거 (Java 소스 3개+ 수정 시, 1회) ──
    cv_trigger_file = os.path.join(project_dir, ".private", ".change-validator-triggered")
    if not os.path.exists(cv_trigger_file) and edited:
        java_sources = [
            fn for fn in edited
            if fn.endswith(".java") and not fn.endswith("Test.java")
        ]
        if len(java_sources) >= 3:
            with open(cv_trigger_file, "w") as f:
                f.write("triggered")
            source_list = ", ".join(java_sources[:5])
            if len(java_sources) > 5:
                source_list += f" 외 {len(java_sources) - 5}개"
            agent_triggers.append(
                f"  **change-validator**: Java 소스 {len(java_sources)}개 변경 ({source_list})"
            )

    # ── 5. Performance-checker 트리거 (Service/Repository/Entity 수정 시, 1회) ──
    perf_trigger_file = os.path.join(
        project_dir, ".private", ".performance-checker-triggered"
    )
    if not os.path.exists(perf_trigger_file) and edited:
        PERF_PATTERNS = ["Service.java", "Repository.java", "Entity.java"]
        perf_files = [
            fn
            for fn in edited
            if any(fn.endswith(p) for p in PERF_PATTERNS)
        ]
        if perf_files:
            with open(perf_trigger_file, "w") as f:
                f.write("triggered")
            agent_triggers.append(
                f"  **performance-checker**: {', '.join(perf_files)} 수정됨"
            )

    # ── 6. 빌드 검증 ──
    failing_tests_file = os.path.join(project_dir, ".private", ".failing-tests")

    try:
        result = subprocess.run(
            ["./gradlew", "compileJava", "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            output_lines = (result.stdout + result.stderr).strip().split("\n")
            tail = "\n".join(output_lines[-15:])
            build_issues.append(f"컴파일 실패:\n```\n{tail}\n```")
    except subprocess.TimeoutExpired:
        build_issues.append("빌드 타임아웃 (120초 초과)")
    except FileNotFoundError:
        pass

    # ── 결과 처리 ──
    all_issues = []

    # 빌드 실패는 먼저 표시
    if build_issues:
        all_issues.extend(build_issues)

    # 에이전트 트리거를 묶어서 병렬 실행 안내
    if agent_triggers:
        triggers_block = "\n".join(agent_triggers)
        if len(agent_triggers) == 1:
            all_issues.append(
                f"아래 에이전트를 실행하세요:\n\n{triggers_block}"
            )
        else:
            all_issues.append(
                f"아래 {len(agent_triggers)}개 에이전트를 **병렬로** 실행하세요:\n\n"
                f"{triggers_block}\n\n"
                f"독립적인 검증이므로 병렬 실행이 가능합니다."
            )

    if all_issues:
        with open(failing_tests_file, "w") as f:
            f.write("\n".join(all_issues))

        reason = (
            "세션 종료 전 검증 실패. 아래 문제를 해결하세요:\n\n"
            + "\n\n".join(all_issues)
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    else:
        if os.path.exists(failing_tests_file):
            os.remove(failing_tests_file)

        # ── 검증 통과 시 트리거 상태 파일 정리 ──
        trigger_files = [
            ".test-generator-triggered",
            ".change-validator-triggered",
            ".performance-checker-triggered",
            ".dep-checker-triggered",
            ".security-audit-count",
            ".edited-files",
        ]
        for tf in trigger_files:
            tf_path = os.path.join(project_dir, ".private", tf)
            if os.path.exists(tf_path):
                os.remove(tf_path)


if __name__ == "__main__":
    main()
