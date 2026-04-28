# KillBug

Slack 에러 스레드를 분석하여 Linear 티켓을 자동 생성하고, Claude Code로 버그 수정 Draft PR까지 만드는 시스템.
**하네스 엔지니어링**을 적용하여 AI 에이전트의 동작을 제어하고, 데이터를 보호하고, 코드 품질을 강제한다.

## 구조

| 모듈 | 포트 | 역할 |
|------|------|------|
| **webhook-server** | 8080 | Slack/Linear 웹훅 수신, 스레드 분석, 티켓 생성 |
| **worker** | 8081 | 이슈 할당 시 Claude Code로 코드 분석/수정, Draft PR 생성 |

```
Slack 에러 스레드 → webhook-server (분석 + Linear 티켓 생성)
                 → worker (Claude Code 실행 → Git push → Draft PR)
                 → Slack/Linear 결과 회신
```

## 기술 스택

- Java 21, Spring Boot 3.5, Gradle
- PostgreSQL 16 (Docker Compose)
- Claude Code CLI
- Linear GraphQL API, Slack API, GitHub CLI

## 실행

```bash
# PostgreSQL 컨테이너
docker compose up -d

# 애플리케이션
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

---

## 하네스 엔지니어링

AI 에이전트가 안전하고 예측 가능한 방식으로 작동하도록 설계된 제어 구조.
3대 축: **제어(Control)** / **감시(Monitoring)** / **개선(Feedback)**

### 훅 파이프라인

```
SessionStart ────────────────────── 컨텍스트 주입 + harness-doctor 자동 진단 + 플랜 상태 초기화
  ▼
PreToolUse
  ├── guardrail-check.py ────────── 위험 명령 / 시크릿 / Bash 우회 차단
  ├── data-governance-check.py ──── 공통 규칙 + 역할별 테이블 접근 + LLM 유출 방지
  └── plan-gate.py ────────────────── 첫 Edit/Write 전 플랜 수립 강제
  ▼
[도구 실행]
  ▼
PostToolUse
  ├── code-style-check.py ──────── 컨벤션 피드백 (즉시) + 5개+ 파일 시 code-reviewer 트리거
  ├── api-spec-update.py ───────── API 스펙 자동 갱신 (MD + OpenAPI YAML)
  ├── output-verify.py ─────────── Spotless 포매팅 + 컴파일 검증 (debounce 30s)
  ├── feedback-loop.py ─────────── 실패 교훈 축적 → 다음 세션 주입
  └── audit.py ─────────────────── JSONL 감사 로그
  ▼
Stop ── stop-final-check.py ────── 보안 감사 트리거 (최대 3회)
  │                                  테스트 생성 트리거 (소스 수정 + 테스트 미작성 시)
  │                                  의존성 검사 트리거 (build.gradle 수정 시)
  │                                  변경 검증 트리거 (Java 소스 3개+ 수정 시)
  │                                  성능 검사 트리거 (Service/Repository/Entity 수정 시)
  │                                  빌드 검증
  │                                  검증 통과 시 트리거 상태 초기화
