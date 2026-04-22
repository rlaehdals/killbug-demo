# 코드 생성 템플릿

> 아래 템플릿을 따르면 누가 작성해도 동일한 구조의 코드가 나온다.
> "새 엔드포인트 만들어줘", "새 서비스 추가해줘" 같은 자연어 요청에 이 템플릿을 적용한다.

## 커밋 & PR 컨벤션

사용자가 이슈 번호를 포함해서 요청하면, 커밋과 PR에 이슈 번호를 반드시 포함한다.

### 요청 예시
```
ISSUE-1771로 senior 조회 API 만들어줘
```

### 커밋 메시지
```
[ISSUE-1771] senior 조회 API 추가
```

- 형식: `[ISSUE-번호] 설명`
- 설명은 한국어 허용
- 한 줄로 작성 (50자 이내 권장)

### PR 제목
```
[ISSUE-1771] senior 조회 API 추가
```

### PR 본문
```markdown
## Summary
- senior 테이블 조회 API 추가 (GET /senior-reviews)
- module, name 파라미터로 필터링 지원

## Issue
[ISSUE-1771]
```

### 브랜치명
```
feature/ISSUE-1771
```

- 형식: `feature/ISSUE-번호`
- 버그 수정: `fix/ISSUE-번호`

---

## 새 REST 엔드포인트 추가 시

**1. Request DTO** — `controller/request/` 패키지에 별도 파일로 생성

```java
package com.killbug.{module}.controller.request;

import java.util.List;

public record {Name}Request(List<String> items, int limit) {}
```

**2. Response DTO** — `controller/response/` 패키지에 별도 파일로 생성

```java
package com.killbug.{module}.controller.response;

import java.util.List;

public record {Name}Response(List<String> items, String status) {}
```

> **금지**: Controller 클래스 내부에 Request/Response 를 inner class로 선언하지 않는다.
> `controller/request/`, `controller/response/` 패키지에 파일을 분리한다.

**3. Controller** — 요청 수신만, 로직 없음

> **HTTP Method 규칙**: 상태를 변경하지 않는 조회는 **GET**을 사용한다.
> POST/PATCH/PUT/DELETE는 상태를 변화시킬 때만 사용한다 (DB, NoSQL, S3 등).
>
> | 상태 변경 여부 | Method | Request DTO |
> |-------------|--------|-------------|
> | 조회 (변경 없음) | GET | `@RequestParam` 사용 (Request DTO 불필요) |
> | 생성 | POST | `@RequestBody` + Request DTO |
> | 수정 | PUT / PATCH | `@RequestBody` + Request DTO |
> | 삭제 | DELETE | `@PathVariable` 또는 `@RequestParam` |

**GET 예시 (조회 — 상태 변경 없음):**

```java
@GetMapping("/{action}")
public ResponseEntity handle(@RequestParam List<Long> numbers) {
    {Name}Response result = {name}Service.calculate(numbers);
    return Response.OK.getApiResponse(result);
}
```

**POST 예시 (생성/변경 — 상태 변경 있음):**

```java
@PostMapping("/{action}")
public ResponseEntity handle(@RequestBody {Name}Request request) {
    {Name}Response result = {name}Service.process(request);
    return Response.OK.getApiResponse(result);
}
```

**4. Service** — 비즈니스 로직, 외부 호출

```java
package com.killbug.{module}.service;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class {Name}Service {

    public {Name}Response process({Name}Request request) {
        log.info("[{module}] 처리 시작");
        try {
            // 비즈니스 로직
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("{module} 처리 실패", e);
        }
    }
}
```

**5. Config** — 타입 세이프 설정

```java
package com.killbug.{module}.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@ConfigurationProperties(prefix = "{prefix}")
public class {Name}Properties {

    private String apiUrl;
    private String apiKey;  // application.yml에서 ${ENV_VAR}로 참조
}
```

**6. 외부 API 클라이언트** — HTTP 호출 캡슐화

```java
package com.killbug.{module}.service;

import org.springframework.stereotype.Service;

import com.killbug.{module}.config.{Module}Properties;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class {Name}Client {

    private final {Module}Properties properties;

    public JsonNode call(String param) {
        // HTTP 호출 로직
        // 시크릿은 properties에서 가져옴 (하드코딩 금지)
    }
}
```

## 비동기 처리 추가 시

```java
@Async("{module}Executor")
public void processAsync(JsonNode input, Runnable cleanup) {
    try {
        doProcess(input);
    } catch (Exception e) {
        log.error("[{module}] 처리 실패", e);
    } finally {
        cleanup.run();  // 정리 작업 실행
    }
}
```

## 외부 프로세스 실행 시

```java
// 인자를 분리하여 전달 (Command Injection 방지)
ProcessBuilder pb = new ProcessBuilder("command", "--flag", value);
pb.directory(workingDir);
pb.environment().put("KEY", properties.getApiKey());
pb.redirectInput(ProcessBuilder.Redirect.from(new File("/dev/null")));

Process process = pb.start();
boolean finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
if (!finished) {
    process.destroyForcibly();
}
```

## 파일 구조 규칙

```
src/main/java/com/killbug/{module}/
  ├── config/                # @Configuration, @ConfigurationProperties
  ├── controller/
  │   ├── request/           # Request DTO (Record)
  │   ├── response/          # Response DTO (Record + @Builder)
  │   └── {Name}Controller.java
  ├── entity/                # @Entity JPA 엔티티
  ├── repository/            # JpaRepository 인터페이스
  ├── service/               # @Service — 비즈니스 로직, 외부 API 호출
  ├── exception/             # 예외 클래스, @RestControllerAdvice
  └── util/                  # 유틸리티 클래스
```

- Controller는 Service만 호출한다 (직접 Client 호출 금지)
- Request/Response DTO는 `controller/request/`, `controller/response/`에 별도 파일로 생성
- Service 간 순환 참조 금지
- Config 클래스는 `@ConfigurationProperties` 기반 타입 세이프 설정
