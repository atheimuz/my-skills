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
prompt: "{feature} 기능에 대한 기획 명세서를 작성해줘. specs/{feature}/plan.md에 저장해줘."
subagent_type: product-spec-writer
```

### Phase 2: 검토 (Blocking)

1. plan.md 내용을 사용자에게 표시
2. AskUserQuestion으로 확인 요청:
   - "기획 명세서 검토가 완료되었나요?"
   - 옵션: "확인, 진행해줘" / "수정 필요"
3. 수정 필요시 Phase 1로 돌아감

### Phase 3: 병렬 실행

Task tool 2개 동시 실행 (단일 메시지에 2개 Task tool call):

**Task 1 - ui-designer:**
```
prompt: "specs/{feature}/plan.md를 읽고 specs/{feature}/design.md를 작성해줘."
subagent_type: ui-designer
```

**Task 2 - playwright-e2e-tester:**
```
prompt: "specs/{feature}/plan.md를 읽고 테스트 시나리오와 테스트 코드를 작성해줘.
- specs/{feature}/test-scenarios.md
- tests/{feature}/*.spec.ts"
subagent_type: playwright-e2e-tester
```

### Phase 4: 구현

1. plan.md + design.md + test-scenarios.md 참조
2. TDD 방식:
   - `npm test` 실행 → 실패 확인
   - 구현 코드 작성
   - `npm test` 재실행 → 통과 확인
3. 모든 테스트 통과할 때까지 반복

## 산출물 구조

```
specs/
└── {feature}/
    ├── plan.md              # Phase 1: 기획 명세서
    ├── design.md            # Phase 3: 디자인 명세서
    └── test-scenarios.md    # Phase 3: 테스트 시나리오

tests/
└── {feature}/
    └── *.spec.ts            # Phase 3: 테스트 코드

src/
└── ...                      # Phase 4: 구현 코드
```

## 예시

```
/feature license-management

→ Phase 1: specs/license-management/plan.md 생성
→ Phase 2: 사용자 검토 및 확인
→ Phase 3:
   - specs/license-management/design.md
   - specs/license-management/test-scenarios.md
   - tests/license-management/*.spec.ts
→ Phase 4: 구현 및 테스트 통과
```

## 주의사항

- Phase 2에서 사용자 확인 없이 다음 단계로 진행하지 않는다
- Phase 3의 두 에이전트는 반드시 병렬로 실행한다 (단일 메시지에 2개 Task call)
- Phase 4는 TDD 방식을 엄격히 따른다
- {feature}는 케밥케이스로 작성 (예: license-management, user-profile)
