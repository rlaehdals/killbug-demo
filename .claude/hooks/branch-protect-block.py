"""PreToolUse(Edit|Write) hook — 보호 브랜치 하드 블록.

main 브랜치에서 직접 편집을 차단한다 (exit 2).
feature 브랜치를 만들어 작업하도록 유도.
"""

import subprocess
import sys


def current_branch():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def main():
    sys.stdin.read()
    branch = current_branch()
    if branch == "main":
        print(
            f"[branch-protect] '{branch}'은 보호 브랜치입니다 — feature 브랜치를 만들어 작업하세요.",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
