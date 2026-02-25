# Bug Fix Command

버그 수정 파이프라인 오케스트레이터. 심각도에 따라 적절한 워크플로우를 실행합니다.
Feature별 버그 수정 기록을 `.claude/bug-report/{feature}/{bug}/report.md`에 관리합니다.

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
[이전 기록 확인] → [report.md 생성] → [분석+수정+검증 루프] → [사용자 최종 확인]
```

**복합 버그 (Major/Critical)**:
```
[이전 기록 확인] → [report.md 생성] → [bug-analyzer] → [사용자 확인] → [bug-fixer + 수정 루프] → [regression-tester] → [verification-agent] → [사용자 최종 확인]
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
  - header: "Feature"
    question: "이 버그가 속하는 feature(기능 영역)는 무엇인가요?"
    options:
      - label: "직접 입력"
        description: "feature명을 직접 입력합니다 (예: auth, dashboard, payment)"
```

추가 수집:
- 버그 설명 (이미 인자로 제공된 경우 생략)
- 에러 로그 (있다면)
- 재현 단계 (있다면)

### Step 2: 이전 버그 기록 확인

```bash
# 같은 feature의 이전 버그 기록 스캔
ls .claude/bug-report/{feature}/ 2>/dev/null
```

- `.claude/bug-report/{feature}/` 디렉토리가 존재하면 기존 report.md들을 읽음
- 같은 feature의 이전 버그 수정 기록에서:
  - 유사한 증상이 있었는지 확인
  - 이전에 실패한 접근법 파악
  - 성공한 수정 패턴 참고
- 발견된 관련 기록을 report.md의 "이전 기록 참고" 필드에 기술

### Step 3: 산출물 디렉토리 및 report.md 생성

```bash
# 디렉토리 생성 (feature명은 kebab-case, bug 설명도 kebab-case)
mkdir -p .claude/bug-report/{feature}/{bug-short-description}
```

report.md 초기 내용 작성:

```markdown
# {버그 제목}

## 버그 정보
- **Feature**: {feature}
- **심각도**: Minor | Major | Critical
- **최초 보고일**: {date}
- **상태**: 미해결

## 증상
{버그 설명}

## 에러 로그
{에러 로그 - 없으면 "없음"}

## 재현 단계
1. ...

---

## 수정 시도 #1 - {date}

### 분석
- **근본 원인 추정**: ...
- **영향 범위**: ...
- **이전 기록 참고**: {이전 기록에서 발견한 관련 정보}

### 수정 계획
- [ ] {할 일 1}
- [ ] {할 일 2}
- [ ] 검증: {검증 방법}

### 수정 결과
(수정 완료 후 작성)
```

### Step 4: 수정 루프 (핵심)

#### Minor 버그 (단순 파이프라인)

```
반복 (최대 5회):
  1. report.md에 수정 계획 (todo 체크리스트) 작성
  2. 분석 + 수정 실행
  3. report.md의 todo 항목을 [x]로 체크
  4. 검증 실행 (테스트/빌드/수동 확인)
  5. 해결됨 → report.md 상태를 "해결"로, 수정 결과 기록, 루프 종료
     미해결 → 실패 원인 기록 → 새 "수정 시도 #N" 섹션 추가 → 1로 돌아감
```

- **UI/인터랙션 버그**: Playwright 검증 테스트로 확인
- **그 외 버그**: 단위 테스트 또는 빌드로 확인

#### Major/Critical 버그 (상세 파이프라인)

**Phase 1: 분석**
```yaml
agent: bug-analyzer
input:
  - 버그 설명, 에러 로그, 재현 단계
  - 이전 버그 기록 (있으면)
output: report.md의 "분석" 섹션 업데이트
```

**사용자 확인**:
```yaml
question: "분석 결과를 확인해주세요. 근본 원인이 맞나요?"
options:
  - "맞습니다, 수정 진행해주세요"
  - "아니요, 추가 분석이 필요합니다"
  - "부분적으로 맞습니다 (추가 설명 제공)"
```

**Phase 2: 수정 루프**
```
반복 (최대 5회):
  1. bug-fixer가 report.md에 수정 계획 작성
  2. 코드 수정 실행
  3. report.md의 todo 항목 체크
  4. regression-tester가 테스트 작성 + 실행
  5. verification-agent가 검증
  6. 해결됨 → report.md 상태 "해결", 수정 결과 기록, 루프 종료
     미해결 → 실패 원인 기록 → 새 "수정 시도 #N" 섹션 추가 → 1로 돌아감
```

**최종 확인**:
```yaml
question: "버그 수정이 완료되었습니다. 추가 작업이 필요한가요?"
options:
  - "완료, 커밋 진행"
  - "수동 테스트 후 확인"
  - "추가 수정 필요"
```

### Step 5: 결과 보고

```markdown
## 버그 수정 완료

### 수정 요약
- **버그**: {설명}
- **원인**: {근본 원인}
- **수정**: {수정 내용}
- **시도 횟수**: {N}회

### 변경된 파일
- `{file1}`: {변경 내용}
- `{file2}`: {변경 내용}

### 테스트 결과
- 새 테스트: {n}/{n} 통과
- 관련 테스트: {n}/{n} 통과

### 버그 리포트
- `.claude/bug-report/{feature}/{bug}/report.md`
```

---

## 수정 결과 기록 형식

각 수정 시도의 "수정 결과" 섹션은 다음과 같이 기록:

```markdown
### 수정 결과
- **결과**: 성공 | 실패 | 부분 해결
- **변경 파일**:
  - `{file1}:{line}`: {변경 내용}
  - `{file2}:{line}`: {변경 내용}
- **검증 내용**: {어떻게 검증했는지}
- **실패 원인** (실패 시): {왜 실패했는지, 다음 시도에서 참고할 점}
```

---

## 프로젝트 컨텍스트

실행 시 자동으로 확인:

1. **CLAUDE.md**: 프로젝트 규칙
2. **package.json**: 테스트 프레임워크, 명령어
3. **테스트 구조**: 기존 테스트 패턴
4. **.claude/bug-report/**: 이전 버그 수정 기록

---

## 에러 처리

### 분석 실패
- 추가 정보 요청
- 에러 로그 재확인

### 수정 실패
- report.md에 실패 원인 기록
- 새 수정 시도 섹션 추가 후 재시도
- 타입/린트 에러 시 즉시 수정

### 테스트 실패
- 실패 원인 분석 후 report.md에 기록
- 수정 또는 사용자 확인 요청
