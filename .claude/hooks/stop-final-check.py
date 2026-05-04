#!/usr/bin/env python3
# =============================================================================
# [Stop Gate] Stop Hook
# 세션 종료 전:
#   1. 보안 민감 파일 수정 감지 → security-auditor 에이전트 트리거 (최대 3회)
#   2. Java 소스 수정 + 테스트 미작성 → test-generator 에이전트 트리거 (1회)
#   3. build.gradle 수정 감지 → dependency-checker 에이전트 트리거 (1회)
#   4. Java 소스 3개+ 수정 → change-validator 에이전트 트리거 (1회)
#   5. Service/Repository/Entity 수정 → performance-checker 에이전트 트리거 (1회)
#   6. 테스트 커버리지 임계값 검증 → test-coverage-gate 에이전트 트리거 (1회)
#   7. 미사용 코드 감지 → dead-code-detector 에이전트 트리거 (1회)
#   8. 빌드 검증 (compileJava)
#   9. 세션 요약 생성 → .claude/session-logs/{date}.md
#
# 개선: 에이전트 트리거를 묶어서 병렬 실행 안내
# =============================================================================
import json
import sys
import subprocess
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime


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
COVERAGE_THRESHOLD = 80  # 라인 커버리지 임계값 (%)
JACOCO_REPORT_PATHS = [
    "webhook-server/build/reports/jacoco/test/jacocoTestReport.xml",
    "worker/build/reports/jacoco/test/jacocoTestReport.xml",
]


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


