#!/bin/sh
# =============================================================================
# 하네스 무결성 Git hook 설치 스크립트
# 클론 후 한 번 실행: bash .claude/scripts/setup-hooks.sh
# =============================================================================

set -e

PROJECT_DIR="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$PROJECT_DIR/.claude/git-hooks"

git config core.hooksPath "$HOOKS_DIR"
chmod +x "$HOOKS_DIR"/*

echo "Git hooks 설치 완료. core.hooksPath = $HOOKS_DIR"
echo "Pre-push 하네스 무결성 검증이 활성화되었습니다."
