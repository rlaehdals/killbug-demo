# JPA & 데이터베이스 컨벤션

> Entity/Repository 작성 시 `.claude/references/jpa-conventions.md`의 상세 패턴과 코드 예시를 참조한다.

## 핵심 규칙
- Entity: @Getter + @NoArgsConstructor(access=PROTECTED) + 생성자 레벨 @Builder
- @Table(name), @Column(nullable, length) 명시
- createdAt은 생성자에서 LocalDateTime.now() 세팅
- 금지: @Setter, @Data, public @NoArgsConstructor, 클래스 레벨 @Builder, new Date()
- 상태 변경: Setter 대신 비즈니스 메서드
- 조회: @Transactional(readOnly=true), 생성/수정/삭제: @Transactional (메서드 레벨)
- Repository: JpaRepository<Entity, Long> 상속 (@Repository 불필요)
