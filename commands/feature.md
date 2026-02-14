---
allowed-tools:
    - Read
    - Write
    - Glob
    - Grep
    - Bash
    - Task
    - AskUserQuestion
    - TodoWrite
---

# Feature

기능 개발 전체 파이프라인을 실행합니다.

## 사용법

```
/feature <feature-name>
```

예시: `/feature license-management`

## 워크플로우

### Phase 1: 기획 (product-spec-writer)

1. Task tool로 `product-spec-writer` 에이전트 실행
2. 사용자와 대화하며 요구사항 수집
3. `specs/{feature}/plan.md` 저장

```
prompt: "{feature} 기능에 대한 기획 명세서를 작성해줘. specs/{feature}/plan.md에 저장해줘.

문서 구조 규칙:
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 핵심 기능 요약 (3줄 이내)
  - 주요 결정사항 테이블 (| 항목 | 결정 | 이유 |)
  - 영향 범위 (신규 파일, 수정 파일 목록)
- TL;DR만 읽어도 전체 방향을 파악할 수 있어야 한다"
subagent_type: product-spec-writer
```

### Phase 1.5: API 명세서 확인

AskUserQuestion으로 질문: - "목업 데이터로 진행" → MSW + HTTP 호출 방식 (서비스 함수는 항상 실제 HTTP 호출, MSW 핸들러로 개발 환경 목업 제공, 테스트는 page.route() 인터셉트) - "API 명세서 제공" → 사용자가 URL/파일 경로 제공 → `specs/{feature}/api-spec.md`로 저장 후 진행

### Phase 2: 검토 (Blocking)

1. plan.md에서 **TL;DR 섹션만 추출**하여 사용자에게 표시한다
2. TL;DR의 주요 결정사항 테이블을 기반으로 핵심 포인트를 정리한다
3. AskUserQuestion으로 확인 요청:
    - "기획 요약을 검토해주세요. 상세 내용은 specs/{feature}/plan.md에서 확인할 수 있습니다."
    - 옵션: "확인, 진행해줘" / "상세 내용 보고 싶어" / "수정 필요"
4. "상세 내용 보고 싶어" 선택 시 plan.md 전체 내용을 표시한다
5. 수정 필요시 Phase 1로 돌아감

### Phase 3: 병렬 실행

Task tool 3개 동시 실행 (단일 메시지에 3개 Task tool call):

**Task 1 - ui-designer:**

```
prompt: "specs/{feature}/plan.md를 읽고 specs/{feature}/design.md를 작성해줘.

문서 구조 규칙:
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 화면 구성 요약 (3줄 이내)
  - 컴포넌트 목록 테이블 (| 컴포넌트 | 위치 | 역할 |)
  - 상태/인터랙션 요약
- TL;DR만 읽어도 전체 디자인 방향을 파악할 수 있어야 한다"
subagent_type: ui-designer
```

**Task 2 - playwright-e2e-tester:**

```
prompt: "specs/{feature}/plan.md를 읽고 테스트 시나리오와 테스트 코드를 작성해줘.
- specs/{feature}/test-scenarios.md
- tests/mocks/{feature}.mock.ts (목업 데이터)
- tests/{feature}/*.spec.ts

테스트 규칙:
- 실제 API 존재 여부와 관계없이 항상 목업 데이터를 사용한다
- 목업 데이터는 tests/mocks/{feature}.mock.ts에 정의한다
- Playwright page.route()로 API 호출을 인터셉트하고 목업 데이터를 반환한다
- specs/{feature}/api-spec.md가 있으면 응답 구조를 맞춘다

문서 구조 규칙 (test-scenarios.md):
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 테스트 범위 요약 (3줄 이내)
  - 시나리오 목록 테이블 (| 시나리오 | 검증 내용 | 우선순위 |)
  - 목업 데이터 구조 요약"
subagent_type: playwright-e2e-tester
```

**Task 3 - code-analyst:**

```
prompt: "specs/{feature}/plan.md를 읽고 specs/{feature}/implementation-guide.md를 생성해줘. specs/{feature}/api-spec.md가 있으면 API 명세 기반으로 작성해줘.

문서 구조 규칙:
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 구현 방향 요약 (3줄 이내)
  - 수정/생성 파일 목록 테이블 (| 파일 | 작업 | 재사용 패턴 |)
  - 핵심 의존성 및 재사용 함수 목록"
subagent_type: code-analyst
```

### Phase 4: 구현

1. **먼저** `specs/{feature}/implementation-guide.md`를 읽는다
    - implementation-guide.md에 기존 패턴, 파일 경로, 재사용할 함수/컴포넌트가 이미 분석되어 있다
    - **추가 탐색 없이** 가이드에 명시된 패턴과 경로를 그대로 따라 구현한다
    - 가이드에 없는 정보가 필요한 경우에만 추가 파일을 읽는다
2. `specs/{feature}/plan.md`, `design.md`, `test-scenarios.md`도 참조
3. TDD 방식:
    - `npm test` 실행 → 실패 확인
    - 구현 코드 작성
    - `npm test` 재실행 → 통과 확인
4. 모든 테스트 통과할 때까지 반복

## 산출물 구조

```
specs/
└── {feature}/
    ├── plan.md              # Phase 1: 기획 명세서
    ├── design.md            # Phase 3: 디자인 명세서
    ├── test-scenarios.md    # Phase 3: 테스트 시나리오
    └── implementation-guide.md  # Phase 3: 구현 가이드

tests/
├── mocks/
│   └── {feature}.mock.ts   # Phase 3: 목업 데이터
└── {feature}/
    └── *.spec.ts            # Phase 3: 테스트 코드

src/
└── ...                      # Phase 4: 구현 코드
```

## 예시

```
/feature license-management

→ Phase 1: specs/license-management/plan.md 생성
→ Phase 1.5: API 명세서 확인 (없으면 목업/명세서 제공 선택)
→ Phase 2: 사용자 검토 및 확인
→ Phase 3:
   - specs/license-management/design.md
   - specs/license-management/test-scenarios.md
   - specs/license-management/implementation-guide.md
   - tests/license-management/*.spec.ts
→ Phase 4: 구현 및 테스트 통과
```

## 주의사항

- Phase 1.5에서 API 명세서가 없으면 반드시 사용자에게 목업/명세서 제공 여부를 질문한다
- Phase 2에서 사용자 확인 없이 다음 단계로 진행하지 않는다
- Phase 3의 세 에이전트는 반드시 병렬로 실행한다 (단일 메시지에 3개 Task call)
- 테스트 코드는 실제 API 존재 여부와 관계없이 항상 page.route() 인터셉트 + 목업 데이터를 사용한다
- Phase 4는 TDD 방식을 엄격히 따른다
- Phase 4 구현 시 implementation-guide.md를 반드시 참조한다
- {feature}는 케밥케이스로 작성 (예: license-management, user-profile)
