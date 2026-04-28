# KillBug - 에러 자동 수정 워크플로우

## 프로젝트 개요

Slack 에러 스레드 감지 -> Claude 분석 -> Linear 티켓 생성 -> 자동 수정 Draft PR 생성

## 아키텍처

- **webhook-server** (port 8080): Slack/Linear 웹훅 수신, 스레드 분석, 티켓 생성
- **worker** (port 8081): 이슈 처리, worktree 기반 Claude Code 실행, Draft PR 생성
- Spring Boot 3.5 / Java 21 / Gradle 멀티모듈

## 빌드 & 실행

```bash
./gradlew :webhook-server:build
./gradlew :worker:build
./gradlew :webhook-server:bootRun   # port 8080
./gradlew :worker:bootRun           # port 8081
```

## 보안 규칙

- Slack 웹훅: HmacSHA256 서명 검증 필수 (5분 윈도우)
- Process 실행: `ProcessBuilder` 사용, 사용자 입력 직접 삽입 금지
- API 키: 환경변수로만 관리 (`SLACK_BOT_TOKEN`, `LINEAR_API_KEY`, `GH_TOKEN`)
- Draft PR만 자동 생성 (머지는 사람이 검토)

## 환경변수

| 변수명 | 용도 |
|--------|------|
| `SLACK_BOT_TOKEN` | Slack Bot 토큰 |
| `SLACK_SIGNING_SECRET` | Slack 서명 검증 시크릿 |
| `LINEAR_API_KEY` | Linear API 키 |
| `GH_TOKEN` | GitHub Personal Access Token |

## 하네스

가드레일, 데이터 거버넌스, 평가, 코드 스타일, API 스펙 자동 갱신을 자동화하는 훅 파이프라인.
상세 원칙과 파이프라인 구조는 `.claude/references/harness-guide.md` 참조.

### 코드 작성 시 따를 패턴
- Controller -> Service -> Client 계층 구조
- @RequiredArgsConstructor 생성자 주입 (@Autowired 금지)
- @Slf4j 로거 (System.out 금지)
- Record 타입으로 DTO 생성
- application.yml 시크릿은 ${ENV_VAR} 참조
- API 작업 시 docs/api-spec.yml을 먼저 참조

### 에이전트

| 에이전트 | 용도 | 호출 |
|---------|------|------|
| `task-planner` | 실행 계획 수립 | "플랜 세워줘" |
| `code-reviewer` | 코드 리뷰 (50점) | "코드 리뷰해줘" / Java 5개+ 자동 |
| `change-validator` | 논리적 정합성 검증 | "변경 검증해줘" / Stop 자동 |
| `performance-checker` | 성능 안티패턴 탐지 | "성능 검사해줘" / Stop 자동 |
| `security-auditor` | OWASP Top 10 감사 | "보안 감사해줘" / Stop 자동 |
| `test-generator` | JUnit 5 테스트 생성 | "테스트 생성해줘" / Stop 자동 |
| `dependency-checker` | 의존성 취약점 스캔 | "의존성 검사해줘" / Stop 자동 |
| `harness-doctor` | 하네스 상태 진단 | "하네스 확인해줘" / SessionStart 자동 |

### 슬래시 커맨드

| 커맨드 | 용도 |
|--------|------|
| `/setup` | 프로젝트 환경 자동 점검 + 설정 |
