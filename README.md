# KillBug

Slack 에러 스레드를 분석하여 Linear 티켓을 자동 생성하고, Claude Code로 버그 수정 PR까지 만드는 시스템.

## 구조

| 모듈 | 포트 | 역할 |
|------|------|------|
| **webhook-server** | 8080 | Slack/Linear 웹훅 수신, 스레드 분석, 티켓 생성 |
| **worker** | 8081 | 이슈 할당 시 Claude Code로 코드 분석/수정, Draft PR 생성 |

## 흐름

```
Slack 에러 스레드 → webhook-server (분석 + Linear 티켓 생성)
                 → worker (Claude Code 실행 → Git push → Draft PR)
                 → Slack/Linear 결과 회신
```

## 실행

```
./gradlew :webhook-server:bootRun
./gradlew :worker:bootRun
```

## 환경변수

| 변수 | 설명 |
|------|------|
| `SLACK_BOT_TOKEN` | Slack Bot 토큰 |
| `SLACK_SIGNING_SECRET` | Slack 서명 검증 시크릿 |
| `LINEAR_API_KEY` | Linear API 키 |
| `GH_TOKEN` | GitHub 토큰 (PR 생성용) |

## 기술 스택

- Java 21, Spring Boot 3.5
- Claude Code CLI
- Linear GraphQL API, Slack API, GitHub CLI
