#!/usr/bin/env python3
# =============================================================================
# [Stop Gate] Stop Hook
# 세션 종료 전:
#   1. 보안 민감 파일 수정 감지 → security-auditor 에이전트 트리거 (최대 3회)
#   2. Java 소스 수정 + 테스트 미작성 → test-generator 에이전트 트리거 (1회)
#   3. build.gradle 수정 감지 → dependency-checker 에이전트 트리거 (1회)
#   4. 빌드 검증 (compileJava)
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
    edited_files_path = os.path.join(project_dir, ".claude", ".edited-files")
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


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    os.chdir(project_dir)

    if not os.path.exists("gradlew"):
        return

    issues = []

    # ── 1. Security-auditor 트리거 (최대 3회) ──
    audit_counter_file = os.path.join(project_dir, ".claude", ".security-audit-count")
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

            file_list = "\n".join(f"  - {sf}" for sf in sensitive_files)
            issues.append(
                f"[Security Audit] 보안 민감 코드가 수정되었습니다 "
                f"({audit_count}/{MAX_SECURITY_AUDIT}회차):\n{file_list}\n"
                f"security-auditor 에이전트로 보안 감사를 실행하세요."
            )

    # ── 2. Test-generator 트리거 (Java 소스 수정 + 테스트 미작성 시, 1회) ──
    test_trigger_file = os.path.join(project_dir, ".claude", ".test-generator-triggered")
    if not os.path.exists(test_trigger_file):
        edited_files_path = os.path.join(project_dir, ".claude", ".edited-files")
        if os.path.exists(edited_files_path):
            with open(edited_files_path) as f:
                edited = [line.strip() for line in f if line.strip()]

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
                issues.append(
                    f"[Test Generator] Java 소스 {len(java_sources)}개가 수정되었으나 "
                    f"테스트 파일이 없습니다: {source_list}\n"
                    f"test-generator 에이전트로 테스트를 생성하세요."
                )

    # ── 3. Dependency-checker 트리거 (build.gradle 수정 시, 1회) ──
    dep_trigger_file = os.path.join(project_dir, ".claude", ".dep-checker-triggered")
    if not os.path.exists(dep_trigger_file):
        edited_files_path = os.path.join(project_dir, ".claude", ".edited-files")
        if os.path.exists(edited_files_path):
            with open(edited_files_path) as f:
                edited = [line.strip() for line in f if line.strip()]

            gradle_files = [fn for fn in edited if fn.endswith(".gradle")]
            if gradle_files:
                with open(dep_trigger_file, "w") as f:
                    f.write("triggered")
                issues.append(
                    f"[Dependency Check] build.gradle이 수정되었습니다: "
                    f"{', '.join(gradle_files)}\n"
                    f"dependency-checker 에이전트로 의존성 보안 검사를 실행하세요."
                )

    # ── 4. 빌드 검증 ──
    failing_tests_file = os.path.join(project_dir, ".claude", ".failing-tests")

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
            issues.append(f"컴파일 실패:\n```\n{tail}\n```")
    except subprocess.TimeoutExpired:
        issues.append("빌드 타임아웃 (120초 초과)")
    except FileNotFoundError:
        pass

    # ── 결과 처리 ──
    if issues:
        with open(failing_tests_file, "w") as f:
            f.write("\n".join(issues))

        reason = (
            "세션 종료 전 검증 실패. 아래 문제를 해결하세요:\n\n"
            + "\n\n".join(issues)
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    else:
        if os.path.exists(failing_tests_file):
            os.remove(failing_tests_file)


if __name__ == "__main__":
    main()
