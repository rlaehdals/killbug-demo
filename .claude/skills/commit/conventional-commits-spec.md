# Conventional Commits 1.0.0

## Summary

커밋 메시지 위에 경량 컨벤션을 얹어 명시적인 커밋 히스토리를 만든다.

구조:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | 용도 |
|------|------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 동작 변경 없는 구조 개선 |
| `docs` | 문서만 수정 |
| `style` | 포매팅, 세미콜론 등 (동작 변경 없음) |
| `test` | 테스트 추가/수정 |
| `build` | 빌드 시스템, 의존성 변경 |
| `ci` | CI 설정 변경 |
| `perf` | 성능 개선 |
| `chore` | 기타 (코드 변경 없음) |

## Examples

```
feat(webhook-server): add Slack thread analysis endpoint
```

```
fix(worker): prevent race condition in worktree cleanup
```

```
refactor(worker): extract Claude CLI runner to separate service
```

```
docs: update API spec for error thread endpoint
```

```
feat(webhook-server)!: change error detection webhook payload format

BREAKING CHANGE: webhook payload now uses `thread_ts` instead of `message_ts`
```

## Specification

1. type 접두사 필수 (noun: feat, fix 등), 선택적 scope, 선택적 `!`, 콜론+공백.
2. `feat` = 새 기능, `fix` = 버그 수정.
3. scope은 괄호로 감싼 명사 (코드베이스 섹션). 예: `feat(worker):`
4. description은 type/scope 접두사 바로 뒤. 변경사항의 짧은 요약.
5. body는 description 뒤 빈 줄 하나 다음에 작성. 자유 형식.
6. footer는 body 뒤 빈 줄 하나 다음. `token: value` 또는 `token #value` 형식.
7. `BREAKING CHANGE:` footer 또는 type 뒤 `!`로 breaking change 표시.
8. type/scope 외의 정보는 대소문자 구분 없음. `BREAKING CHANGE`만 대문자 필수.
