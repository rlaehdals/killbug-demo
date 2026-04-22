#!/usr/bin/env python3
# =============================================================================
# [가드레일] PreToolUse Hook
# 위험한 명령 실행, 시크릿 하드코딩, 파괴적 작업을 사전에 차단한다.
# 차단 시 .claude/audit/blocked.jsonl에 이유와 함께 기록한다.
# =============================================================================
import json, sys, re, os
from datetime import datetime

def log_block(tool_name, tool_input, reason):
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    audit_dir = os.path.join(project_dir, ".claude", "audit")
    os.makedirs(audit_dir, exist_ok=True)

    input_summary = json.dumps(tool_input, ensure_ascii=False)
    if len(input_summary) > 300:
        input_summary = input_summary[:300] + "..."

    entry = {
        "ts": datetime.now().isoformat(),
        "hook": "guardrail",
        "tool": tool_name,
        "input": input_summary,
        "reason": reason
    }
    with open(os.path.join(audit_dir, "blocked.jsonl"), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def main():
    hook_input = json.loads(sys.stdin.read())
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    def block(reason):
        log_block(tool_name, tool_input, reason)
        print(json.dumps({"decision": "block", "reason": reason}))
        sys.exit(0)

    # =========================================================================
    # Bash 명령어 가드레일
    # =========================================================================
    if tool_name == "Bash":
        command = tool_input.get("command", "")

        # 보호 파일 접근 차단 — 어떤 명령이든 보호 파일명이 포함되면 차단
        # cat, sed, awk, grep, python3, cp, mv, base64, xxd 등 모든 우회 방지
        protected_patterns = [
            (r'application-prod\.(yml|yaml)', "application-prod 설정 파일"),
            (r'\.claude/(settings|hooks|governance)', "하네스 설정 파일"),
            (r'(credentials|credential)\.(json|yml|yaml)', "크레덴셜 파일"),
        ]
        for pattern, desc in protected_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                # 허용 목록: 보호 파일을 직접 읽는 게 아닌 명령은 통과
                safe_prefixes = ["echo", "git add", "git status", "git diff", "ls"]
                is_safe = any(command.strip().startswith(p) for p in safe_prefixes)
                if not is_safe:
                    block(f"\U0001f6ab [가드레일] Bash 명령에 보호 대상({desc})이 포함되어 있습니다.")

        # 보호 파일 복사/이동/이름변경 차단
        if re.search(r'(cp|mv|ln)\s+.*application-prod\.(yml|yaml)', command):
            block("\U0001f6ab [가드레일] 보호 파일(application-prod.yaml)을 복사/이동/링크할 수 없습니다.")

        if re.search(r'git\s+(push\s+(-f|--force)|reset\s+--hard|clean\s+-fd|branch\s+-D)', command):
            block("\U0001f6ab [가드레일] git force push, hard reset, clean, branch -D는 금지된 명령입니다.")

        if re.search(r'rm\s+(-rf|-fr)\s+(/|~/|\$HOME)', command):
            block("\U0001f6ab [가드레일] 루트 또는 홈 디렉토리 삭제는 금지된 명령입니다.")

        if re.search(r'(DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE)', command, re.IGNORECASE):
            block("\U0001f6ab [가드레일] DROP/TRUNCATE SQL 명령이 감지되었습니다.")

        if re.search(r'(kill\s+-9\s+-1|killall)', command):
            block("\U0001f6ab [가드레일] 무차별 프로세스 종료는 금지된 명령입니다.")

    # =========================================================================
    # Edit/Write 콘텐츠 가드레일
    # =========================================================================
    if tool_name in ("Edit", "Write"):
        content = tool_input.get("new_string", "") if tool_name == "Edit" else tool_input.get("content", "")
        file_path = tool_input.get("file_path", "")

        # Java/Kotlin 소스에서 시크릿 하드코딩 검사
        if re.search(r'\.(java|kt|scala)$', file_path):
            if re.search(r'(password|secret|token|api[_\-]?key)\s*=\s*"[^$\{][^"]{8,}"', content, re.IGNORECASE):
                block("\U0001f6ab [가드레일] Java 소스에 시크릿이 하드코딩되어 있습니다. 환경변수를 사용하세요.")

            if re.search(r'AKIA[0-9A-Z]{16}', content):
                block("\U0001f6ab [가드레일] AWS Access Key가 코드에 포함되어 있습니다. 환경변수를 사용하세요.")

        # YAML/Properties 설정 파일에서 시크릿 하드코딩 검사
        if re.search(r'\.(yml|yaml|properties)$', file_path):
            for match in re.finditer(
                r'(password|secret|token|api[_\-]?key)[:\s]+\$\{[^}]+:([^}]{8,})\}',
                content, re.IGNORECASE
            ):
                default_val = match.group(2).strip()
                if default_val and default_val.upper() != "CHANGE":
                    block(
                        "\U0001f6ab [가드레일] 설정 파일에 시크릿 디폴트 값이 하드코딩되어 있습니다: "
                        f"'{default_val[:20]}...'\n"
                        "${ENV_VAR:CHANGE} 또는 ${ENV_VAR} 형태로 수정하세요."
                    )

            for match in re.finditer(
                r'(password|secret|token|api[_\-]?key)[:\s]+(?!\$\{)([^\s\n#]{8,})',
                content, re.IGNORECASE
            ):
                val = match.group(2).strip()
                if val and val.upper() != "CHANGE":
                    block(
                        "\U0001f6ab [가드레일] 설정 파일에 시크릿이 직접 기입되어 있습니다: "
                        f"'{val[:20]}...'\n"
                        "${ENV_VAR} 형태로 환경변수를 참조하세요."
                    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 보안 훅은 fail-closed: 에러 나면 차단
        print(json.dumps({
            "decision": "block",
            "reason": f"\U0001f6ab [가드레일] 훅 실행 중 오류 발생 (fail-closed): {e}"
        }))
        sys.exit(0)
