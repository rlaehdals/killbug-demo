# API 스펙 참조 규칙

API 관련 작업(엔드포인트 추가/수정/삭제/조회) 시:

1. **`docs/api-spec.yml`** (OpenAPI 3.0)을 먼저 읽어 현재 API 구조를 파악한다
2. 엔드포인트 경로, 파라미터, DTO 스키마는 YAML에서 확인한다
3. `docs/api-spec.md`는 사람용 문서 — 직접 수정하지 않는다 (PostToolUse 훅이 자동 갱신)
4. Controller/DTO 수정 후 훅이 두 파일을 동시에 갱신하므로 별도 문서 작업은 불필요하다
