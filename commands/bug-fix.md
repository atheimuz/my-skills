# Bug Fix Command

버그 수정 파이프라인 오케스트레이터. 심각도에 따라 적절한 워크플로우를 실행합니다.

## 사용법

```
/bug-fix
/bug-fix {버그 설명}
```

## allowed-tools

Bash(git diff:*), Bash(git status:*), Bash(npm test:*), Bash(yarn test:*), Bash(npx:*), Bash(mkdir:*), Read, Write, Glob, Grep, Edit, AskUserQuestion, Task

---

## 워크플로우

### 파이프라인 개요

**단순 버그 (Minor)**:
```
[분석+수정 통합] → [테스트+검증 통합] → [사용자 최종 확인]
```

**복합 버그 (Major/Critical)**:
```
[bug-analyzer] → [사용자 확인] → [bug-fixer] → [regression-tester] → [verification-agent] → [사용자 최종 확인]
```

---

## 실행 절차

### Step 1: 버그 정보 수집

AskUserQuestion으로 버그 정보를 수집합니다:

```yaml
questions:
  - header: "심각도"
    question: "버그의 심각도는 어느 정도인가요?"
    options:
      - label: "Minor"
        description: "UI 오타, 스타일 깨짐 등 기능에 영향 없음"
      - label: "Major"
        description: "주요 기능 오류, 데이터 표시 문제"
      - label: "Critical"
        description: "앱 크래시, 데이터 손실, 보안 이슈"
```

추가 수집:
- 버그 설명 (이미 인자로 제공된 경우 생략)
- 에러 로그 (있다면)
- 재현 단계 (있다면)

### Step 2: 산출물 디렉토리 생성

```bash
# 버그 ID 생성 (날짜-시간 기반)
BUG_ID=$(date +%Y-%m-%d-%H-%M)-{short-description}

# 디렉토리 생성
mkdir -p .claude/bug-reports/${BUG_ID}
```

### Step 3: 파이프라인 실행

#### Minor 버그 (단순 파이프라인)

**분석+수정 통합**:
1. 버그 원인 빠르게 파악
2. 코드 수정
3. 간단한 분석 메모 작성

**테스트+검증 통합**:
1. 수정 확인 테스트 작성
2. 테스트 실행
3. 결과 확인

**최종 확인**:
- 사용자에게 결과 보고

#### Major/Critical 버그 (상세 파이프라인)

**Phase 1: 분석**
```yaml
agent: bug-analyzer
input:
  - 버그 설명
  - 에러 로그
  - 재현 단계
output: .claude/bug-reports/{id}/analysis.md
```

**사용자 확인**:
```yaml
question: "분석 결과를 확인해주세요. 근본 원인이 맞나요?"
options:
  - "맞습니다, 수정 진행해주세요"
  - "아니요, 추가 분석이 필요합니다"
  - "부분적으로 맞습니다 (추가 설명 제공)"
```

**Phase 2: 수정**
```yaml
agent: bug-fixer
input:
  - analysis.md
output:
  - .claude/bug-reports/{id}/fix-plan.md
  - 코드 수정
```

**Phase 3: 테스트 작성**
```yaml
agent: regression-tester
input:
  - analysis.md
  - fix-plan.md
output:
  - .claude/bug-reports/{id}/test-scenarios.md
  - tests/{feature}/bug-{id}.spec.ts
```

**Phase 4: 검증**
```yaml
agent: verification-agent
input:
  - 테스트 파일
output:
  - .claude/bug-reports/{id}/verification.md
```

**최종 확인**:
```yaml
question: "버그 수정이 완료되었습니다. 추가 작업이 필요한가요?"
options:
  - "완료, 커밋 진행"
  - "수동 테스트 후 확인"
  - "추가 수정 필요"
```

### Step 4: 결과 보고

```markdown
## 버그 수정 완료

### 수정 요약
- **버그**: {설명}
- **원인**: {근본 원인}
- **수정**: {수정 내용}

### 변경된 파일
- `{file1}`: {변경 내용}
- `{file2}`: {변경 내용}

### 테스트 결과
- 새 테스트: {n}/{n} 통과
- 관련 테스트: {n}/{n} 통과

### 산출물
- `.claude/bug-reports/{id}/`
```

---

## 프로젝트 컨텍스트

실행 시 자동으로 확인:

1. **CLAUDE.md**: 프로젝트 규칙
2. **package.json**: 테스트 프레임워크, 명령어
3. **테스트 구조**: 기존 테스트 패턴

---

## 에러 처리

### 분석 실패
- 추가 정보 요청
- 에러 로그 재확인

### 수정 실패
- 타입/린트 에러 시 수정
- 사용자에게 알림

### 테스트 실패
- 실패 원인 분석
- 수정 또는 사용자 확인 요청
