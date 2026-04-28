# Java & Spring Boot Conventions

> 상세 코드 예시와 패턴은 `.claude/references/java-spring-conventions.md` 참조.

## 핵심 규칙
- Java 21, java.time API (new Date() 금지)
- @RequiredArgsConstructor 생성자 주입 (@Autowired 금지)
- @Slf4j 로거 + `[module]` 프리픽스 (System.out 금지)
- 명시적 import (와일드카드 금지), 순서: java → javax → org → com → static
- 명시적 타입 선언 (var 금지)
- Record로 DTO, 필드 3개+ → @Builder
- 예외: 구체적 타입 + RuntimeException 래핑 패턴
- ProcessBuilder 인자 분리 (셸 명령어 금지)

## 금지 패턴

| 금지 | 대안 |
|------|------|
| `@Autowired` | `@RequiredArgsConstructor` |
| `System.out.println` | `@Slf4j` + `log.info()` |
| `import xxx.*` | 명시적 import |
| `new Date()` | `java.time` |
| `throws Exception` | 구체적 예외 타입 |
| 빈 catch 블록 | 최소한 로깅 |
| 하드코딩 시크릿 | `${ENV_VAR}` |
| `var` | 명시적 타입 |
