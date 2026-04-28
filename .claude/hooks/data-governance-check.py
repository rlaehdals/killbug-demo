#!/usr/bin/env python3
# =============================================================================
# [데이터 거버넌스] PreToolUse Hook
#
# 2가지 레이어로 동작한다:
#   1) 공통 규칙 — 모든 역할에게 적용 (시크릿 파일, PII)
#   2) 역할 기반 규칙 — access-policy.json에 따라 차등 적용
#
# 역할 결정 우선순위:
#   1. KILLBUG_ROLE 환경변수
#   2. .claude/.developer-role 파일
#   3. 기본값: "junior" (제한적)
# =============================================================================
import json, sys, os, re, subprocess
from datetime import datetime

_tool_name = ""
_tool_input = {}

def log_block(reason):
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    audit_dir = os.path.join(project_dir, ".private", "audit")
    os.makedirs(audit_dir, exist_ok=True)

    input_summary = json.dumps(_tool_input, ensure_ascii=False)
    if len(input_summary) > 300:
        input_summary = input_summary[:300] + "..."

    entry = {
        "ts": datetime.now().isoformat(),
        "hook": "governance",
        "tool": _tool_name,
        "input": input_summary,
        "reason": reason
    }
    with open(os.path.join(audit_dir, "blocked.jsonl"), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def block(reason):
    log_block(reason)
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)

def get_git_email():
    """git config user.email을 읽는다."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().lower()
    except Exception:
        return ""

def get_role(policy):
    """git email → members 매핑으로 역할을 결정한다."""
    default_role = "junior"
    if policy:
        default_role = policy.get("default_role", "junior")

    # 1. git email → members 매핑 (신뢰할 수 있는 소스)
    email = get_git_email()
    if email and policy:
        members = policy.get("members", {})
        # 대소문자 무시 매핑
        for member_email, role in members.items():
            if member_email.lower() == email:
                return role, email

    # 2. 매핑에 없으면 기본값 (제한적)
    return default_role, email or "unknown"

def load_policy():
    """access-policy.json을 로드한다."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    policy_file = os.path.join(project_dir, ".claude", "governance", "access-policy.json")
    if not os.path.exists(policy_file):
        return None
    with open(policy_file) as f:
        return json.load(f)

def main():
    global _tool_name, _tool_input
    hook_input = json.loads(sys.stdin.read())
    _tool_name = tool_name = hook_input.get("tool_name", "")
    _tool_input = tool_input = hook_input.get("tool_input", {})

    policy = load_policy()
    role, email = get_role(policy)

    # =========================================================================
    # Layer 1: 공통 규칙 (모든 역할에게 적용)
    # =========================================================================
    if tool_name in ("Read", "Edit", "Write"):
        file_path = tool_input.get("file_path", "")

        # application-prod 설정 파일 접근 차단
        if re.search(r'application-prod\.(yml|yaml)$', file_path):
            block("\U0001f512 [Governance] application-prod 설정 파일 접근 차단. 시크릿은 시스템 레벨에서 관리하세요.")

    if tool_name in ("Edit", "Write"):
        content = tool_input.get("new_string", "") if tool_name == "Edit" else tool_input.get("content", "")
        file_path = tool_input.get("file_path", "")

        # 로그에 PII 출력 차단
        if re.search(r'\.(java|kt)$', file_path):
            if re.search(r'log\.(info|warn|error|debug)\(.*\b(password|token|secret)\b', content):
                block("\U0001f512 [Governance] Logging PII detected. Mask sensitive data before logging.")

        # 주민등록번호 패턴 차단 (테스트 파일 제외)
        if not re.search(r'(test/|Test\.java$)', file_path):
            if re.search(r'"[0-9]{6}-[0-9]{7}"', content):
                block("\U0001f512 [Governance] Resident registration number pattern detected.")

    # =========================================================================
    # Layer 2: 테이블 레벨 접근 제어 (allowed_tables 기반)
    # =========================================================================
    if not policy:
        return
    allowed_tables = policy.get("allowed_tables", {}).get(role)
    if allowed_tables is not None:
        all_tables = set()
        for tables in policy.get("allowed_tables", {}).values():
            all_tables.update(tables)
        denied_tables = all_tables - set(allowed_tables)

        if denied_tables and tool_name == "Bash":
            command = tool_input.get("command", "")
            for table in denied_tables:
                # DB 쿼리에서 테이블 접근 차단 (psql, docker exec psql, curl API)
                if re.search(rf'\b{table}\b', command, re.IGNORECASE):
                    block(
                        f"\U0001f512 [Governance] Role '{role}' cannot access table '{table}'.\n"
                        f"Allowed tables: {', '.join(allowed_tables)}\n"
                        f"This data requires higher access level."
                    )


    # =========================================================================
    # Layer 3: LLM 유출 방지 (모든 역할에게 적용)
    # Claude Code가 읽은 데이터는 외부 LLM API로 전송된다.
    # 민감 데이터가 포함된 쿼리/파일 읽기를 사전에 차단한다.
    # =========================================================================
    llm_blocked = policy.get("llm_blocked", {})

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # 민감 데이터를 반환하는 DB 쿼리 차단
        for pattern in llm_blocked.get("sensitive_bash_patterns", []):
            if re.search(pattern, command, re.IGNORECASE):
                block(
                    "\U0001f6e1 [LLM 유출 방지] 이 명령의 결과에 민감 데이터가 포함될 수 있습니다.\n"
                    f"Blocked pattern: {pattern}\n"
                    "Claude Code가 읽은 데이터는 외부 LLM API로 전송됩니다.\n"
                    "민감 데이터를 직접 조회하지 말고, 애플리케이션 API를 통해 마스킹된 형태로 접근하세요."
                )

        # 민감 컬럼을 SELECT하는 쿼리 차단
        for col in llm_blocked.get("sensitive_columns", []):
            if re.search(rf'SELECT\b.*\b{col}\b', command, re.IGNORECASE):
                block(
                    f"\U0001f6e1 [LLM 유출 방지] 민감 컬럼 '{col}'이 포함된 쿼리입니다.\n"
                    "이 데이터는 외부 LLM으로 전송될 수 있습니다.\n"
                    "SELECT에서 민감 컬럼을 제외하거나, 마스킹 처리하세요."
                )

    if tool_name in ("Read",):
        file_path = tool_input.get("file_path", "")
        # 민감 데이터 파일 읽기 차단
        for pattern in llm_blocked.get("sensitive_file_patterns", []):
            if re.search(pattern, file_path, re.IGNORECASE):
                block(
                    f"\U0001f6e1 [LLM 유출 방지] 민감 데이터 파일입니다: {file_path}\n"
                    "이 파일의 내용이 외부 LLM API로 전송됩니다.\n"
                    "직접 읽지 말고, 필요한 정보만 애플리케이션 로직으로 처리하세요."
                )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({
            "decision": "block",
            "reason": f"\U0001f512 [거버넌스] 훅 실행 중 오류 발생 (fail-closed): {e}"
        }))
        sys.exit(0)
