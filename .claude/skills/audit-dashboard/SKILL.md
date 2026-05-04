---
name: audit-dashboard
description: 감사 로그 대시보드 생성. 도구 호출 통계, 차단 내역, 세션별 활동을 HTML로 시각화한다.
effort: low
argument-hint: "[days]"
allowed-tools: Bash(python3 *) Read
---

# Audit Dashboard

감사 로그(.private/audit/)를 분석하여 HTML 대시보드를 생성한다.

**Arguments: $ARGUMENTS**

## Steps

1. `python3 ${CLAUDE_SKILL_DIR}/dashboard.py`를 실행한다.
   - 인자가 있으면 최근 N일만 분석: `python3 ${CLAUDE_SKILL_DIR}/dashboard.py --days N`
   - 기본값: 전체 기간
2. 생성된 HTML 파일 경로를 사용자에게 안내한다.
3. `open` 명령으로 브라우저에서 열어준다.

## Output

`.private/audit/dashboard.html` 파일이 생성된다.
