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
- 기술 제약조건/방향성 (구체적 명세는 제외)

제외할 것:
- 디자인 방향성 / 시각적 컨셉 / UX 흐름 설계 / 레이아웃 (→ Step 3 디자인 단계에서 다룸)
- 화면별 UI 요구사항 / 상태별 UI 설계 (→ Step 3 디자인 단계에서 다룸)
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

### Step 2: 사용자 컨펌 (기획)

1. plan.md에서 **TL;DR 섹션만 추출**하여 사용자에게 표시한다
2. TL;DR의 주요 결정사항 테이블과 스코프 요약을 기반으로 핵심 포인트를 정리한다
3. AskUserQuestion으로 확인 요청:
    - "기획 요약을 검토해주세요. 상세 내용은 specs/{feature}/plan.md에서 확인할 수 있습니다."
    - 옵션: "확인, 진행해줘" / "상세 내용 보고 싶어" / "수정 필요"
4. "상세 내용 보고 싶어" 선택 시 plan.md 전체 내용을 표시한다
5. 수정 필요시 Step 1로 돌아감

### Step 3: 디자인 (ux-researcher → ui-designer)

#### Step 3a: 디자인 레퍼런스 수집

AskUserQuestion으로 디자인 레퍼런스를 수집한다:
- "디자인 레퍼런스가 있으면 공유해주세요. (여러 개 가능)"
- 옵션: "URL 공유" / "이미지/스크린샷 경로 공유" / "텍스트로 설명" / "레퍼런스 없이 진행"
- 사용자가 레퍼런스를 공유하면 추가 질문: "추가 레퍼런스가 있나요?" (옵션: "추가" / "완료")
- 수집된 레퍼런스는 이후 에이전트 prompt에 삽입한다

#### Step 3b: UX 분석 (ux-researcher)

Task tool로 `ux-researcher` 에이전트 실행

```
prompt: "specs/{feature}/plan.md를 읽고 UX 분석을 수행해줘. specs/{feature}/ux-analysis.md에 저장해줘.

디자인 레퍼런스:
{수집된 레퍼런스 목록 - URL, 이미지 경로, 텍스트 설명. 없으면 '없음'}

레퍼런스가 있는 경우:
- URL은 WebFetch로 분석하여 디자인 패턴, 레이아웃, 인터랙션 특징을 추출한다
- 레퍼런스의 좋은 점과 개선할 점을 UX 관점에서 평가한다
- 분석 결과를 'UI Designer를 위한 핵심 권장사항' 섹션에 반영한다

추가 지시:
- 출력 파일명은 반드시 specs/{feature}/ux-analysis.md로 저장한다
- 레퍼런스가 제공된 경우 '디자인 레퍼런스 분석' 섹션을 추가한다"
subagent_type: ux-researcher
```

#### Step 3c: UI 디자인 (ui-designer)

Task tool로 `ui-designer` 에이전트 실행

```
prompt: "specs/{feature}/plan.md와 specs/{feature}/ux-analysis.md를 읽고 디자인 명세서를 작성해줘. specs/{feature}/design.md에 저장해줘.

디자인 레퍼런스:
{Step 3a에서 수집된 동일한 레퍼런스 목록}

작업 지시:
- plan.md의 기획 요구사항을 기반으로 디자인한다
- ux-analysis.md의 'UI Designer를 위한 핵심 권장사항' 섹션을 반드시 반영한다
- ux-analysis.md에서 식별된 Critical/Major 이슈를 디자인으로 해결한다
- 디자인 레퍼런스가 있으면 해당 레퍼런스의 디자인 패턴을 참고한다
- 레퍼런스 이미지 파일이 있으면 Read로 확인하여 시각적 패턴을 참고한다"
subagent_type: ui-designer
```

### Step 4: 사용자 컨펌 (디자인)

1. design.md에서 **TL;DR 섹션**과 **전체 레이아웃 와이어프레임**을 추출하여 사용자에게 표시한다
2. 주요 인터랙션과 반응형 설계 요약을 함께 제시한다
3. AskUserQuestion으로 확인 요청:
    - "디자인 명세를 검토해주세요. 상세 내용은 specs/{feature}/design.md에서 확인할 수 있습니다."
    - 옵션: "확인, 진행해줘" / "상세 내용 보고 싶어" / "수정 필요"
