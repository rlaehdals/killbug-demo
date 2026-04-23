# KillBug - 에러 자동 수정 워크플로우

## 프로젝트 개요

Slack 에러 스레드 감지 -> Claude 분석 -> Linear 티켓 생성 -> 자동 수정 Draft PR 생성

```
Slack Error Thread
  -> webhook-server (분석 + Linear 티켓 생성)
  -> worker (Claude Code 수정 -> Git push -> Draft PR)
  -> 결과를 Slack & Linear에 보고
```

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

---

# 하네스 엔지니어링 원칙

> 숙련도가 낮거나 높은 개발자의 격차를 줄이고, 데이터를 안전하게 지키기 위한 제어 구조.
> hooks와 agents를 통해 **제어(Control)**, **감시(Monitoring)**, **개선(Feedback)** 을 자동화한다.

## 1. 가드레일 (Guardrail)

입력과 출력 양쪽을 기술적으로 제어하여 설계된 목적 범위 밖의 동작을 사전에 차단한다.

**PreToolUse 훅 (`guardrail-check.py`)이 자동으로 차단하는 항목:**

- 위험한 git 명령: `push --force`, `reset --hard`, `clean -fd`, `branch -D`
- 파괴적 파일 명령: `rm -rf /`, 루트/홈 삭제
- 위험한 SQL: `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`
- 시크릿 하드코딩: Java 소스/YAML/Properties에 시크릿 직접 기입
- 보호 파일 Bash 우회: `sed/awk/grep/python3/base64 application-prod.yaml` 등 우회 차단
- 보호 파일 복사/이동: `cp/mv/ln application-prod.yaml` 차단

**하네스 자기 보호** (`settings.json` deny):
- `.claude/settings.json` — 훅 파이프라인 수정 불가
- `.claude/hooks/**` — 훅 스크립트 수정 불가
- `.claude/governance/**` — 접근 정책 수정 불가
- `.claude/rules/**` — 코드 컨벤션 규칙 수정 불가
- `CLAUDE.md` — 프로젝트 원칙 수정 불가

**에러 핸들링:**
- PreToolUse 훅 (guardrail, governance): **fail-closed** — 에러 시 차단
- PostToolUse 훅 (style, audit): **fail-open** — 에러 시 통과

**개발자가 지켜야 할 규칙:**
- 환경변수 또는 시크릿 매니저를 사용한다 (`${ENV_VAR}` 형태)
- 외부 입력을 명령어에 직접 삽입하지 않는다 (Command Injection 방지)
- SQL 쿼리에 사용자 입력을 직접 연결하지 않는다 (SQL Injection 방지)

## 2. 데이터 거버넌스 (Data Governance)

조직 차원에서 AI가 사용하는 데이터를 통일된 기준으로 관리한다.
**3단계 구조**: 공통 규칙 + 역할 기반 접근 제어 + LLM 유출 방지.

### 공통 규칙 (모든 역할에게 적용)

- `application-prod.yaml`, credentials 파일 접근 차단
- 로그에 PII 출력 차단 (password, token 등)
- settings.json deny: `application-prod*`, `**/credential*`

### 역할 기반 접근 제어 (`.claude/governance/access-policy.json`)

| 테이블 | junior | senior | lead  |
|--------|--------|--------|-------|
| `junior` | 접근 가능 | 접근 가능 | 접근 가능 |
| `senior` | **차단** | 접근 가능 | 접근 가능 |
| `lead` | **차단** | **차단** | 접근 가능 |

DB 쿼리, API 호출 모두 테이블 단위로 제어된다.

### LLM 유출 방지 (모든 역할 — lead 포함)

Claude Code가 읽은 데이터는 외부 LLM API로 전송된다. 아래 패턴은 역할과 무관하게 전부 차단된다:
- 민감 테이블 쿼리: `SELECT * FROM users/customer/payment/salary/account`
- 민감 컬럼 조회: `SELECT password/ssn/salary/credit_card/phone ...`
- DB 덤프: `pg_dump`, `mysqldump`
- 민감 파일: `*customer*.csv`, `*salary*`, `*payment*.csv`, `*dump*.sql`

**역할은 git email로 자동 결정된다:**
- `git config user.email` → `access-policy.json`의 `members` 매핑에서 역할 조회
- 매핑에 없는 이메일 → 기본값 `junior` (안전)
- 새 팀원 추가 시: `access-policy.json`의 `members`에 이메일과 역할을 추가

