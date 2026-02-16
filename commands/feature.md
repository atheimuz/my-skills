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

### Step 1: 기획 (product-spec-writer)

1. Task tool로 `product-spec-writer` 에이전트 실행
2. 사용자와 대화하며 요구사항 수집
3. `specs/{feature}/plan.md` 저장

```
prompt: "{feature} 기능에 대한 기획 명세서를 작성해줘. specs/{feature}/plan.md에 저장해줘.

plan.md는 '무엇을, 왜' 에만 집중한다. 기술 구현 명세는 포함하지 않는다.

포함할 것:
- 배경/목적
- 사용자 스토리 (우선순위 P0/P1/P2 표기)
- 사용자 흐름 (Happy Path + 예외 시나리오)
- 수용 기준 (Given-When-Then 형식)
- 스코프 (In Scope / Out of Scope)
- 디자인 방향성 (시각적 컨셉, 참고 레퍼런스 - 구체적 디자인 토큰은 제외)
- 기술 제약조건/방향성 (구체적 명세는 제외)

제외할 것:
- TypeScript 인터페이스 정의
- API 엔드포인트 상세 설계
- 컴포넌트 트리 / 파일 구조
- 구체적 디자인 토큰 (색상 코드, px 값 등)

문서 구조 규칙:
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 핵심 기능 요약 (3줄 이내)
  - 주요 결정사항 테이블 (| 항목 | 결정 | 이유 |)
  - 스코프 요약 (In / Out)
- TL;DR만 읽어도 전체 방향을 파악할 수 있어야 한다
- 전체 문서는 500줄 이내로 간결하게 작성한다"
subagent_type: product-spec-writer
```

### Step 2: 사용자 컨펌

1. plan.md에서 **TL;DR 섹션만 추출**하여 사용자에게 표시한다
2. TL;DR의 주요 결정사항 테이블과 스코프 요약을 기반으로 핵심 포인트를 정리한다
3. AskUserQuestion으로 확인 요청:
    - "기획 요약을 검토해주세요. 상세 내용은 specs/{feature}/plan.md에서 확인할 수 있습니다."
    - 옵션: "확인, 진행해줘" / "상세 내용 보고 싶어" / "수정 필요"
4. "상세 내용 보고 싶어" 선택 시 plan.md 전체 내용을 표시한다
5. 수정 필요시 Step 1로 돌아감

### Step 3: 설계 (code-analyst)

Task tool로 `code-analyst` 에이전트 실행

```
prompt: "specs/{feature}/plan.md를 읽고 specs/{feature}/implementation-guide.md를 생성해줘.

API 명세 처리:
- 사용자에게 API 명세서가 있는지 AskUserQuestion으로 질문한다
  - 옵션: 'API 명세서 제공' / '목업 데이터로 진행'
- 'API 명세서 제공' 선택 시: 사용자가 URL/파일 경로 제공 → specs/{feature}/api-spec.md로 저장 후 반영
- '목업 데이터로 진행' 선택 시: plan.md의 요구사항을 기반으로 API 명세 리스트를 직접 작성하여 implementation-guide.md에 포함한다

implementation-guide.md 포함 내용:
- 기존 코드베이스 패턴 분석 (재사용할 함수/유틸리티 경로:라인 포함)
- 파일 구조 및 컴포넌트 구조
- API 명세 (제공된 명세 또는 생성한 목업 스펙)
- 디자인 상세 (상태별 UI, 인터랙션, 반응형 레이아웃)
- 구현 순서 (의존성 표기: → 는 선행 의존, // 는 병렬 가능)

문서 구조 규칙:
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 구현 방향 요약 (3줄 이내)
  - 수정/생성 파일 목록 테이블 (| 파일 | 작업 | 재사용 패턴 |)
  - 핵심 의존성 및 재사용 함수 목록
- TL;DR만 읽어도 전체 구현 방향을 파악할 수 있어야 한다"
subagent_type: code-analyst
```

### Step 4: 사용자 컨펌

1. implementation-guide.md에서 **TL;DR 섹션만 추출**하여 사용자에게 표시한다
2. 파일 구조, 핵심 기술 결정, 구현 순서를 요약하여 제시한다
3. AskUserQuestion으로 확인 요청:
    - "구현 설계를 검토해주세요. 상세 내용은 specs/{feature}/implementation-guide.md에서 확인할 수 있습니다."
    - 옵션: "확인, 진행해줘" / "상세 내용 보고 싶어" / "수정 필요"