```

### 데이터 거버넌스

**3-Layer 구조:**

| Layer | 대상 | 적용 |
|-------|------|------|
| 공통 규칙 | application-prod, credentials, PII 로깅 | 모든 역할 |
| 테이블 접근 | junior/senior/lead 테이블별 차등 | 역할별 |
| LLM 유출 방지 | 민감 쿼리, 컬럼, 파일 | 모든 역할 (lead 포함) |

**역할 결정:** `git config user.email` → `access-policy.json` 매핑 (미등록 = junior)

### 하네스 자기 보호

| 보호 수단 | 대상 |
|----------|------|
| `settings.json` deny | 하네스 파일 Edit/Write 차단 (hooks, governance, rules, CLAUDE.md) |
| `guardrail-check.py` | Bash로 보호 파일 읽기/복사 우회 차단 |
| SHA-256 체크섬 | `harness-checksums.json` + `pre-push` hook으로 수동 수정 탐지 |
| fail-closed | 보안 훅 에러 시 차단 (통과 아님) |

### 코드 품질

| 수단 | 역할 |
|------|------|
| `code-style-check.py` | `@Autowired`, `System.out`, `var` 등 컨벤션 피드백 (즉시) |
| `api-spec-update.py` | Controller/DTO 수정 시 `docs/api-spec.md` + `api-spec.yml` 자동 갱신 |
| `output-verify.py` | Spotless(palantir-java-format) 포매팅 + incremental compile (debounce 30s) |
| `plan-gate.py` | 첫 Edit/Write 전 task-planner 에이전트로 플랜 수립 강제 (fail-open) |
| `stop-final-check.py` | 세션 종료 전: 보안 감사 + 테스트 생성 + 의존성 + 변경 검증 + 성능 검사 + 빌드 검증 |
| `.claude/rules/*.md` | 핵심 규칙 slim 포인터 (상세 템플릿은 `.claude/references/`에서 on-demand 로드) |
| 피드백 루프 | 실패 교훈 축적 → 다음 세션 주입 + 규칙 점진적 추가 |

## 하네스 설치

```bash
# 전체 환경 자동 점검 + 설정 (권장)
/setup

# 또는 수동 설치
bash .claude/scripts/setup-hooks.sh        # git pre-push hook 활성화
python3 .claude/scripts/update-checksums.py # 체크섬 갱신
```

`/setup` 커맨드는 Java 21, Gradle, Docker, Git Hooks, 체크섬, 빌드를 한 번에 점검하고 자동 설정한다.

> `setup-hooks.sh`를 실행하지 않으면 pre-push hook이 비활성 상태다.
> git은 기본적으로 `.git/hooks/`를 보기 때문에, `.claude/git-hooks/`는 수동 설치가 필요하다.

## 디렉토리 구조

```
.claude/
├── settings.json                 # 훅 파이프라인 + deny 권한
├── harness-checksums.json        # SHA-256 체크섬 매니페스트
├── governance/
│   └── access-policy.json        # 역할-테이블 매핑 + 멤버 이메일 + LLM 유출 정책
├── hooks/
│   ├── session-start.py          # 컨텍스트 주입 + harness-doctor 자동 진단
│   ├── guardrail-check.py        # 위험 명령 / 시크릿 / Bash 우회 차단
│   ├── data-governance-check.py  # 공통 + 역할별 + LLM 유출 방지
│   ├── plan-gate.py              # 첫 Edit/Write 전 플랜 수립 강제
│   ├── code-style-check.py       # 컨벤션 피드백 + code-reviewer 트리거
│   ├── output-verify.py          # Spotless 포매팅 + 컴파일 검증
│   ├── feedback-loop.py          # 실패 교훈 축적
│   ├── audit.py                  # JSONL 감사 로그
│   └── stop-final-check.py       # 보안 감사 + 테스트 + 의존성 + 변경 검증 + 성능 검사 + 빌드
├── git-hooks/
│   └── pre-push                  # 체크섬 무결성 검증
├── scripts/
│   ├── api-spec-update.py        # API 스펙 자동 갱신 훅
│   ├── setup-hooks.sh            # git hook 설치
│   └── update-checksums.py       # 체크섬 갱신
├── agents/
│   ├── task-planner.md           # 자연어 → 실행 계획 변환 (plan-gate에서 자동 유도)
│   ├── code-reviewer.md          # 코드 리뷰 (5개+ 파일 수정 시 자동 트리거)
│   ├── change-validator.md       # 변경 정합성 검증 (Stop에서 Java 3개+ 수정 시)
│   ├── performance-checker.md    # 성능 안티패턴 탐지 (Stop에서 Service/Repo/Entity 수정 시)
│   ├── security-auditor.md       # 보안 감사 (Stop에서 자동 트리거, 최대 3회)
│   ├── harness-doctor.md         # 하네스 진단 (SessionStart 자동 실행)
│   ├── test-generator.md         # 테스트 생성 (Stop에서 소스 수정 + 테스트 미작성 시)
│   └── dependency-checker.md     # 의존성 검사 (Stop에서 build.gradle 수정 시)
├── references/                      # 상세 컨벤션/템플릿 원본 (on-demand 로드)
│   ├── code-templates.md
│   ├── java-spring-conventions.md
│   ├── jpa-conventions.md
│   ├── database-schema.md
│   └── harness-guide.md
└── rules/                           # slim 포인터 (항상 로드, references/로 연결)
    ├── java-spring-conventions.md
    ├── code-templates.md
    ├── jpa-conventions.md
    ├── database-schema.md
    └── api-spec-guide.md

.private/                            # 런타임 상태 파일 (.gitignore 대상)
├── .edit-count                      # 세션 편집 카운터
├── .edited-files                    # 수정된 파일 목록
├── .task-plan-established           # 플랜 수립 플래그
├── .learnings                       # 실패 교훈 (세션 간 유지)
├── .failing-tests                   # 빌드 실패 기록
├── .*-triggered                     # 에이전트 트리거 상태
└── audit/                           # JSONL 감사 로그

docs/
├── api-spec.md                   # API 스펙 (Markdown, 사람용)
└── api-spec.yml                  # API 스펙 (OpenAPI 3.0, Claude용)
```