**개발자가 지켜야 할 규칙:**
- application-prod.yaml의 시크릿 값은 `${ENV_VAR:DEFAULT}` 형태로 참조
- 로그에 PII를 출력할 때 마스킹 처리
- 자신의 역할에 맞는 테이블만 접근
- 민감 데이터를 Claude Code로 직접 조회하지 않는다

## 3. 평가 (Evaluation)

에이전트의 동작과 출력을 추적하고, 발견된 문제를 다음 동작에 반영한다.

**자동 평가 메커니즘:**
- Worker의 confidence threshold (기본 0.8) — 임계값 미만이면 PR 미생성
- PostToolUse 훅 (`code-style-check.py`) — 스타일 위반 즉시 피드백
- 코드 리뷰 에이전트 (`code-reviewer.md`) — 구조적 품질 평가
- 변경 검증 에이전트 (`change-validator.md`) — 논리적 정합성 독립 검증 (API 계약, 데이터 흐름, 트랜잭션, 의존성 방향)
- 성능 검사 에이전트 (`performance-checker.md`) — 성능 안티패턴 탐지 (N+1, 무제한 조회, 리소스 누수, 동시성)
- 테스트 생성 에이전트 (`test-generator.md`) — 변경 코드 JUnit 5 테스트 자동 생성
- 의존성 검사 에이전트 (`dependency-checker.md`) — build.gradle 보안/호환성 검사

**코드 리뷰 에이전트 평가 항목:**
- 아키텍처 준수 (Controller -> Service -> Client 계층)
- 에러 처리 적절성
- 테스트 커버리지
- 보안 취약점
- 성능 영향

**작업 계획 수립 (PreToolUse — `plan-gate.py`):**
- 첫 Edit/Write 전에 `task-planner` 에이전트로 실행 계획 수립을 강제
- `.private/.task-plan-established` 파일이 존재하면 통과 (세션 시작 시 자동 삭제 → 매 세션 플랜 수립 강제)
- `.claude/` 내부 파일과 `*Test.java` 수정은 항상 허용
- fail-open — 에러 시 차단하지 않음 (품질 영역)

## 4. 코드 스타일 & 템플릿

코드 스타일과 생성 템플릿은 `.claude/rules/`에서 관리한다:

- **`.claude/rules/java-spring-conventions.md`** — Java/Spring 코드 컨벤션 (DI, 로깅, import, 예외 처리, 네이밍, 포매팅, 금지 패턴)
- **`.claude/rules/code-templates.md`** — 코드 생성 템플릿 (Controller, Service, Config, Client, DTO, 비동기, 프로세스 실행)
- **`.claude/rules/jpa-conventions.md`** — JPA Entity/Repository 컨벤션 (Entity 생성 규칙, 트랜잭션, 상태 변경 패턴)
- **`.claude/rules/database-schema.md`** — 데이터베이스 스키마 (테이블 정의, 컬럼, Entity 매핑, API 엔드포인트)
- **`.claude/rules/api-spec-guide.md`** — API 스펙 참조 규칙 (api-spec.yml 우선 참조, 자동 갱신 안내)

`code-style-check.py`(PostToolUse)가 컨벤션 위반을 **즉시 피드백**하고, 편집이 끝나면 `output-verify.py`가 **Spotless 포매팅 + 컴파일 검증**을 실행한다.

**즉시 피드백 (code-style-check.py):** `@Autowired`, `System.out`, `var`, `new Date()`, 빈 catch 블록
**debounce 후 자동 수정 (output-verify.py):** Spotless(palantir-java-format) import 순서, 들여쓰기, 미사용 import 제거 + incremental compile

Java 파일 5개 이상 수정 시 `code-reviewer` 에이전트 실행을 자동 트리거한다.

## 5. API 스펙 자동 갱신

Controller/DTO 파일 수정 시 PostToolUse 훅(`api-spec-update.py`)이 자동으로 API 스펙을 재생성한다.

**산출물:**
- `docs/api-spec.md` — Markdown 테이블 (소스 파일 경로 포함)
- `docs/api-spec.yml` — OpenAPI 3.0 YAML

**트리거 조건:** `controller/`, `request/`, `response/` 경로의 Java 파일 수정 시

**활용:** "이 API에 파라미터 추가해줘" → spec의 Source 경로로 즉시 점프 → 수정 → spec 자동 갱신

