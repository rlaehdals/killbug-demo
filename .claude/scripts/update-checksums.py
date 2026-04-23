#!/usr/bin/env python3
# =============================================================================
# [하네스 무결성] 체크섬 매니페스트 생성 스크립트
#
# 하네스 파일의 SHA-256 해시를 계산하여 매니페스트에 저장한다.
# 하네스 파일을 수정한 후 이 스크립트를 실행하고 매니페스트를 함께 커밋한다.
#
# 사용법: python3 .claude/scripts/update-checksums.py
# =============================================================================
import hashlib, json, os, sys
from datetime import datetime, timezone

HARNESS_FILES = [
    # settings
    ".claude/settings.json",
    # hooks (9)
    ".claude/hooks/guardrail-check.py",
    ".claude/hooks/data-governance-check.py",
    ".claude/hooks/plan-gate.py",
    ".claude/hooks/code-style-check.py",
    ".claude/hooks/output-verify.py",
    ".claude/hooks/feedback-loop.py",
    ".claude/hooks/audit.py",
    ".claude/hooks/session-start.py",
    ".claude/hooks/stop-final-check.py",
    # scripts (3)
    ".claude/scripts/api-spec-update.py",
    ".claude/scripts/update-checksums.py",
    ".claude/scripts/setup-hooks.sh",
    # governance (1)
    ".claude/governance/access-policy.json",
    # agents (8)
    ".claude/agents/task-planner.md",
    ".claude/agents/code-reviewer.md",
    ".claude/agents/change-validator.md",
    ".claude/agents/performance-checker.md",
    ".claude/agents/security-auditor.md",
    ".claude/agents/harness-doctor.md",
    ".claude/agents/test-generator.md",
    ".claude/agents/dependency-checker.md",
    # rules (5)
    ".claude/rules/java-spring-conventions.md",
    ".claude/rules/code-templates.md",
    ".claude/rules/jpa-conventions.md",
    ".claude/rules/database-schema.md",
    ".claude/rules/api-spec-guide.md",
    # git-hooks (1)
    ".claude/git-hooks/pre-push",
    # commands (1)
    ".claude/commands/setup.md",
    # project root
    "CLAUDE.md",
]

MANIFEST_PATH = ".claude/harness-checksums.json"


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    os.chdir(project_dir)

    # 이전 매니페스트 로드 (변경 비교용)
    old_files = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            old_files = json.load(f).get("files", {})

    # 해시 계산
    new_files = {}
    missing = []
    for rel_path in HARNESS_FILES:
        if not os.path.exists(rel_path):
            missing.append(rel_path)
            continue
        new_files[rel_path] = sha256_file(rel_path)

    if missing:
        print(f"ERROR: 하네스 파일 누락: {missing}", file=sys.stderr)
        sys.exit(1)

    # 매니페스트 생성
    manifest = {
        "version": 1,
        "algorithm": "sha256",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "update-checksums.py",
        "files": new_files,
    }

    # 원자적 쓰기
    tmp_path = MANIFEST_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, MANIFEST_PATH)

    # 변경 사항 출력
    changed = [p for p in HARNESS_FILES if old_files.get(p) != new_files.get(p)]
    if changed:
        print(f"체크섬 {len(changed)}개 갱신:")
        for p in changed:
            status = "NEW" if p not in old_files else "CHANGED"
            print(f"  [{status}] {p}")
    else:
        print("변경된 체크섬 없음.")

    print(f"매니페스트 저장: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
