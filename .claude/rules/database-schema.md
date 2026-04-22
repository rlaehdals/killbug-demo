# 데이터베이스 스키마

> PostgreSQL 16 / 로컬 컨테이너 (docker-compose.yml)
> 접속 정보: localhost:5432 / testdb / postgres:postgres

## 테이블 목록

### junior

주니어 개발자의 작업 기록.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | BIGSERIAL | PK, AUTO | 고유 식별자 |
| name | VARCHAR(100) | NOT NULL | 작성자 이름 |
| task | VARCHAR(500) | NOT NULL | 작업 내용 |
| created_at | TIMESTAMP | DEFAULT now() | 생성 시각 |

**Entity**: `JuniorTask`
**Repository**: `JuniorTaskRepository`

### senior

시니어 개발자의 코드 리뷰 기록.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | BIGSERIAL | PK, AUTO | 고유 식별자 |
| name | VARCHAR(100) | NOT NULL | 리뷰어 이름 |
| review | VARCHAR(500) | NOT NULL | 리뷰 내용 |
| module | VARCHAR(100) | NULLABLE | 대상 모듈 (webhook-server, worker) |
| created_at | TIMESTAMP | DEFAULT now() | 생성 시각 |

**Entity**: `SeniorReview`
**Repository**: `SeniorReviewRepository`

### lead

리드의 아키텍처/기술 결정 기록.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | BIGSERIAL | PK, AUTO | 고유 식별자 |
| name | VARCHAR(100) | NOT NULL | 결정자 이름 |
| decision | VARCHAR(500) | NOT NULL | 결정 내용 |
| priority | INT | DEFAULT 3 | 우선순위 (1=최상, 5=최하) |
| created_at | TIMESTAMP | DEFAULT now() | 생성 시각 |

**Entity**: `LeadDecision`
**Repository**: `LeadDecisionRepository`

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/role-data/{role}` | 해당 역할 테이블 전체 조회 |
| POST | `/role-data/{role}` | 해당 역할 테이블에 데이터 생성 |

`{role}`: `junior`, `senior`, `lead`

### Request (POST)
```json
{
  "name": "이름",
  "content": "내용 (junior=task, senior=review, lead=decision)",
  "extra": "추가 정보 (senior=module, lead=priority)"
}
```

### Response
```json
{
  "id": 1,
  "name": "이름",
  "content": "내용",
  "extra": "추가 정보",
  "createdAt": "2026-04-21T15:14:54"
}
```
