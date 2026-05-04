#!/usr/bin/env python3
# =============================================================================
# [커밋 메시지 검증] PostToolUse Hook
# git commit 실행 시:
#   1. Conventional Commits 형식 준수 여부 검증
#   2. 커밋 타입과 변경 파일 범위 일관성 검사
# fail-open — 에러 시 통과 (피드백 영역)
# =============================================================================
import json
import sys
import re
import subprocess
import os

# Conventional Commits 정규식
# <type>[optional scope]: <description>
CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[a-zA-Z0-9_\-/]+)\))?"
    r"(?P<breaking>!)?"
    r":\s+(?P<desc>.+)$"
)

VALID_TYPES = {
    "feat", "fix", "docs", "style", "refactor", "perf",
    "test", "build", "ci", "chore", "revert",
}

# 타입별 예상 변경 파일 패턴
TYPE_FILE_RULES = {
    "feat": {
        "warn_only": ["Test.java"],
        "reason": "feat인데 테스트 파일만 변경됨 — 실제 기능 코드가 포함되어야 합니다",
    },
    "fix": {
        "warn_only": ["Test.java"],
        "reason": "fix인데 테스트 파일만 변경됨 — 수정 대상 코드가 포함되어야 합니다",
    },
    "test": {
        "warn_no_test": True,
        "reason": "test인데 테스트 파일이 없음 — *Test.java 파일이 포함되어야 합니다",
    },
    "docs": {
        "warn_java": True,
        "reason": "docs인데 Java 소스 파일이 변경됨 — 문서만 변경하거나 타입을 재검토하세요",
    },
    "style": {
        "warn_logic": True,
        "reason": "style은 포매팅/공백/세미콜론 등만 변경해야 합니다 — 로직 변경이 감지되면 타입을 재검토하세요",
    },
}


def extract_commit_message(command):
    """Bash 명령에서 git commit 메시지를 추출한다."""
    if not command:
        return None

    # git commit -m "message" 또는 git commit -m 'message'
    match = re.search(r'git\s+commit\s+.*-m\s+["\'](.+?)["\']', command)
    if match:
        return match.group(1)

    # git commit -m message (따옴표 없이)
    match = re.search(r"git\s+commit\s+.*-m\s+(\S+)", command)
    if match:
        return match.group(1)

    # HEREDOC 패턴: git commit -m "$(cat <<'EOF' ... EOF )"
    match = re.search(
        r"git\s+commit\s+.*-m\s+\"\$\(cat\s+<<'?EOF'?\s*\n(.+?)\nEOF",
        command,
        re.DOTALL,
    )
    if match:
        # 첫 번째 줄만 (제목 라인)
        first_line = match.group(1).strip().split("\n")[0].strip()
        return first_line

    return None


def get_staged_files():
    """스테이징된 파일 목록을 반환한다."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        pass

    # 커밋 직후라면 마지막 커밋의 파일 목록
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        pass

    return []


def validate_format(message):
    """Conventional Commits 형식 검증."""
    issues = []
    first_line = message.split("\n")[0].strip()

    match = CC_PATTERN.match(first_line)
    if not match:
        # 어떤 부분이 잘못되었는지 더 구체적으로 안내
        if ":" not in first_line:
            issues.append(
                "Conventional Commits 형식 위반: 콜론(:)이 없습니다. "
                "형식: `<type>(<scope>): <description>`"
            )
        elif not re.match(r"^[a-z]+", first_line):
            issues.append(
                "Conventional Commits 형식 위반: 타입은 소문자로 시작해야 합니다. "
                f"유효한 타입: {', '.join(sorted(VALID_TYPES))}"
            )
        else:
            type_part = first_line.split(":")[0].split("(")[0].rstrip("!")
            if type_part not in VALID_TYPES:
                issues.append(
                    f"유효하지 않은 커밋 타입: `{type_part}`. "
                    f"유효한 타입: {', '.join(sorted(VALID_TYPES))}"
                )
            else:
                issues.append(
                    "Conventional Commits 형식 위반: `<type>(<scope>): <description>` "
                    "형식을 따라야 합니다. 콜론 뒤에 공백이 필요합니다."
                )
        return issues, None

    # 설명 길이 검증
    desc = match.group("desc")
    if len(first_line) > 72:
        issues.append(
            f"커밋 제목이 너무 깁니다 ({len(first_line)}자). 72자 이내로 작성하세요."
        )

    if desc and desc[0].isupper():
        issues.append("커밋 설명은 소문자로 시작해야 합니다.")

    if desc and desc.endswith("."):
        issues.append("커밋 설명 끝에 마침표를 붙이지 마세요.")

    return issues, match


def validate_type_file_consistency(commit_type, files):
    """커밋 타입과 변경된 파일 범위의 일관성 검사."""
    warnings = []

    if not files or commit_type not in TYPE_FILE_RULES:
        return warnings

    rules = TYPE_FILE_RULES[commit_type]
    java_files = [f for f in files if f.endswith(".java")]
    test_files = [f for f in java_files if f.endswith("Test.java")]
    source_files = [f for f in java_files if not f.endswith("Test.java")]

    # feat/fix: 테스트 파일만 변경된 경우
    if "warn_only" in rules and java_files:
        non_test = [f for f in java_files if not any(f.endswith(p) for p in rules["warn_only"])]
        if not non_test and test_files:
            warnings.append(rules["reason"])

    # test: 테스트 파일이 없는 경우
    if rules.get("warn_no_test") and java_files and not test_files:
        warnings.append(rules["reason"])

    # docs: Java 소스 파일이 변경된 경우
    if rules.get("warn_java") and source_files:
        warnings.append(rules["reason"])

    return warnings


def main():
    hook_input = json.loads(sys.stdin.read())
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Bash 도구의 git commit 명령만 대상
    if tool_name != "Bash":
        return

    command = tool_input.get("command", "")
    if "git commit" not in command or "git commit --amend" in command:
        return

    # 커밋 메시지 추출
    message = extract_commit_message(command)
    if not message:
        return

    # Co-Authored-By 라인은 제거 후 검증
    clean_message = re.sub(
        r"\s*Co-Authored-By:.*$", "", message, flags=re.MULTILINE
    ).strip()

    if not clean_message:
        return

    feedback_parts = []

    # 1. 형식 검증
    format_issues, match = validate_format(clean_message)
    if format_issues:
        feedback_parts.append(
            "[Commit Message] 형식 문제:\n"
            + "\n".join(f"  - {issue}" for issue in format_issues)
        )

    # 2. 타입-파일 일관성 검증 (형식이 올바를 때만)
    if match:
        commit_type = match.group("type")
        files = get_staged_files()
        consistency_warnings = validate_type_file_consistency(commit_type, files)
        if consistency_warnings:
            feedback_parts.append(
                "[Commit Message] 타입-파일 불일치 경고:\n"
                + "\n".join(f"  - {w}" for w in consistency_warnings)
            )

    if feedback_parts:
        output = "\n".join(feedback_parts)
        output += "\n\nConventional Commits 형식: `<type>(<scope>): <description>`"
        print(json.dumps({"hookSpecificOutput": output}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # PostToolUse 훅은 fail-open
        pass
