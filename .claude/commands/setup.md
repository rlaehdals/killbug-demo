# Project Setup

프로젝트 개발 환경을 자동으로 점검하고 설정합니다.
각 단계를 순서대로 실행하고, 최종 결과를 요약 테이블로 출력합니다.

**원칙**: 자동화 가능한 항목은 즉시 실행하고, 수동 설치가 필요한 항목만 안내합니다.

---

## 실행 단계

아래 단계를 **순서대로** 실행하세요. 각 단계의 성공/실패를 기록하며 진행합니다.

### 1단계: Java 21 확인

```bash
java -version 2>&1
```

- Java 21이 확인되면 → 통과
- Java가 없거나 버전이 다르면 → 수동 안내 항목으로 기록
  - Homebrew: `brew install openjdk@21`
  - SDKMAN: `sdk install java 21.0.7-tem`

### 2단계: Gradle Wrapper 확인

```bash
ls -la ./gradlew && ./gradlew --version 2>&1 | head -5
```

- `./gradlew` 파일이 있고 실행 가능하면 → 통과
- 실행 권한이 없으면 → `chmod +x ./gradlew` 자동 실행
- 파일이 없으면 → 수동 안내 항목으로 기록

### 3단계: Docker 확인

```bash
docker --version 2>&1
docker info 2>&1 | head -3
```

- Docker가 설치되어 있고 데몬이 실행 중이면 → 통과
- Docker가 설치되어 있지만 데몬이 꺼져 있으면 → "Docker Desktop을 실행해주세요" 안내
- Docker가 없으면 → 수동 안내 항목으로 기록
  - macOS: `brew install --cask docker` 또는 https://docs.docker.com/desktop/setup/install/mac-install/

### 4단계: Git Hooks 설정 (자동)

```bash
bash .claude/scripts/setup-hooks.sh
git config core.hooksPath
```

- 스크립트 실행하고 `core.hooksPath`가 `.claude/git-hooks`로 설정되었는지 확인
- 성공하면 → 통과
- 실패하면 → 에러 메시지 기록

### 5단계: Harness Checksums 갱신 (자동)

```bash
python3 .claude/scripts/update-checksums.py
```

- 체크섬 매니페스트 갱신 확인
- 성공하면 → 통과
- 실패하면 → 누락 파일 목록 기록

### 6단계: Pre-push Hook 검증 (자동)

```bash
sh .claude/git-hooks/pre-push
```

- 하네스 무결성 검증이 정상 동작하는지 확인
- 통과하면 → 성공
- 실패하면 → 5단계 체크섬 갱신이 제대로 되었는지 재확인

### 7단계: Gradle Build (자동)

```bash
./gradlew clean build 2>&1
```

- 전체 빌드 (컴파일 + 테스트 + Spotless) 실행
- 성공하면 → 통과
- 실패하면 → 에러 원인 분석 후 기록

---

## 결과 출력

모든 단계 완료 후 아래 형식으로 결과를 출력합니다:

```
## Setup Results

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1 | Java 21 | ✅/❌ | 버전 또는 설치 안내 |
| 2 | Gradle Wrapper | ✅/❌ | 버전 또는 상태 |
| 3 | Docker | ✅/❌ | 버전 또는 설치 안내 |
| 4 | Git Hooks | ✅/❌ | hooksPath 설정값 |
| 5 | Checksums | ✅/❌ | 갱신 결과 |
| 6 | Pre-push Hook | ✅/❌ | 무결성 검증 결과 |
| 7 | Gradle Build | ✅/❌ | 빌드 결과 |
```

### 수동 조치 필요
실패한 항목 중 자동으로 해결할 수 없는 것만 나열합니다.
각 항목에 대해 **정확한 실행 명령어**를 포함합니다.

### 자동 완료
자동으로 성공한 항목은 간단히 한 줄로만 표시합니다.

---

**주의**: 이 명령은 프로젝트 소스 코드를 수정하지 않습니다. 환경 설정과 검증만 수행합니다.