## 보안 규칙

- Slack 웹훅: HmacSHA256 서명 검증 필수 (5분 윈도우)
- Process 실행: `ProcessBuilder` 사용, 사용자 입력 직접 삽입 금지
- API 키: 환경변수로만 관리 (`SLACK_BOT_TOKEN`, `LINEAR_API_KEY`, `GH_TOKEN`)
- Draft PR만 자동 생성 (머지는 사람이 검토 후 수행)

## 환경변수

| 변수명 | 용도 |
|--------|------|
| `SLACK_BOT_TOKEN` | Slack Bot 토큰 |
| `SLACK_SIGNING_SECRET` | Slack 서명 검증 시크릿 |
| `LINEAR_API_KEY` | Linear API 키 |
| `GH_TOKEN` | GitHub Personal Access Token |

---

# 하네스 훅 파이프라인

블로그 3대 축: **제어(Control)** / **감시(Monitoring)** / **개선(Feedback)**

```
SessionStart ─────────────────────────────────────────────── [감시] 컨텍스트 주입 + harness-doctor 진단 + 플랜 상태 초기화
  │  git 상태 + 빌드 상태 + 접근 레벨 + 과거 세션 교훈 + 하네스 무결성 + 하네스 진단 + 플랜 파일 삭제
  ▼
PreToolUse ──── guardrail-check.py ──── [제어] 위험 명령/시크릿 차단
  │             data-governance-check.py ── [제어] 민감 파일/PII 차단
  │             plan-gate.py ────────────── [개선] 첫 Edit/Write 전 플랜 수립 강제
  ▼
[도구 실행]
  │
  ▼
PostToolUse ─── code-style-check.py ─── [제어] 컨벤션 피드백 (즉시) + 리뷰 트리거
  │             api-spec-update.py ──── [개선] API 스펙 자동 갱신
  │             output-verify.py ──────── [제어] Spotless 포매팅 + 컴파일 (debounce 30s)
  │             feedback-loop.py ──────── [개선] 실패 교훈 축적
  │             audit.py ──────────────── [감시] JSONL 감사 로그
  ▼
Stop ──────── stop-final-check.py ───── [제어] 보안 감사 트리거 (최대 3회)
  │                                      [개선] 테스트 생성 트리거 (소스 수정 + 테스트 미작성 시)
  │                                      [개선] 의존성 검사 트리거 (build.gradle 수정 시)
  │                                      [평가] 변경 검증 트리거 (Java 소스 3개+ 수정 시)
  │                                      [평가] 성능 검사 트리거 (Service/Repository/Entity 수정 시)
  │                                      [제어] 빌드 검증
  │                                      [감시] 검증 통과 시 트리거 상태 초기화
  ▼
[세션 종료]
```

## 에이전트 활용

| 에이전트 | 용도 | 호출 방법 |
|---------|------|----------|
| `task-planner` | 자연어 명령 → 구조화된 실행 계획 변환 | "플랜 세워줘", "계획 만들어줘", "작업 분해해줘" |
| `code-reviewer` | 5개 항목 코드 리뷰 (50점 평가) | "코드 리뷰해줘" 또는 Java 5개+ 수정 시 자동 트리거 |
| `change-validator` | 변경 코드 논리적 정합성 독립 검증 | "변경 검증해줘" 또는 Stop에서 Java 소스 3개+ 수정 시 자동 트리거 (1회) |
| `performance-checker` | 성능 안티패턴 탐지 (N+1, 리소스 누수 등) | "성능 검사해줘" 또는 Stop에서 Service/Repository/Entity 수정 시 자동 트리거 (1회) |
| `security-auditor` | OWASP Top 10 보안 감사 | "보안 감사해줘" 또는 Stop에서 보안 민감 파일 수정 시 자동 트리거 (최대 3회) |
| `harness-doctor` | 하네스 전체 상태 진단 (7항목) | "하네스 상태 확인해줘" 또는 SessionStart 자동 실행 |
| `test-generator` | 변경 코드 JUnit 5 테스트 자동 생성 | "테스트 생성해줘" 또는 Stop에서 Java 소스 수정 + 테스트 미작성 시 자동 트리거 (1회) |
| `dependency-checker` | build.gradle 의존성 취약점 스캔 | "의존성 검사해줘" 또는 Stop에서 build.gradle 수정 시 자동 트리거 (1회) |