def check_coverage(project_dir, edited):
    """JaCoCo XML 리포트에서 변경된 파일의 라인 커버리지를 검사한다."""
    java_sources = [
        fn for fn in edited
        if fn.endswith(".java")
        and not fn.endswith("Test.java")
        and not fn.endswith("Config.java")
        and not fn.endswith("Application.java")
    ]
    if not java_sources:
        return []

    # JaCoCo 리포트 실행 (테스트가 이미 실행된 경우 캐시됨)
    try:
        subprocess.run(
            ["./gradlew", "test", "jacocoTestReport", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    # XML 리포트 파싱
    source_names = {os.path.splitext(fn)[0] for fn in java_sources}
    low_coverage = []

    for report_path in JACOCO_REPORT_PATHS:
        full_path = os.path.join(project_dir, report_path)
        if not os.path.exists(full_path):
            continue

        try:
            tree = ET.parse(full_path)
            root = tree.getroot()

            for package in root.findall(".//package"):
                for cls in package.findall("class"):
                    class_name = cls.get("name", "").split("/")[-1]
                    # 내부 클래스($) 제거
                    base_name = class_name.split("$")[0]

                    if base_name not in source_names:
                        continue

                    # LINE 카운터 찾기
                    for counter in cls.findall("counter"):
                        if counter.get("type") == "LINE":
                            missed = int(counter.get("missed", "0"))
                            covered = int(counter.get("covered", "0"))
                            total = missed + covered
                            if total == 0:
                                continue
                            pct = (covered / total) * 100
                            if pct < COVERAGE_THRESHOLD:
                                module = report_path.split("/")[0]
                                low_coverage.append(
                                    f"{base_name}.java ({module}): "
                                    f"{covered}/{total} lines = {pct:.1f}%"
                                )
        except ET.ParseError:
            continue

    return low_coverage


def check_dead_code(project_dir, edited):
    """변경된 Java 파일에서 참조되지 않는 public 메서드를 빠르게 탐지한다."""
    SKIP_SUFFIXES = (
        "Test.java", "Config.java", "Application.java",
        "Repository.java", "Request.java", "Response.java",
    )
    # 프레임워크가 호출하는 어노테이션 (이 메서드는 미사용으로 판정하지 않음)
    FRAMEWORK_ANNOTATIONS = {
        "@Bean", "@EventListener", "@Scheduled", "@PostConstruct",
        "@PreDestroy", "@Override", "@GetMapping", "@PostMapping",
        "@PutMapping", "@DeleteMapping", "@PatchMapping", "@RequestMapping",
        "@ExceptionHandler",
    }

    target_files = [
        fn for fn in edited
        if fn.endswith(".java") and not any(fn.endswith(s) for s in SKIP_SUFFIXES)
    ]
    if not target_files:
        return []

    # 대상 파일의 전체 경로를 찾기
    file_paths = {}
    for root_dir, dirs, files in os.walk(project_dir):
        if ".git" in root_dir or "build" in root_dir or "test" in root_dir:
            continue
        for fname in files:
            if fname in target_files:
                file_paths[fname] = os.path.join(root_dir, fname)

    if not file_paths:
        return []

    # 각 파일에서 public 메서드 시그니처 추출
    METHOD_PATTERN = re.compile(
        r"^\s+public\s+(?:static\s+)?(?:\S+)\s+(\w+)\s*\(",
        re.MULTILINE,
    )

    unreferenced = []

    for fname, fpath in file_paths.items():
        try:
            with open(fpath) as f:
                content = f.read()
        except Exception:
            continue

        lines = content.split("\n")
        methods_to_check = []

        for i, line in enumerate(lines):
            match = METHOD_PATTERN.match(line)
            if not match:
                continue

            method_name = match.group(1)
            if method_name in ("main", "toString", "hashCode", "equals"):
                continue

            # 직전 라인들에서 프레임워크 어노테이션 확인
            has_framework_annotation = False
            for j in range(max(0, i - 5), i):
                if any(ann in lines[j] for ann in FRAMEWORK_ANNOTATIONS):
                    has_framework_annotation = True
                    break

            if not has_framework_annotation:
                methods_to_check.append(method_name)

        # 프로젝트 전체에서 메서드 참조 검색 (멀티모듈: 각 모듈 src 탐색)
        src_dirs = []
        for entry in os.listdir(project_dir):
            candidate = os.path.join(entry, "src", "main", "java")
            if os.path.isdir(os.path.join(project_dir, candidate)):
                src_dirs.append(candidate)

        for method_name in methods_to_check:
            if not src_dirs:
                break
            try:
                result = subprocess.run(
                    ["grep", "-r", "--include=*.java", "-l",
                     f"{method_name}("] + src_dirs,
                    capture_output=True, text=True, timeout=5,
                )
                # 자기 자신의 파일에서만 발견되면 미사용
                referencing_files = [
                    f.strip() for f in result.stdout.strip().split("\n") if f.strip()
                ]
                other_refs = [f for f in referencing_files if not f.endswith(fname)]
                if not other_refs:
                    unreferenced.append(f"{fname}: {method_name}()")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

    return unreferenced


def generate_session_summary(project_dir, edited, agent_triggers, build_ok):
    """세션 요약을 .claude/session-logs/{date}.md에 저장한다."""
    logs_dir = os.path.join(project_dir, ".claude", "session-logs")
    os.makedirs(logs_dir, exist_ok=True)

    now = datetime.now()
    session_id = os.environ.get("CLAUDE_SESSION_ID", str(os.getppid()))

    # 커밋 해시 수집
    commits = ""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10", "--no-decorate"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            commits = result.stdout.strip()
    except Exception:
        pass

    # 테스트 파일 수
    test_files = [fn for fn in edited if fn.endswith("Test.java")]

    # audit 로그에서 도구 호출 통계
    tool_stats = {}
    blocked_count = 0
    audit_file = os.path.join(
        project_dir, ".private", "audit", now.strftime("%Y-%m-%d") + ".jsonl"
    )
    if os.path.exists(audit_file):
        try:
            with open(audit_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        tool = entry.get("tool", "unknown")
                        tool_stats[tool] = tool_stats.get(tool, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

    blocked_file = os.path.join(project_dir, ".private", "audit", "blocked.jsonl")
    if os.path.exists(blocked_file):
        try:
            with open(blocked_file) as f:
                blocked_count = sum(1 for line in f if line.strip())
        except Exception:
            pass

    # 에이전트 트리거 요약
    agent_summary = "없음"
    if agent_triggers:
        agent_names = []
        for t in agent_triggers:
            match = re.search(r"\*\*(\S+)\*\*", t)
            if match:
                agent_names.append(match.group(1))
        if agent_names:
            agent_summary = ", ".join(agent_names)

    # 도구 호출 통계 테이블
    tool_table = ""
    if tool_stats:
        sorted_tools = sorted(tool_stats.items(), key=lambda x: -x[1])
        tool_rows = "\n".join(f"| {t} | {c} |" for t, c in sorted_tools)
        tool_table = f"\n| Tool | Calls |\n|------|-------|\n{tool_rows}\n"

    # 요약 작성
    summary = f"""# Session Summary — {now.strftime("%Y-%m-%d %H:%M")}

**Session ID**: {session_id}
**Build**: {"PASS" if build_ok else "FAIL"}

## 변경 파일 ({len(edited)}개)

{chr(10).join(f"- {fn}" for fn in sorted(edited)) if edited else "- (없음)"}

## 테스트

- 생성/수정된 테스트: {len(test_files)}개
{chr(10).join(f"  - {fn}" for fn in test_files) if test_files else ""}

## 에이전트 트리거

{agent_summary}

## 도구 호출 통계
{tool_table if tool_table else "- (감사 로그 없음)"}
- 차단된 호출: {blocked_count}건

## 최근 커밋

```
{commits if commits else "(커밋 없음)"}
```
"""

    # 파일 저장 (동일 날짜에 여러 세션이면 append)
    log_file = os.path.join(logs_dir, f"{now.strftime('%Y-%m-%d')}.md")
    mode = "a" if os.path.exists(log_file) else "w"
    with open(log_file, mode) as f:
        if mode == "a":
            f.write("\n---\n\n")
        f.write(summary)


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

    # ── 6. Test-coverage-gate 트리거 (커버리지 임계값 미달 시, 1회) ──
    cov_trigger_file = os.path.join(
        project_dir, ".private", ".coverage-gate-triggered"
    )
    if not os.path.exists(cov_trigger_file) and edited:
        java_sources = [
            fn for fn in edited
            if fn.endswith(".java") and not fn.endswith("Test.java")
        ]
        if java_sources:
            low_coverage = check_coverage(project_dir, edited)
            if low_coverage:
                with open(cov_trigger_file, "w") as f:
                    f.write("triggered")
                cov_list = "\n".join(f"      - {lc}" for lc in low_coverage)
                agent_triggers.append(
                    f"  **test-coverage-gate**: 커버리지 {COVERAGE_THRESHOLD}% 미달 파일:\n{cov_list}"
                )

    # ── 7. Dead-code-detector 트리거 (미사용 public 메서드 감지 시, 1회) ──
    dead_trigger_file = os.path.join(
        project_dir, ".private", ".dead-code-triggered"
    )
    if not os.path.exists(dead_trigger_file) and edited:
        java_sources = [
            fn for fn in edited
            if fn.endswith(".java") and not fn.endswith("Test.java")
        ]
        if java_sources:
            unreferenced = check_dead_code(project_dir, edited)
            if unreferenced:
                with open(dead_trigger_file, "w") as f:
                    f.write("triggered")
                dead_list = "\n".join(f"      - {u}" for u in unreferenced[:10])
                extra = ""
                if len(unreferenced) > 10:
                    extra = f"\n      외 {len(unreferenced) - 10}개"
                agent_triggers.append(
                    f"  **dead-code-detector**: 미사용 코드 {len(unreferenced)}건 감지:\n{dead_list}{extra}"
                )

    # ── 8. 빌드 검증 ──
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

        # 세션 요약 생성 (실패 시에도 기록)
        generate_session_summary(
            project_dir, edited, agent_triggers, build_ok=not build_issues
        )

        reason = (
            "세션 종료 전 검증 실패. 아래 문제를 해결하세요:\n\n"
            + "\n\n".join(all_issues)
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    else:
        if os.path.exists(failing_tests_file):
            os.remove(failing_tests_file)

        # 세션 요약 생성
        generate_session_summary(
            project_dir, edited, agent_triggers, build_ok=True
        )

        # ── 검증 통과 시 트리거 상태 파일 정리 ──
        trigger_files = [
            ".test-generator-triggered",
            ".change-validator-triggered",
            ".performance-checker-triggered",
            ".dep-checker-triggered",
            ".coverage-gate-triggered",
            ".dead-code-triggered",
            ".security-audit-count",
            ".edited-files",
        ]
        for tf in trigger_files:
            tf_path = os.path.join(project_dir, ".private", tf)
            if os.path.exists(tf_path):
                os.remove(tf_path)


if __name__ == "__main__":
    main()