4. "상세 내용 보고 싶어" 선택 시 design.md 전체 내용을 표시한다
5. 수정 필요시 Step 3c로 돌아감

### Step 5: 설계 (code-analyst)

Task tool로 `code-analyst` 에이전트 실행

```
prompt: "specs/{feature}/plan.md를 읽고 specs/{feature}/implementation-guide.md를 생성해줘.
specs/{feature}/design.md가 존재하면 함께 읽고 디자인 명세를 구현 가이드에 반영한다.

API 명세 처리:
- 사용자에게 API 명세서가 있는지 AskUserQuestion으로 질문한다
  - 옵션: 'API 명세서 제공' / '목업 데이터로 진행'
- 'API 명세서 제공' 선택 시: 사용자가 URL/파일 경로 제공 → specs/{feature}/api-spec.md로 저장 후 반영
- '목업 데이터로 진행' 선택 시: plan.md의 요구사항을 기반으로 API 명세 리스트를 직접 작성하여 implementation-guide.md에 포함한다

implementation-guide.md 포함 내용:
- 기존 코드베이스 패턴 분석 (재사용할 함수/유틸리티 경로:라인 포함)
- 파일 구조 및 컴포넌트 구조
- API 명세 (제공된 명세 또는 생성한 목업 스펙)
- 구현 순서 (체크리스트 `- [ ]` 형식으로 작성, 의존성 표기: → 는 선행 의존, // 는 병렬 가능)

design.md 반영 규칙 (design.md가 존재하는 경우):
- design.md의 레이아웃 구조를 컴포넌트 분리 기준으로 사용한다
- design.md의 상태별 UI(로딩, 빈 상태, 에러)를 구현 항목에 포함한다
- design.md의 인터랙션 상세를 이벤트 핸들러 구현 가이드로 변환한다
- design.md의 접근성 요구사항을 구현 체크리스트에 포함한다

implementation-guide.md 작성 규칙:
- 코드 블록(\`\`\`tsx, \`\`\`ts 등)을 포함하지 않는다
- 구조, 접근방식, 파일 경로만 간결하게 기술한다
- 참고할 코드는 파일 경로만 명시하고 '해당 파일 참조'로 안내한다

문서 구조 규칙:
- 문서 최상단에 반드시 '## TL;DR' 섹션을 작성한다
- TL;DR에는 다음을 포함한다:
  - 구현 방향 요약 (3줄 이내)
  - 수정/생성 파일 목록 테이블 (| 파일 | 작업 | 재사용 패턴 |)
  - 핵심 의존성 및 재사용 함수 목록
- TL;DR만 읽어도 전체 구현 방향을 파악할 수 있어야 한다"
subagent_type: code-analyst
```

### Step 6: 사용자 컨펌 (설계)

1. implementation-guide.md에서 **TL;DR 섹션만 추출**하여 사용자에게 표시한다
2. 파일 구조, 핵심 기술 결정, 구현 순서를 요약하여 제시한다
3. AskUserQuestion으로 확인 요청:
    - "구현 설계를 검토해주세요. 상세 내용은 specs/{feature}/implementation-guide.md에서 확인할 수 있습니다."
    - 옵션: "확인, 진행해줘" / "상세 내용 보고 싶어" / "수정 필요"
4. "상세 내용 보고 싶어" 선택 시 implementation-guide.md 전체 내용을 표시한다
5. 수정 필요시 Step 5로 돌아감

### Step 7: 테스트 코드 작성 (playwright-e2e-tester)

Task tool로 `playwright-e2e-tester` 에이전트 실행

```
prompt: "specs/{feature}/plan.md와 specs/{feature}/implementation-guide.md를 읽고 TDD용 테스트를 준비해줘.

1단계: 테스트 시나리오 문서 작성
- plan.md의 수용 기준(Given-When-Then)을 기반으로 specs/{feature}/test-scenarios.md를 작성한다
- 각 시나리오를 체크리스트(- [ ]) 형태로 작성한다

2단계: 테스트 코드 구현
- test-scenarios.md의 모든 항목에 대해 테스트 코드를 작성한다
- 산출물:
  - tests/mocks/{feature}.mock.ts (목업 데이터)
  - tests/{feature}/*.spec.ts (테스트 코드)
  - tests/page-objects/{feature}.page.ts (Page Object)

테스트 규칙:
- 실제 API 존재 여부와 관계없이 항상 목업 데이터를 사용한다
- 목업 데이터는 tests/mocks/{feature}.mock.ts에 정의한다
- Playwright page.route()로 API 호출을 인터셉트하고 목업 데이터를 반환한다
- implementation-guide.md에 API 명세가 있으면 응답 구조를 맞춘다
- 테스트는 행동(behavior) 중심으로 작성한다 (CSS 색상값 등 세부 스타일 검증 금지)"
subagent_type: playwright-e2e-tester
```

