# 코드 생성 템플릿

> 새 엔드포인트/서비스/DTO 추가 시 `.claude/references/code-templates.md`의 상세 템플릿을 읽고 따른다.

## 핵심 규칙
- Controller → Service → Client 계층 (Controller에서 Client 직접 호출 금지)
- Request/Response DTO는 `controller/request/`, `controller/response/`에 별도 파일 (inner class 금지)
- 조회 = GET + @RequestParam, 생성/수정 = POST/PUT + @RequestBody + DTO
- 필드 3개 이상 → @Builder, 2개 이하 → new 직접 생성
- Service 간 순환 참조 금지

## 커밋 & PR 컨벤션
- 이슈 번호 포함 요청 시: 커밋 `[ISSUE-번호] 설명`, 브랜치 `feature/ISSUE-번호` (버그: `fix/ISSUE-번호`)
- PR 본문: `## Summary` + `## Issue` 섹션

## 파일 구조
`config/ | controller/{request,response}/ | entity/ | repository/ | service/ | exception/ | util/`