4. "상세 내용 보고 싶어" 선택 시 implementation-guide.md 전체 내용을 표시한다
5. 수정 필요시 Step 3으로 돌아감

### Step 5: 테스트 코드 작성 (playwright-e2e-tester)

Task tool로 `playwright-e2e-tester` 에이전트 실행

```
prompt: "specs/{feature}/plan.md와 specs/{feature}/implementation-guide.md를 읽고 TDD용 테스트 코드를 작성해줘.
- tests/mocks/{feature}.mock.ts (목업 데이터)
- tests/{feature}/*.spec.ts

테스트 규칙:
- 실제 API 존재 여부와 관계없이 항상 목업 데이터를 사용한다
- 목업 데이터는 tests/mocks/{feature}.mock.ts에 정의한다
- Playwright page.route()로 API 호출을 인터셉트하고 목업 데이터를 반환한다
- implementation-guide.md에 API 명세가 있으면 응답 구조를 맞춘다
- plan.md의 수용 기준(Given-When-Then)을 기반으로 테스트 시나리오를 작성한다
- 테스트는 행동(behavior) 중심으로 작성한다 (CSS 색상값 등 세부 스타일 검증 금지)"
subagent_type: playwright-e2e-tester
```

### Step 6: 구현 (TDD)

1. **먼저** `specs/{feature}/implementation-guide.md`를 읽는다
    - implementation-guide.md에 기존 패턴, 파일 경로, 재사용할 함수/컴포넌트가 이미 분석되어 있다
    - **추가 탐색 없이** 가이드에 명시된 패턴과 경로를 그대로 따라 구현한다
    - 가이드에 없는 정보가 필요한 경우에만 추가 파일을 읽는다
2. `specs/{feature}/plan.md`도 참조
3. implementation-guide.md의 구현 순서를 기반으로 TodoWrite로 태스크 생성
4. TDD 방식:
    - `npm test` 실행 → 실패 확인
    - 구현 코드 작성
    - `npm test` 재실행 → 통과 확인
5. 모든 테스트 통과할 때까지 반복

### Step 7: 테스트 정리 (test-consolidator)

모든 테스트가 통과하면 자동으로 실행한다.

```
prompt: "tests/{feature}/ 디렉토리의 테스트 코드를 정리해줘.
specs/{feature}/plan.md의 수용 기준을 참조하여 시나리오 기반으로 통합한다.

정리 규칙:
- TDD 과정에서 생성된 세분화된 테스트를 사용자 시나리오 단위로 통합
- 중복/불필요한 테스트 제거
- Given-When-Then 패턴의 시나리오 테스트로 리팩토링
- 목업 데이터(tests/mocks/{feature}.mock.ts)도 함께 정리"
subagent_type: test-consolidator
```

## 산출물 구조

```
specs/
└── {feature}/
    ├── plan.md                 # Step 1: 기획 명세서 (무엇을/왜)
    ├── implementation-guide.md # Step 3: 구현 가이드 (어떻게)
    └── api-spec.md             # Step 3: API 명세서 (선택, 제공된 경우)

tests/
├── mocks/
│   └── {feature}.mock.ts      # Step 5: 목업 데이터
└── {feature}/
    └── *.spec.ts               # Step 5→7: 테스트 코드 (최종 정리됨)

src/
└── ...                         # Step 6: 구현 코드
```

## 예시

```
/feature license-management

→ Step 1: specs/license-management/plan.md 생성 (기획)
→ Step 2: 사용자 검토 및 확인
→ Step 3: specs/license-management/implementation-guide.md 생성 (설계 + API 명세 확인)
→ Step 4: 사용자 검토 및 확인
→ Step 5: tests/license-management/*.spec.ts 생성 (테스트 코드)
→ Step 6: 구현 및 테스트 통과
→ Step 7: 테스트 코드 정리
```

## 주의사항

- Step 2, Step 4에서 사용자 확인 없이 다음 단계로 진행하지 않는다
- plan.md에 기술 구현 명세(인터페이스, API 상세 설계, 컴포넌트 구조)를 포함하지 않는다
- 테스트 코드는 실제 API 존재 여부와 관계없이 항상 page.route() 인터셉트 + 목업 데이터를 사용한다
- Step 6은 TDD 방식을 엄격히 따른다
- Step 6 구현 시 implementation-guide.md를 반드시 참조한다
- Step 7은 모든 테스트 통과 후 자동으로 실행한다
- {feature}는 케밥케이스로 작성 (예: license-management, user-profile)
