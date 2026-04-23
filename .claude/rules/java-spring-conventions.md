# Java & Spring Boot Conventions

KillBug 프로젝트의 Java/Spring Boot 코드 컨벤션. 이 규칙은 숙련도와 무관하게 일관된 코드 품질을 보장한다.

## Java 버전

- Java 21 사용
- Record, Pattern Matching, Text Block, Switch Expression 활용
- `new Date()` 대신 `java.time` API 사용 (LocalDateTime, Instant, ZonedDateTime)

## 의존성 주입

```java
// Good: 생성자 주입 + Lombok
@RequiredArgsConstructor
public class MyService {
    private final OtherService otherService;
}

// Bad: 필드 주입
@Autowired
private OtherService otherService;
```

## 로깅

```java
// Good: Lombok @Slf4j
@Slf4j
public class MyService {
    public void process() {
        log.info("[module] 처리 시작: {}", id);
    }
}

// Bad: System.out
System.out.println("처리 시작");

// Bad: 민감정보 로깅
log.info("token: {}", secretToken);  // NEVER
```

- 로그 프리픽스: `[module]` 형태 (예: `[worker]`, `[slack]`, `[claude]`)
- 한국어 로그 메시지 허용

## Import 규칙

```java
// 순서: java -> javax -> org -> com -> static
import java.util.List;
import java.util.Map;

import javax.crypto.Mac;

import org.springframework.stereotype.Service;

import com.killbug.worker.service.GitService;

import lombok.RequiredArgsConstructor;

// Bad: 와일드카드 import
import java.util.*;  // NEVER
```

## 예외 처리

```java
// Good: 구체적 예외 + 로깅
try {
    process();
} catch (IOException e) {
    log.error("[module] 처리 실패: {}", id, e);
    throw new RuntimeException("처리 실패", e);
}

// Bad: 빈 catch 블록
try { process(); } catch (Exception e) {}

// Good: RuntimeException 래핑 패턴 (이 프로젝트의 관례)
} catch (RuntimeException e) {
    throw e;
} catch (Exception e) {
    throw new RuntimeException("설명", e);
}
```

## 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 클래스 | PascalCase | `IssueProcessorService` |
| 메서드 | camelCase | `createWorktree` |
| 상수 | UPPER_SNAKE | `CONFIDENCE_PATTERN` |
| 패키지 | lowercase | `com.killbug.worker.service` |
| 변수 | camelCase | `threadTs`, `issueId` |

## 포매팅

- 들여쓰기: 4 spaces (탭 금지)
- 최대 줄 길이: 120자
- 중괄호: 같은 줄에 여는 중괄호
- 빈 줄: 메서드 사이 1줄, import 그룹 사이 1줄

## Record 활용

```java
// Good: 불변 데이터 전달에 Record 사용
public record Result(String output, double confidence) {
    public String truncated(int max) {
        if (output.length() <= max) return output;
        return output.substring(0, max) + "\n\n... (truncated)";
    }
}

// Bad: 단순 데이터에 Getter/Setter 클래스
public class Result {
    private String output;
    private double confidence;
    // ... getters, setters, constructor
}
```

## Builder 패턴 규칙

**필드 3개 이상이면 Builder 패턴을 사용한다.** 2개 이하면 `new`로 직접 생성해도 된다.

```java
// Good: 필드 3개 이상 → @Builder + builder()
@Builder
public record IncidentResponse(
        String id, String title, String description,
        int severity, String status, Instant createdAt
) {}

var incident = IncidentResponse.builder()
        .id(id)
        .title(request.title())
        .description(request.description())
        .severity(3)
        .status("open")
        .createdAt(Instant.now())
        .build();

// Good: 필드 2개 이하 → new로 직접 생성
public record GcdResponse(List<Long> numbers, long gcd) {}

var result = new GcdResponse(numbers, gcd);
```

## Spring Boot 패턴

### @ConfigurationProperties (타입 세이프 설정)

```java
@Getter
@Setter
@ConfigurationProperties(prefix = "worker")
public class WorkerProperties {
    private String reposBaseDir;
    private Map<String, RepoRoute> routing;
}
```

### @Async (비동기 처리)

```java
@Async("workerExecutor")
public void process(JsonNode issue, Runnable cleanup) {
    try {
        doProcess(issue);
    } catch (Exception e) {
        log.error("[worker] 처리 실패", e);
    } finally {
        cleanup.run();  // 항상 정리 작업 실행
    }
}
```

### ProcessBuilder (외부 프로세스 실행)

```java
// Good: 인자를 분리해서 전달
ProcessBuilder pb = new ProcessBuilder("git", "status", "--porcelain");
pb.directory(cwd);

// Bad: 셸 명령어로 직접 실행 (injection 위험)
ProcessBuilder pb = new ProcessBuilder("sh", "-c", "git status " + userInput);
```

## 금지 패턴

| 패턴 | 이유 | 대안 |
|------|------|------|
| `@Autowired` 필드 주입 | 테스트 어려움, 불변성 미보장 | `@RequiredArgsConstructor` |
| `System.out.println` | 구조화 로깅 불가 | `@Slf4j` + `log.info()` |
| `import xxx.*` | 의존성 불명확 | 명시적 import |
| `new Date()` | 레거시 API | `java.time` |
| `throws Exception` | 너무 넓은 예외 선언 | 구체적 예외 타입 |
| 빈 catch 블록 | 에러 무시 | 최소한 로깅 |
| 하드코딩 시크릿 | 보안 위험 | `${ENV_VAR}` |
| `var` 타입 추론 | 타입이 불명확 | 명시적 타입 선언 |
