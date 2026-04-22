#!/usr/bin/env python3
# =============================================================================
# [컨텍스트 주입] SessionStart Hook
# 세션 시작 시 프로젝트 상태 + 하네스 진단(harness-doctor)을 주입한다.
# 누가 실행해도 동일한 맥락에서 시작하게 만드는 핵심 장치.
# =============================================================================
import json
import sys
import subprocess
import os
import hashlib


def run(cmd, fallback="(없음)"):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or fallback
    except Exception:
        return fallback


def check_harness_health(project_dir):
    """harness-doctor: 하네스 전체 상태 진단."""
    results = []

    # ── 1. 훅 파일 존재 확인 ──
    hook_files = [
        ".claude/hooks/session-start.py",
        ".claude/hooks/guardrail-check.py",
        ".claude/hooks/data-governance-check.py",
        ".claude/hooks/code-style-check.py",
        ".claude/hooks/output-verify.py",
        ".claude/hooks/feedback-loop.py",
        ".claude/hooks/audit.py",
        ".claude/hooks/stop-final-check.py",
        ".claude/scripts/api-spec-update.py",
    ]
    missing = [f for f in hook_files if not os.path.exists(os.path.join(project_dir, f))]
    if missing:
        results.append(("훅 파일", "MISSING", ", ".join(missing)))
    else:
        results.append(("훅 파일 (9개)", "OK", ""))

    # ── 2. deny 규칙 확인 ──
    settings_file = os.path.join(project_dir, ".claude", "settings.json")
    deny_ok = True
    if os.path.exists(settings_file):
        with open(settings_file) as f:
            raw = f.read()
        required_denys = [
            "Edit(.claude/settings.json)",
            "Write(.claude/hooks/**)",
            "Edit(CLAUDE.md)",
        ]
        inactive = []
        for pattern in required_denys:
            # 주석 처리된 경우 감지 (// "Edit(...)")
            if f'// "{pattern}"' in raw or f"// '{pattern}'" in raw:
                inactive.append(pattern)
            elif f'"{pattern}"' not in raw:
                inactive.append(pattern)
        if inactive:
            deny_ok = False
            results.append(("deny 규칙", "WARN", f"비활성: {', '.join(inactive)}"))
        else:
            results.append(("deny 규칙", "OK", ""))
    else:
        results.append(("deny 규칙", "MISSING", "settings.json 없음"))

    # ── 3. 체크섬 무결성 ──
    manifest_file = os.path.join(project_dir, ".claude", "harness-checksums.json")
    if os.path.exists(manifest_file):
        with open(manifest_file) as f:
            manifest = json.load(f)
        expected = manifest.get("files", {})
        mismatched = []
        for rel_path, expected_hash in expected.items():
            abs_path = os.path.join(project_dir, rel_path)
            if not os.path.exists(abs_path):
                mismatched.append(f"{rel_path} (MISSING)")
                continue
            h = hashlib.sha256()
            with open(abs_path, "rb") as hf:
                for chunk in iter(lambda: hf.read(8192), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_hash:
                mismatched.append(rel_path)
        if mismatched:
            results.append(("체크섬 무결성", "TAMPERED", ", ".join(mismatched)))
        else:
            results.append(("체크섬 무결성", "OK", f"{len(expected)}개 파일"))
    else:
        results.append(("체크섬 무결성", "NO MANIFEST", "update-checksums.py 실행 필요"))

    # ── 4. git hooks 설치 확인 ──
    hooks_path = run(["git", "config", "core.hooksPath"], "").strip()
    if ".claude/git-hooks" in hooks_path:
        results.append(("git hooks", "OK", hooks_path))
    else:
        results.append(("git hooks", "NOT INSTALLED", "bash .claude/scripts/setup-hooks.sh 실행 필요"))

    # ── 5. API 스펙 동기화 ──
    spec_md = os.path.join(project_dir, "docs", "api-spec.md")
    spec_yml = os.path.join(project_dir, "docs", "api-spec.yml")
    if os.path.exists(spec_md) and os.path.exists(spec_yml):
        results.append(("API 스펙", "OK", "md + yml"))
    else:
        results.append(("API 스펙", "MISSING", "Controller 수정 시 자동 생성됨"))

    return results


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    os.chdir(project_dir)

    # ── Git 상태 수집 ──
    branch = run(["git", "branch", "--show-current"], "unknown")
    recent_commits = run(["git", "log", "--oneline", "-5"], "커밋 없음")
    unstaged = run(["git", "diff", "--stat"], "변경 없음")

    # ── 빌드 상태 확인 ──
    build_status = "확인 안 됨"
    if os.path.exists("gradlew"):
        webhook_build = os.path.exists("webhook-server/build")
        worker_build = os.path.exists("worker/build")
        if webhook_build and worker_build:
            build_status = "webhook-server: OK, worker: OK"
        elif webhook_build:
            build_status = "webhook-server: OK, worker: 빌드 필요"
        elif worker_build:
            build_status = "webhook-server: 빌드 필요, worker: OK"
        else:
            build_status = "빌드 필요 (./gradlew build)"

    # ── 알려진 실패 테스트 ──
    failing_tests = "(없음)"
    failing_tests_file = os.path.join(project_dir, ".claude", ".failing-tests")
    if os.path.exists(failing_tests_file):
        with open(failing_tests_file) as f:
            failing_tests = f.read().strip() or "(없음)"

    # ── 역할 기반 접근 레벨 ──
    git_email = run(["git", "config", "user.email"], "unknown").lower()
    role = "junior"
    policy_file = os.path.join(project_dir, ".claude", "governance", "access-policy.json")
    if os.path.exists(policy_file):
        with open(policy_file) as f:
            policy = json.load(f)
        members = policy.get("members", {})
        for member_email, member_role in members.items():
            if member_email.lower() == git_email:
                role = member_role
                break
        else:
            role = policy.get("default_role", "junior")

    role_desc = {
        "junior": "junior — 제한적 (prod 접근 불가, DB/S3 불가)",
        "senior": "senior — prod 읽기 가능, DB/S3 읽기 전용",
        "lead": "lead — 대부분 허용 (시크릿 하드코딩/파괴적 명령만 차단)",
    }
    role_display = role_desc.get(role, f"{role} — 정의되지 않은 역할 (junior로 취급)")
    role_display = f"{role_display} ({git_email})"

    # ── 피드백 루프: 과거 세션 교훈 ──
    learnings = "(없음)"
    learnings_file = os.path.join(project_dir, ".claude", ".learnings")
    if os.path.exists(learnings_file):
        with open(learnings_file) as f:
            content = f.read().strip()
            if content:
                learnings = content

    # ── harness-doctor 진단 ──
    health_results = check_harness_health(project_dir)
    passed = sum(1 for _, status, _ in health_results if status == "OK")
    total = len(health_results)

    health_table = "| # | 항목 | 상태 | 비고 |\n|---|------|------|------|\n"
    for i, (item, status, note) in enumerate(health_results, 1):
        health_table += f"| {i} | {item} | {status} | {note} |\n"

    # ── 세션 편집 카운터 초기화 ──
    counter_file = os.path.join(project_dir, ".claude", ".edit-count")
    with open(counter_file, "w") as f:
        f.write("0")

    # ── 컨텍스트 메시지 구성 ──
    context = f"""## 프로젝트 현재 상태
**브랜치**: {branch}
**최근 커밋**:
{recent_commits}
**변경 사항**:
{unstaged}
**빌드 상태**: {build_status}
**접근 레벨**: {role_display}
**알려진 실패 테스트**: {failing_tests}
**과거 세션 교훈**:
{learnings}

## 하네스 진단 (harness-doctor)

{health_table}
**전체: {passed}/{total} 통과**

## 활성 하네스 요약

| Layer | 역할 | 자동 실행 |
|-------|------|----------|
| **Session Start** | 컨텍스트 주입 + 하네스 진단 (지금 실행됨) | O |
| **가드레일** | 위험 명령/시크릿 차단 (PreToolUse) | O |
| **데이터 거버넌스** | 민감 파일/PII 차단 (PreToolUse) | O |
| **코드 스타일** | 컨벤션 피드백 — 즉시 (PostToolUse) | O |
| **API 스펙** | Controller/DTO 수정 시 spec 자동 갱신 (PostToolUse) | O |
| **출력 검증** | Spotless 포매팅 + 컴파일 — debounce 30s (PostToolUse) | O |
| **피드백 루프** | 실패 교훈 축적 → 다음 세션 주입 (PostToolUse) | O |
| **감사 로그** | 모든 도구 호출 JSONL 기록 (PostToolUse) | O |
| **Stop Gate** | 세션 종료 전 빌드 검증 (Stop) | O |

## 코드 작성 시 따를 패턴
- Controller -> Service -> Client 계층 구조
- @RequiredArgsConstructor 생성자 주입 (@Autowired 금지)
- @Slf4j 로거 (System.out 금지)
- Record 타입으로 DTO 생성
- application.yml 시크릿은 ${{ENV_VAR}} 참조
- API 작업 시 docs/api-spec.yml을 먼저 참조
- 상세한 패턴은 .claude/rules/ 참조"""

    output = {"hookSpecificOutput": context}
    print(json.dumps(output))


if __name__ == "__main__":
    main()