### Step 8: 구현 (TDD)

1. **먼저** `specs/{feature}/implementation-guide.md`를 읽는다
    - implementation-guide.md에 기존 패턴, 파일 경로, 재사용할 함수/컴포넌트가 이미 분석되어 있다
    - **추가 탐색 없이** 가이드에 명시된 패턴과 경로를 그대로 따라 구현한다
    - 가이드에 없는 정보가 필요한 경우에만 추가 파일을 읽는다
2. `specs/{feature}/plan.md`도 참조
3. `specs/{feature}/design.md`가 존재하면 참조 (레이아웃, 상태별 UI, 접근성 확인용)
4. implementation-guide.md의 구현 순서(체크리스트)를 기반으로 TodoWrite로 태스크 생성
5. TDD 방식:
    - `npm test` 실행 → 실패 확인
    - 구현 코드 작성
    - `npm test` 재실행 → 통과 확인
6. **각 구현 항목 완료 시 implementation-guide.md의 해당 체크박스를 `- [x]`로 업데이트한다**
    - 구현 + 테스트 통과가 확인된 항목만 체크한다
    - Edit 도구로 `- [ ]`를 `- [x]`로 변경한다
7. 모든 테스트 통과하고 모든 체크박스가 체크될 때까지 반복

### Step 9: 테스트 정리 (test-consolidator)

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
    ├── ux-analysis.md          # Step 3b: UX 분석 보고서
    ├── design.md               # Step 3c: 디자인 명세서
    ├── implementation-guide.md # Step 5: 구현 가이드 (어떻게)
    ├── api-spec.md             # Step 5: API 명세서 (선택, 제공된 경우)
    └── test-scenarios.md       # Step 7: 테스트 시나리오 문서

tests/
├── mocks/
│   └── {feature}.mock.ts      # Step 7: 목업 데이터
└── {feature}/
    └── *.spec.ts               # Step 7→9: 테스트 코드 (최종 정리됨)

src/
└── ...                         # Step 8: 구현 코드
```

## 예시

```
/feature license-management

→ Step 1: specs/license-management/plan.md 생성 (기획)
→ Step 2: 사용자 검토 및 확인 (기획)
→ Step 3: 디자인 레퍼런스 수집 → UX 분석 → 디자인 명세서 생성
→ Step 4: 사용자 검토 및 확인 (디자인)
→ Step 5: specs/license-management/implementation-guide.md 생성 (설계 + API 명세 확인)
→ Step 6: 사용자 검토 및 확인 (설계)
→ Step 7: tests/license-management/*.spec.ts 생성 (테스트 코드)
→ Step 8: 구현 및 테스트 통과
→ Step 9: 테스트 코드 정리
```

## 주의사항

- Step 2, Step 4, Step 6에서 사용자 확인 없이 다음 단계로 진행하지 않는다
- plan.md에 기술 구현 명세(인터페이스, API 상세 설계, 컴포넌트 구조)를 포함하지 않는다
- Step 3a의 디자인 레퍼런스 URL은 ux-researcher가 WebFetch로 직접 분석한다
- Step 3c의 ui-designer는 ux-analysis.md의 권장사항을 반드시 반영한다
- Step 5의 code-analyst는 design.md가 존재하면 반드시 참조한다
- 테스트 코드는 실제 API 존재 여부와 관계없이 항상 page.route() 인터셉트 + 목업 데이터를 사용한다
- Step 8은 TDD 방식을 엄격히 따른다
- Step 8 구현 시 implementation-guide.md를 반드시 참조하고, design.md가 존재하면 함께 참조한다
- Step 9는 모든 테스트 통과 후 자동으로 실행한다
- {feature}는 케밥케이스로 작성 (예: license-management, user-profile)
