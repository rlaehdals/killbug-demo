# JPA & 데이터베이스 컨벤션

## Entity 생성 규칙

```java
package com.killbug.{module}.entity;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(name = "{table_name}")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class {EntityName} {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Builder
    public {EntityName}(String name) {
        this.name = name;
        this.createdAt = LocalDateTime.now();
    }
}
```

**필수 규칙:**
- `@Getter` 사용 (Setter 금지 — 불변성 유지)
- `@NoArgsConstructor(access = AccessLevel.PROTECTED)` — JPA용 기본 생성자는 외부 호출 차단
- `@Builder`는 생성자에 붙인다 (클래스 레벨 X)
- `createdAt`은 생성자에서 `LocalDateTime.now()` 세팅
- `@Table(name = "...")` 명시적으로 테이블명 지정
- `@Column`에 nullable, length 등 제약 조건 명시

**금지 패턴:**

| 금지 | 이유 | 대안 |
|------|------|------|
| `@Setter` | 엔티티 불변성 훼손 | 비즈니스 메서드로 상태 변경 |
| `@Data` | Setter + equals/hashCode 문제 | `@Getter` + `@Builder` |
| `@NoArgsConstructor` (public) | 아무 곳에서나 빈 객체 생성 가능 | `access = PROTECTED` |
| `@Builder` 클래스 레벨 | 모든 필드 노출 (id, createdAt 포함) | 생성자 레벨에 `@Builder` |
| `new Date()` | 레거시 | `LocalDateTime.now()` |

## Repository 규칙

```java
package com.killbug.{module}.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.killbug.{module}.entity.{EntityName};

public interface {EntityName}Repository extends JpaRepository<{EntityName}, Long> {}
```

- `JpaRepository<Entity, ID타입>` 상속
- 커스텀 쿼리는 메서드 네이밍 또는 `@Query`로 작성
- 인터페이스에 `@Repository` 안 붙여도 됨 (JpaRepository가 이미 포함)

## Service 트랜잭션 규칙

```java
// 조회: readOnly = true (성능 최적화, 더티 체킹 비활성화)
@Transactional(readOnly = true)
public List<Response> list() {
    return repository.findAll().stream()
            .map(this::toResponse)
            .toList();
}

// 생성/수정/삭제: readOnly 없이
@Transactional
public Response create(Request request) {
    Entity entity = Entity.builder()...build();
    Entity saved = repository.save(entity);
    return toResponse(saved);
}
```

- 조회 메서드는 `@Transactional(readOnly = true)`
- 생성/수정/삭제는 `@Transactional`
- Service 클래스 레벨에 `@Transactional` 붙이지 않는다 (메서드별로 명시)

## 엔티티 상태 변경 패턴

```java
// Good: 비즈니스 메서드로 상태 변경
public class SeniorReview {
    public void updateReview(String review) {
        this.review = review;
    }
}

// Bad: Setter로 상태 변경
entity.setReview("new review");
```

## 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 테이블명 | snake_case (소문자) | `junior`, `senior_review` |
| 컬럼명 | snake_case | `created_at`, `team_key` |
| Entity 클래스 | PascalCase | `JuniorTask`, `SeniorReview` |
| Repository | Entity명 + Repository | `JuniorTaskRepository` |

## 파일 구조

```
src/main/java/com/killbug/{module}/
  ├── entity/           # @Entity JPA 엔티티
  ├── repository/       # JpaRepository 인터페이스
  ├── service/          # @Transactional 비즈니스 로직
  ├── controller/
  │   ├── request/      # Request DTO (Record)
  │   └── response/     # Response DTO (Record + @Builder)
  ...
```
