# API 스펙 참조 규칙

API 관련 작업(엔드포인트 추가/수정/삭제/조회) 시:

1. **`docs/api-spec.md`**를 먼저 읽어 현재 API 구조를 파악한다
2. `docs/api-spec.md`는 PostToolUse 훅이 자동 갱신한다 — 직접 수정하지 않는다
3. API 설계 변경이 필요하면 **OpenSpec**을 활용한다:
   - `/opsx:propose` — 변경 제안 + 스펙 아티팩트 생성
   - `/opsx:apply` — 구현
   - `/opsx:archive` — 완료 후 아카이브
4. 대규모 API 변경은 OpenSpec으로 설계를 먼저 확정한 뒤 구현한다
